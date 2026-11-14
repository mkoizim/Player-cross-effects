"""The pitching-change decision, raw: when a reliever enters to face a left-handed hitter,
how often is he left-handed? By the next two batters, outs at entry, and era.

Uses the lineup as it stood (last batter seen in each slot), since this is the manager's view.
Conditions on a change having been made, so it describes who comes in, not whether a change occurs.
"""
from pce.describe import *

ap = load("appearances")
d = ap[~ap.is_starter & ~ap.position_player
       & (ap.first_slot_stype == "L") & ap.first_bat_starter].copy()
d["cfg"] = pool(d.first_next1_c) + pool(d.first_next2_c)
d = d[d.cfg.isin(CFG_ORDER)]
d["enters_lhp"] = d.throws == "L"
d["outs_grp"] = np.where(d.entry_outs == 2, "2 outs", "0–1 outs")
d["timing"] = np.where(d.entry_mid_inning, "mid-inning", "start of inning")

t = rate(d, ["era", "outs_grp", "cfg"], "enters_lhp").rename(columns={"rate": "lhp_share"})
write_table(t, "fig03_entry_decision_by_outs")
t2 = rate(d, ["era", "timing", "cfg"], "enters_lhp").rename(columns={"rate": "lhp_share"})
write_table(t2, "fig03_entry_decision_by_timing")

g = t.pivot(index=["era", "outs_grp"], columns="cfg", values="lhp_share")
g["RR_minus_LL_pp"] = (g["RR"] - g["LL"]) * 100
write_table(g.reset_index(), "fig03_gap_RR_vs_LL_by_outs")

style()
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)
x = np.arange(len(CFG_ORDER))
for ax, og in zip(axes, ["0–1 outs", "2 outs"]):
    ends = []
    for e in MAIN_ERAS:
        s = t[(t.era == e) & (t.outs_grp == og)].set_index("cfg").reindex(CFG_ORDER)
        ax.plot(x, s.lhp_share * 100, color=ERA_COLOR[e], marker="o", markersize=7, label=e)
        ends.append((x[-1], s.lhp_share.iloc[-1] * 100, e))
    ax.set_xticks(x, [CFG_LABEL[c] for c in CFG_ORDER])
    ax.set_xlim(-0.3, 3.85)
    ax.set_title(f"Reliever enters with {og}")
    ax.set_xlabel("Batting side of the next two hitters")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(0, 100)
    end_labels(ax, ends)
axes[0].set_ylabel("Entering reliever is left-handed")
axes[0].legend(loc="lower right", title="Seasons", fontsize=9)
fig.suptitle("Who comes in to face a left-handed hitter, by what follows him",
             x=0.01, ha="left", fontsize=11.5, fontweight="bold")
fig.tight_layout()
save(fig, "fig03_entry_decision_by_outs",
     "Relief entries whose first batter is a starting left-handed hitter. With two outs a reliever can end the "
     "inning with one batter, so the rule binds less. Raw rates. Source: Retrosheet.")
