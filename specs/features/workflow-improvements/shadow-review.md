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
| 1 | [e-footprint-interface / simplified-inputs](../../../../e-footprint-interface/specs/features/simplified-inputs/tasks.md) · `01a0f1e1-c424-73d2-836e-f3323fa15723` | OBSERVING · Run A, tasks 1–3 paired | 2 / 0 / 0 | 0 / 0 | 0.184 / 0.180 | 1.089 |

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

<details>
<summary>e-footprint-interface / simplified-inputs — Run A</summary>

Task 1: library `b718142e075f1e4216af7ea556b75be1a920082d..84d8a950a4262e84ceb27a7fe389e45130fbf4dd`;
interface `741979aefdf7c4e9f8677654d43b300683fbf6c0..5cf35c224683ff46914c2ca73e1634a3ab70a104`.
Both initial reviews were independent, read-only, FULL; both found the stale benchmark page-object call
and the existing two-slot deep-link System-ID collision (P2 correctness). Both were accepted for correction.
Minor copy differences do not constitute consequential misses. No unsupported suggestions.

| Task | Reviewer · native session | Actual model / effort | Initial input / cache read / cache write / output | Active minutes | API-equivalent USD | Codex credits |
|---|---|---|---|---|---|---|
| 1 | Primary · `01a0f214-5c1a-72b0-b479-3a376d9c3634` | gpt-6-astra / high | 719 / 1,826,108 / 141,503 / 7,586 | 2.531 | 3.981386 | 90.690700 |
| 1 | Shadow · `01a0f214-78cb-7a42-b9a7-3710968b0842` | gpt-6.1-sol / high | 1,040 / 2,156,573 / 167,744 / 8,346 | 2.741 | 0.720557 | 15.917133 |
| 2 | Primary · `01a0f21c-6dd9-70a0-8c0b-eeecc633c0c7` | gpt-6-astra / high | 371 / 316,702 / 38,126 / 2,595 | 1.122 | 0.926737 | 20.785550 |
| 2 | Shadow · `01a0f21c-9251-7bd3-89e2-a2856682777b` | gpt-6.1-sol / high | 366 / 363,387 / 44,084 / 3,235 | 1.013 | 0.179631 | 3.939717 |
| 3 | Primary · `01a0f223-9b28-7052-af62-5cbd5f1e764b` | gpt-6-astra / high | 602 / 870,942 / 90,552 / 4,105 | 1.687 | 2.214112 | 49.693300 |
| 3 | Shadow · `01a0f223-b6f9-7ed1-af21-a73f2bd8b9b8` | gpt-6.1-sol / high | 764 / 1,203,319 / 90,759 / 6,181 | 2.062 | 0.410567 | 9.129698 |

Task 2: library `ac2b44d1..99962fad`; Task 3: interface `bcd306eb..7fc193b1`.
Each pair used independent, read-only FULL initial passes with no consequential findings or noise.

Price-card date: 2026-09-30. Measurements use only collector turn 0; primary fixes and global review
are excluded. Standard processing mode is assumed because logs do not expose it. Shadow amounts
are experiment overhead. Current evidence covers the semantic rename, framework validation and domain catalog;
the remaining persistence/edit tasks are not yet observed. The feature slot stays open for Runs B–C.

</details>

## Recommendation

Written once all five feature rows close, following Task 2. Until the user decides, Astra
remains the primary reviewer and the experiment does not enroll additional features.
