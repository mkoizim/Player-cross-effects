"""How lineups are built: lefty counts by opposing starter hand, and what follows a lefty."""
from pce.describe import *

tg = load("team_game")
tg = tg[tg.opp_starter_throws.isin(["L", "R"])]
tg["n_L_c"] = tg.n_L.clip(upper=6)
dist = (tg.groupby(["era", "opp_starter_throws", "n_L_c"]).size()
        / tg.groupby(["era", "opp_starter_throws"]).size()).rename("share").reset_index()
write_table(dist, "fig04_lefty_count_by_opp_starter")
means = tg.groupby(["era", "opp_starter_throws"]).agg(
    team_games=("n_L", "size"), mean_n_L=("n_L", "mean"), mean_n_S=("n_S", "mean")).reset_index()
write_table(means, "fig04_mean_lefties_by_opp_starter")

lu = load("lineup")
m = lu.pivot(index=["season", "game_id", "team"], columns="slot", values="stype")
arr = m.to_numpy()
rows = []
for s in range(9):
    rows.append(pd.DataFrame({"season": m.index.get_level_values("season"), "stype": arr[:, s],
                              "n1": arr[:, (s + 1) % 9], "n2": arr[:, (s + 2) % 9]}))
f = pd.concat(rows)
f = f[f.stype == "L"]
f["cfg"] = pool(f.n1) + pool(f.n2)
f["grp"] = np.select([f.cfg == "RR", f.cfg == "LL", f.cfg.isin(["RL", "LR"])],
                     ["right, right", "left, left", "one of each"], "pitcher in next two")
follow = (f.groupby(["season", "grp"]).size() / f.groupby("season").size()).rename("share").reset_index()
write_table(follow.pivot(index="season", columns="grp", values="share").reset_index(),
            "fig04_what_follows_a_lefty")

style()
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.1))
for ax, hand, name in zip(axes, ["R", "L"], ["right-handed", "left-handed"]):
    for e, off in zip(["2015–19", "2021–25"], [-0.19, 0.19]):
        s = dist[(dist.era == e) & (dist.opp_starter_throws == hand)]
        ax.bar(s.n_L_c + off, s.share * 100, width=0.34, color=ERA_COLOR[e], label=e,
               edgecolor=SURFACE, linewidth=1)
    ax.set_title(f"Lefties in the lineup vs. a {name} starter")
    ax.set_xticks(range(7), ["0", "1", "2", "3", "4", "5", "6+"])
    ax.set_xlabel("Left-only hitters among the nine starters")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].set_ylabel("Share of team-games")
axes[0].legend(title="Seasons", fontsize=9)
fig.tight_layout()
save(fig, "fig04a_lefty_count_by_opp_starter", "Starting lineups, regular season. Source: Retrosheet.")

fig, ax = plt.subplots(figsize=(7.4, 4.2))
for grp, color in (("right, right", BLUE), ("one of each", ORANGE), ("left, left", AQUA)):
    s = follow[follow.grp == grp]
    ax.plot(s.season, s.share * 100, color=color, label=grp)
    ax.annotate(grp, (s.season.iloc[-1], s.share.iloc[-1] * 100), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9, color=INK)
ax.axvline(2019.5, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
ax.set_xlim(1999.5, 2030)
ax.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
ax.set_ylim(0, None)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("What bats in the two slots after a left-handed hitter\nShare of left-only starters, by season",
             fontsize=10.5)
ax.legend(loc="center left", fontsize=9)
fig.tight_layout()
save(fig, "fig04b_what_follows_a_lefty",
     "Switch hitters counted as right. Remainder: a pitcher bats in one of the next two slots (NL through 2021). "
     "Dashed line: three-batter minimum. Source: Retrosheet.")
