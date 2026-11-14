"""Phase 3 shared modelling code: analysis frame, fixed-effects fits, unit conversions.

All models are linear with high-dimensional fixed effects (pyfixest), standard errors
clustered by game unless stated. Outcomes:
  vs_lhp      E1  pitcher is left-handed (linear probability)
  e2          E2  expected matchup wOBA of whoever batted in the slot (primary; includes pinch hitters)
  e2_starter      expected matchup wOBA had the slot's starter batted (isolates the pitcher faced)
  woba        E3  realized wOBA value (validation; underpowered by design)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyfixest as pf

from .config import PROCESSED
from .describe import pool

SESOI_WOBA = 0.002     # DESIGN.md section 3: 1 run per 600 PA
SESOI_PP = 2.0

# Fixed effects of the primary specification (DESIGN.md section 5.1):
#   bs_sh   batter(slot starter) x season x opposing starter hand
#   opp_ts  opposing team x season
FE = "bs_sh + opp_ts + slot + inning_c + outs_bases + score_c + bat_home_id"
CONTROLS = "n_L_else + next1_q + next2_q + pen_lhp_c"


def frame(first: int = 2000, last: int = 2025) -> pd.DataFrame:
    """One row per PA with outcomes, neighbor indicators and fixed-effect keys."""
    pa = pd.read_parquet(PROCESSED / "pa.parquet")
    pa = pa[pa.season.between(first, last)]
    e2 = pd.read_parquet(PROCESSED / "pa_e2.parquet")
    d = pa.merge(e2, on=["season", "game_id", "event_id"], how="left")

    for c in ("next1_s", "next2_s", "prev1_s", "prev2_s", "next1_c", "next2_c"):
        d[c[:-2] + ("L" if c.endswith("_s") else "L_c")] = (d[c] == "L").astype(np.int8)
    d["has_P"] = (d[["next1_s", "next2_s", "prev1_s", "prev2_s"]] == "P").any(axis=1)
    d["anyL"] = ((d.next1L + d.next2L) > 0).astype(np.int8)
    d["anyL_c"] = ((d.next1L_c + d.next2L_c) > 0).astype(np.int8)
    d["cfg"] = pool(d.next1_s) + pool(d.next2_s)
    d["n_L_else"] = d.n_L_others - d.next1L - d.next2L

    # neighbor quality: prior-data overall talent of the starters in the next two slots
    lu = pd.read_parquet(PROCESSED / "lineup.parquet", columns=["season", "game_id", "team", "slot", "starter_id"])
    tb = pd.read_parquet(PROCESSED / "talent_bat.parquet", columns=["bat_id", "season", "overall"])
    lu = lu.merge(tb, left_on=["starter_id", "season"], right_on=["bat_id", "season"], how="left")
    q = lu.set_index(["game_id", "team", "slot"]).overall
    for name, off in (("next1_q", 1), ("next2_q", 2)):
        tgt = (d.slot - 1 + off) % 9 + 1
        d[name] = q.reindex(pd.MultiIndex.from_arrays([d.game_id, d.bat_team, tgt])).to_numpy()

    d["relief"] = ~d.vs_starter & ~d.pit_is_position_player
    d["vs_lhp"] = d.vs_lhp.astype(float)
    d["woba"] = d.woba_num
    d["pen_lhp_c"] = d.opp_pen_lhp.clip(upper=5)
    d["inning_c"] = d.inning.clip(upper=10)
    d["outs_bases"] = d.outs * 8 + d.bases
    d["score_c"] = d.score_diff.clip(-4, 4)
    d["bs"] = d.starter_id + "_" + d.season.astype(str)
    d["bs_sh"] = d.bs + "_" + d.opp_starter_throws.astype(str)
    d["opp_ts"] = d.fld_team + "_" + d.season.astype(str)
    d["bat_ts"] = d.bat_team + "_" + d.season.astype(str)
    d["post"] = (d.season >= 2021).astype(np.int8)
    return d


def lhh_relief(d: pd.DataFrame) -> pd.DataFrame:
    """Primary sample: slots whose starter bats left only, PAs vs. relievers, no pitcher batting nearby."""
    return d[(d.slot_stype == "L") & d.relief & ~d.has_P & d.pen_lhp_c.notna()
             & d.next1_q.notna() & d.next2_q.notna()]


def fit(formula: str, data: pd.DataFrame, cluster: str = "game_id", weights: str | None = None):
    return pf.feols(formula, data=data, vcov={"CRV1": cluster}, weights=weights)


def tidy(m, keep: list[str] | None = None, **labels) -> pd.DataFrame:
    t = m.tidy().reset_index().rename(columns={
        "Coefficient": "term", "Estimate": "coef", "Std. Error": "se", "2.5%": "lo", "97.5%": "hi",
        "Pr(>|t|)": "p"})[["term", "coef", "se", "lo", "hi", "p"]]
    if keep is not None:
        t = t[t.term.isin(keep)]
    t["n"] = m._N
    for k, v in reversed(list(labels.items())):
        t.insert(0, k, v)
    return t


def run_outcomes(data, rhs, outcomes=("vs_lhp", "e2", "e2_starter", "woba"), keep=None,
                 fe=FE, cluster="game_id", **labels) -> pd.DataFrame:
    out = []
    for y in outcomes:
        dd = data[data.woba_den == 1] if y == "woba" else data
        m = fit(f"{y} ~ {rhs} | {fe}", dd, cluster)
        out.append(tidy(m, keep, outcome=y, **labels))
    return pd.concat(out, ignore_index=True)


def verdict(lo: float, hi: float, sesoi: float) -> str:
    """Classify an interval against the smallest effect size of interest."""
    if lo > -sesoi and hi < sesoi:
        return "inside ±SESOI: no effect of practical size"
    if lo >= sesoi or hi <= -sesoi:
        return "beyond SESOI"
    if lo > 0 or hi < 0:
        return "nonzero; cannot rule SESOI in or out"
    return "inconclusive"


def runs_per_600(d_woba, relief_share: float, woba_scale: float):
    """wOBA change on relief-phase PAs -> runs per 600 PA of a full season."""
    return d_woba * relief_share * 600 / woba_scale


def era_constants() -> pd.DataFrame:
    """Relief share of LHH-slot PAs and mean wOBA scale, by era (from pipeline tables)."""
    pa = pd.read_parquet(PROCESSED / "pa.parquet",
                         columns=["era", "season", "slot_stype", "vs_starter", "pit_is_position_player"])
    w = pd.read_parquet(PROCESSED / "weights.parquet").set_index("season").woba_scale
    pa["relief"] = ~pa.vs_starter & ~pa.pit_is_position_player
    out = []
    for t in ("L", "R"):
        s = pa[pa.slot_stype == t]
        g = s.groupby("era").agg(relief_share=("relief", "mean"))
        g["woba_scale"] = s.groupby("era").season.apply(lambda x: x.map(w).mean())
        g["stype"] = t
        out.append(g.reset_index())
    return pd.concat(out).set_index(["stype", "era"])
