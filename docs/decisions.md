# Decision log

Append-only. Newest last. Each entry: date, decision, reason, who decided.

| Date | Decision | Reason | By |
|---|---|---|---|
| 2026-11-14 | Chadwick Bureau GitHub mirror confirmed as Retrosheet source; event files complete through 2025, 2026 schedule only (earliest season not checked) | Checked repo tree directly | Claude (verified) |
| 2026-11-14 | Proposed: reframe from "RHH improve LHH" to "handedness mix changes pitcher deployment"; primary outcome is expected matchup value, not realized wOBA | Hitter skill does not change, only matchup mix; realized wOBA is underpowered at the plausible effect size (DESIGN §1.1, §7) | Claude; **approved by user 2026-11-14** |
| 2026-11-14 | Proposed: credit = team-specific marginal lineup value + Shapley presentation; no context-free per-player "protection runs" | The externality is mutual and configuration-dependent (DESIGN §1.4, §8) | Claude; **approved by user 2026-11-14** |
| 2026-11-14 | Proposed: SESOI of 1 run per LHH per 600 PA (0.002 wOBA), 2 pp on LHP exposure | Needed to make hypotheses falsifiable (DESIGN §3) | Claude; **approved by user 2026-11-14** |
| 2026-11-14 | Proposed: 2015–19 vs 2021–25 primary; 2020 set aside; 2000–2025 descriptive | 2020 bundles the rule with too many other changes (DESIGN §4.2) | Claude; **approved by user 2026-11-14** |
| 2026-11-14 | Phase 1 approved; all DESIGN §11 recommendations accepted; broader cross-effects survey deferred; literature search pulled forward | User message | User |
| 2026-11-14 | Chadwick tools pinned at v0.9.5, built from source; Python deps via `uv` | Approved toolchain | User / Claude |
| 2026-11-14 | Literature search run from search summaries only; no published estimate of the neighbor-handedness effect found | Article hosts blocked by network policy; full texts unread | Claude |
| 2026-11-14 | Two-way rule: a starting pitcher with ≥150 PA that season is typed as a hitter, else P | Ohtani-type seasons; value in `config.toml` | Claude |
| 2026-11-14 | Bullpen supply = distinct relievers used by the team in the trailing 14 days, game day excluded | No roster-status data in Retrosheet; limits listed in phase2 report §5 | Claude |
| 2026-11-14 | `talent` table deferred to Phase 3 | Shrinkage estimates are a model; Phase 2 gate forbids models | Claude |
| 2026-11-14 | Statcast ingestion deferred | Savant host blocked; only needed for Phase 3 xwOBA check | Claude |
| 2026-11-14 | Proposed (post-data, see DESIGN §12.4; **approved by user 2026-11-14** except opener, see below): RR-vs-anyL as primary contrast; mid-inning contrast as exploratory addition to H4; pinch-hitting response as H8; opener = starter with <10 BF | Raised by Phase 2 descriptives | Claude |
| 2026-11-14 | Phase 2 approved; Phase 3 to proceed. Broaden: bullpen supply and pinch-hitting (H8) added; RR-vs-anyL primary; two-out test kept as pre-specified, mid-inning contrast exploratory | User message | User |
| 2026-11-14 | Opener = start of ≤10 batters by a pitcher who starts in <50% of his appearances that season; bulk pitcher is de facto starter (H7 only) | User's definition, replacing the proposed <10 BF rule; 50% cut-off is Claude's reading of "usually don't start" | User / Claude |
| 2026-11-14 | Statcast not used; no environment change requested | Only an optional xwOBA check; Retrosheet wOBA serves as E3 | Claude |
| 2026-11-14 | Design C implemented as a reduced-form lineup value function, not a manager decision model; Design D not run | Effects small and near-additive; recorded as deviations in DESIGN §13.3 | Claude |
| 2026-11-14 | E2 pitcher term centred within pitcher-hand × batter-side | First version double-counted the platoon effect; found via calibration check | Claude |
| 2026-11-14 | Value verdicts judged in runs per 600 full-season PA | DESIGN §3 threshold was ambiguous about which PAs | Claude |
| 2026-11-14 | README gains a dollar conversion and a free-vs-paid reading of "small"; rates (10 runs/win, $8M/win) are external assumptions in `config.toml` `[valuation]`, table from `scripts/m09_dollar_values.py` | User asked what benchmark justifies "not worth much"; the 1-run SESOI was a convention, not cost-derived | User / Claude |
| 2026-11-14 | Created cloud environment `player-cross-effects` allowing MLB, FanGraphs, SABR, RePEc and IZA hosts; this session switched to it | User asked for access to be obtained within each source's terms | User (approved) / Claude |
| 2026-11-14 | MLB-hosted data (Statcast, stats API) not used | Read MLB Terms of Use: automated scripts prohibited; data notice: non-bulk, non-commercial only. One sample transactions request made before reading the clause was deleted | Claude |
| 2026-11-14 | Literature re-reviewed from full text; README "Prior work" section added | Article hosts now reachable | Claude |
| 2026-11-14 | Dollars per win set to $11.23M (range $6.74M–$12.84M) | Read the FanGraphs source; the earlier $8M came from a search summary and was wrong for this article | Claude |
| 2026-11-14 | Design D run using Retrosheet-inferred absences (`m10`); result inconclusive | IL data unavailable under MLB terms; absences of ≥10 games by regulars used instead | Claude |
| 2026-11-14 | README corrected after user review: "every team avoids adjacent lefties" → teams roughly halve adjacency (29 of 30 below random; 38% of lineups still have a pair); "about 3 runs on the rest of the lineup" → 2 on the swapped slot, 1 on the other eight; "a run or so left" now backed by a best-ordering upper bound; righties' role as separators and the WAR bookkeeping stated explicitly. Tables from `scripts/m11_lineup_followups.py` | Three README claims were stronger than what had been computed | User (questions) / Claude |
