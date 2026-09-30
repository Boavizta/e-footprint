# Shadow-review observations

Protocol and activation state: [`tasks.md`](tasks.md). Primary: GPT-6 Astra/high.
Shadow: GPT-6.1 Sol/high. Five distinct feature slots across both repositories.

## Features

Add one row at enrollment and update it across that feature's runs. Link the feature's task
list and its evidence below. States are `OBSERVING`, `COMPLETE` or `PARTIAL`; closed partial
features retain their slot. Ratios are Sol/Astra for matched initial-review pairs, with the
API and credit ratios identified separately. `Unknown` is distinct from zero.

| # | Driving repo / feature · writer session | State · runs/tasks covered | Consequential findings: both / Sol missed / Astra missed | Noise: Astra / Sol | Initial cost ratios: API / credits | Initial active-time ratio |
|---|---|---|---|---|---|---|
| 1 | [e-footprint-interface / simplified-inputs](../../../../e-footprint-interface/specs/features/simplified-inputs/tasks.md) · `01a0f1e1-c424-73d2-836e-f3323fa15723` | OBSERVING · Run A in progress | Unknown | Unknown | Unknown / Unknown | Unknown |

## Supporting evidence

Add one collapsible `<details>` section per enrolled feature. Keep the table above sufficient
for a quick review. Inside, record only:

- **Pair provenance:** run/task, immutable commit ranges per repo, both reviewer session IDs,
  actual model/effort and review tier. Identify incomplete or non-comparable pairs.
- **Measurements:** per reviewer and initial turn, input/cache-read/cache-write/output tokens,
  active minutes, API-equivalent cost and Codex credits, with price-card date and coverage.
  Keep shadow overhead separate from the feature's ordinary implementation and review cost.
- **Consequential differences:** short finding, severity, supported evidence and disposition;
  link existing plan decisions or relevant commits. Include shared misses discovered later
  when they affect the recommendation. Omit routine findings and passing checks.
- **Interpretation:** only patterns or limitations that change the recommendation, such as
  an uncovered risk surface, a recurring miss or a meaningful noise difference.

Raw transcripts and private ledgers remain outside git. Do not create separate per-run logs.

## Recommendation

Written once all five feature rows close, following Task 2. Until the user decides, Astra
remains the primary reviewer and the experiment does not enroll additional features.
