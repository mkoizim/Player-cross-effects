"""Follow-ups on lineup arrangement (questions raised at final review).

1. Whose batting line the arrangement runs land on (lefties vs. righties).
2. For a one-hitter swap: how much falls on the swapped slot itself vs. the other eight.
3. Do teams avoid adjacent lefties? Actual vs. random orderings of the same nine, by team (2025).
4. How much is left: each 2025 lineup vs. (a) its best single swap of two adjacent hitters and
   (b) the best ordering of the same nine by this model alone, which ignores every other reason
   a lineup is ordered the way it is and so is an upper bound.
5. How much variation the main estimate rests on.
"""
import itertools

from pce.describe import *
from pce.lineup import *
from pce.model import *

RNG = np.random.default_rng(20261114)
d = frame(2021, 2025)
beta, vcov, m = estimate(design(d))
B = beta.to_numpy()
games = d.groupby(["game_id", "bat_team"]).ngroups
rel_pa = d[d.relief].groupby("slot").size().reindex(range(1, 10)) / games
scale = pd.read_parquet(PROCESSED / "weights.parquet").query("season >= 2021").woba_scale.mean()
w = (rel_pa / scale * 162).to_numpy()


def slot_values(types):
    """Spillover runs per 162 games landing on each of the nine slots."""
    own, pL = onehot(types)
    return np.array([loadings(own, pL, np.where(np.arange(9) == i, w, 0.0)) @ B for i in range(9)])


def total(types):
    return float(slot_values(types).sum())


# 1. whose line: three and four lefties, spread vs. block ---------------------------------
rows = []
for a, b in (("LRRLRRLRR", "LLLRRRRRR"), ("LRLRLRRLR", "LLLLRRRRR")):
    va, vb = slot_values(a), slot_values(b)
    la = sum(v for v, t in zip(va, a) if t == "L") - sum(v for v, t in zip(vb, b) if t == "L")
    ra = sum(v for v, t in zip(va, a) if t == "R") - sum(v for v, t in zip(vb, b) if t == "R")
    rows.append({"spread": a, "block": b, "total_runs": va.sum() - vb.sum(),
                 "on_lefties_lines": la, "on_righties_lines": ra,
                 "per_lefty": la / a.count("L"), "per_righty": ra / a.count("R")})
write_table(pd.DataFrame(rows), "m11_whose_line")

# 2. one-hitter swaps: own slot vs. the other eight ----------------------------------------
ex = []
base = "LRLRRLRRR"
for label, new in (("replace the #2 righty with a lefty", "LLLRRLRRR"),
                   ("replace the #3 lefty with a righty", "LRRRRLRRR"),
                   ("replace the #4 righty with a switch hitter", "LRLSRLRRR"),
                   ("replace the #5 righty with a lefty", "LRLRLLRRR"),
                   ("replace the #8 righty with a lefty", "LRLRRLRLR")):
    dv = slot_values(new) - slot_values(base)
    i = [k for k in range(9) if new[k] != base[k]][0]
    ex.append({"base_lineup": base, "change": label, "new_lineup": new, "total_runs": dv.sum(),
               "on_that_slot": dv[i], "on_the_other_eight": dv.sum() - dv[i]})
write_table(pd.DataFrame(ex), "m11_swap_decomposition")

# 3-4. 2025 lineups -----------------------------------------------------------------------
lu = load("lineup")
lu = lu[lu.season == 2025]
types = lu.pivot(index=["game_id", "team"], columns="slot", values="stype").apply(lambda r: "".join(r), axis=1)
tg = types.rename("types").reset_index()


def adj(t):                                             # adjacent lefty pairs, wrapping 9 -> 1
    return sum(t[i] == "L" and t[(i + 1) % 9] == "L" for i in range(9))


info = {}
for t in tg.types.unique():
    perms = {"".join(p) for p in itertools.permutations(t)} if len(set(t)) > 1 else {t}
    perms = list(perms)
    vals = np.array([total(p) for p in perms])
    swaps = [t] + [t[:i] + t[i + 1] + t[i] + t[i + 2:] for i in range(8)]
    info[t] = {"actual": total(t), "random": vals.mean(), "best": vals.max(),
               "best_adjacent_swap": max(total(s) for s in swaps),
               "adj_actual": adj(t), "adj_random": np.mean([adj(p) for p in perms]),
               "n_L": t.count("L")}
tg = tg.join(pd.DataFrame(info).T, on="types")
per = tg.groupby("team").agg(
    games=("actual", "size"), lefties_per_game=("n_L", "mean"),
    adjacent_pairs_per_game=("adj_actual", "mean"), adjacent_pairs_if_random=("adj_random", "mean"),
    actual_runs=("actual", lambda x: x.sum() / 162), random_runs=("random", lambda x: x.sum() / 162),
    best_swap_runs=("best_adjacent_swap", lambda x: x.sum() / 162), best_runs=("best", lambda x: x.sum() / 162),
).reset_index()
per["vs_random"] = per.actual_runs - per.random_runs
per["left_with_one_adjacent_swap"] = per.best_swap_runs - per.actual_runs
per["left_vs_best_order_upper_bound"] = per.best_runs - per.actual_runs
per["share_of_possible_captured"] = per.vs_random / (per.best_runs - per.random_runs)
write_table(per.sort_values("vs_random", ascending=False), "m11_team_arrangement_detail_2025")
lg = pd.DataFrame([{
    "adjacent_pairs_per_game_actual": tg.adj_actual.mean(), "adjacent_pairs_per_game_random": tg.adj_random.mean(),
    "teams_below_random_adjacency": int((per.adjacent_pairs_per_game < per.adjacent_pairs_if_random).sum()),
    "share_of_lineups_with_no_adjacent_lefties": (tg.adj_actual == 0).mean(),
    "share_possible_without_adjacency": (tg.n_L <= 4).mean(),
    "median_team_left_one_swap": per.left_with_one_adjacent_swap.median(),
    "median_team_left_upper_bound": per.left_vs_best_order_upper_bound.median(),
    "max_team_left_upper_bound": per.left_vs_best_order_upper_bound.max()}])
write_table(lg, "m11_league_arrangement_2025")

# 5. variation behind the main estimate ---------------------------------------------------
s = lhh_relief(d)
g = s.groupby("bs_sh").anyL.agg(["mean", "size"])
varies = g[(g["mean"] > 0) & (g["mean"] < 1)]
K = era_constants().loc[("L", "2021–25")]
write_table(pd.DataFrame([{
    "pa": len(s), "games": s.game_id.nunique(), "hitter_seasons": s.bs.nunique(),
    "comparison_groups": len(g), "groups_with_both_kinds_of_day": len(varies),
    "pa_in_those_groups": int(varies["size"].sum()), "share_of_pa": varies["size"].sum() / len(s),
    "share_pa_with_lefty_next_two": s.anyL.mean(),
    "relief_share_of_lefty_pa": K.relief_share, "woba_scale": K.woba_scale}]), "m11_main_estimate_sample")
