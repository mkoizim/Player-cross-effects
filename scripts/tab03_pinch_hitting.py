"""The pinch-hitting channel (C3): who actually bats in a lefty's slot against relievers."""
from pce.describe import *

d = relief_lhh(["starter_batting", "bat_hand_cd"])
d["pit"] = np.where(d.vs_lhp, "LHP", "RHP")
d["replaced"] = ~d.starter_batting
d["replaced_by_rhb"] = d.replaced & (d.bat_hand_cd == "R")
t = d.groupby(["era", "pit"]).agg(pa=("replaced", "size"), starter_replaced_share=("replaced", "mean"),
                                  batter_hits_right_share=("replaced_by_rhb", "mean")).reset_index()
w_all = woba(d, ["era", "pit"]).rename(columns={"woba": "slot_woba"})
w_st = woba(d[d.starter_batting], ["era", "pit"]).rename(columns={"woba": "starter_only_woba"})
t = t.merge(w_all[["era", "pit", "slot_woba"]], on=["era", "pit"]).merge(
    w_st[["era", "pit", "starter_only_woba"]], on=["era", "pit"])
write_table(t, "tab03_pinch_hitting")
