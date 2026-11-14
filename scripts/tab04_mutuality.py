"""H6, raw: do right-handed hitters see more left-handed relievers when a lefty bats ahead of them?"""
from pce.describe import *

pa = load("pa", ["era", "slot_stype", "vs_starter", "pit_is_position_player", "vs_lhp",
                 "prev1_s", "prev2_s", "woba_num", "woba_den"])
d = pa[(pa.slot_stype == "R") & ~pa.vs_starter & ~pa.pit_is_position_player].copy()
d["prev"] = pool(d.prev2_s) + pool(d.prev1_s)       # written in batting order
d = d[d.prev.isin(CFG_ORDER)]
t = rate(d, ["era", "prev"]).rename(columns={"rate": "lhp_share", "prev": "two_slots_before"})
w = woba(d, ["era", "prev"]).rename(columns={"prev": "two_slots_before", "woba": "slot_woba_raw"})
t = t.merge(w[["era", "two_slots_before", "slot_woba_raw"]], on=["era", "two_slots_before"])
write_table(t, "tab04_mutuality")
