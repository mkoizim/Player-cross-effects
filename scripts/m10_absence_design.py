"""Design D (DESIGN.md 5.4), built from Retrosheet alone: extended absences of regular
right-side hitters as a shock to the lefties who usually bat in front of them.

MLB's injured-list data are not used (MLB's terms of use prohibit scripted collection), so an
"absence" is inferred: a hitter who started at least 15 of his team's previous 20 games and then
does not bat in any of the next 10. Most such spells are injuries; some are demotions or
suspensions, which serve the same purpose here.

For a lefty on that team, exposure = the share of his starts in the 20 games before the absence
in which the absent hitter occupied one of the two slots behind him. The absence changes who
bats behind exposed lefties for reasons unrelated to the opposing bullpen.

  first stage   anyL    ~ during x exposure      (does the absence put a lefty behind him?)
  reduced form  outcome ~ during x exposure
  IV            outcome ~ anyL, instrumented by during x exposure
Fixed effects: lefty x spell, spell x during (anything that changes for the whole team),
opposing team-season, inning, base-out, score. Clustered by spell.
"""
from pce.describe import *
from pce.model import *

PRE, MIN_PRE_STARTS, GAP, POST = 20, 15, 10, 20

d = frame(2000, 2025)
d = d[d.season != 2020]
lu = load("lineup")
lu = lu[lu.season != 2020]
tg = load("team_game", ["season", "game_id", "team", "date"]).sort_values(["season", "team", "date", "game_id"])
tg["g"] = tg.groupby(["season", "team"]).cumcount()
lu = lu.merge(tg[["game_id", "team", "g"]], on=["game_id", "team"])
ngames = tg.groupby(["season", "team"]).g.max() + 1

# games in which each player batted at all (so a bench appearance is not an absence)
batted = d[["season", "bat_team", "game_id", "bat_id"]].drop_duplicates().merge(
    tg[["game_id", "team", "g"]].rename(columns={"team": "bat_team"}), on=["game_id", "bat_team"])
batted_g = batted.groupby(["season", "bat_team", "bat_id"]).g.apply(np.array)

spells = []
right = lu[lu.stype.isin(["R", "S"])]
for (season, team, pid), x in right.groupby(["season", "team", "starter_id"]):
    n = ngames[(season, team)]
    starts = np.zeros(n, bool)
    starts[x.g.to_numpy()] = True
    played = np.zeros(n, bool)
    played[batted_g.get((season, team, pid), np.array([], int))] = True
    cs = np.concatenate([[0], np.cumsum(starts)])
    for t in range(PRE, n - GAP + 1):
        if cs[t] - cs[t - PRE] >= MIN_PRE_STARTS and starts[t - 1] and not played[t:t + GAP].any():
            back = np.flatnonzero(played[t:])
            length = int(back[0]) if len(back) else n - t
            spells.append({"season": season, "team": team, "absent_id": pid, "t0": t, "length": length})
            break                                   # first spell per player-season
sp = pd.DataFrame(spells)
sp["spell"] = np.arange(len(sp))

# who started in the two slots behind each slot, each team-game
wide = lu.pivot(index=["game_id", "team"], columns="slot", values="starter_id")
arr = wide.to_numpy()
nxt = []
for s in range(9):
    nxt.append(pd.DataFrame({"game_id": wide.index.get_level_values(0), "team": wide.index.get_level_values(1),
                             "slot": s + 1, "n1_id": arr[:, (s + 1) % 9], "n2_id": arr[:, (s + 2) % 9]}))
nxt = pd.concat(nxt)
lefty_starts = lu[lu.stype == "L"].merge(nxt, on=["game_id", "team", "slot"])

s = lhh_relief(d).merge(tg[["game_id", "team", "g"]].rename(columns={"team": "bat_team"}), on=["game_id", "bat_team"])
parts = []
for r in sp.itertuples():
    ls = lefty_starts[(lefty_starts.season == r.season) & (lefty_starts.team == r.team)
                      & lefty_starts.g.between(r.t0 - PRE, r.t0 - 1)]
    if ls.empty:
        continue
    behind = (ls.n1_id == r.absent_id) | (ls.n2_id == r.absent_id)
    ex = behind.groupby(ls.starter_id).agg(["mean", "size"])
    ex = ex[ex["size"] >= 8]["mean"].rename("exposure")
    w = s[(s.season == r.season) & (s.bat_team == r.team)
          & s.g.between(r.t0 - PRE, r.t0 + min(r.length, POST) - 1) & s.starter_id.isin(ex.index)].copy()
    if w.empty:
        continue
    w["spell"] = r.spell
    w["during"] = (w.g >= r.t0).astype(int)
    w["exposure"] = w.starter_id.map(ex)
    parts.append(w)
x = pd.concat(parts, ignore_index=True)
x["z"] = x.during * x.exposure
x["unit"] = x.starter_id + "_" + x.spell.astype(str)
x["spell_during"] = x.spell.astype(str) + "_" + x.during.astype(str)
fe = "unit + spell_during + opp_ts + inning_c + outs_bases + score_c"

summ = pd.DataFrame([{
    "absence_spells": sp.spell.nunique(), "spells_with_exposed_lefties": x[x.exposure > 0].spell.nunique(),
    "median_length_games": sp.length.median(), "lefty_spell_units": x.unit.nunique(), "relief_pa": len(x),
    "relief_pa_exposed_half_or_more": int((x.exposure >= 0.5).sum())}])
write_table(summ, "m10_absence_sample")

# raw before/during, by exposure group
x["grp"] = np.select([x.exposure == 0, x.exposure < 0.5], ["not behind him", "sometimes behind him"],
                     "usually behind him")
raw = x.groupby(["grp", "during"]).agg(pa=("anyL", "size"), any_lefty_next_two=("anyL", "mean"),
                                       vs_lhp=("vs_lhp", "mean"), e2=("e2", "mean")).reset_index()
write_table(raw, "m10_absence_raw")

rows = []
for label, sub in (("2000–25", x), ("2015–25", x[x.season >= 2015])):
    rows.append(tidy(fit(f"anyL ~ z | {fe}", sub, cluster="spell"), ["z"], sample=label,
                     model="first stage", outcome="lefty in next two"))
    for y in ("vs_lhp", "e2"):
        rows.append(tidy(fit(f"{y} ~ z | {fe}", sub, cluster="spell"), ["z"], sample=label,
                         model="reduced form", outcome=y))
        rows.append(tidy(fit(f"{y} ~ 1 | {fe} | anyL ~ z", sub, cluster="spell"), ["anyL"], sample=label,
                         model="IV", outcome=y))
        rows.append(tidy(fit(f"{y} ~ anyL | {fe}", sub, cluster="spell"), ["anyL"], sample=label,
                         model="OLS, same sample", outcome=y))
res = pd.concat(rows, ignore_index=True)
res["t"] = res.coef / res.se
write_table(res, "m10_absence_design")
