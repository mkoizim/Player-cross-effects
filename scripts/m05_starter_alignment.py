"""H7: do opponents point left-handed starters at lefty-heavy lineups?

Game level. Outcome: the opposing (de facto) starter throws left. Exposure: how many left-only
hitters this team usually starts against right-handed starters that season, leaving out the
current game. Opponent-season fixed effects hold the opponent's rotation fixed, so the coefficient
asks whether a given rotation is *aligned* differently against lefty-heavy teams.

Openers (user definition, config.toml): the bulk pitcher is the de facto starter.
"""
from pce.describe import *
from pce.model import *

tg = load("team_game")
tg = tg[tg.opp_defacto_throws.isin(["L", "R"])].copy()
vr = tg[tg.opp_defacto_throws == "R"]
g = vr.groupby(["season", "team"]).n_L.agg(["sum", "count"])
tg = tg.join(g, on=["season", "team"])
own = np.where(tg.opp_defacto_throws == "R", tg.n_L, 0)
cnt = np.where(tg.opp_defacto_throws == "R", 1, 0)
tg["lefty_heaviness"] = (tg["sum"] - own) / (tg["count"] - cnt)     # leave-one-out
tg["lhp_start"] = (tg.opp_defacto_throws == "L").astype(float)
tg["lhp_start_nominal"] = (tg.opp_starter_throws == "L").astype(float)
tg["opp_ts"] = tg.opp + "_" + tg.season.astype(str)
tg["bat_ts"] = tg.team + "_" + tg.season.astype(str)

rows = []
for e in ("2000–14", "2015–19", "2021–25"):
    x = tg[tg.era == e]
    for y, lab in (("lhp_start", "de facto starter (openers resolved)"), ("lhp_start_nominal", "nominal starter")):
        m = fit(f"{y} ~ lefty_heaviness | opp_ts", x, cluster="bat_ts")
        rows.append(tidy(m, ["lefty_heaviness"], era=e, outcome=lab, fe="opponent-season"))
    m = fit("lhp_start ~ lefty_heaviness | season", x, cluster="bat_ts")
    rows.append(tidy(m, ["lefty_heaviness"], era=e, outcome="de facto starter (openers resolved)", fe="season only"))
res = pd.concat(rows)
res["pp_per_additional_lefty"] = res.coef * 100
res["verdict_vs_1pp"] = [verdict(a, b, 0.01) for a, b in zip(res.lo, res.hi)]
write_table(res, "m05_starter_alignment")
op = tg.groupby("era").agg(team_games=("opp_opener", "size"), opener_share=("opp_opener", "mean"),
                           hand_differs=("lhp_start", lambda s: (s != tg.loc[s.index, "lhp_start_nominal"]).mean()))
write_table(op.reset_index(), "m05_opener_incidence")
