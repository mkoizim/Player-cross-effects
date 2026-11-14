"""H6: right-handed hitters batting behind a lefty get more platoon-advantaged PAs.
Treatment: the slot immediately before bats left only (prev1L); the slot two before as a second term."""
from pce.describe import *
from pce.model import *

d = frame(2000, 2025)
r = d[(d.slot_stype == "R") & d.relief & ~d.has_P & d.pen_lhp_c.notna()
      & d.next1_q.notna() & d.next2_q.notna()].copy()
K = era_constants()
rows = []
for e in ("2000–14", "2015–19", "2021–25"):
    t = run_outcomes(r[r.era == e], "prev1L + prev2L + next1L + next2L + next1_q + next2_q + pen_lhp_c",
                     keep=["prev1L", "prev2L"], era=e)
    k = K.loc[("R", e)]
    for c in ("coef", "lo", "hi"):
        t[f"{c}_runs_per_600"] = np.where(t.outcome == "vs_lhp", np.nan,
                                          runs_per_600(t[c], k.relief_share, k.woba_scale))
    rows.append(t)
res = pd.concat(rows)
res["verdict"] = [verdict(a, b, SESOI_PP / 100) if y == "vs_lhp" else verdict(c, e_, 1.0)
                  for a, b, c, e_, y in zip(res.lo, res.hi, res.lo_runs_per_600, res.hi_runs_per_600, res.outcome)]
write_table(res, "m04_mutuality")
