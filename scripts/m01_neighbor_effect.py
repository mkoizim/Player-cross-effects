"""H1 and H2 (Design A): effect of the next two slots' handedness on who pitches to a lefty,
and whether the count of lefties elsewhere in the lineup matters. Plus negative controls NC1, NC4,
robustness, and heterogeneity by the hitter's own platoon split.

Primary contrast (approved post-data, DESIGN 12.4): at least one lefty in the next two slots
("anyL") vs. two right-side hitters. Lineup as started (intent to treat by slot).
"""
from pce.describe import *
from pce.model import *

d = frame()
s = lhh_relief(d)
K = era_constants()
ERAS3 = ["2000–14", "2015–19", "2021–25"]
rhs = f"anyL + {CONTROLS}"

# --- primary, by era
res = pd.concat([run_outcomes(s[s.era == e], rhs, keep=["anyL", "n_L_else"], era=e) for e in ERAS3])
k = K.loc["L"].reindex(res.era)
for c in ("coef", "lo", "hi"):
    res[f"{c}_runs_per_600"] = np.where(res.outcome == "vs_lhp", np.nan,
                                        runs_per_600(res[c].to_numpy(), k.relief_share.to_numpy(),
                                                     k.woba_scale.to_numpy()))


def judge(r):
    """Exposure against 2 pp; value against 1 run per 600 PA of a full season (DESIGN section 3)."""
    if r.outcome == "vs_lhp":
        return verdict(r.lo, r.hi, SESOI_PP / 100)
    return verdict(r.lo_runs_per_600, r.hi_runs_per_600, 1.0)


res["verdict"] = res.apply(judge, axis=1)
write_table(res, "m01_neighbor_effect_primary")

# --- H2: count of lefties elsewhere, per additional lefty (same models; isolated here)
write_table(res[res.term == "n_L_else"].rename(columns={"verdict": "verdict_per_additional_lefty"}),
            "m01_h2_lefty_count")

# --- secondary: four-way configuration (RR omitted)
s4 = s.assign(RL=(s.cfg == "RL").astype(int), LR=(s.cfg == "LR").astype(int), LL=(s.cfg == "LL").astype(int))
four = pd.concat([run_outcomes(s4[s4.era == e], f"RL + LR + LL + {CONTROLS}", outcomes=("vs_lhp", "e2"),
                               keep=["RL", "LR", "LL"], era=e) for e in ERAS3])
write_table(four, "m01_neighbor_effect_four_way")

# --- robustness (2021-25 and 2015-19, E1 and E2)
rob = []
for e in ("2015–19", "2021–25"):
    x = s[s.era == e]
    o = ("vs_lhp", "e2")
    rob += [
        run_outcomes(x, rhs, o, ["anyL"], era=e, spec="primary"),
        run_outcomes(x, rhs, o, ["anyL"], cluster="bat_ts", era=e, spec="cluster by batting team-season"),
        run_outcomes(x, f"anyL_c + {CONTROLS}", o, ["anyL_c"], era=e, spec="neighbors as currently in game"),
        run_outcomes(x, "anyL", o, ["anyL"], era=e, spec="no continuous controls"),
        run_outcomes(x, rhs, o, ["anyL"], fe="bs + opp_ts", era=e, spec="batter-season and opponent FE only"),
        run_outcomes(x[x.inning.between(6, 8)], rhs, o, ["anyL"], era=e, spec="innings 6-8"),
        run_outcomes(x[x.score_diff.abs() <= 3], rhs, o, ["anyL"], era=e, spec="within 3 runs"),
        run_outcomes(x[x.opp_starter_throws == "R"], rhs, o, ["anyL"], era=e, spec="vs right-handed starters only"),
    ]
write_table(pd.concat(rob), "m01_robustness")

# --- heterogeneity: hitters with larger prior platoon splits (selection on gains)
tb = pd.read_parquet(PROCESSED / "talent_bat.parquet", columns=["bat_id", "season", "split", "prior_n"])
x = s.merge(tb.rename(columns={"bat_id": "starter_id"}), on=["starter_id", "season"], how="left")
x = x[(x.prior_n >= 300) & x.era.isin(["2015–19", "2021–25"])]
x["big_split"] = (x.split > x.split.median()).astype(int)
x["anyL_big"] = x.anyL * x.big_split
het = run_outcomes(x, f"anyL + anyL_big + {CONTROLS}", ("vs_lhp", "e2"), ["anyL", "anyL_big"],
                   sample="2015–25, hitters with 300+ prior PA")
write_table(het, "m01_heterogeneity_by_split")

# --- negative controls
nc = []
first = d[(d.slot_stype == "L") & d.vs_starter & (d.pit_bf_before < 9) & ~d.has_P
          & d.next1_q.notna() & d.next2_q.notna() & d.pen_lhp_c.notna() & (d.season >= 2015) & (d.season != 2020)]
nc.append(run_outcomes(first, rhs, ("e2", "woba"), ["anyL"], control="NC1 first time through vs. starter"))
blow = s[(s.score_diff.abs() >= 7) & (s.inning >= 7) & (s.season >= 2015) & (s.season != 2020)]
nc.append(run_outcomes(blow, rhs, ("vs_lhp", "e2"), ["anyL"], fe="bs + opp_ts",
                       control="NC4 blowouts (7+ runs, inning 7+)"))
write_table(pd.concat(nc), "m01_negative_controls")

# --- figure: primary estimates with intervals
style()
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
p = res[res.term == "anyL"]
for ax, y, mult, unit, ses, title in (
        (axes[0], "vs_lhp", 100, "percentage points", SESOI_PP, "Chance the pitcher is left-handed"),
        (axes[1], "e2", 1, "runs per 600 PA", -1.0, "Value to the hitter's slot, full season")):
    q = p[p.outcome == y].set_index("era").reindex(ERAS3)
    if y == "e2":
        q = q.assign(coef=q.coef_runs_per_600, lo=q.lo_runs_per_600, hi=q.hi_runs_per_600)
    yy = np.arange(len(ERAS3))[::-1]
    ax.axvline(0, color=INK2, linewidth=1)
    ax.axvline(ses, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
    ax.hlines(yy, q.lo * mult, q.hi * mult, color=BLUE, linewidth=2)
    ax.plot(q.coef * mult, yy, "o", color=BLUE, markersize=8)
    for a, b in zip(q.coef * mult, yy):
        ax.annotate(f"{a:+.1f}" if y == "vs_lhp" else f"{a:+.2f}", (a, b), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9)
    ax.set_yticks(yy, ERAS3)
    ax.set_ylim(-0.6, len(ERAS3) - 0.4)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x")
    ax.set_xlabel(f"Effect of a lefty in the next two slots ({unit})")
    ax.set_title(title)
    lo, hi = ax.get_xlim()
    ax.set_xlim(min(lo, ses * 1.25, -0.1), max(hi, ses * 1.25, 0.1))
    ax.annotate("threshold for\n“matters”", (ses, len(ERAS3) - 0.45), xytext=(4 if ses > 0 else -4, 0),
                textcoords="offset points", ha="left" if ses > 0 else "right", va="top", fontsize=8, color=INK2)
fig.tight_layout()
save(fig, "m01_neighbor_effect",
     "Left-handed hitters' relief-phase PAs. Fixed effects: hitter-season-starter hand, opponent-season, slot, inning, "
     "base-out, score. 95% intervals, clustered by game.")
