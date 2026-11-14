"""Opposing bullpen supply of left-handers, and raw exposure by supply (H5, descriptive)."""
from pce.describe import *

tg = load("team_game")
tg = tg[tg.opp_days_into_season >= 14]          # trailing window needs two weeks to fill
sup = tg.groupby("season").agg(
    mean_lhp=("opp_pen_lhp", "mean"), mean_rhp=("opp_pen_rhp", "mean"),
    share_zero_lhp=("opp_pen_lhp", lambda s: (s == 0).mean()),
    share_one_lhp=("opp_pen_lhp", lambda s: (s == 1).mean())).reset_index()
write_table(sup, "fig05_bullpen_supply_by_season")

d = relief_lhh(["opp_pen_lhp", "opp_days_into_season"])
d = d[(d.opp_days_into_season >= 14) & d.opp_pen_lhp.notna()]
d["supply"] = d.opp_pen_lhp.clip(upper=4).astype(int)
t = rate(d, ["era", "supply"]).rename(columns={"rate": "lhp_share"})
write_table(t, "fig05_exposure_by_supply")
d2 = d[d.cfg.isin(["RR", "LL"])]
t2 = rate(d2, ["era", "supply", "cfg"]).rename(columns={"rate": "lhp_share"})
g = t2.pivot(index=["era", "supply"], columns="cfg", values=["lhp_share", "n"])
g.columns = [f"{a}_{b}" for a, b in g.columns]
g["RR_minus_LL_pp"] = (g.lhp_share_RR - g.lhp_share_LL) * 100
write_table(g.reset_index(), "fig05_gap_RR_vs_LL_by_supply")

style()
fig, axes = plt.subplots(1, 2, figsize=(11, 4.1))
ax = axes[0]
ax.plot(sup.season, sup.mean_lhp, color=BLUE, marker="o", markersize=3.5)
ax.axvline(2019.5, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
ax.set_ylim(0, None)
ax.set_title("Left-handed relievers an opponent has used\nin the previous 14 days (mean per game)")
ax = axes[1]
labels = ["0", "1", "2", "3", "4+"]
ends = []
for e in MAIN_ERAS:
    s = t[t.era == e].set_index("supply").reindex(range(5))
    ax.plot(range(5), s.lhp_share * 100, color=ERA_COLOR[e], marker="o", markersize=7, label=e)
    ends.append((4, s.lhp_share.iloc[-1] * 100, e))
ax.set_xticks(range(5), labels)
ax.set_xlim(-0.3, 4.9)
ax.set_ylim(0, None)
end_labels(ax, ends)
ax.set_xlabel("Left-handed relievers in the opposing bullpen")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("Lefty hitters' relief-phase PAs vs. a left-hander,\nby opposing supply")
ax.legend(loc="lower right", title="Seasons", fontsize=9)
fig.tight_layout()
save(fig, "fig05_bullpen_supply",
     "Supply = distinct left-handers with a relief appearance for that team in the trailing 14 days, game day "
     "excluded; first 14 days of each team-season dropped. Raw rates. Source: Retrosheet.")
