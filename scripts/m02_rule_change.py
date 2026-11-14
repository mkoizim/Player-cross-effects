"""H4 (Design B): did the three-batter minimum change the neighbor effect?

1. Event study: the anyL effect on exposure and matchup value, season by season.
2. Difference-in-differences, 2015-19 vs 2021-25 (2020 set aside).
3. Pre-specified triple difference on outs (DESIGN 5.2), at PA level and at relief-entry level.
4. Exploratory (chosen after seeing Phase 2): mid-inning vs. inning-start entries.
5. Placebo rule dates inside 2015-19 (NC3).
"""
from pce.describe import *
from pce.model import *

d = frame(2008, 2025)
s = lhh_relief(d)
K = era_constants()

# 1. event study --------------------------------------------------------------------------
ev = []
for season, x in s.groupby("season"):
    ev.append(run_outcomes(x, f"anyL + {CONTROLS}", ("vs_lhp", "e2"), ["anyL"], season=season))
ev = pd.concat(ev)
write_table(ev, "m02_event_study")

# 2-3. PA-level DiD and triple difference ------------------------------------------------
w = s[s.era.isin(["2015–19", "2021–25"])].copy()
w["anyL_post"] = w.anyL * w.post
w["early"] = (w.outs < 2).astype(int)            # rule binds more with fewer than two outs
for a, b in (("anyL", "early"), ("post", "early"), ("anyL_post", "early")):
    w[f"{a}_{b}"] = w[a] * w[b]
fe = FE + " + season"
did = run_outcomes(w, f"anyL + anyL_post + {CONTROLS}", ("vs_lhp", "e2", "e2_starter"),
                   ["anyL", "anyL_post"], fe=fe, level="PA", test="DiD (pre-specified)")
ddd = run_outcomes(w, f"anyL + anyL_post + anyL_early + post_early + anyL_post_early + {CONTROLS}",
                   ("vs_lhp", "e2"), ["anyL_post", "anyL_post_early"], fe=fe, level="PA",
                   test="triple difference on outs (pre-specified)")

# 3-4. entry level -----------------------------------------------------------------------
ap = load("appearances")
e = ap[~ap.is_starter & ~ap.position_player & (ap.first_slot_stype == "L") & ap.first_bat_starter
       & ap.era.isin(["2015–19", "2021–25"])].copy()
cfg = pool(e.first_next1_c) + pool(e.first_next2_c)
e = e[cfg.isin(CFG_ORDER)].copy()
e["anyL"] = (cfg[e.index] != "RR").astype(int)
e["lhp"] = (e.throws == "L").astype(float)
e["post"] = (e.season >= 2021).astype(int)
e["early"] = (e.entry_outs < 2).astype(int)
e["mid"] = e.entry_mid_inning.astype(int)
e["anyL_post"] = e.anyL * e.post
for a, b in (("anyL", "early"), ("post", "early"), ("anyL_post", "early"),
             ("anyL", "mid"), ("post", "mid"), ("anyL_post", "mid")):
    e[f"{a}_{b}"] = e[a] * e[b]
e["opp_ts"] = e.fld_team + "_" + e.season.astype(str)
e["inning_c"] = e.entry_inning.clip(upper=10)
e["score_c"] = e.entry_score_diff.clip(-4, 4)
efe = "opp_ts + inning_c + score_c + entry_outs + entry_bases + season"


def efit(rhs, keep, sub=None, **lab):
    x = e if sub is None else e[sub]
    return tidy(fit(f"lhp ~ {rhs} | {efe}", x), keep, outcome="entering pitcher is LHP", level="entry", **lab)


ent = pd.concat([
    efit("anyL + anyL_post", ["anyL", "anyL_post"], test="DiD (pre-specified)"),
    efit("anyL + anyL_post + anyL_early + anyL_post_early + post_early", ["anyL_post", "anyL_post_early"],
         test="triple difference on outs (pre-specified)"),
    efit("anyL + anyL_post + anyL_early + anyL_post_early + post_early", ["anyL_post", "anyL_post_early"],
         sub=e.entry_mid_inning, test="triple difference on outs, mid-inning entries only (pre-specified)"),
    efit("anyL + anyL_post + anyL_mid + anyL_post_mid + post_mid + mid", ["anyL_post", "anyL_post_mid"],
         test="mid-inning vs inning-start (EXPLORATORY, post-data)"),
])
allres = pd.concat([did, ddd, ent], ignore_index=True)
write_table(allres, "m02_rule_tests")

# 5. placebo dates inside the pre-period -------------------------------------------------
pre = s[s.season.between(2015, 2019)].copy()
pl = []
for cut in (2017, 2018):
    pre["fake_post"] = (pre.season >= cut).astype(int)
    pre["anyL_fake"] = pre.anyL * pre.fake_post
    pl.append(run_outcomes(pre, f"anyL + anyL_fake + {CONTROLS}", ("vs_lhp", "e2"), ["anyL_fake"],
                           fe=fe, placebo_rule_year=cut))
write_table(pd.concat(pl), "m02_placebo_dates")

# figure ----------------------------------------------------------------------------------
style()
fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
for ax, y, mult, lab in ((axes[0], "vs_lhp", 100, "percentage points"),
                         (axes[1], "e2", 1000, "points of wOBA, relief-phase PAs")):
    q = ev[ev.outcome == y]
    ax.axhline(0, color=INK2, linewidth=1)
    ax.axvline(2019.5, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
    ax.vlines(q.season, q.lo * mult, q.hi * mult, color=BLUE, linewidth=1.5)
    ax.plot(q.season, q.coef * mult, "o", color=BLUE, markersize=5)
    ax.set_ylabel(lab)
    ax.set_xticks(range(2008, 2026, 2))
axes[0].set_title("Effect of a lefty in the next two slots on\nfacing a left-handed reliever, by season")
axes[1].set_title("Same, on expected matchup value")
fig.tight_layout()
save(fig, "m02_event_study",
     "One model per season, same fixed effects as the main model. 95% intervals clustered by game. "
     "Dashed line: three-batter minimum.")
