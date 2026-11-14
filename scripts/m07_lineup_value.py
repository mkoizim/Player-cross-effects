"""Lineup value, order effects (H3) and credit allocation.

1. Estimate neighbor effects on expected matchup value for L, R and S slots (2021-25).
2. H3: for a fixed set of hitters, how much does arrangement move lineup spillover?
3. Credit: Shapley split of each 2025 starting lineup's spillover, summed by player and team;
   team arrangement value vs. random orderings of the same nine.
"""
from pce.describe import *
from pce.lineup import *
from pce.model import *

RNG = np.random.default_rng(20261114)
d = frame(2021, 2025)
x = design(d)
beta, vcov, m = estimate(x)
se = np.sqrt(np.diag(vcov))
coefs = pd.DataFrame({"term": TERMS, "coef_woba": beta.to_numpy(), "se": se, "n": m._N})
coefs[["own_type", "neighbor"]] = coefs.term.str.split("_", expand=True)
write_table(coefs, "m07_neighbor_coefficients")

# slot weights: relief-phase PAs per team-game by slot, and runs per unit wOBA per 162 games
games = d.groupby(["game_id", "bat_team"]).ngroups
rel_pa = d[d.relief].groupby("slot").size().reindex(range(1, 10)) / games
scale = pd.read_parquet(PROCESSED / "weights.parquet").query("season >= 2021").woba_scale.mean()
w = (rel_pa / scale * 162).to_numpy()
write_table(pd.DataFrame({"slot": range(1, 10), "relief_pa_per_game": rel_pa.to_numpy(),
                          "runs_per_woba_point_per_162": w / 1000}), "m07_slot_weights")
B = beta.to_numpy()
V = vcov.to_numpy()


def val(types):
    own, pL = onehot(types)
    return loadings(own, pL, w)


def contrast(a, b):
    lo = val(a) - val(b)
    est, s = float(lo @ B), float(np.sqrt(lo @ V @ lo))
    return est, s


# --- H3: arrangement, holding the set of hitters fixed -----------------------------------
rows, arr = [], []
for k in (2, 3, 4, 5):
    perms = ["".join("L" if i in c else "R" for i in range(9)) for c in itertools.combinations(range(9), k)]
    vals = np.array([float(val(p) @ B) for p in perms])
    best, worst = perms[int(vals.argmax())], perms[int(vals.argmin())]
    spread = "".join("L" if i in set(np.round(np.linspace(0, 9, k, endpoint=False)).astype(int)) else "R"
                     for i in range(9))
    block = "L" * k + "R" * (9 - k)
    for name, a, b in (("best vs worst arrangement", best, worst), ("spread out vs one block", spread, block)):
        est, s = contrast(a, b)
        rows.append({"lefties": k, "contrast": name, "lineup_a": a, "lineup_b": b, "runs_per_162": est, "se": s,
                     "lo": est - 1.96 * s, "hi": est + 1.96 * s, "threshold_runs": float(k),
                     "verdict": verdict(est - 1.96 * s, est + 1.96 * s, float(k))})
    arr.append({"lefties": k, "arrangements": len(perms), "mean": vals.mean(), "sd": vals.std(),
                "min": vals.min(), "max": vals.max()})
write_table(pd.DataFrame(rows), "m07_h3_arrangement")
write_table(pd.DataFrame(arr), "m07_h3_arrangement_distribution")

# --- marginal value examples: swap one hitter, split into spillover on the other eight ----
ex = []
base = "LRLRRLRRR"
for label, new in (("replace the #2 righty with a lefty", "LLLRRLRRR"),
                   ("replace the #3 lefty with a righty", "LRRRRLRRR"),
                   ("replace the #4 righty with a switch hitter", "LRLSRLRRR"),
                   ("move the #3 lefty to #5 (swap with a righty)", "LRRRLLRRR")):
    est, s = contrast(new, base)
    ex.append({"base_lineup": base, "change": label, "new_lineup": new, "spillover_runs_per_162": est, "se": s})
write_table(pd.DataFrame(ex), "m07_marginal_examples")

# --- credit: 2025 starting lineups --------------------------------------------------------
lu = load("lineup")
lu = lu[lu.season == 2025]
wide = lu.pivot(index=["game_id", "team"], columns="slot", values="stype")
types = wide.apply(lambda r: "".join(r), axis=1).rename("types")
allst = load("lineup")
allst = allst[(allst.season >= 2021) & allst.stype.isin(TYPES)]
q = allst.stype.value_counts(normalize=True).reindex(TYPES).to_numpy()

uniq = types.unique()
phi = {t: shapley(t, beta, w, q) / 162 for t in uniq}                 # runs per game, by slot
tot = {t: float(val(t) @ B) / 162 for t in uniq}
rand = {}
for t in uniq:
    perms = ["".join(RNG.permutation(list(t))) for _ in range(200)]
    rand[t] = float(np.mean([val(p) @ B for p in perms])) / 162

names = pd.concat([pd.read_parquet(p) for p in sorted((PROCESSED.parent / "interim").glob("roster_2025.parquet"))])
names = names.drop_duplicates("player_id").set_index("player_id")
names = (names["first"] + " " + names["last"]).rename("name")

long = lu.merge(types.reset_index(), on=["game_id", "team"])
long["credit"] = [phi[t][s - 1] for t, s in zip(long.types, long.slot)]
pl = long.groupby("starter_id").agg(starts=("credit", "size"), credit_runs=("credit", "sum"),
                                    bats=("stype", "first"), team=("team", "last")).reset_index()
pl["name"] = pl.starter_id.map(names)
pl["credit_runs_per_150_starts"] = pl.credit_runs / pl.starts * 150
pl = pl[pl.starts >= 100].sort_values("credit_runs", ascending=False)
write_table(pl[["name", "team", "bats", "starts", "credit_runs", "credit_runs_per_150_starts"]],
            "m07_shapley_credit_2025")
summ = pl.groupby("bats").credit_runs_per_150_starts.describe()[["count", "mean", "std", "min", "max"]].reset_index()
write_table(summ, "m07_shapley_credit_2025_summary")

tg = types.reset_index()
tg["spillover"] = tg.types.map(tot)
tg["random_order"] = tg.types.map(rand)
team = tg.groupby("team").agg(games=("spillover", "size"), spillover_runs=("spillover", "sum"),
                              random_order_runs=("random_order", "sum")).reset_index()
team["arrangement_runs"] = team.spillover_runs - team.random_order_runs
write_table(team.sort_values("arrangement_runs", ascending=False), "m07_team_arrangement_2025")

# --- figure: the neighbor coefficients ----------------------------------------------------
style()
fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6), sharex=True)
lab = {"p2L": "lefty two slots before", "p1L": "lefty one slot before", "n1L": "lefty one slot after",
       "n2L": "lefty two slots after", "n12": "extra when both of\nthe next two are lefties"}
for ax, t, nm in zip(axes, TYPES, ["Left-handed hitter", "Right-handed hitter", "Switch hitter"]):
    c = coefs[coefs.own_type == t].set_index("neighbor").reindex(NB)
    yy = np.arange(len(NB))[::-1]
    ax.axvline(0, color=INK2, linewidth=1)
    ax.hlines(yy, (c.coef_woba - 1.96 * c.se) * 1000, (c.coef_woba + 1.96 * c.se) * 1000, color=BLUE, linewidth=2)
    ax.plot(c.coef_woba * 1000, yy, "o", color=BLUE, markersize=7)
    ax.set_yticks(yy, [lab[n] for n in NB] if t == "L" else [""] * len(NB))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x")
    ax.set_title(nm)
    ax.set_xlabel("points of expected wOBA,\nrelief-phase PAs")
fig.tight_layout()
save(fig, "m07_neighbor_coefficients",
     "2021–25. Effect on the slot's expected matchup value of a left-only hitter in each nearby slot. 95% intervals.")
