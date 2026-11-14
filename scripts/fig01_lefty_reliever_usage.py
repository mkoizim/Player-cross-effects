"""Left-handed relief usage by season, 2000-2025: the long-run backdrop for the 2020 rule."""
import matplotlib.ticker

from pce.describe import *

ap = load("appearances")
rel = ap[~ap.is_starter & ~ap.position_player]
lhp = rel[rel.throws == "L"]
rhp = rel[rel.throws == "R"]
t = pd.DataFrame({
    "relief_apps": rel.groupby("season").size(),
    "lhp_share_of_relief_apps": rel.groupby("season").throws.apply(lambda s: (s == "L").mean()),
    "lhp_one_batter_share": lhp.groupby("season").bf.apply(lambda s: (s == 1).mean()),
    "rhp_one_batter_share": rhp.groupby("season").bf.apply(lambda s: (s == 1).mean()),
    "lhp_short_stint_share": lhp.groupby("season").short_stint.mean(),
    "rhp_short_stint_share": rhp.groupby("season").short_stint.mean(),
    "lhp_mean_bf": lhp.groupby("season").bf.mean(),
    "rhp_mean_bf": rhp.groupby("season").bf.mean(),
}).reset_index()
write_table(t, "fig01_lefty_reliever_usage")

style()
fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
panels = [
    ("Relief appearances made\nby left-handers", [("lhp_share_of_relief_apps", BLUE, None)]),
    ("Relief appearances facing\nexactly one batter",
     [("lhp_one_batter_share", BLUE, "LHP"), ("rhp_one_batter_share", ORANGE, "RHP")]),
    ("Outings the three-batter rule forbids\n(under 3 batters, inning not ended)",
     [("lhp_short_stint_share", BLUE, "LHP"), ("rhp_short_stint_share", ORANGE, "RHP")]),
]
for ax, (title, series) in zip(axes, panels):
    for col, color, lab in series:
        ax.plot(t.season, t[col] * 100, color=color, marker="o", markersize=3.5)
        if lab:
            y0 = t[col].iloc[0] * 100
            ax.annotate(lab, (t.season.iloc[0], y0), xytext=(4, 7), textcoords="offset points",
                        color=INK, fontsize=9)
    ax.axvline(2019.5, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
    ax.set_title(title)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=7))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlim(1999.5, 2025.5)
top = axes[0].get_ylim()[1]
axes[0].annotate("three-batter\nminimum", (2019.5, top), xytext=(-5, -4), textcoords="offset points",
                 ha="right", va="top", fontsize=8, color=INK2)
fig.tight_layout()
save(fig, "fig01_lefty_reliever_usage",
     "Regular season, relief appearances by pitchers (position players excluded). Source: Retrosheet.")
