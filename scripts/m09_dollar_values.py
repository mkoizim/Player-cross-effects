"""Run values from the models expressed in wins and dollars.

Runs come from the model tables; the two conversion rates are external assumptions set in
config.toml ([valuation]) and are not estimated in this repository.
"""
from pce.config import CFG
from pce.describe import *

RPW = CFG["valuation"]["runs_per_win"]
DPW = CFG["valuation"]["dollars_per_win"]


def read(name):
    return pd.read_csv(TABLES / f"{name}.csv")


m01 = read("m01_neighbor_effect_primary")
h1 = m01[(m01.era == "2021–25") & (m01.term == "anyL") & (m01.outcome == "e2")].iloc[0]
m04 = read("m04_mutuality")
h6 = m04[(m04.era == "2021–25") & (m04.term == "prev1L") & (m04.outcome == "e2")].iloc[0]
m03 = read("m03_supply_effect")
sup = m03[(m03.era == "2021–25") & (m03.outcome == "e2") & (m03.spec == "within opponent-season")].iloc[0]
ph = read("m06_pinch_hitting_value").set_index("era").runs_per_600_slot_pa
arr = read("m07_h3_arrangement")
a3 = arr[(arr.lefties == 3) & (arr.contrast == "spread out vs one block")].iloc[0]
team = read("m07_team_arrangement_2025").arrangement_runs

rows = [
    ("Neighbor effect on one left-handed hitter (600 PA)", -h1.coef_runs_per_600, -h1.hi_runs_per_600, -h1.lo_runs_per_600),
    ("Same, summed over a lineup with three lefties", -3 * h1.coef_runs_per_600, -3 * h1.hi_runs_per_600, -3 * h1.lo_runs_per_600),
    ("Same, summed over a lineup with four lefties", -4 * h1.coef_runs_per_600, -4 * h1.hi_runs_per_600, -4 * h1.lo_runs_per_600),
    ("Gain to a right-handed hitter directly behind a lefty (600 PA)", h6.coef_runs_per_600, h6.lo_runs_per_600, h6.hi_runs_per_600),
    ("One more lefty reliever in the opposing bullpen, per lefty hitter (600 PA)",
     -sup.coef_runs_per_600, -sup.hi_runs_per_600, -sup.lo_runs_per_600),
    ("Pinch-hitting for a lefty vs. lefty relievers, per slot (600 PA), 2021-25", ph["2021–25"], np.nan, np.nan),
    ("Increase in that pinch-hitting value since 2015-19", ph["2021–25"] - ph["2015–19"], np.nan, np.nan),
    ("Three lefties spread out vs. batted consecutively (team, 162 games)", a3.runs_per_162, a3.lo, a3.hi),
    ("2025 teams' actual batting order vs. a random order: smallest", team.min(), np.nan, np.nan),
    ("2025 teams' actual batting order vs. a random order: median", team.median(), np.nan, np.nan),
    ("2025 teams' actual batting order vs. a random order: largest", team.max(), np.nan, np.nan),
]
t = pd.DataFrame(rows, columns=["item", "runs", "runs_lo", "runs_hi"])
t["wins"] = t.runs / RPW
for c, src in (("dollars_m", "runs"), ("dollars_m_lo", "runs_lo"), ("dollars_m_hi", "runs_hi")):
    t[c] = t[src] / RPW * DPW / 1e6
t["runs_per_win_assumed"] = RPW
t["dollars_per_win_assumed_m"] = DPW / 1e6
write_table(t, "m09_dollar_values")
