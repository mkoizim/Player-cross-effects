"""H8 (added post-data, DESIGN 12.4): after the three-batter minimum, are lefties pinch-hit for
more often when a left-handed reliever is in, and what is that worth?

Outcome: the slot's starter did not bat. DiD: (vs LHP - vs RHP) x (2021-25 - 2015-19).
To separate the rule from the universal DH (2022), the DiD is repeated on games played with the DH
in both periods, and with 2021 and 2022-25 split.
"""
from pce.describe import *
from pce.model import *

d = frame(2015, 2025)
tg = load("team_game", ["game_id", "team", "n_P"]).rename(columns={"team": "bat_team"})
d = d.merge(tg, on=["game_id", "bat_team"], how="left")
s = d[(d.slot_stype == "L") & d.relief & (d.season != 2020) & d.pen_lhp_c.notna()].copy()
s["replaced"] = (~s.starter_batting).astype(float)
s["lhp"] = s.vs_lhp
s["lhp_post"] = s.lhp * s.post
s["lhp_2021"] = s.lhp * (s.season == 2021)
s["lhp_2022on"] = s.lhp * (s.season >= 2022)
s["ph_gain"] = s.e2 - s.e2_starter           # expected wOBA gained by whoever batted instead
fe = "bs + opp_ts + slot + inning_c + outs_bases + score_c + bat_home_id + season"

rows = [
    tidy(fit(f"replaced ~ lhp + lhp_post | {fe}", s), ["lhp", "lhp_post"], sample="all games", outcome="starter replaced"),
    tidy(fit(f"replaced ~ lhp + lhp_post | {fe}", s[s.n_P == 0]), ["lhp", "lhp_post"],
         sample="DH games only", outcome="starter replaced"),
    tidy(fit(f"replaced ~ lhp + lhp_2021 + lhp_2022on | {fe}", s[s.n_P == 0]), ["lhp", "lhp_2021", "lhp_2022on"],
         sample="DH games only", outcome="starter replaced"),
    tidy(fit(f"ph_gain ~ lhp + lhp_post | {fe}", s[s.n_P == 0]), ["lhp", "lhp_post"],
         sample="DH games only", outcome="expected wOBA gained by substitution (slot)"),
]
# Teams that always had the DH (AL clubs, identified as teams whose 2019 home games used it):
# for them neither the universal DH nor the mix of teams changes, so the timing is cleaner.
home19 = d[(d.season == 2019) & (d.bat_home_id == 1)].groupby("bat_team").n_P.max()
al = set(home19[home19 == 0].index)
a = s[s.bat_team.isin(al) & (s.n_P == 0)]
rows += [
    tidy(fit(f"replaced ~ lhp + lhp_2021 + lhp_2022on | {fe}", a), ["lhp", "lhp_2021", "lhp_2022on"],
         sample="AL clubs, DH games", outcome="starter replaced"),
]
by_season = (a.groupby(["season", "lhp"]).replaced.mean().unstack().rename(columns={0.0: "vs_RHP", 1.0: "vs_LHP"})
             .reset_index())
by_season["gap_pp"] = (by_season.vs_LHP - by_season.vs_RHP) * 100
write_table(by_season, "m06_pinch_hitting_al_by_season")
res = pd.concat(rows)
write_table(res, "m06_pinch_hitting")

# value: expected wOBA of the slot vs. the starter staying in, on PAs against lefty relievers
K = era_constants()
v = s[s.vs_lhp == 1].groupby("era").agg(pa=("ph_gain", "size"), replaced_share=("replaced", "mean"),
                                         gain_per_slot_pa=("ph_gain", "mean")).reset_index()
v["gain_when_replaced"] = v.gain_per_slot_pa / v.replaced_share
lhp_share = s.groupby("era").vs_lhp.mean()
v["lhp_share_of_relief_pa"] = v.era.map(lhp_share)
k = K.loc["L"].reindex(v.era)
v["runs_per_600_slot_pa"] = (v.gain_per_slot_pa * v.lhp_share_of_relief_pa * k.relief_share.to_numpy()
                             * 600 / k.woba_scale.to_numpy())
write_table(v, "m06_pinch_hitting_value")
