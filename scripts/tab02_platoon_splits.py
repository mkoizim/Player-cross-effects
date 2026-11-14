"""Observed platoon splits by era and pitcher role: replaces the prior in DESIGN.md section 1.2.

Hitters who bat one side only; pitchers batting and position players pitching excluded.
Raw wOBA, not regressed and not adjusted for who gets to face whom.
"""
from pce.describe import *

pa = load("pa", ["era", "season", "cur_type", "vs_lhp", "vs_starter", "pit_is_position_player",
                 "woba_num", "woba_den"])
d = pa[pa.cur_type.isin(["L", "R"]) & ~pa.pit_is_position_player].copy()
d["role"] = np.where(d.vs_starter, "starter", "reliever")
d["pit"] = np.where(d.vs_lhp, "LHP", "RHP")

rows = []
for keys, label in ((["era", "cur_type"], "all"), (["era", "cur_type", "role"], None)):
    w = woba(d, keys + ["pit"])
    wide = w.pivot(index=keys, columns="pit", values=["woba", "pa"]).reset_index()
    wide.columns = ["_".join(c).strip("_") for c in wide.columns]
    if label:
        wide["role"] = label
    rows.append(wide)
t = pd.concat(rows, ignore_index=True).rename(columns={"cur_type": "bats"})
# split = wOBA with the platoon advantage minus wOBA without it
t["split"] = np.where(t.bats == "L", t.woba_RHP - t.woba_LHP, t.woba_LHP - t.woba_RHP)
t = t[["era", "bats", "role", "pa_LHP", "pa_RHP", "woba_LHP", "woba_RHP", "split"]]
write_table(t.sort_values(["bats", "role", "era"]), "tab02_platoon_splits")
