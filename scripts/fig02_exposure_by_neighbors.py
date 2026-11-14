"""E1, raw: how often a left-handed hitter's slot faces a left-handed reliever, by the
handedness of the next two lineup slots and by era. Also by outs, and raw slot wOBA."""
from pce.describe import *

d = relief_lhh()
d = d[d.cfg.isin(CFG_ORDER)]            # drops configurations with a pitcher batting next

t = rate(d, ["era", "cfg"])
w = woba(d, ["era", "cfg"])
t = t.merge(w[["era", "cfg", "woba"]], on=["era", "cfg"])
t["cfg"] = pd.Categorical(t.cfg, CFG_ORDER, ordered=True)
t = t.sort_values(["era", "cfg"]).rename(columns={"rate": "lhp_share", "woba": "slot_woba_raw"})
write_table(t, "fig02_exposure_by_neighbors")

gap = t.pivot(index="era", columns="cfg", values="lhp_share")
gap["RR_minus_LL_pp"] = (gap["RR"] - gap["LL"]) * 100
write_table(gap.reset_index(), "fig02_gap_RR_vs_LL")

d["outs_grp"] = np.where(d.outs == 2, "2 outs", "0-1 outs")
o = rate(d, ["era", "outs_grp", "cfg"]).rename(columns={"rate": "lhp_share"})
write_table(o, "fig02_exposure_by_neighbors_and_outs")

late = rate(d[d.inning.between(6, 8)], ["era", "cfg"]).rename(columns={"rate": "lhp_share"})
write_table(late, "fig02_exposure_by_neighbors_innings_6_to_8")

style()
fig, ax = plt.subplots(figsize=(7.6, 4.4))
x = np.arange(len(CFG_ORDER))
ends = []
for e in MAIN_ERAS:
    s = t[t.era == e].set_index("cfg").reindex(CFG_ORDER)
    ax.plot(x, s.lhp_share * 100, color=ERA_COLOR[e], marker="o", markersize=7, label=e)
    ends.append((x[-1], s.lhp_share.iloc[-1] * 100, e))
ax.set_xticks(x, [CFG_LABEL[c] for c in CFG_ORDER])
ax.set_xlim(-0.3, 3.75)
ax.set_xlabel("Batting side of the next two lineup slots (switch hitters counted as right)")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_ylim(0, None)
end_labels(ax, ends)
ax.set_title("Left-handed hitters see more left-handed relievers when lefties follow them\n"
             "Share of relief-phase plate appearances against a left-hander", fontsize=10.5)
ax.legend(loc="lower right", title="Seasons", fontsize=9)
fig.tight_layout()
save(fig, "fig02_exposure_by_neighbors",
     "Slots whose starter bats left only; PAs vs. relievers; lineup as started. Raw rates, no adjustment. "
     "Source: Retrosheet.")
