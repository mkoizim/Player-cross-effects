"""Raw before/after contrasts around the three-batter minimum, with the rarer lefty-follows
configurations pooled for sample size: next two both right ("RR") vs. at least one lefty ("anyL").

Two views: (a) plate appearances, (b) relief entries whose first batter is a starting lefty.
The last table is arithmetic on these raw numbers, not an estimate: it converts an exposure gap
into wOBA and runs using the observed relief-phase platoon split and relief share of PAs.
"""
from pce.describe import *

ERAS2 = ["2015–19", "2021–25"]


def gaps(t, keys):
    g = t.pivot(index=keys, columns="grp", values=["lhp_share", "n"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    g["anyL_minus_RR_pp"] = (g.lhp_share_anyL - g.lhp_share_RR) * 100
    g["se_naive_pp"] = 100 * np.sqrt(
        g.lhp_share_anyL * (1 - g.lhp_share_anyL) / g.n_anyL + g.lhp_share_RR * (1 - g.lhp_share_RR) / g.n_RR)
    return g.reset_index()


# (a) plate appearances
d = relief_lhh()
d = d[d.cfg.isin(CFG_ORDER)]
d["grp"] = np.where(d.cfg == "RR", "RR", "anyL")
d["cut"] = np.where(d.outs == 2, "2 outs", "0-1 outs")
a_all = gaps(rate(d, ["era", "grp"]).rename(columns={"rate": "lhp_share"}), ["era"])
a_all.insert(1, "cut", "all")
a_outs = gaps(rate(d, ["era", "cut", "grp"]).rename(columns={"rate": "lhp_share"}), ["era", "cut"])
pa_t = pd.concat([a_all, a_outs], ignore_index=True)
write_table(pa_t, "tab06_pa_level_RR_vs_anyL")

# (b) relief entries
ap = load("appearances")
e = ap[~ap.is_starter & ~ap.position_player & (ap.first_slot_stype == "L") & ap.first_bat_starter].copy()
e["cfg"] = pool(e.first_next1_c) + pool(e.first_next2_c)
e = e[e.cfg.isin(CFG_ORDER)]
e["grp"] = np.where(e.cfg == "RR", "RR", "anyL")
e["vs_lhp"] = e.throws == "L"
cuts = {
    "all": pd.Series("all", index=e.index),
    "outs": pd.Series(np.where(e.entry_outs == 2, "2 outs", "0-1 outs"), index=e.index),
    "timing": pd.Series(np.where(e.entry_mid_inning, "mid-inning", "start of inning"), index=e.index),
    "mid-inning by outs": pd.Series(np.where(~e.entry_mid_inning, None,
                                    np.where(e.entry_outs == 2, "mid-inning, 2 outs", "mid-inning, 0-1 outs")),
                                    index=e.index),
}
parts = []
for name, c in cuts.items():
    x = e.assign(cut=c).dropna(subset=["cut"])
    parts.append(gaps(rate(x, ["era", "cut", "grp"]).rename(columns={"rate": "lhp_share"}), ["era", "cut"]))
en_t = pd.concat(parts, ignore_index=True)
write_table(en_t, "tab06_entry_level_RR_vs_anyL")

# change in the gap, 2015-19 -> 2021-25
rows = []
for label, t in (("PA", pa_t), ("entry", en_t)):
    w = t[t.era.isin(ERAS2)].pivot(index="cut", columns="era", values=["anyL_minus_RR_pp", "se_naive_pp"])
    ch = pd.DataFrame({
        "level": label,
        "gap_2015_19_pp": w[("anyL_minus_RR_pp", "2015–19")],
        "gap_2021_25_pp": w[("anyL_minus_RR_pp", "2021–25")],
    })
    ch["change_pp"] = ch.gap_2021_25_pp - ch.gap_2015_19_pp
    ch["se_naive_pp"] = np.sqrt(w[("se_naive_pp", "2015–19")] ** 2 + w[("se_naive_pp", "2021–25")] ** 2)
    rows.append(ch.reset_index())
write_table(pd.concat(rows, ignore_index=True), "tab06_change_in_gap")

# implied magnitude (arithmetic, not an estimate)
splits = pd.read_csv(TABLES / "tab02_platoon_splits.csv")
sizes = pd.read_csv(TABLES / "tab01_sample_sizes_by_era.csv").set_index("era")
wts = load("weights")
wts["era"] = wts.season.map(lambda s: "2015–19" if 2015 <= s <= 2019 else "2021–25" if s >= 2021 else None)
scale = wts.dropna(subset=["era"]).groupby("era").woba_scale.mean()
out = []
for er in ERAS2:
    gap = pa_t[(pa_t.era == er) & (pa_t.cut == "all")].anyL_minus_RR_pp.iloc[0] / 100
    split = splits[(splits.era == er) & (splits.bats == "L") & (splits.role == "reliever")].split.iloc[0]
    relief = sizes.loc[er, "relief_share_of_lhh_pa"]
    dw = gap * split * relief
    out.append({"era": er, "exposure_gap": gap, "lhh_split_vs_relievers": split,
                "relief_share_of_pa": relief, "implied_woba_all_pa": dw,
                "implied_runs_per_600_pa": dw / scale[er] * 600})
write_table(pd.DataFrame(out), "tab06_implied_magnitude")
