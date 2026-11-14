# Player cross-effects: lineup handedness and pitcher deployment

How much does the handedness of the hitters around a left-handed batter change
which pitchers he faces, what is that worth, and how did the three-batter
minimum (2020) change it?

**Status: work in progress.** This is not the final write-up.

| Phase | State | Read |
|---|---|---|
| 1. Design | approved | [`DESIGN.md`](DESIGN.md) |
| 2. Data pipeline and descriptive analysis | complete, under review | [`reports/phase2_descriptives.md`](reports/phase2_descriptives.md) |
| 3. Modeling, credit allocation, final write-up | not started | — |

Nothing in the repository so far is a causal estimate. The Phase 2 report
contains raw rates only.

## Reproduce

Requires `git`, `uv`, a C toolchain (`gcc`, `make`, `autoconf`, `automake`,
`libtool`) and network access to github.com.

```
make data       # clone pinned Retrosheet data, build Chadwick tools, parse, derive
make describe   # write every table and figure under reports/
make test
```

Inputs are pinned by commit in [`config.toml`](config.toml). Raw and derived
data are written under `data/` and are not committed. Each file in
`reports/figures/` and `reports/tables/` is produced by the script of the same
name in `scripts/`.

## Data

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at
[www.retrosheet.org](https://www.retrosheet.org).

Event files are read from the Chadwick Bureau mirror
(`chadwickbureau/retrosheet`) and parsed with the Chadwick tools
(`chadwickbureau/chadwick`).
