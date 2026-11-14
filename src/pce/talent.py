"""Expected matchup value (E2, DESIGN.md section 2.2).

For every plate appearance: the wOBA expected from the batter's and pitcher's hand-specific
talent, estimated from the three *prior* seasons only, so that a PA's own outcome never
enters its expectation.

    talent  = empirical-Bayes shrinkage of (a) overall wOBA and (b) platoon split, each toward
              the mean of the player's group (batting side, or throwing hand x role)
    e2      = batter talent vs. this pitcher's hand
              + (pitcher talent vs. this batter's side - average pitcher of his hand vs. that side)
                                                             (additive; effects here are small)
    e2_starter = same, but with the slot's *starter* as the batter, whoever actually hit

Shrinkage variances are method-of-moments estimates pooled over all seasons. Players with no
prior data get their group mean, which flatters rookies; fixed effects absorb level errors.

Outputs data/processed/talent_bat.parquet, talent_pit.parquet, pa_e2.parquet
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CFG, PROCESSED

W = CFG["talent"]["season_weights"]


def _weighted_prior(agg: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Sum prior seasons with Marcel-style weights. agg: keys + season, num, den."""
    parts = []
    for lag, w in enumerate(W, start=1):
        a = agg.copy()
        a["season"] = a.season + lag
        a["num"] *= w / W[0]
        a["den"] *= w / W[0]
        parts.append(a)
    return pd.concat(parts).groupby(keys + ["season"], as_index=False)[["num", "den"]].sum()


def _shrink(obs, n, grp, sigma2):
    """Empirical-Bayes shrinkage of obs (with effective sample n) toward its group mean."""
    df = pd.DataFrame({"obs": obs, "n": n, "grp": grp})
    out = pd.Series(np.nan, index=df.index)
    info = []
    for g, d in df.groupby("grp"):
        ok = d.n > 0
        if ok.sum() == 0:
            continue
        w = d.n[ok]
        mu = np.average(d.obs[ok], weights=w)
        big = ok & (d.n >= 50)                      # moments from reasonably sized samples
        var_obs = np.average((d.obs[big] - mu) ** 2, weights=d.n[big])
        var_true = max(var_obs - sigma2 * np.average(1 / d.n[big], weights=d.n[big]), 1e-8)
        b = var_true / (var_true + sigma2 / d.n.where(ok, np.nan))
        out[d.index] = (mu + b * (d.obs - mu)).fillna(mu)
        info.append({"group": g, "mean": mu, "sd_true": var_true ** 0.5,
                     "n_half_shrunk": sigma2 / var_true})
    return out, pd.DataFrame(info)


def _talent(pa: pd.DataFrame, who: str, vs: str, group: pd.DataFrame, sigma2: float):
    """who: id column; vs: opposing-hand column (values L/R); group: season, id -> grp."""
    agg = (pa.groupby([who, "season", vs], as_index=False)
           .agg(num=("woba_num", "sum"), den=("woba_den", "sum")))
    pr = _weighted_prior(agg, [who, vs])
    wide = pr.pivot(index=[who, "season"], columns=vs, values=["num", "den"]).fillna(0.0)
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    cur = group.merge(wide, on=[who, "season"], how="left").fillna(
        {c: 0.0 for c in ["num_L", "num_R", "den_L", "den_R"]})
    n = cur.den_L + cur.den_R
    overall = (cur.num_L + cur.num_R) / n.where(n > 0)
    rL = cur.num_L / cur.den_L.where(cur.den_L > 0)
    rR = cur.num_R / cur.den_R.where(cur.den_R > 0)
    n_split = 1 / (1 / cur.den_L.where(cur.den_L > 0) + 1 / cur.den_R.where(cur.den_R > 0))
    cur["overall"], i1 = _shrink(overall, n.fillna(0), cur.grp, sigma2)
    cur["split"], i2 = _shrink(rR - rL, n_split.fillna(0), cur.grp, sigma2)   # vs R minus vs L
    # own mix of opposing hands; group mix when unseen
    pL = (cur.den_L / n.where(n > 0))
    gL = cur.groupby("grp").den_L.transform("sum")
    gR = cur.groupby("grp").den_R.transform("sum")
    pL = pL.fillna(gL / (gL + gR).clip(lower=1))
    cur["vs_L"] = cur.overall - (1 - pL) * cur.split
    cur["vs_R"] = cur.overall + pL * cur.split
    cur["prior_n"] = n
    info = i1.merge(i2, on="group", suffixes=("_overall", "_split"))
    return cur[[who, "season", "grp", "prior_n", "overall", "split", "vs_L", "vs_R"]], info


def main() -> None:
    pa = pd.read_parquet(PROCESSED / "pa.parquet")
    players = pd.read_parquet(PROCESSED / "players.parquet")
    ap = pd.read_parquet(PROCESSED / "appearances.parquet")
    sigma2 = pa.loc[pa.woba_den == 1, "woba_num"].var()

    # batters: group = batting side, pitchers batting kept apart
    bg = players[["season", "player_id", "bats", "pos", "season_pa"]].rename(columns={"player_id": "bat_id"})
    bg["grp"] = np.where((bg.pos == "P") & (bg.season_pa < CFG["definitions"]["two_way_min_pa"]),
                         "pitcher", "bats_" + bg.bats.astype(str))
    bat, bat_info = _talent(pa.rename(columns={"pit_hand_cd": "vs"}), "bat_id", "vs",
                            bg[["season", "bat_id", "grp"]], sigma2)

    # pitchers: group = throwing hand x current-season role
    role = ap.groupby(["season", "pit_id"]).is_starter.mean().rename("ss").reset_index()
    pg = players[["season", "player_id", "throws"]].rename(columns={"player_id": "pit_id"}).merge(
        role, on=["season", "pit_id"])
    pg["grp"] = "throws_" + pg.throws.astype(str) + np.where(pg.ss >= 0.5, "_starter", "_reliever")
    pit_pa = pa[pa.bat_hand_cd.isin(["L", "R"])].rename(columns={"bat_hand_cd": "vs"})
    pit, pit_info = _talent(pit_pa, "pit_id", "vs", pg[["season", "pit_id", "grp"]], sigma2)

    bat.to_parquet(PROCESSED / "talent_bat.parquet", index=False)
    pit.to_parquet(PROCESSED / "talent_pit.parquet", index=False)
    pd.concat([bat_info.assign(kind="batter"), pit_info.assign(kind="pitcher")]).to_parquet(
        PROCESSED / "talent_shrinkage.parquet", index=False)

    # attach to PAs
    key = ["season", "game_id", "event_id"]
    x = pa[key + ["bat_id", "starter_id", "pit_id", "pit_hand_cd", "bat_hand_cd"]].copy()
    b = bat.set_index(["bat_id", "season"])
    p = pit.set_index(["pit_id", "season"])

    def look(tab, ids, hand):
        idx = pd.MultiIndex.from_arrays([ids, x.season])
        vl = tab.vs_L.reindex(idx).to_numpy()
        vr = tab.vs_R.reindex(idx).to_numpy()
        return np.where(hand.to_numpy() == "L", vl, vr)

    # The batter's talent vs. this hand already contains the average platoon effect of pitchers
    # of that hand, so the pitcher enters as a deviation from the average pitcher of his hand
    # against this batting side (PA-weighted, same season). Adding raw pitcher talent instead
    # would count the platoon effect twice.
    def centred(part, side):
        cell = pd.DataFrame({"v": part, "s": x.season.to_numpy(), "ph": x.pit_hand_cd.to_numpy(),
                             "bh": np.asarray(side)})
        return part - cell.groupby(["s", "ph", "bh"]).v.transform("mean").to_numpy()

    bat_part = look(b, x.bat_id, x.pit_hand_cd)
    pit_part = centred(look(p, x.pit_id, x.bat_hand_cd), x.bat_hand_cd)
    x["e2"] = bat_part + pit_part
    # starter as batter: his side against this pitcher (switch hitters take the far side)
    sb = players.set_index(["season", "player_id"]).bats.reindex(
        pd.MultiIndex.from_arrays([x.season, x.starter_id])).to_numpy()
    side = np.where(sb == "S", np.where(x.pit_hand_cd == "L", "R", "L"), sb)
    pit_vs_starter = centred(look(p, x.pit_id, pd.Series(side, index=x.index)), side)
    x["e2_starter"] = look(b, x.starter_id, x.pit_hand_cd) + pit_vs_starter
    x["pit_talent_vs_bat"] = pit_part
    x["bat_overall"] = b.overall.reindex(pd.MultiIndex.from_arrays([x.bat_id, x.season])).to_numpy()
    x[key + ["e2", "e2_starter", "pit_talent_vs_bat", "bat_overall"]].to_parquet(
        PROCESSED / "pa_e2.parquet", index=False)
    print(f"sigma2 per PA {sigma2:.4f}; e2 missing {x.e2.isna().mean():.4%}; "
          f"e2_starter missing {x.e2_starter.isna().mean():.4%}")
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(pd.concat([bat_info.assign(kind="batter"), pit_info.assign(kind="pitcher")]).to_string(index=False))


if __name__ == "__main__":
    main()
