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

- **Current phase: 3 complete — README is the final write-up, awaiting final
  review.** Phase 3 approved by user 2026-11-14.
- Never begin the next phase without explicit user approval in the
  conversation.
- "Descriptive" in Phase 2 means counts, rates, cross-tabs, and plots of
  them. No regressions, fixed-effects models, or simulators until Phase 3.
- Hypotheses, primary specifications, and effect-size thresholds are fixed in
  `DESIGN.md`. Changing any of them after seeing data requires user sign-off
  and an entry in `docs/decisions.md` stating what changed and why.
- Report nulls and results that contradict the premise as plainly as
  positive ones. The user wants critique, not confirmation.

## Data sources and where raw data lives

| Source | Location (gitignored) | How obtained |
|---|---|---|
| Retrosheet event files, rosters, game logs | `data/raw/retrosheet/` | Fetched by `python -m pce.fetch` at the SHA pinned in `config.toml`. Layout: `seasons/YYYY/` (event files `*.EVA/*.EVN`, rosters `*.ROS`, game log `GLYYYY.TXT`, filename case varies). Complete through 2025 as of 2026-11-14 |
| Chadwick tools (`cwevent`, `cwgame`) | source `data/raw/chadwick-src/`, binaries `data/raw/chadwick/` | Cloned at the tag pinned in `config.toml` and built from source by `pce.fetch`; needs `autoreconf`, `make`, `gcc` |
| Chadwick register (ID crosswalk) | `data/raw/register/` | `git clone https://github.com/chadwickbureau/register`, pinned |
| Statcast, MLB stats API | not used | **Do not script against MLB-hosted sites** (`baseballsavant.mlb.com`, `statsapi.mlb.com`, so also `pybaseball` Statcast pulls): MLB Terms of Use prohibit automated collection, and the data notice allows only individual, non-commercial, non-bulk use. Needs written permission from MLB or an explicit user decision |
| Parsed / derived tables | `data/interim/`, `data/processed/` | Built by the pipeline; never hand-edited |

Retrosheet is the backbone; Statcast is supplementary. Any use of Retrosheet
data must carry its notice in the README: "The information used here was
obtained free of charge from and is copyrighted by Retrosheet. Interested
parties may contact Retrosheet at www.retrosheet.org."

## How to run

```
make data       # fetch pinned inputs, build Chadwick, parse, derive  (~8 min after clone)
make describe   # descriptive tables and figures (scripts/tab*, scripts/fig*)
make models     # Phase 3 models, lineup value, credit (scripts/m*)
make test       # checks, incl. PA totals vs Retrosheet game logs by team-season
make check-reports   # regenerated tables and figure records (*.json) match committed exactly; PNG pixels not compared
```

Code: `src/pce/` (`fetch`, `parse`, `derive`, `talent`, `describe` helpers,
`model` = analysis frame and fixed-effects fits, `lineup` = value function and Shapley); one script
per output in `scripts/`; pins and definitions in `config.toml`. Handedness
types are L / R / S (switch) / P (pitcher batting); "RR", "anyL" etc. describe
the next two lineup slots with S counted as R.

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

Kept in [`docs/decisions.md`](docs/decisions.md). Append-only, newest last.
Each entry: date, decision, reason, who decided.
