# Nova.csv Dataset Analysis
This analysis labels and categorizes 15 `(claim, truth)` pairs to understand patterns in the data. Labels and taxonomy below are **for this analysis only** — the system does not use a fixed mutation taxonomy.

> **Important nuance:** Several "mutations" are **logically consistent** with the truth (e.g., "above X", "under Y", "at least Z") but are **coarser / less informative**. *Technically true isn't always faithful* — it can still mislead via framing or omission.

---

## Dataset Overview

- **Source:** `hacktrace-cam/Nova.csv`
- **Columns:** `claim` (external claim), `truth` (internal fact)
- **Rows:** 15 pairs
- **Domains:** COVID-19, entertainment, finance, astronomy, politics, comics

---

## Dataset Analysis

### Main Mutation Types in Nova.csv
| Type | Description |
|------|-------------|
| hard_contradiction | Claim cannot be true given the fact |
| unsupported_detail | Adds number/date/mechanism not supported |
| entailed_but_coarsened | Truth implies claim, but claim is less precise |
| misleading_framing | Coarsening likely changes takeaway |
| scope_under-specification | Weaker/lower-detail scope than truth |
| temporal_mismatch | Wrong or shifted timeframe |
| context_omission | Omits key qualifiers/caveats |
| interpretation_as_fact | Subjective inference as objective claim |
| faithful | No material change |

### Pair-by-Pair Analysis

| # | Claim Summary | Truth Summary | Mutation Type | Severity |
|---|---------------|---------------|---------------|----------|
| 1 | 30M Amharic speakers (22M native + 25M others) | 47M speakers (22M native + 25M others) | **hard_contradiction** | High |
| 2 | Under 650k cases, <29,950 deaths, 150+ countries | 645k+ cases, ~29,900 deaths, 190+ countries | **entailed_but_coarsened**, **scope_under-specification** | Low |
| 3 | Forbes: franchise above $400M | Club worth ~$500M, revenue $78M | **entailed_but_coarsened**, **entity_ambiguity** | Medium |
| 4 | Before 7 Oct 2019: 4.2B YouTube views | As of 9 Oct 2019: 4.2B views | **temporal_mismatch** | Low |
| 5 | 452,999+ cases before 26 Mar | As of 25 Mar: 453k+ cases | **entailed_but_coarsened** | None |
| 6 | 16 Apr Michigan: 5k cases, 150 deaths | Same numbers, same date | faithful | None |
| 7 | Venus orbits within Earth's orbit | Same, plus technical details | faithful | None |
| 8 | 16 reviews, 81% Rotten Tomatoes | Same numbers, plus consensus quote | faithful (minor omission) | None |
| 9 | Doctor Manhattan removed ~10 years | Same, plus "reasons unknown" + consequences | **context_omission** | Low |
| 10 | Born to Die: at least 3 years on chart | 300+ weeks (~5.8 years) on chart | **entailed_but_coarsened**, **misleading_framing** | Medium |
| 11 | <413k cases, <107k recoveries | >411k cases, 107.2k recoveries | **hard_contradiction** | High |
| 12 | Ontario: schools closed 2 weeks | Same, plus dates + court suspension | **context_omission** | Low |
| 13 | Scotland: "high number" untested with symptoms | 0.15% tested; many can't test | **interpretation_as_fact** | Medium |
| 14 | After Mar 2019: 535M+ views | Feb 2019: 530M+ views | **unsupported_detail**, **temporal_mismatch** | Medium |
| 15 | 73 evacuated, 5+ from Dominican Republic | 73 evacuated, 6 from Dominican Republic | **entailed_but_coarsened** | None |


### Mutation Type Frequency (Nova.csv)

| Category | Count | Pairs |
|----------|------:|-------|
| hard_contradiction | 2 | 1, 11 |
| entailed_but_coarsened | 5 | 2, 3, 5, 10, 15 |
| temporal_mismatch | 2 | 4, 14 |
| context_omission | 2 | 9, 12 |
| interpretation_as_fact | 1 | 13 |
| unsupported_detail | 1 | 14 |
| faithful | 4 | 6, 7, 8, 15 |

### Key Patterns

1. **Coarsening is common** — Claims logically implied by truth but less precise. Ideal for debate.
2. **Hard contradictions are rarer** — Clear, high-signal failures.
3. **Timeframe wording matters** — "Before" vs "as of", date shifts.
4. **Context and interpretation** — Omissions and subjective inferences matter.
