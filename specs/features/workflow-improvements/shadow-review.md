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
| 1 | [e-footprint-interface / simplified-inputs](../../../../e-footprint-interface/specs/features/simplified-inputs/tasks.md) · `01a0f282-6cc2-7352-81c4-93d8c71d40b1` | OBSERVING · Run A complete, tasks 1–5 paired; Run B complete, tasks 6–8 paired; Run C pending | 10 / 3 / 3 | 0 / 0 | 0.156 / 0.152 | 0.975 |

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
| 1 | Shadow · `01a0f214-78cb-7a42-b9a7-3710968b0842` | gpt-6.1-sol / high | 1,040 / 2,156,573 / 167,744 / 8,346 | 2.741 | 0.720557 | 15.917132 |
| 2 | Primary · `01a0f21c-6dd9-70a0-8c0b-eeecc633c0c7` | gpt-6-astra / high | 371 / 316,702 / 38,126 / 2,595 | 1.122 | 0.926737 | 20.785550 |
| 2 | Shadow · `01a0f21c-9251-7bd3-89e2-a2856682777b` | gpt-6.1-sol / high | 366 / 363,387 / 44,084 / 3,235 | 1.013 | 0.179631 | 3.939717 |
| 3 | Primary · `01a0f223-9b28-7052-af62-5cbd5f1e764b` | gpt-6-astra / high | 602 / 870,942 / 90,552 / 4,105 | 1.687 | 2.214112 | 49.693300 |
| 3 | Shadow · `01a0f223-b6f9-7ed1-af21-a73f2bd8b9b8` | gpt-6.1-sol / high | 764 / 1,203,319 / 90,759 / 6,181 | 2.062 | 0.410567 | 9.129698 |
| 4 | Primary · `01a0f22b-ca6d-7623-98ed-f313749e93fd` | gpt-6-astra / high | 581 / 1,829,989 / 107,775 / 7,309 | 2.949 | 3.548437 | 81.974975 |
| 4 | Shadow · `01a0f22b-e4d2-7e01-8485-0086187b4f50` | gpt-6.1-sol / high | 1,073 / 1,923,003 / 94,820 / 9,322 | 3.218 | 0.524716 | 11.932657 |
| 5 | Primary · `01a0f23f-becd-7492-aaf4-dde15677918e` | gpt-6-astra / high | 576 / 1,623,595 / 103,034 / 6,839 | 2.853 | 3.259230 | 75.041125 |
| 5 | Shadow · `01a0f23f-e0cd-7453-bbf5-cede48651b7a` | gpt-6.1-sol / high | 958 / 1,786,767 / 94,360 / 9,594 | 3.322 | 0.512433 | 11.631318 |

Task 2: library `ac2b44d1..99962fad`; Task 3: interface `bcd306eb..7fc193b1`.
Each pair used independent, read-only FULL initial passes with no consequential findings or noise.

Task 4: interface `9e94e06d..8e881aaab1e5f1ca964f05e2edc3c0fd88c6f510`; both initial passes FULL.
Both found complete definitions retaining addresses of disconnected objects lost by System-only copying/reminting.
Accepted correction follows [IMPL-DECISION-02](../../../../e-footprint-interface/specs/features/simplified-inputs/plan.html#impl-decision-02).
Sol alone found the P1 rejected-import recovery path publishing incoming settings onto the old model when Redis is absent;
its supported isolated reproduction was accepted for correction by the primary reviewer. No unsupported suggestions.

Task 5: library `a76ce657..d80d5e7f`; interface `d17c0e58..e228911f`. Both independent FULL initial
passes found the same two consequential defects: equal-output timeseries edits discarding authored settings/provenance,
and numeric zero satisfying an empty-only conditional choice (P2). Both were corrected through the library-owned
matching rule; see [IMPL-DECISION-03](../../../../e-footprint-interface/specs/features/simplified-inputs/plan.html#impl-decision-03).
No unsupported suggestions. Global review is not part of the paired measurements.

Price-card date: 2026-09-30. Measurements merge both repository ledgers and use only collector turn 0; primary fixes and global review
are excluded. Standard processing mode is assumed because logs do not expose it. Shadow amounts
are experiment overhead. Current evidence covers the semantic rename, framework validation, domain catalog, persistence
and atomic edits. Persistence adds one consequential Sol-only finding; browser authoring/consumption remain unobserved. The feature slot stays open for Runs B–C.

</details>

<details>
<summary>e-footprint-interface / simplified-inputs — Run B</summary>

Task 6: interface `0f6f64659d2bcaeff847d99dafd41dc9caeea347..71696aae1570b6d6f36333ee2577b3df53935dcd`.
Both independent initial passes were read-only, FULL. Both found saved Sankey diagrams after the first
losing their automatic initialization under the new mutation guard (P2). Astra alone found GET-based
object deletion bypassing serialization (P1); Sol alone found export anchors retaining browser-native
navigation during saves (P2). All three were accepted and corrected in `0481af00923dfeab5c93a901ccf6a103905803aa`.
The deliberate saved-diagram read/write separation is recorded in
[IMPL-DECISION-04](../../../../e-footprint-interface/specs/features/simplified-inputs/plan.html#impl-decision-04).
No unsupported suggestions.

Task 7: interface `34b1e2e62eb1439f73f337affdb514ef98be0c28..ad20fb53ad606cb95ff0eac5cd3ebb7c14fb50b7`.
Both independent initial passes were read-only, FULL. Both found repeated Configure reads overwriting a
new draft and compact object navigation incorrectly entering the editor/dirty-state path. Astra alone
found complete configuration forms exceeding Django's 1,000-parameter limit on supported large models (P2);
Sol alone found a delayed Configure response being parked across a model switch and resurfacing on return (P2).
All four were accepted and corrected in `c95b11bb2e69856522e64d00c7a66d82e64f1c73`.
The bounded form transport choice is recorded in
[IMPL-DECISION-05](../../../../e-footprint-interface/specs/features/simplified-inputs/plan.html#impl-decision-05).
No unsupported suggestions.

Task 8: interface `5cfe21b02f228beb3272afafa4826112b48f3049..3f0b344b05749088c8397d1469bd582e804dd1f9`.
Both independent initial passes were read-only, FULL. Both found nested Storage creation settings omitted
from the composite panel submission and dependency checkbox locks being overwritten during mutation-guard
settlement (P2). Astra alone found a same-bookmark membership save erasing a failed help draft (P2).
All three were accepted and corrected in `753c63d94baa46599c06e2e530247803a8ded214`.
No unsupported suggestions.

Global browser validation additionally exposed expanded panel controls covering the adjacent bookmark's
click target, missed by both Task 8 initial passes. The existing absolute-positioned disclosure was
replaced with normal-flow panel layout in `b336dfb98427f79ab24d177ccc55fbee794c25ec`.
This identifies a visual integration coverage limit of the read-only initial passes; the unpaired global
review and its corrections are excluded from paired measurements.

| Task | Reviewer · native session | Actual model / effort | Initial input / cache read / cache write / output | Active minutes | API-equivalent USD | Codex credits |
|---|---|---|---|---|---|---|
| 6 | Primary · `01a0f28d-0f0f-78e2-951a-ddfc2ff91e64` | gpt-6-astra / high | 459 / 2,146,560 / 146,340 / 9,530 | 4.408 | 4.456900 | 102.276250 |
| 6 | Shadow · `01a0f28d-4b72-7610-af93-c322893c0e44` | gpt-6.1-sol / high | 1,191 / 1,519,222 / 135,128 / 9,498 | 3.580 | 0.587104 | 12.988505 |
| 7 | Primary · `01a0f2c5-67e1-76f2-819d-6ddf64ed6d9c` | gpt-6-astra / high | 821 / 3,265,645 / 163,509 / 13,590 | 6.072 | 5.997218 | 139.711125 |
| 7 | Shadow · `01a0f2c5-8d4a-71b0-8af8-472e88018be7` | gpt-6.1-sol / high | 727 / 3,109,395 / 176,681 / 16,597 | 5.976 | 0.920066 | 20.793138 |
| 8 | Primary · `01a0f2e8-aa54-7f22-b08e-adeabef72fcb` | gpt-6-astra / high | 750 / 2,676,004 / 129,580 / 10,490 | 4.534 | 4.827754 | 112.595100 |
| 8 | Shadow · `01a0f2e8-d4e1-70a2-b764-aa0cb925e59c` | gpt-6.1-sol / high | 869 / 2,169,975 / 159,697 / 9,509 | 3.595 | 0.713068 | 15.830488 |

Price-card date: 2026-09-30. Measurements merge both repository ledgers and select only collector turn 0;
primary fixes and global review are excluded. Standard processing mode is assumed because logs do not expose it.
Shadow amounts are experiment overhead. The feature slot remains open for Run C.

</details>

## Recommendation

Written once all five feature rows close, following Task 2. Until the user decides, Astra
remains the primary reviewer and the experiment does not enroll additional features.
