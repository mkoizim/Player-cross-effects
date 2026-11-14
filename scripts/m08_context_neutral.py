"""Context-neutral production: how much of a hitter's expected line comes from who he faced.

For each hitter-season (300+ PA, 2021-25):
  actual   = mean expected matchup wOBA over the PAs he took (talent vs. each pitcher faced)
  neutral  = his talent against the league-average mix of pitcher hands for his batting side,
             facing the average pitcher of each hand
  context  = actual - neutral, in runs
"neighbor part" is the piece of context predicted from the handedness of the hitters around him
in the lineups he started (coefficients from m07), relative to the average for his type.
"""
from pce.describe import *
from pce.model import *

d = frame(2021, 2025)
tb = pd.read_parquet(PROCESSED / "talent_bat.parquet")
w = pd.read_parquet(PROCESSED / "weights.parquet").set_index("season").woba_scale
pl = load("players")[["season", "player_id", "bats"]].rename(columns={"player_id": "bat_id"})
d = d.merge(pl, on=["season", "bat_id"], how="left")
d = d[d.bats.isin(["L", "R", "S"]) & d.e2.notna() & ~d.pit_is_position_player]

lg_pL = d.groupby(["season", "bats"]).vs_lhp.mean().rename("lg_pL")
g = d.groupby(["season", "bat_id", "bats"]).agg(pa=("e2", "size"), actual=("e2", "mean"),
                                                 share_vs_lhp=("vs_lhp", "mean")).reset_index()
g = g.merge(tb[["bat_id", "season", "vs_L", "vs_R"]], on=["bat_id", "season"]).join(lg_pL, on=["season", "bats"])
g["neutral"] = g.lg_pL * g.vs_L + (1 - g.lg_pL) * g.vs_R
g["context_woba"] = g.actual - g.neutral
g["context_runs"] = g.context_woba * g.pa / g.season.map(w)

# neighbor part, from m07 coefficients applied to the PAs he took as the slot's starter vs relievers
co = pd.read_csv(TABLES / "m07_neighbor_coefficients.csv").set_index("term").coef_woba
s = d[d.relief & d.starter_batting & ~d.has_P & d.slot_stype.isin(["L", "R", "S"])].copy()
nb = {"p2L": s.prev2L, "p1L": s.prev1L, "n1L": s.next1L, "n2L": s.next2L, "n12": s.next1L * s.next2L}
s["nbr"] = 0.0
for t in ("L", "R", "S"):
    own = (s.slot_stype == t)
    s.loc[own, "nbr"] = sum(co[f"{t}_{k}"] * v[own] for k, v in nb.items())
s["nbr"] -= s.groupby(["season", "slot_stype"]).nbr.transform("mean")
n = s.groupby(["season", "bat_id"]).nbr.sum().rename("nbr_sum").reset_index()
g = g.merge(n, on=["season", "bat_id"], how="left").fillna({"nbr_sum": 0.0})
g["neighbor_runs"] = g.nbr_sum / g.season.map(w)

names = pd.concat([pd.read_parquet(p) for p in sorted((PROCESSED.parent / "interim").glob("roster_202[1-5].parquet"))])
names = names.drop_duplicates("player_id").set_index("player_id")
g["name"] = g.bat_id.map(names["first"] + " " + names["last"])
q = g[g.pa >= 300].copy()

summ = q.groupby("bats").agg(hitter_seasons=("pa", "size"), sd_context_runs=("context_runs", "std"),
                             p05=("context_runs", lambda x: x.quantile(0.05)),
                             p95=("context_runs", lambda x: x.quantile(0.95)),
                             sd_neighbor_runs=("neighbor_runs", "std"),
                             max_abs_neighbor_runs=("neighbor_runs", lambda x: x.abs().max())).reset_index()
write_table(summ, "m08_context_summary")
cols = ["season", "name", "bats", "pa", "share_vs_lhp", "lg_pL", "context_runs", "neighbor_runs"]
y = q[q.season == 2025].sort_values("context_runs")
write_table(pd.concat([y.head(10), y.tail(10)])[cols], "m08_context_2025_extremes")
write_table(q.sort_values(["season", "context_runs"])[cols], "m08_context_all")
