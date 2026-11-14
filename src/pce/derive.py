"""Derived tables (DESIGN.md section 4.3). Accounting only: no models are fitted here.

Outputs in data/processed/:
  players.parquet      player-season: bats, throws, listed position, season PA
  lineup.parquet       team-game-slot: starter, started type (L/R/S/P)
  team_game.parquet    team-game: lineup string, handedness counts, opposing starter,
                       opposing bullpen supply
  weights.parquet      season: linear weights and wOBA scale derived from run expectancy
  pa.parquet           plate appearance: context, pitcher, neighbors, wOBA value
  appearances.parquet  pitcher-game: role, entry state, batters faced

Handedness "type" of a lineup slot, from the point of view of a manager weighing a
left-handed reliever:
  L  bats left only            (platoon disadvantage vs LHP)
  R  bats right only
  S  switch hitter             (bats right vs LHP)
  P  pitcher batting
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CFG, INTERIM, PROCESSED, SEASONS, era

DEFS = CFG["definitions"]


def _load(name: str) -> pd.DataFrame:
    return pd.concat(
        [pd.read_parquet(INTERIM / f"{name}_{s}.parquet") for s in SEASONS], ignore_index=True
    )


# --------------------------------------------------------------------------- players
def build_players(ev: pd.DataFrame) -> pd.DataFrame:
    ros = _load("roster")
    # One row per player-season; a traded player has identical bats/throws on each team.
    ros = ros.sort_values(["season", "player_id"]).drop_duplicates(["season", "player_id"])
    pa = (ev[ev.bat_event_fl].groupby(["season", "bat_id"]).size()
          .rename("season_pa").reset_index().rename(columns={"bat_id": "player_id"}))
    out = ros.merge(pa, how="left", on=["season", "player_id"])
    out["season_pa"] = out["season_pa"].fillna(0).astype(int)
    out["bats"] = out["bats"].replace({"B": "S"})
    return out[["season", "player_id", "bats", "throws", "pos", "season_pa"]]


# --------------------------------------------------------------------------- lineups
def build_lineup(games: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for side in ("away", "home"):
        for slot in range(1, 10):
            parts.append(pd.DataFrame({
                "season": games.season,
                "game_id": games.game_id,
                "team": games[f"{side}_team_id"],
                "is_home": int(side == "home"),
                "slot": slot,
                "starter_id": games[f"{side}_lineup{slot}_bat_id"],
                "starter_fld": games[f"{side}_lineup{slot}_fld_cd"],
            }))
    lu = pd.concat(parts, ignore_index=True)
    lu = lu.merge(
        players[["season", "player_id", "bats", "season_pa"]],
        how="left", left_on=["season", "starter_id"], right_on=["season", "player_id"],
    ).drop(columns="player_id")
    is_pitcher = (lu.starter_fld == 1) & (lu.season_pa < DEFS["two_way_min_pa"])
    lu["stype"] = np.where(is_pitcher, "P", lu.bats)
    return lu.drop(columns=["bats", "season_pa"])


def _type_matrix(lu: pd.DataFrame) -> pd.DataFrame:
    """team-game x slot matrix of started types, columns 1..9."""
    return lu.pivot(index=["game_id", "team"], columns="slot", values="stype")


# --------------------------------------------------------------------------- weights
def build_weights(ev: pd.DataFrame) -> pd.DataFrame:
    """Linear weights from run expectancy, per season, computed from these events only.

    Run expectancy uses innings 1-8 so that walk-off truncation and the extra-inning
    automatic runner (2020+) do not enter. wOBA scale sets league wOBA equal to league OBP.
    """
    rows = []
    for season, e in ev.groupby("season"):
        full = e[e.inn_ct <= 8]
        re = (full.assign(rest=full.event_runs_ct + full.fate_runs_ct)
              .groupby(["start_bases_cd", "outs_ct"]).rest.mean())
        start = pd.MultiIndex.from_arrays([e.start_bases_cd, e.outs_ct])
        end_outs = e.outs_ct + e.event_outs_ct
        end = pd.MultiIndex.from_arrays([e.end_bases_cd, end_outs])
        re_end = np.where(end_outs >= 3, 0.0, re.reindex(end).to_numpy())
        rv = re_end - re.reindex(start).to_numpy() + e.event_runs_ct.to_numpy()
        b = e.assign(rv=rv)[e.bat_event_fl & (e.inn_ct <= 8)]
        kind = _event_kind(b)
        m = b.groupby(kind).rv.mean()
        out_rv = m["out"]
        w = {k: m[k] - out_rv for k in ("bb", "hbp", "1b", "2b", "3b", "hr")}
        allb = e[e.bat_event_fl]
        k_all = _event_kind(allb)
        n = k_all.value_counts()
        denom = n.reindex(["out", "bb", "hbp", "1b", "2b", "3b", "hr"]).sum() + allb.sf_fl.sum()
        raw = sum(w[k] * n[k] for k in w) / denom
        on_base = n.reindex(["bb", "ibb", "hbp", "1b", "2b", "3b", "hr"]).sum()
        obp = on_base / (denom + n.get("ibb", 0))
        scale = obp / raw
        rows.append({"season": season, **{f"w_{k}": w[k] * scale for k in w},
                     "woba_scale": scale, "lg_woba": obp, "run_value_out": out_rv,
                     "runs_per_pa": (allb.event_runs_ct.sum()) / len(allb)})
    return pd.DataFrame(rows)


def _event_kind(b: pd.DataFrame) -> pd.Series:
    """Batting-event class. 'out' = at-bat without a hit (includes errors, fielder's choice).

    'other' = sacrifice bunts and interference, which are outside the wOBA denominator.
    Sacrifice flies are at-bat-less outs that *are* in the denominator; they are counted
    separately by the caller via sf_fl.
    """
    cd = b.event_cd
    k = pd.Series("other", index=b.index)
    k[b.ab_fl & (b.h_cd == 0)] = "out"
    k[cd == 14] = "bb"
    k[cd == 15] = "ibb"
    k[cd == 16] = "hbp"
    k[cd == 20] = "1b"
    k[cd == 21] = "2b"
    k[cd == 22] = "3b"
    k[cd == 23] = "hr"
    k[b.sf_fl] = "sf"
    return k


# --------------------------------------------------------------------------- PA table
def build_pa(ev, games, players, lu, weights) -> pd.DataFrame:
    pa = ev[ev.bat_event_fl].copy()
    pa = pa.rename(columns={"bat_team_id": "bat_team", "fld_team_id": "fld_team",
                            "bat_lineup_id": "slot", "inn_ct": "inning", "outs_ct": "outs",
                            "start_bases_cd": "bases"})
    g = games[["game_id", "game_dt", "away_team_id", "home_team_id",
               "away_start_pit_id", "home_start_pit_id"]]
    pa = pa.merge(g, on="game_id", how="left")
    pa["date"] = pd.to_datetime(pa.game_dt.astype(str), format="%Y%m%d")
    home_bat = pa.bat_home_id == 1
    pa["fld_starter_id"] = np.where(home_bat, pa.away_start_pit_id, pa.home_start_pit_id)
    pa["score_diff"] = np.where(home_bat, pa.home_score_ct - pa.away_score_ct,
                                pa.away_score_ct - pa.home_score_ct)
    pa["vs_starter"] = pa.pit_id == pa.fld_starter_id
    pa["era"] = pa.season.map(era)

    # order within game, and pitcher's batters-faced count before this PA
    pa = pa.sort_values(["season", "game_id", "event_id"]).reset_index(drop=True)
    pa["pit_bf_before"] = pa.groupby(["game_id", "pit_id"]).cumcount()
    pa["tto"] = pa.pit_bf_before // 9 + 1

    # pitcher hand / role
    pit = players[["season", "player_id", "pos"]].rename(columns={"player_id": "pit_id", "pos": "pit_pos"})
    pa = pa.merge(pit, on=["season", "pit_id"], how="left")
    pa["pit_is_position_player"] = pa.pit_pos.ne("P") & pa.pit_pos.notna() & ~pa.vs_starter
    pa["vs_lhp"] = pa.pit_hand_cd == "L"

    # the slot's starter and started type
    s = lu[["game_id", "team", "slot", "starter_id", "stype"]].rename(
        columns={"team": "bat_team", "stype": "slot_stype"})
    pa = pa.merge(s, on=["game_id", "bat_team", "slot"], how="left")
    pa["starter_batting"] = pa.bat_id == pa.starter_id

    # neighbors as started (the intent-to-treat treatment)
    tm = _type_matrix(lu)
    key = pd.MultiIndex.from_arrays([pa.game_id, pa.bat_team])
    tmat = tm.reindex(key).to_numpy()
    slot0 = pa.slot.to_numpy() - 1
    rows = np.arange(len(pa))
    for name, off in (("next1", 1), ("next2", 2), ("prev1", -1), ("prev2", -2)):
        pa[f"{name}_s"] = tmat[rows, (slot0 + off) % 9]
    is_L = (tmat == "L")
    pa["n_L_lineup"] = is_L.sum(axis=1)
    pa["n_L_others"] = pa.n_L_lineup - is_L[rows, slot0]

    # neighbors as currently in the game: last batter seen in that slot, else the starter.
    # (A defensive substitute who has not yet batted is not seen; documented approximation.)
    bats = players.set_index(["season", "player_id"]).bats
    # A batter fielding at pitcher is type P, unless he is a two-way starter typed as a hitter.
    pa["cur_type"] = np.where(
        (pa.bat_fld_cd == 1) & ~(pa.starter_batting & pa.slot_stype.ne("P")),
        "P",
        bats.reindex(pd.MultiIndex.from_arrays([pa.season, pa.bat_id])).to_numpy(),
    )
    pa["ord"] = np.arange(len(pa))
    seen = pa[["ord", "game_id", "bat_team", "slot", "cur_type"]].rename(
        columns={"slot": "tslot", "cur_type": "seen_type"})
    for name, off in (("next1", 1), ("next2", 2), ("prev1", -1)):
        q = pa[["ord", "game_id", "bat_team"]].copy()
        q["tslot"] = (slot0 + off) % 9 + 1
        m = pd.merge_asof(q, seen, on="ord", by=["game_id", "bat_team", "tslot"],
                          direction="backward", allow_exact_matches=False)
        pa[f"{name}_c"] = m.seen_type.fillna(pa[f"{name}_s"]).to_numpy()

    # wOBA value of the PA
    kind = _event_kind(pa)
    w = weights.set_index("season")
    val = np.zeros(len(pa))
    for k in ("bb", "hbp", "1b", "2b", "3b", "hr"):
        val = np.where(kind == k, pa.season.map(w[f"w_{k}"]).to_numpy(), val)
    pa["event_kind"] = kind.to_numpy()
    pa["woba_den"] = (~kind.isin(["ibb", "other"])).to_numpy().astype(np.int8)
    pa["woba_num"] = val * pa.woba_den

    keep = ["season", "era", "date", "game_id", "event_id", "bat_team", "fld_team", "inning",
            "bat_home_id", "outs", "bases", "score_diff", "slot", "bat_id", "bat_hand_cd",
            "starter_id", "starter_batting", "slot_stype", "cur_type", "ph_fl",
            "pit_id", "pit_hand_cd", "vs_lhp", "vs_starter", "pit_bf_before", "tto",
            "pit_is_position_player", "next1_s", "next2_s", "prev1_s", "prev2_s",
            "next1_c", "next2_c", "prev1_c", "n_L_lineup", "n_L_others",
            "event_kind", "event_outs_ct", "inn_pa_ct", "woba_num", "woba_den"]
    return pa[keep]


# --------------------------------------------------------------------------- appearances
def build_appearances(pa: pd.DataFrame) -> pd.DataFrame:
    """One row per pitcher-game, from the plate appearances he completed."""
    g = pa.groupby(["season", "game_id", "fld_team", "pit_id"], sort=False)
    first = g.head(1).set_index(["season", "game_id", "fld_team", "pit_id"])
    last = g.tail(1).set_index(["season", "game_id", "fld_team", "pit_id"])
    ap = pd.DataFrame({
        "date": first.date,
        "era": first.era,
        "throws": first.pit_hand_cd,
        "is_starter": first.vs_starter,
        "position_player": first.pit_is_position_player,
        "entry_inning": first.inning,
        "entry_outs": first.outs,
        "entry_bases": first.bases,
        "entry_mid_inning": first.inn_pa_ct > 0,
        "entry_score_diff": -first.score_diff,       # from the pitching team's side
        "first_bat_hand": first.bat_hand_cd,
        "first_slot_stype": first.slot_stype,
        "first_bat_starter": first.starter_batting,
        "first_next1_c": first.next1_c,
        "first_next2_c": first.next2_c,
        "first_next1_s": first.next1_s,
        "first_next2_s": first.next2_s,
        "bf": g.size(),
        "bf_vs_L": pa.assign(x=pa.bat_hand_cd.eq("L")).groupby(
            ["season", "game_id", "fld_team", "pit_id"], sort=False).x.sum(),
        "exit_ended_inning": (last.outs + last.event_outs_ct) >= 3,
    }).reset_index()
    # last pitcher of the game for his team
    lastpit = pa.groupby(["game_id", "fld_team"], sort=False).pit_id.last().rename("last_pit")
    ap = ap.merge(lastpit, on=["game_id", "fld_team"])
    ap["finished_game"] = ap.pit_id == ap.last_pit
    # An outing the three-batter minimum would not allow absent injury: fewer than three
    # batters, not ending a half-inning, not the end of the game.
    ap["short_stint"] = (ap.bf < 3) & ~ap.exit_ended_inning & ~ap.finished_game
    return ap.drop(columns="last_pit")


# --------------------------------------------------------------------------- bullpen supply
def build_bullpen(ap: pd.DataFrame) -> pd.DataFrame:
    """Per team-date: relievers seen in relief for this team in the trailing window.

    Window excludes the game day itself, so today's usage never defines today's supply.
    `rested` additionally requires no appearance on the previous calendar day.
    """
    win = DEFS["bullpen_window_days"]
    rel = ap[~ap.is_starter & ~ap.position_player]
    out = []
    for (season, team), d in rel.groupby(["season", "fld_team"]):
        days = pd.date_range(d.date.min(), d.date.max(), freq="D")
        res = pd.DataFrame(index=days)
        for hand, col in (("L", "lhp"), ("R", "rhp")):
            m = (d[d.throws == hand].assign(one=1)
                 .pivot_table(index="date", columns="pit_id", values="one", aggfunc="max")
                 .reindex(days).fillna(0))
            if m.shape[1] == 0:
                res[f"pen_{col}"] = 0
                res[f"pen_{col}_rested"] = 0
                continue
            seen = m.rolling(win, min_periods=1).max().shift(1).fillna(0)
            yday = m.shift(1).fillna(0)
            res[f"pen_{col}"] = seen.sum(axis=1).astype(int)
            res[f"pen_{col}_rested"] = ((seen > 0) & (yday == 0)).sum(axis=1).astype(int)
        res["season"], res["team"] = season, team
        res["days_into_season"] = np.arange(len(res))
        out.append(res.rename_axis("date").reset_index())
    return pd.concat(out, ignore_index=True)


def build_team_game(games, lu, players, bullpen) -> pd.DataFrame:
    tm = _type_matrix(lu)
    tg = pd.DataFrame({
        "lineup_types": tm.apply(lambda r: "".join(r.fillna("?")), axis=1),
        "n_L": (tm == "L").sum(axis=1), "n_R": (tm == "R").sum(axis=1),
        "n_S": (tm == "S").sum(axis=1), "n_P": (tm == "P").sum(axis=1),
    }).reset_index()
    g = games[["season", "game_id", "game_dt", "away_team_id", "home_team_id",
               "away_start_pit_id", "home_start_pit_id"]]
    a = g.rename(columns={"away_team_id": "team", "home_team_id": "opp",
                          "home_start_pit_id": "opp_starter_id"}).assign(is_home=0)
    h = g.rename(columns={"home_team_id": "team", "away_team_id": "opp",
                          "away_start_pit_id": "opp_starter_id"}).assign(is_home=1)
    cols = ["season", "game_id", "game_dt", "team", "opp", "opp_starter_id", "is_home"]
    tg = tg.merge(pd.concat([a[cols], h[cols]]), on=["game_id", "team"])
    tg["date"] = pd.to_datetime(tg.game_dt.astype(str), format="%Y%m%d")
    thr = players[["season", "player_id", "throws"]].rename(
        columns={"player_id": "opp_starter_id", "throws": "opp_starter_throws"})
    tg = tg.merge(thr, on=["season", "opp_starter_id"], how="left")
    bp = bullpen.rename(columns={"team": "opp"}).add_prefix("opp_").rename(
        columns={"opp_opp": "opp", "opp_date": "date", "opp_season": "season"})
    tg = tg.merge(bp, on=["season", "opp", "date"], how="left")
    tg["era"] = tg.season.map(era)
    return tg.drop(columns="game_dt")


# --------------------------------------------------------------------------- main
def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ev = _load("events")
    games = _load("games")
    print(f"events {len(ev):,}  games {len(games):,}")

    players = build_players(ev)
    players.to_parquet(PROCESSED / "players.parquet", index=False)

    lu = build_lineup(games, players)
    lu.to_parquet(PROCESSED / "lineup.parquet", index=False)

    weights = build_weights(ev)
    weights.to_parquet(PROCESSED / "weights.parquet", index=False)

    pa = build_pa(ev, games, players, lu, weights)
    del ev
    ap = build_appearances(pa)
    ap.to_parquet(PROCESSED / "appearances.parquet", index=False)

    bullpen = build_bullpen(ap)
    tg = build_team_game(games, lu, players, bullpen)
    tg.to_parquet(PROCESSED / "team_game.parquet", index=False)

    opp = tg[["game_id", "team", "opp_starter_throws", "opp_pen_lhp", "opp_pen_lhp_rested",
              "opp_pen_rhp", "opp_days_into_season"]].rename(columns={"team": "bat_team"})
    pa = pa.merge(opp, on=["game_id", "bat_team"], how="left")
    pa.to_parquet(PROCESSED / "pa.parquet", index=False)
    print(f"pa {len(pa):,}  appearances {len(ap):,}  team-games {len(tg):,}")


if __name__ == "__main__":
    main()
