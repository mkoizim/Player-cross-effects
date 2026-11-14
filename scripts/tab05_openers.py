"""Starter length by season, to set the opener threshold (DESIGN.md section 4.4)."""
from pce.describe import *

ap = load("appearances")
s = ap[ap.is_starter]
t = s.groupby("season").agg(
    starts=("bf", "size"), median_bf=("bf", "median"),
    share_bf_under_10=("bf", lambda x: (x < 10).mean()),
    share_bf_under_7=("bf", lambda x: (x < 7).mean()),
    share_bf_under_4=("bf", lambda x: (x < 4).mean())).reset_index()
write_table(t, "tab05_openers")
