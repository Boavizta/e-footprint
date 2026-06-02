# Duration-aware impact attribution — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — EcoLogits external-API server: spread impact over request duration

**Goal:** Make the EcoLogits external-API server book each job's per-request energy / usage-GWP /
embodied-GWP across the hours the request actually runs, instead of dumping the whole amount in the
request's start hour. This is the duration-aware *source* footprint that the attribution rework
(Tasks 2–3) then carries up the tree — landing it first gives that work a correct, multi-hour server
profile to aggregate rather than a masked single-hour spike. Small, low-risk, independently correct;
totals unchanged (redistribution in time only).

**Ported from the `ecologits-video` branch** (commits `2245b7d7` + `e7d42d38`), which implemented this
against `EcoLogitsExternalAPIServerBase` in `ecologits_external_api_server_base.py`. **That class does
not exist on `dev`** — the branch's shared LLM/video server-infrastructure refactor is not here. On
`dev` the identical bug lives in **`EcoLogitsGenAIExternalAPIServer`** (`ecologits_external_api.py:45`).
This task re-applies the fix onto that class — it is a port, not a cherry-pick.

**Approach:**
- Add a `_spread_over_request_duration(job, per_request_value)` helper mirroring the network/storage
  per-hour-spread idiom already on `dev` (`job.py:174-175`):
  `per_request_value × (1h / job.request_duration) × job.hourly_avg_occurrences_across_usage_patterns`,
  returning `EmptyExplainableObject()` when the per-request value is unset (a job with no usage patterns,
  whose `request_duration` is still its 0 s default).
- Swap the five `EcoLogitsGenAIExternalAPIServer` aggregation methods from
  `request_* × job.hourly_occurrences_across_usage_patterns` (raw start-hour counts) to the helper:
  `update_instances_fabrication_footprint` (`request_embodied_gwp`, ~line 73),
  `update_instances_energy` (`request_energy`, ~83), `update_energy_footprint` (`request_usage_gwp`, ~92),
  `update_dict_element_in_fabrication_impact_repartition_weights` (`request_embodied_gwp`, ~98),
  `update_dict_element_in_usage_impact_repartition_weights` (`request_usage_gwp`, ~107).
- **Not a raw→avg swap.** `request_*` are per-request *totals*, so the `× (1h / request_duration)` factor
  is what preserves magnitude — over the run window `Σ_hours (request_X / duration × avg_occurrences) =
  request_X × occurrence_count`, the same total, redistributed in time.
- The data this needs is already on `dev`: `hourly_avg_occurrences_across_usage_patterns` is computed for
  the ecologits job (inherited via `Job`), and `request_duration` comes from `generation_latency`
  (`ecologits_external_api.py:331-333`).

**Files touched:**
- `efootprint/builders/external_apis/ecologits/ecologits_external_api.py` — add `_spread_over_request_duration`; convert the five `EcoLogitsGenAIExternalAPIServer` aggregation methods.
- `specs/bug-fixes/ecologits-server-duration-spread/task.md` — port the sibling task write-up (the spec references it; it now lands here as the Task 1 record).
- `CHANGELOG.md` — `### Fixed` entry: EcoLogits server spreads per-request impact over `request_duration`.

**Tests added/changed:**
- `tests/builders/external_apis/ecologits/test_ecologits_generative_ai.py` (or a new `test_*_server` module — `test_ecologits_external_api_server_base.py` does **not** exist on `dev`) — port the branch's unit assertions against `EcoLogitsGenAIExternalAPIServer`: a 2 h request spreads at half-rate per hour (`request_X × 0.5 × avg_occ`); a 1 h request collapses to the old single-hour result (no regression); the no-jobs case stays `EmptyExplainableObject`.
- **Do not port** the branch's `test_ecologits_video_integration.py` multi-hour test — it depends on video-generation infra absent from `dev`. The real multi-hour end-to-end coverage is provided by Task 2's repro test (a job whose `request_duration` outlives its journey), which drives a spread server footprint through the whole attribution chain.

**Acceptance:**
- The five `EcoLogitsGenAIExternalAPIServer` aggregation outputs span the run window of a `>1h` job (non-zero in more than one hour bucket) instead of length-1 at the start hour.
- `request_duration ≤ 1h` jobs are byte-identical to today (the spread factor collapses to 1).
- `system.total_footprint` unchanged for a representative model (redistribution in time only).
- Full `pytest` green; JSON round-trip unaffected (no schema change); CHANGELOG updated.

**Depends on:** none.

**Status:** Done.

---

## Task 2 — Demand (web) paradigm: aggregate-and-route attribution

**Goal:** Replace the normalised-share roll-up in the demand chain with per-`(source, usage_pattern)`
aggregation, so a journey's attributed footprint spans the full run window of its jobs and the
negative-remainder crash disappears *by construction*. This is the headline fix: opening *Results* on
a model whose job outlives its journey renders without error. The generic base weight machinery is
**kept** in this task — the edge paradigm still rides it; it is removed in Task 3.

**Approach (from plan §1–§3):**
- **Source apportioning stays, but usage-phase keying becomes per-pattern.** The neutral shared
  sources (`ServerBase`, `Storage`, external-API server) currently lump across patterns
  (`job_repartition_weights` built from `hourly_avg_occurrences_across_usage_patterns`). Split so the
  *usage* weight is keyed per `(job, usage_pattern)` (via `hourly_avg_occurrences_per_usage_pattern`)
  while the *fabrication* weight stays per-job — `ServerBase.fabrication_impact_repartition_weights`
  and `usage_impact_repartition_weights` can no longer return the same `job_repartition_weights` dict.
  The external-API (EcoLogits) server's usage weight is already duration-aware after Task 1; here it
  additionally gains the per-pattern key, so `_spread_over_request_duration` needs a per-`usage_pattern`
  variant keyed on `hourly_avg_occurrences_per_usage_pattern`. `Network`/`Device` are per-country
  objects already and are untouched.
- **Logical containers aggregate instead of multiply.** Give `Job` and `UsageJourneyStep` aggregation
  overrides of `attributed_{energy,fabrication}_footprint_per_source` (replacing their reliance on the
  base `_compute_default_impact_repartition_weight`): `Job` routes its incoming per-source dict upward
  **per source, preserving provenance** (no lumped `occ_in_step/total_occ` ratio that would smear a
  job's per-country network mix); `UsageJourneyStep` sums two per-source streams — device contributions
  (base path) + its jobs' routed footprints — keyed per source.
- **Journey → pattern split is a direct per-pattern sum.** In `UsageJourney`, produce
  `attributed_energy_footprint_per_usage_pattern` by directly summing per-`(source, usage_pattern)`
  contributions. **Delete** the country-dependent/neutral subtraction logic, `_neutral_activity_share`,
  and the negative-remainder `raise` (`usage_journey.py:137-168`). Fabrication aggregates per-source,
  occurrence-routed, duration-aware — no per-pattern carbon tracking (plan §3).
- **Consistency invariant (cheap assertion).** Assert that a child's routed contributions summed over
  its parents reproduce its own total, and that per-pattern job activity reconciles with
  `hourly_avg_occurrences_per_usage_pattern`.
- **Sankey / resolved-attribution shape is preserved.** Aggregation must reproduce the identical
  `{source_object: footprint}` dict shape that `resolve_attributed_footprint_per_source` and
  `ImpactRepartitionSankey` consume (incl. intermediate keys that skip/exclude resolution traverses).
  Guard with the existing sankey + resolved-attribution suites; do not re-implement traversal.
- **`UsagePattern` is a thin consumer, not a re-computer.** `UsagePattern.attributed_energy_footprint`
  (`usage_pattern.py:105-106`) just reads `self.usage_journey.attributed_energy_footprint_per_usage_pattern[self]`,
  so it picks up the corrected dict for free — no new computation on the class. Its *pattern→country*
  weight builder (`update_*_impact_repartition_weights` keyed by `Country`, scalar-`1`) is a different
  axis and stays as-is. But **delete the now-dead `UsagePattern.usage_activity_weight` and
  `country_dependent_usage_footprint`** — both are consumed *only* by the re-split being removed
  (verified: their sole callers are `usage_journey.py:127,144,146`). `Country`/`System` are untouched.

**Files touched:**
- `efootprint/core/hardware/server_base.py` — factor `job_repartition_weights` so usage is per-pattern, fabrication per-job.
- `efootprint/core/hardware/storage.py` — usage-phase per-pattern keying.
- `efootprint/builders/external_apis/external_api_base_class.py` — usage-phase per-pattern keying.
- `efootprint/core/usage/job.py` — drop weight reliance; add per-source provenance-preserving routing override.
- `efootprint/core/usage/usage_journey_step.py` — aggregate device + routed-job streams per source.
- `efootprint/core/usage/usage_journey.py` — `attributed_energy_footprint_per_usage_pattern` becomes a direct per-`(source, usage_pattern)` sum; delete `_neutral_activity_share`, the country-dependent/neutral re-split, and the negative-remainder `raise`.
- `efootprint/core/usage/usage_pattern.py` — delete the now-dead `usage_activity_weight` and `country_dependent_usage_footprint` (sole consumers were the deleted re-split); `attributed_energy_footprint` stays a thin read of the journey dict.
- `efootprint/utils/impact_repartition/sankey.py` — audit only (no behavioural change; confirm dict-shape compatibility).
- `efootprint/abstract_modeling_classes/modeling_object.py` — audit `resolve_attributed_footprint_per_source`, `_attributed_footprint_cached_property_names`, `invalidate_impact_repartition_cache` still flush correctly with the demand overrides (base generic method retained for now).
- `specs/conventions.md` — one-line note: attribution above the source apportioning boundary aggregates per `(source, usage_pattern)`; it does not re-split lumped totals.
- `CHANGELOG.md` — `### Fixed` entry for the duration-aware demand-chain attribution.

**Tests added/changed:**
- `tests/integration_tests/test_per_usage_pattern_impact_cascade.py` (or a new integration test) — **repro built in code** (no reliance on the gitignored `bug when clicking results.json`): a short journey triggering a job whose `request_duration` spills into the next hour. Assert: impact-repartition diagram builds with **no raise**; journey attributed footprint is non-zero in the tail hour and matches the source (network) tail; `system.total_footprint` is conserved hour-by-hour and in total.
- Test (b): a jobless, device-only step still attributes its device footprint upward.
- Test (c): a `>1h` job's footprint is spread across its whole run window.
- Test (d): all-short-jobs / single-pattern model — results identical to today (no regression).
- Test (e): a `Job` **and** a `UsageJourneyStep` shared across two journeys in different countries — each country's grid intensity stays with its own network/device; the neutral server splits by per-pattern occurrence (currently uncovered; if it exposes a latent discrepancy, surface it — do **not** pin old numbers, constitution §3.1).
- `tests/abstract_modeling_classes/test_modeling_object.py` — update/extend the cache-invalidation tests for the aggregated demand path; add one aggregated-path leaf-mutation case.
- `tests/test_impact_repartition_sankey.py` — must stay green (dict-shape guard); adjust only assertions that encoded the old truncated per-UP values by design.

**Acceptance:**
- Opening *Results* (building the impact-repartition / Sankey diagram) on a job-longer-than-journey model renders — no `ValueError`.
- A journey's attributed footprint spans its jobs' run window; tail hours are non-zero and reconcile with the source tail.
- `_neutral_activity_share`, the country-dependent/neutral re-split, and the negative-remainder `raise` are gone from `usage_journey.py`.
- Conservation holds (system + each top-level category total unchanged to float noise) and the single-pattern no-regression test passes identically.
- Full `pytest` green; `mkdocs build --strict` passes; JSON round-trip unaffected (all changed attributes are calculated). Base generic weight machinery still present and used by the edge classes.

**Depends on:** Task 1.

**Status:** Not started.

---

## Task 3 — Edge paradigm mirror + remove the generic weight machinery + document the boundary

**Goal:** Apply the same aggregate-and-route treatment to the deployment-driven (edge) chain, then
**delete** the now-dead generic weight machinery from the framework layer once no caller depends on it,
and rewrite the architecture doc around the apportioning-vs-aggregation principle. After this task both
paradigms attribute identically and the base layer carries no domain-specific roll-up.

**Approach (from plan §2–§3, §7):**
- **Edge logical containers aggregate.** Give aggregation overrides to the edge generic-default callers:
  `RecurrentServerNeed`, `RecurrentEdgeDeviceNeed`, `RecurrentEdgeComponentNeed`,
  `RecurrentEdgeStorageNeed`, `EdgeFunction`. Cover both chains:
  `Server/Storage → Job → RecurrentServerNeed → EdgeFunction → EdgeUsageJourney` and
  `EdgeDevice → RecurrentEdgeComponentNeed → RecurrentEdgeDeviceNeed → EdgeFunction`.
- **Edge journey → pattern split mirrors the demand fix.** In `edge_usage_journey.py` make
  `attributed_energy_footprint_per_usage_pattern` a direct per-pattern sum and retire the re-split
  machinery (mirror of `UsageJourney`: delete the neutral re-split and the negative-remainder `raise` at
  `edge_usage_journey.py:126,143,145`). `EdgeUsagePattern.attributed_energy_footprint` stays a thin read
  of the journey dict, its pattern→country weight builder is untouched, and its now-dead
  `usage_activity_weight` / `country_dependent_usage_footprint` are deleted (mirror of the `UsagePattern`
  cleanup in Task 2). Apply edge source-level usage-phase per-pattern keying wherever an edge
  server/storage is shared across edge patterns.
- **Remove the base generic default.** With every logical-container caller (demand + edge) now on an
  aggregation override, delete `_compute_default_impact_repartition_weight` and the base
  `update_dict_element_in_{fabrication,usage}_impact_repartition_weights` /
  `update_{fabrication,usage}_impact_repartition_weights` from
  `abstract_modeling_classes/modeling_object.py`. The source-level overrides (Server/Storage/Network/
  Device/Country/ExternalAPI) and the base `attributed_*_footprint_per_source` path **stay**. Re-confirm
  by grep that no class still relies on the base default before deleting (plan §2).
- **Consistency invariant** on the edge chain, as in Task 2.
- **Docs.** Rewrite the `## Usage attribution boundary` section of `specs/architecture.md` (currently
  ~line 93) around the apportioning-vs-aggregation principle; update affected docstrings (SSOT,
  conventions §1.4).

**Files touched:**
- `efootprint/core/usage/edge/recurrent_server_need.py`
- `efootprint/core/usage/edge/recurrent_edge_device_need.py`
- `efootprint/core/usage/edge/recurrent_edge_component_need.py`
- `efootprint/core/usage/edge/recurrent_edge_storage_need.py`
- `efootprint/core/usage/edge/edge_function.py`
- `efootprint/core/usage/edge/edge_usage_journey.py` — per-pattern aggregation; retire re-split machinery.
- `efootprint/core/usage/edge/edge_usage_pattern.py` — mirror of `UsagePattern` (shape unchanged).
- `efootprint/core/hardware/server_base.py` / `storage.py` — edge-shared-source usage per-pattern keying, if not already covered by Task 2.
- `efootprint/abstract_modeling_classes/modeling_object.py` — **delete** `_compute_default_impact_repartition_weight` and the base `update_*_impact_repartition_weights` methods.
- `specs/architecture.md` — rewrite the Usage attribution boundary section.
- affected docstrings across the modified classes.
- `CHANGELOG.md` — extend/finalise the `### Fixed` entry to cover the edge paradigm and the machinery removal.

**Tests added/changed:**
- `tests/usage/edge/test_edge_usage_journey.py` (and edge pattern/integration tests) — edge mirrors of Task 2 tests (a)–(e): repro long edge job, jobless edge-component-only need, `>1h` edge job spread, single-pattern no-regression, edge job/need shared across two edge patterns in different countries.
- `tests/abstract_modeling_classes/test_modeling_object.py` — remove/replace tests that asserted the deleted generic weight behaviour (e.g. `test_update_impact_repartition_weights_uses_container_weight_sums_and_occurrences`, `test_update_impact_repartition_normalizes_weights`); keep the `attributed_*_footprint_per_source` and resolved-attribution tests green.
- `tests/test_impact_repartition_sankey.py` — stays green for both paradigms (dict-shape guard).
- A JSON round-trip / no-schema-migration confirmation on a representative edge model.

**Acceptance:**
- Edge *Results* renders for a model whose edge job outlives its journey; edge conservation and no-regression hold, mirroring Task 2.
- `_compute_default_impact_repartition_weight` and the base `update_*_impact_repartition_weights` methods are deleted; a grep confirms no remaining caller; source-level and `attributed_*_per_source` paths remain intact.
- `specs/architecture.md` describes the apportioning-vs-aggregation boundary as the actual implemented mechanism; docstrings of changed classes match the new behaviour.
- Full `pytest` green; `mkdocs build --strict` passes; CHANGELOG updated; JSON round-trip unaffected.

**Depends on:** Task 2.

**Status:** Not started.

---

## Ordering rationale

Task 1 lands first because it is the *source* of the duration-aware footprints the rest of the work
carries: until the EcoLogits server spreads its per-request impact over the run window, the attribution
chain would be aggregating a masked single-hour spike, and the per-pattern source keying in Task 2 would
build on wrong temporal allocation. It is also small, low-risk, and independently correct (totals
unchanged), so it is a clean, separately-shippable foundation — and it absorbs the "external
prerequisite" the spec/plan referenced, porting it onto `dev`'s actual ecologits structure rather than
leaving a dangling dependency on the unmerged `ecologits-video` branch.

Tasks 2 and 3 then follow the plan's own landing guidance, "one level at a time — demand chain, then
edge." The dependency structure forces that split: the base generic
`_compute_default_impact_repartition_weight` can only be deleted once **no** logical container still
rides it, so it must survive the demand-chain conversion (Task 2) and is removed only after the edge
chain is converted (Task 3). These are the genuine behavioural pause points — after Task 1 the server
footprint is correctly spread, after Task 2 the web *Results* panel works and the crash is gone, and
after Task 3 the edge paradigm matches and the framework layer is clean.

Within each task the units are kept together because there is no working intermediate state between
them: changing source-level keying without the matching container aggregation would feed the old
journey→pattern re-split an incompatible dict shape (red tests), and converting `Job`/`UsageJourneyStep`
without `UsageJourney` would leave the deleted-vs-retained re-split logic half-wired. The Sankey/resolved
attribution audit is **not** a separate task — it is a dict-shape *constraint* satisfied inside each
task (you cannot ship aggregation that breaks the renderer and fix it later), guarded by the existing
sankey suite. Docs follow the house precedent (sibling `per-usage-pattern-impact-cascade/tasks.md`): the
one-line convention note lands with the demand chain that establishes it (Task 2); the full
architecture-doc rewrite lands with Task 3, when the mechanism is complete across both paradigms and
accurately describes the final state. Conservation is asserted, not snapshotted — the plan deliberately rejects a battery-wide
snapshot-equality guard because per-source dicts and per-pattern splits change by design.
