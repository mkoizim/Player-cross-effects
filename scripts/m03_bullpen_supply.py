"""H5 and the bullpen-supply finding (promoted post-data, DESIGN 12.4).

(a) Does the neighbor effect scale with how many lefty relievers the opponent has? (NC2: zero supply)
(b) How much does one more lefty in the opposing bullpen change a lefty hitter's exposure and
    expected matchup value? Identified from changes in a given opponent's bullpen within a season.
"""
from pce.describe import *
from pce.model import *

d = frame(2015, 2025)
s = lhh_relief(d)
s = s[(s.opp_days_into_season >= 14) & (s.season != 2020)].copy()
K = era_constants()
s["sup"] = s.opp_pen_lhp.clip(upper=4).astype(int)

# (a) neighbor effect within supply level
rows = []
for e in ("2015–19", "2021–25"):
    for k in range(5):
        x = s[(s.era == e) & (s.sup == k)]
        fe = FE if k > 0 else "bs + opp_ts"          # zero-supply cell is too small for full FE
        rows.append(run_outcomes(x, "anyL + n_L_else + next1_q + next2_q", ("vs_lhp", "e2"), ["anyL"],
                                 fe=fe, era=e, opp_lefty_relievers="4+" if k == 4 else str(k)))
a = pd.concat(rows)
write_table(a, "m03_neighbor_effect_by_supply")

# (b) effect of supply itself
rows = []
for e in ("2015–19", "2021–25"):
    x = s[s.era == e]
    r = run_outcomes(x, "pen_lhp_c + anyL + n_L_else + next1_q + next2_q", ("vs_lhp", "e2", "woba"),
                     ["pen_lhp_c"], era=e, spec="within opponent-season")
    k = K.loc[("L", e)]
    for c in ("coef", "lo", "hi"):
        r[f"{c}_runs_per_600"] = np.where(r.outcome == "vs_lhp", np.nan,
                                          runs_per_600(r[c], k.relief_share, k.woba_scale))
    rows.append(r)
    r2 = run_outcomes(x, "pen_lhp_c + anyL + n_L_else + next1_q + next2_q", ("vs_lhp", "e2"), ["pen_lhp_c"],
                      fe="bs_sh + slot + inning_c + outs_bases + score_c + bat_home_id",
                      era=e, spec="across opponents (no opponent FE)")
    for c in ("coef", "lo", "hi"):
        r2[f"{c}_runs_per_600"] = np.where(r2.outcome == "vs_lhp", np.nan,
                                           runs_per_600(r2[c], k.relief_share, k.woba_scale))
    rows.append(r2)
b = pd.concat(rows)
write_table(b, "m03_supply_effect")

style()
fig, ax = plt.subplots(figsize=(7.2, 4.0))
q = a[a.outcome == "vs_lhp"]
xs = np.arange(5)
ends = []
for e, off in (("2015–19", -0.08), ("2021–25", 0.08)):
    t = q[q.era == e]
    ax.vlines(xs + off, t.lo * 100, t.hi * 100, color=ERA_COLOR[e], linewidth=1.5)
    ax.plot(xs + off, t.coef * 100, "o", color=ERA_COLOR[e], label=e, markersize=7)
ax.axhline(0, color=INK2, linewidth=1)
ax.set_xticks(xs, ["0", "1", "2", "3", "4+"])
ax.set_xlabel("Left-handed relievers in the opposing bullpen")
ax.set_ylabel("Effect of a lefty in the next two slots (pp)")
ax.set_title("The neighbor effect needs lefties in the other bullpen")
ax.legend(title="Seasons", fontsize=9, loc="upper left")
fig.tight_layout()
save(fig, "m03_neighbor_effect_by_supply",
     "Effect on the chance a left-handed hitter faces a left-handed reliever. 95% intervals clustered by game.")
