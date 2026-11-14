"""H2, raw: exposure by how many other lefties are in the lineup, split by opposing starter hand
(lineups are stacked against the starter, so pooling the two would mislead)."""
from pce.describe import *

d = relief_lhh(["n_L_others", "opp_starter_throws"])
d = d[d.opp_starter_throws.isin(["L", "R"])]
d["others"] = d.n_L_others.clip(upper=5)
t = rate(d, ["era", "opp_starter_throws", "others"]).rename(columns={"rate": "lhp_share"})
write_table(t, "fig06_exposure_by_lefty_count")
# same, holding the local configuration fixed
d2 = d[d.cfg.isin(["RR", "LL"])]
t2 = rate(d2, ["era", "opp_starter_throws", "cfg", "others"]).rename(columns={"rate": "lhp_share"})
write_table(t2, "fig06_exposure_by_lefty_count_within_cfg")

style()
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
for ax, hand, name in zip(axes, ["R", "L"], ["right-handed", "left-handed"]):
    ends = []
    for e in MAIN_ERAS:
        s = t[(t.era == e) & (t.opp_starter_throws == hand) & (t.n >= 500)]
        ax.plot(s.others, s.lhp_share * 100, color=ERA_COLOR[e], marker="o", markersize=7, label=e)
        ends.append((s.others.iloc[-1], s.lhp_share.iloc[-1] * 100, e))
    ax.set_title(f"Games started by a {name} opponent")
    ax.set_xticks(range(6), ["0", "1", "2", "3", "4", "5+"])
    ax.set_xlim(-0.3, 6.1)
    ax.set_xlabel("Other left-only hitters in the starting lineup")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(0, 45)
    end_labels(ax, ends)
axes[0].set_ylabel("Relief-phase PAs vs. a left-hander")
axes[0].legend(loc="lower right", title="Seasons", fontsize=9)
fig.suptitle("Left-handed relief exposure by how many other lefties are in the lineup",
             x=0.01, ha="left", fontsize=11.5, fontweight="bold")
fig.tight_layout()
save(fig, "fig06_exposure_by_lefty_count",
     "Slots whose starter bats left only; PAs vs. relievers. Cells under 500 PAs not drawn. Raw rates. "
     "Source: Retrosheet.")
