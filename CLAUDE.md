# CLAUDE.md

## Purpose

Portfolio MLB research project. Question: how does a player's presence in a
lineup change the performance of his teammates? Worked case: how much does
lineup handedness mix (RHH around LHH) change the pitchers LHH face, what is
that worth in runs, how did the three-batter minimum (2020) change it, and
how should the value be attributed.

`DESIGN.md` is the source of truth for hypotheses, estimands, identification,
falsification thresholds, and scope. Read it before doing any analysis work.
Final deliverable is `README.md`, written for an MLB front-office reader.

## Phase and checkpoint rules — do not skip

| Phase | Work | Gate |
|---|---|---|
| 1 | `DESIGN.md` | Commit, then **STOP** for user review |
| 2 | Reproducible data pipeline + descriptive analysis only | **STOP** for user review before any modeling |
| 3 | Modeling, credit allocation, README write-up | Final review |

- **Current phase: 1 — awaiting review of DESIGN.md.** Update this line when
  a phase is approved.
- Never begin the next phase without explicit user approval in the
  conversation.
- "Descriptive" in Phase 2 means counts, rates, cross-tabs, and plots of
  them. No regressions, fixed-effects models, or simulators until Phase 3.
- Hypotheses, primary specifications, and effect-size thresholds are fixed in
  `DESIGN.md`. Changing any of them after seeing data requires user sign-off
  and an entry in the decision log below stating what changed and why.
- Report nulls and results that contradict the premise as plainly as
  positive ones. The user wants critique, not confirmation.

## Data sources and where raw data lives

| Source | Location (gitignored) | How obtained |
|---|---|---|
| Retrosheet event files, rosters, game logs | `data/raw/retrosheet/` | `git clone https://github.com/chadwickbureau/retrosheet`, pinned to a commit SHA recorded in the pipeline config. Layout: `seasons/YYYY/`, `gamelog/`, `reference/`. Complete through 2025 as of 2026-11-14 |
| Chadwick register (ID crosswalk) | `data/raw/register/` | `git clone https://github.com/chadwickbureau/register`, pinned |
| Statcast | `data/raw/statcast/` | `pybaseball`, cached per date range with a manifest of query dates. Used only where Retrosheet cannot answer (xwOBA, pitch-level) |
| Parsed / derived tables | `data/interim/`, `data/processed/` | Built by the pipeline; never hand-edited |

Retrosheet is the backbone; Statcast is supplementary. Any use of Retrosheet
data must carry its notice in the README: "The information used here was
obtained free of charge from and is copyrighted by Retrosheet. Interested
parties may contact Retrosheet at www.retrosheet.org."

## Conventions

- Python. Dependencies declared in `pyproject.toml` and locked (`uv`).
- **Raw and derived data are never committed.** `data/` is gitignored. The
  repo must rebuild everything from a clean clone with documented commands.
- **Every figure and table is regenerable by a script** in `scripts/`, one
  script per output, writing to `reports/figures/` or `reports/tables/`. No
  figure in the README without a script that produces it. Notebooks may be
  used for exploration but are never the source of a reported result.
- Pin external data by commit SHA or query date; record pins in config, not
  in prose.
- Fixed random seeds for anything stochastic.
- Tests in `tests/` validate parsing and derived tables against known
  totals (e.g. league PA counts, team game counts).
- Numbers in prose come from pipeline output, not from memory. Anything
  quoted from memory is marked as a prior until replaced.
- Units: wOBA for rates, runs for value; linear weights derived in-repo from
  Retrosheet, not imported from an external table.
- Commit on the designated working branch; no pull requests unless asked.

## Decision log

Append-only. Newest last. Each entry: date, decision, reason, who decided.

| Date | Decision | Reason | By |
|---|---|---|---|
| 2026-11-14 | Chadwick Bureau GitHub mirror confirmed as Retrosheet source; event files complete through 2025, 2026 schedule only (earliest season not checked) | Checked repo tree directly | Claude (verified) |
| 2026-11-14 | Proposed: reframe from "RHH improve LHH" to "handedness mix changes pitcher deployment"; primary outcome is expected matchup value, not realized wOBA | Hitter skill does not change, only matchup mix; realized wOBA is underpowered at the plausible effect size (DESIGN §1.1, §7) | Claude — **pending user approval** |
| 2026-11-14 | Proposed: credit = team-specific marginal lineup value + Shapley presentation; no context-free per-player "protection runs" | The externality is mutual and configuration-dependent (DESIGN §1.4, §8) | Claude — **pending user approval** |
| 2026-11-14 | Proposed: SESOI of 1 run per LHH per 600 PA (0.002 wOBA), 2 pp on LHP exposure | Needed to make hypotheses falsifiable (DESIGN §3) | Claude — **pending user approval** |
| 2026-11-14 | Proposed: 2015–19 vs 2021–25 primary; 2020 set aside; 2000–2025 descriptive | 2020 bundles the rule with too many other changes (DESIGN §4.2) | Claude — **pending user approval** |
