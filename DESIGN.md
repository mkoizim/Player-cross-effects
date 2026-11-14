# DESIGN — Player cross-effects: the handedness-mix externality

Status: **Phase 1 draft, awaiting review.** Nothing below has been run against
data. Numbers marked *(prior)* are back-of-envelope figures from memory or
arithmetic, to be replaced by estimates in Phase 2.

---

## 1. The question, and what is wrong with it

**As posed:** How does the presence of a player on a roster affect the
performance of other players? Worked case: how much do right-handed hitters
(RHH) raise the production of left-handed hitters (LHH) in the same lineup by
constraining how opponents deploy pitchers, and how should that value be
credited to the RHH?

I think the worked case is answerable but the framing has five problems. The
design below is built around the repaired version.

### 1.1 The LHH does not get better; his matchup mix does

A hitter's skill is not changed by who bats next to him. What changes is the
distribution of pitchers he faces: how often he has the platoon disadvantage,
and how good those pitchers are. So the effect is mechanically bounded:

```
Δ production(LHH) ≈ Δ P(faces LHP) × (his platoon split vs. the LHP he would face)
                  + Δ (quality of pitcher faced, holding hand fixed)
```

That gives a causal chain with a well-powered first link (who pitches) and a
badly-powered last link (what the hitter does). The design measures the first
link directly and *derives* the last, instead of regressing wOBA on lineup
composition and hoping.

### 1.2 The plausible effect size is small, and the write-up has to be honest about that

*(prior)* An average LHH platoon split is on the order of 25–30 points of wOBA
(The Book, Tango/Lichtman/Dolphin 2007, puts LHH splits larger than RHH
splits; exact figures to be re-estimated from our data). Lefty specialists are
tougher than the average LHP on lefties, so the relevant split for the
marginal reliever might be 40–50 points.

Only relief-phase PAs can be affected — roughly 40% of a regular's PAs. If
lineup context moves the LHP share of those PAs by 10 percentage points (which
would be a big behavioral effect), the season-level effect is about
`0.40 × 0.10 × 0.045 ≈ 0.002 wOBA`, or **about one run per LHH per 600 PA**.
A lineup with four LHH would gain a few runs a season — a fraction of a win.

So the likely headline is "real, measurable in pitcher deployment, and worth
somewhere between zero and a few runs a year." That is still a useful result
for a front office (it tells them how much *not* to pay for lineup balance),
but anyone expecting a hidden half-win per righty should recalibrate now. If
the estimate comes out much larger than this, the first hypothesis should be
a bug or a confound, not a discovery.

### 1.3 "An all-LHH lineup is easy to neutralize" is itself a hypothesis, and may be wrong at the margin

LHP are scarce. A bullpen carries maybe one to three lefties, and RHP are the
default. Two mechanisms push in opposite directions as you add LHH:

- **Protection** (the premise): an LHH surrounded by RHH is costly to target
  with a lefty reliever, especially under the three-batter minimum.
- **Dilution** (the counter): each additional LHH competes for the same small
  supply of opposing lefty relief innings. A lone LHH in a righty lineup can
  have the opponent's best lefty saved for his high-leverage PA. In an
  all-lefty lineup, most LHH PAs still come against righties because the
  opponent runs out of lefties.

Which dominates is an empirical question and plausibly depends on the
configuration (clusters vs. alternation), not the count. The design treats
"exposure rises with LHH count" as H2, to be tested, not assumed.

### 1.4 The externality is mutual, so "credit the righties" is ill-posed

When a lefty reliever is forced to face the RHH batting behind an LHH, that
RHH gets a platoon-advantaged PA he would not otherwise have had. The LHH
"created" that value for the RHH just as the RHH "protected" the LHH. The
value is a property of the **mix**, not of right-handedness. Two consequences:

1. A player-attribute credit ledger ("Player X is worth +N protection runs")
   is not well-defined: the number depends on which teammates he is placed
   among and who he displaces. The well-defined object is the **marginal
   value of adding hitter X to lineup L in place of hitter Y**.
2. Existing metrics already book each PA to the hitter who took it. The
   protected LHH's better matchups show up in *his* wRC+; the RHH's bonus
   platoon PAs show up in *his*. So the practical front-office question is
   not "who gets credit" but "how much of each hitter's observed line would
   not travel with him to a differently-shaped lineup."

Proposed deliverable for credit (Phase 3, details in §8): (a) a
context-neutral restatement of each hitter's production, (b) a team-specific
marginal-value calculator, and (c) Shapley values over the lineup as an
accounting presentation of (b), clearly labeled as a convention, not a fact.

### 1.5 "Roster" vs. "lineup" are different treatments

The example is about the starting nine. But a right-handed bat on the *bench*
also deters a lefty reliever (he can pinch-hit), and it changes the LHH's
observed stats by removing his worst PAs. That is a roster effect operating
through a different channel. Phase 1–3 scope is the **lineup** effect; bench
composition enters as a control and moderator, and as a flagged extension.

### 1.6 Scope recommendation

The general question ("how does any player affect any other") is a research
program, not a project: protection, baserunner effects on the hitter,
catcher framing on pitchers, defense on pitchers, and so on each need their
own identification. I recommend doing the handedness case rigorously and
closing the write-up with a short section on which parts of the method
generalize. **Decision needed — see §11.**

---

## 2. Mechanisms and estimands

### 2.1 Channels by which lineup handedness can reach an LHH's production

| # | Channel | Who acts | Expected size |
|---|---|---|---|
| C1 | Reliever choice: lefty brought in (or left in) for the LHH | Opp. manager, in-game | Main channel |
| C2 | Starter alignment: opponent shuffles rotation / uses opener to throw a LHP starter at a lefty-heavy lineup | Opp. manager, pre-game | Small; rotations are sticky |
| C3 | Pinch-hitting: own manager pulls the LHH when the lefty arrives | Own manager | Changes *who* takes the PA; a selection problem as much as an effect |
| C4 | Pitch-level approach ("protection" in the traditional sense) | Opp. pitcher | Literature finds little; out of primary scope |

### 2.2 Estimands, in order of statistical power

Unit of analysis: a plate appearance by a lineup slot whose **starter** bats
left (true LHH; switch hitters handled separately, §4.4).

- **E1 — Exposure.** P(pitcher throws left | context, neighbor configuration).
  Binary, millions of PAs, directly reflects the opposing manager's decision.
- **E2 — Matchup value.** Expected wOBA of the batter–pitcher matchup,
  computed from *out-of-sample* talent estimates (regressed, hand-specific,
  prior-window) combined via odds-ratio. This captures pitcher quality as
  well as hand, with no outcome noise. **Primary outcome.**
- **E3 — Realized production.** wOBA (Retrosheet, all years) and xwOBA
  (Statcast, 2015+). Reported for validation; not expected to be powered
  (§7).
- **E4 — Lineup-level.** Sum of E2 across all nine slots, so that the RHH's
  own gains and losses are netted in. This is the quantity that maps to runs.

**Treatment** is not "number of RHH." It is the local structure the opposing
manager actually sees:

- `next1`, `next2`: batting side vs. a LHP of the next two lineup slots
  (the batters a new reliever must face under the three-batter minimum);
- `prev1`, `prev2`: same for the preceding slots (a lefty brought in for an
  earlier LHH may still be in);
- `n_L`: count of true LHH among the other eight starters (for dilution);
- pocket descriptors derived from these (isolated L, LL pair, LLL run,
  alternating).

Count-based summaries (the user's "as you add RHH") are then *computed from*
the fitted model by averaging over configurations, not estimated directly.

**Intent-to-treat by slot.** Because of C3, the PA in "the LHH's slot" may be
taken by a pinch hitter. Primary analysis assigns the outcome of the slot to
the configuration (ITT). A secondary analysis follows the player. The gap
between them is the pinch-hitting channel.

---

## 3. Hypotheses and what would falsify them

Smallest effect size of interest (SESOI), fixed now: **1 run per 600 PA per
LHH ≈ 0.002 wOBA** on E2/E3. On E1, **2 percentage points** of relief-phase
LHP share. Estimates whose confidence interval lies inside ±SESOI are reported
as "no effect of practical size," not as "inconclusive."

| ID | Hypothesis | Prediction | Falsified if |
|---|---|---|---|
| **H1** Protection exists | In the relief phase, an LHH whose next two slots bat right vs. LHP faces LHP less often, and has higher matchup value, than the same LHH followed by lefties | E1: negative effect of R-neighbors on P(LHP); E2: positive | E1 interval inside ±2 pp, or sign reversed; or E1 moves but E2 interval is inside ±0.002 (exposure changes but it does not matter) |
| **H2** Dose–response in count | Holding local neighbors fixed, more LHH elsewhere in the lineup changes exposure | *Two-sided by design:* protection story predicts exposure rises with `n_L`; dilution predicts it falls | Neither: `n_L` coefficient inside SESOI once local structure is controlled → count is irrelevant, only arrangement matters. (That would itself be a finding.) |
| **H3** Order matters beyond count | For a fixed handedness multiset, alternating arrangements produce higher lineup-level E4 than clustered ones | E4(alternating) > E4(clustered) | Difference inside SESOI×(number of LHH), i.e. arrangement is worth under ~1 run/season per LHH |
| **H4** The three-batter minimum amplified protection | The neighbor effect on E1/E2 is larger in 2021–25 than 2015–19; and post-rule it is weaker when the lefty could escape by ending the inning (two outs) | Neighbor × post > 0; neighbor × post × (outs<2) > 0 | Neighbor × post interval inside SESOI; **or** the neighbor effect grows equally with two outs (then something other than the rule is driving it); **or** event-study shows the trend already under way in 2017–19 at the same slope |
| **H5** Supply moderates | The effect scales with the number of lefty relievers available to the opponent that day | Effect ≈ 0 when the opposing bullpen has no LHP; increasing in available LHP | Effect of similar size against lefty-less bullpens → the "effect" is confounding, and H1's estimate is not credible |
| **H6** Mutuality | RHH following an LHH get more platoon-advantaged PAs vs. LHP relievers than RHH following RHH, more so post-2020 | Positive effect on RHH E2 | Interval inside SESOI → the externality is one-directional and §1.4's objection is weaker than I claim |
| **H7** Starter alignment (C2) | Lefty-heavier lineups draw LHP starters more often than schedule alone implies | Positive association after conditioning on opponent rotation composition | Interval excludes a 1 pp shift in LHP-start share per additional LHH regular |

Negative controls (should show nothing; if they show something, the design is
leaking):

- **NC1.** First PA of the game for each slot vs. the true starter: neighbors
  cannot change pitcher hand, so any neighbor "effect" on E2 here is selection.
- **NC2.** H5's zero-supply cell (above).
- **NC3.** Placebo rule dates: re-run H4 pretending the rule arrived in 2017
  or 2018.
- **NC4.** Position players pitching and blowouts (|score diff| ≥ 7 late):
  managers are not optimizing matchups.

---

## 4. Data

### 4.1 Sources

| Source | Use | Access | Notes |
|---|---|---|---|
| **Retrosheet event files** via `chadwickbureau/retrosheet` (GitHub) | Backbone: every PA, lineups, substitutions, batter/pitcher hand, base-out-score state | `git clone` pinned to a commit SHA | Verified reachable 2026-11-14; layout is `seasons/YYYY/*.EVA|EVN|ROS`, plus `gamelog/`, `reference/`. Complete through **2025**; 2026 has schedule only |
| **Chadwick tools** (`cwevent`, `cwgame`, `cwsub`) | Parse event files to tabular | Build from source at a pinned tag | Adds a C build step. Alternative is a pure-Python parser; decide in Phase 2 after testing fidelity on substitutions |
| **Chadwick register** (`chadwickbureau/register`) | Retrosheet ID ↔ MLBAM ID crosswalk | `git clone` pinned | Needed only to join Statcast |
| **Statcast** via `pybaseball` | xwOBA (lower-noise E3), pitch-level data for C4 if pursued | Scraped from Baseball Savant, cached to `data/raw/statcast/` | 2015+. Scrape is slow and occasionally changes schema; cache is the reproducibility unit, with a manifest of query dates |
| **Transactions / IL** (MLB Stats API) | Only if the injury design (§5.4) is pursued | HTTP, cached | Optional; not required for primary analysis |

Retrosheet requires this notice wherever its data is used, and it will go in
the README: *"The information used here was obtained free of charge from and
is copyrighted by Retrosheet. Interested parties may contact Retrosheet at
www.retrosheet.org."*

### 4.2 Study window

- **Primary rule comparison:** 2015–2019 (pre) vs. 2021–2025 (post).
- **2020** excluded from primary estimates and shown separately: 60 games,
  no fans, regional schedule, 28-man rosters, universal DH, seven-inning
  doubleheaders — and it is the rule's first year. Too many things at once.
- **Extended descriptive window:** 2000–2025, for the long-run decline of the
  one-batter lefty and for power on H1–H3 in the pre-rule regime.

### 4.3 Derived tables (Phase 2)

1. `pa` — one row per PA: game, inning, outs, bases, score, lineup slot,
   batter, pitcher, effective batting side, pitcher hand, starter-vs-reliever
   flag, times-through-order, pinch-hit flag, event, linear-weight value.
2. `lineup` — one row per team-game: nine starters with handedness, plus
   bench hitters available (from roster activity within ±N days).
3. `neighbors` — per PA: `next1/next2/prev1/prev2` handedness *as currently in
   the game* and *as started* (the latter is the ITT treatment).
4. `bullpen` — per team-game: relievers plausibly available, by hand, using
   appearance history in the trailing window and recent-days workload.
5. `talent` — per player-date: regressed, hand-specific wOBA talent estimates
   using only prior data (to build E2 without leakage).
6. Linear weights and run expectancy derived from the same Retrosheet data,
   by season — no external "guts" table, so the run conversion is
   reproducible in-repo.

### 4.4 Definitions that need care

- **Switch hitters** always take the platoon advantage, so from the opposing
  manager's view a switch-hitting neighbor is an R-neighbor when a lefty is
  contemplated. Coded as a third type `S`; primary specification pools S with
  R on the neighbor side and excludes S from the *subject* side.
- **Pitchers batting** (NL through 2021): the nine-hole is a pinch-hit locus
  and a free out. Coded as its own neighbor type `P`. Robustness: AL-park
  games only for pre-2022.
- **"Starter"** means the first pitcher *unless* he faces fewer than ~10
  batters by design (opener); then the bulk pitcher is the de facto starter
  for C2 purposes. Threshold to be set from the data and logged.
- **Relief phase**: any PA against a pitcher other than the game's first, plus
  PAs against the first pitcher from the third time through the order (where
  the hook decision is live). Sensitivity to this definition reported.

---

## 5. Identification

The core problem: lineups are chosen by a manager who knows the opposing
starter's hand, his own hitters' splits, and the opposing bullpen. Raw
correlations between "RHH in lineup" and "LHH production" are contaminated
before the first pitch. Four designs, from most to least reliance on
modelling assumptions. Agreement across them is the evidence; no single one
is decisive.

### 5.1 Design A — within-batter, within-context variation in neighbors (H1, H2, H3, H5, H6)

PA-level models of E1 and E2 on neighbor configuration with:

- batter × season fixed effects (compares the same hitter with different
  neighbors);
- opposing team × season fixed effects, and bullpen supply (§4.3-4);
- opposing **starter hand × batter** interaction — essential, because the
  own manager stacks RHH against LHP starters, which changes both the
  neighbors and the LHH's whole day;
- lineup slot, inning, outs, base state, score differential, leverage,
  times-through-order, park, home/away;
- neighbor **quality** (talent wOBA of `next1/next2`) so handedness is not a
  proxy for "good hitter behind him";
- standard errors clustered by game, with team-season clustering as a check.

Identifying variation: day-to-day lineup changes from rest days, injuries,
and platoons elsewhere in the order. The assumption is that, conditional on
the above, which hand bats behind a given LHH on a given day is unrelated to
anything else that determines which pitcher he faces. NC1 and NC2 test it.

### 5.2 Design B — the three-batter minimum as a policy shock (H4)

Rule 5.10(g), effective 2020: a pitcher must face three batters or finish the
half-inning. This changes the *price* of targeting an isolated LHH without
changing anyone's talent.

- Difference-in-differences: neighbor configuration × post-rule, on E1/E2.
- **Triple difference** using the rule's own escape hatch: with two outs, a
  lefty brought in for an LHH can retire him and be done, so the rule binds
  far less. Neighbor × post × (outs at entry < 2) isolates the rule from
  everything else that changed across eras.
- Event-study by season to show pre-trends; the one-batter lefty was already
  declining before 2020, so the test is a *break* in the neighbor gradient,
  not a level change in lefty usage.

### 5.3 Design C — the opposing manager's decision model (H3, credit allocation)

Model the pitching-change decision directly: at each batter-reliever decision
point, P(lefty faces this batter | upcoming three batters' handedness and
quality, available arms by hand, leverage, outs, era). This is the object
needed for counterfactuals: swap a hitter or reorder a lineup, re-simulate
pitcher deployment, and read off E2/E4 for every slot. Designs A and B
discipline it — the simulator must reproduce their reduced-form estimates
before its counterfactuals are trusted.

### 5.4 Design D — injury-driven lineup changes (optional corroboration)

When a regular RHH goes on the IL, compare LHH teammates' E1/E2 before vs.
during the absence, by whether the replacement bats right or left. Cleaner
exogeneity, much less data, and needs a transactions source. Proposed as a
stretch goal after A–C, only if they disagree or leave doubt.

---

## 6. Threats to validity

| Threat | Why it bites | Mitigation | Residual risk |
|---|---|---|---|
| Lineups respond to starter hand | Neighbors and the LHH's own matchup both depend on it | Starter-hand × batter interaction; stratify by starter hand | Low |
| Selection on gains | Managers alternate hands *because* a particular LHH has a big split | Batter FE absorb levels; interact treatment with batter's prior split; Design B does not depend on why the lineup looks as it does | Medium — ATE vs. effect-on-the-treated may differ; report both |
| Pinch-hitting censors LHH-vs-LHP PAs | The worst matchups vanish from the LHH's record | Slot-level ITT (§2.2) | Low |
| Slot confounds | Batting 2nd vs. 7th changes leverage and inning mix | Slot and context controls; within-slot comparisons | Low–medium |
| Neighbor quality ≠ neighbor hand | A star behind you changes pitching-around, IBB | Control neighbor talent; drop IBB in a robustness check | Low |
| Bullpen supply is measured with error | "Available" is inferred from usage | Multiple availability definitions; H5 uses roster count as a coarse fallback | Medium |
| Post-2020 era confounds | Universal DH (2022), pitch clock and shift limits (2023, the latter specifically helps LHH), 13-pitcher cap, runner on second in extras, fewer mid-inning changes generally | Triple difference on outs; year effects; E2 is immune to shift/clock outcome effects because it is built from talent, not outcomes; split post period at 2023 | Medium — this is the main reason H4 rests on the triple difference |
| Secular decline of specialists | Pre-trend in the thing the rule targeted | Event study; placebo dates (NC3) | Medium |
| E2 depends on talent-model choices | Regression amounts, split estimation | Out-of-sample only; sensitivity to priors; E1 needs no model at all | Low–medium |
| Low power on realized outcomes | Per-PA wOBA SD ≈ 0.5 | E2 primary; E3 as consistency check only (§7) | Accepted |
| General-equilibrium response | Opposing GMs carry lefties *because* lineups have LHH; we observe behavior at the current equilibrium only | State it; counterfactuals are valid for one team's marginal change, not for league-wide shifts | Not fixable — a stated limit |
| Multiple comparisons | Seven hypotheses, many specs | Primary spec per hypothesis fixed in this doc; everything else labelled exploratory | Low |
| External validity | 2021–25 behavior under current rules and roster limits | Report pre and post separately; recommend using post-rule estimates for decisions | Low |

---

## 7. Power — why realized production is not the primary outcome

*(prior, to be replaced)* About 185k PAs per season; roughly 40% by
left-side batters; roughly 40% of those in the relief phase → ~30k
subject PAs per season, ~150k per five-year regime.

- **E3:** splitting 150k PAs in half, the standard error of a difference in
  mean wOBA is about `0.5 × 2 / √150,000 ≈ 0.0026` — larger than the 0.002
  SESOI. Even the full 2000–2025 window barely gets there. A null on realized
  wOBA would say nothing.
- **E1:** a binary outcome with p≈0.3 has a standard error on a difference of
  about `0.46 × 2 / √150,000 ≈ 0.24 pp` — ample for a 2 pp SESOI, including
  the triple interaction.
- **E2:** no outcome noise at all; precision is limited by clustering and
  talent-estimate error, not by the PA lottery.

Hence: establish the effect on E1, value it through E2, and treat E3 as a
check that the sign and rough magnitude are not contradicted.

---

## 8. Credit allocation (Phase 3 plan, for review now because it shapes the model)

Given §1.4, three outputs:

1. **Context-neutral production.** For each hitter-season, restate wOBA as if
   he had faced the league-average pitcher mix for his batting side. The gap
   between actual and neutral is "context," decomposed into the part
   attributable to neighbor configuration (from Design C) and the rest
   (schedule, luck of the draw).
2. **Marginal lineup value.** `V(L ∪ {X} \ {Y}) − V(L)` where V is simulated
   lineup E4 in runs. This is the acquisition-relevant number, and it is
   explicitly team-specific. Split into X's own expected production and the
   **spillover** onto the other eight slots.
3. **Shapley values** of the spillover across the nine hitters, as a way to
   present (2) in a per-player table. Labeled as an accounting convention.
   If the interaction turns out to be essentially pairwise and local
   (adjacent slots), Shapley reduces to splitting each adjacent-pair surplus
   in half, and I will say so instead of dressing it up.

What I will **not** produce unless you overrule me: a single context-free
"protection runs" number per player, because §1.4 says it does not exist.

---

## 9. Phase plan and checkpoints

| Phase | Output | Stop condition |
|---|---|---|
| 1 | This document, `CLAUDE.md` | **Stop for review** (here) |
| 2 | Reproducible pipeline (`make data`), derived tables of §4.3, validation against published totals, descriptive figures: lefty-reliever usage over time; E1 by neighbor configuration, era, outs; lineup handedness distributions; bullpen supply; replaced *(prior)* numbers in §1.2 and §7 | **Stop for review before any modeling.** No regressions, no fixed-effects models, no simulator |
| 3 | Designs A–C (D if warranted), negative controls, credit allocation, README written for a front office | Final review |

Phase 2 descriptive work is limited to counts, rates, and cross-tabs. If a
descriptive cut makes a hypothesis look dead or the SESOI look wrong, that
gets raised at the Phase 2 checkpoint, and any change to hypotheses or
thresholds is recorded in the decision log with the date and the reason, so
it cannot pass as pre-specified.

Proposed layout:

```
DESIGN.md  CLAUDE.md  README.md  Makefile  pyproject.toml
src/pce/            # package: ingest, parse, derive, describe, model
scripts/            # one script per figure/table; no notebooks as source of truth
data/raw/           # gitignored: retrosheet clone, statcast cache, manifests
data/interim/       # gitignored: parsed events
data/processed/     # gitignored: derived tables (parquet)
reports/figures/    # committed outputs, each regenerable by a named script
tests/              # parser and derivation checks against known box-score totals
```

---

## 10. Related work (to verify and expand in the write-up)

- Tango, Lichtman, Dolphin, *The Book* (2007): platoon split sizes, how much
  to regress them, and the general finding that lineup-order effects are
  small. Sets the prior in §1.2.
- Bradbury & Drinen, "Pigou at the Plate: Externalities in Major League
  Baseball," *Journal of Sports Economics* 9(2), 2008: tests for
  on-deck-hitter spillovers at the PA level and finds them small. Closest
  precedent for the PA-level, neighbor-as-treatment setup; they study
  quality, not handedness.
- MLB Official Baseball Rule 5.10(g) (three-batter minimum, 2020).

Citations are from memory; page-level verification is a Phase 3 task. I have
not found a published estimate of the handedness-neighbor effect on reliever
deployment under the three-batter minimum, but I have not searched
systematically, and "not found" is not "does not exist." A literature check
is the first task of Phase 3 (or earlier, if you would rather know before
Phase 2 is built).

---

## 11. Decisions I need from you

1. **Scope.** Handedness case only, with a closing section on
   generalization (my recommendation) — or a broader survey of cross-effects
   with handedness as one chapter?
2. **Credit.** Accept §8's position that the deliverable is marginal lineup
   value plus a Shapley presentation, not a context-free per-player number?
3. **SESOI.** Is 1 run per LHH per 600 PA the right threshold for "matters"?
   A front office might care at 0.5; an article might not care below 3.
4. **Window.** 2015–19 vs. 2021–25 primary, 2000–2025 descriptive, 2020 set
   aside. Any objection?
5. **Bench/roster channel (§1.5).** Control-and-moderator only (my
   recommendation), or promote to a hypothesis?
6. **Design D and the literature search.** Defer both to Phase 3, or pull
   the literature search forward?
7. **Toolchain.** OK to build the Chadwick C tools from source in the
   pipeline (most faithful parser), with `uv` for Python dependencies?
