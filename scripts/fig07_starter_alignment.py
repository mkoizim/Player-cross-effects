"""H7, raw: do lefty-heavy teams draw more left-handed starters? One point per team-season."""
from pce.describe import *

pa = load("pa", ["season", "era", "bat_team", "cur_type"])
share_l = pa.assign(l=pa.cur_type == "L").groupby(["season", "era", "bat_team"]).l.mean().rename("lhh_pa_share")
tg = load("team_game")
tg = tg[tg.opp_starter_throws.isin(["L", "R"])]
vs = tg.assign(l=tg.opp_starter_throws == "L").groupby(["season", "team"]).l.mean().rename("lhp_start_share")
t = share_l.reset_index().merge(vs.reset_index(), left_on=["season", "bat_team"], right_on=["season", "team"])
t = t.drop(columns="team")
# within-season deviations remove league-wide swings in the supply of lefty starters
for c in ("lhh_pa_share", "lhp_start_share"):
    t[c + "_dev"] = t[c] - t.groupby("season")[c].transform("mean")
write_table(t, "fig07_starter_alignment_team_seasons")
corr = t.groupby("era").apply(lambda g: pd.Series({
    "team_seasons": len(g),
    "corr_raw": g.lhh_pa_share.corr(g.lhp_start_share),
    "corr_within_season": g.lhh_pa_share_dev.corr(g.lhp_start_share_dev),
    "sd_lhp_start_share_within_season": g.lhp_start_share_dev.std(),
}), include_groups=False).reset_index()
write_table(corr, "fig07_starter_alignment_correlations")

style()
fig, ax = plt.subplots(figsize=(6.6, 4.6))
s = t[t.season != 2020]
ax.scatter(s.lhh_pa_share_dev * 100, s.lhp_start_share_dev * 100, s=14, color=BLUE, alpha=0.45,
           edgecolor="none")
ax.axhline(0, color=GRID, linewidth=1)
ax.grid(axis="x")
ax.set_xlabel("Team share of PAs by left-only hitters, vs. league that season (pp)")
ax.set_ylabel("Share of games facing a LHP starter,\nvs. league that season (pp)")
ax.set_title("Lefty-heavy teams and the starters they draw\nOne point per team-season, 2000–2025 (2020 omitted)",
             fontsize=10.5)
fig.tight_layout()
save(fig, "fig07_starter_alignment", "Raw association; schedule and division not accounted for. Source: Retrosheet.")
