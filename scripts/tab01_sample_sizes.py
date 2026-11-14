"""Sample sizes by season and era: replaces the back-of-envelope counts in DESIGN.md section 7."""
from pce.describe import *

pa = load("pa", ["season", "era", "slot_stype", "vs_starter", "pit_is_position_player", "vs_lhp", "tto"])
pa["lhh_slot"] = pa.slot_stype == "L"
pa["relief"] = ~pa.vs_starter & ~pa.pit_is_position_player
pa["lhh_relief"] = pa.lhh_slot & pa.relief
pa["lhh_relief_lhp"] = pa.lhh_relief & pa.vs_lhp


def summarize(g):
    return pd.Series({
        "pa": len(g),
        "lhh_slot_pa": g.lhh_slot.sum(),
        "lhh_slot_share": g.lhh_slot.mean(),
        "relief_share_of_lhh_pa": g.lhh_relief.sum() / g.lhh_slot.sum(),
        "lhh_relief_pa": g.lhh_relief.sum(),
        "lhp_share_lhh_relief": g.lhh_relief_lhp.sum() / g.lhh_relief.sum(),
        "lhp_share_all_relief": (g.relief & g.vs_lhp).sum() / g.relief.sum(),
    })


by_season = pa.groupby("season").apply(summarize, include_groups=False).reset_index()
by_era = pa.groupby("era").apply(summarize, include_groups=False).reset_index()
write_table(by_season, "tab01_sample_sizes_by_season")
write_table(by_era, "tab01_sample_sizes_by_era")
