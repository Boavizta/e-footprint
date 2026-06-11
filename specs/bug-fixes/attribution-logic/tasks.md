# Attribution-logic revamp (atom model) — Tasks

**Status:** Tasks — under review.
**Spec:** [`analysis.md`](analysis.md) + [`edge-analysis.md`](edge-analysis.md). **Plan:** [`plan.html`](plan.html) (v2, atom model).

Migration sequencing (plan §7) is settled here: tasks 1–5 build the atom layer *alongside* the
legacy attribution paths (purely additive, each gated by its own conservation tests); task 6 cuts
the renderer over; task 7 deletes the legacy paths. Every task leaves the full suite green.

**Eager vs lazy rule (binds every task):** anything computed *only* for attribution is a
`@cached_property` — lazy, flushed by the auto-flush sweep, never listed in
`calculated_attributes`, never serialized. `calculated_attributes` stay reserved for the eager
graph that feeds the footprint totals. Where analysis.md says "new calculated attribute", read
"new cached property" — the only exceptions are quantities the eager totals are re-derived
*from* (e.g. Device's per-UP fabrication dict, ServerBase's idle/load energy components), which
stay eager. Corollary: each builder task audits the classes it touches and refactors any
**existing** calculated attribute that, after this revamp, only attribution consumes into a
cached property — fewer serialized keys and less eager work per update, with no schema bump per
the serialization policy (task 7).

**Open question §7 (public surface) — resolved:** the interface consumes only
`ImpactRepartitionSankey` (verified by grep: `sankey_views.py` imports the class and passes
`skipped_impact_repartition_classes` / `excluded_object_types` / `lifecycle_phase_filter`).
The thin `attributed_fabrication_footprint` / `attributed_energy_footprint` cached properties
are **kept** — getting a footprint from any object is part of the package's public surface —
reimplemented in task 7 as delegations to `attribution.footprint_per_node`. The heavyweight
`attributed_*_per_source[_resolved]` / `resolve_*` machinery behind them is still deleted.

---

## Task 1 — Container occurrence / data primitives + cell enumeration

**Status:** Done

**Implementation notes:**
- `attribution_cells` landed as a `@cached_property` (per the eager-vs-lazy rule), not a callable as the
  illustrative sketches show — builders read `job.attribution_cells` without parens.
- Step occupancy is built as a telescoping difference of journey-parallel counts at the step's start/end offsets
  (exact for fractional offsets), so the tiling identity holds structurally; the floored-shift build of the job
  occurrence primitives is kept as-is since it mirrors the eager per-pattern build (partition identity preserved).
- The new cached properties are registered in `_attributed_footprint_cached_property_names` so `to_json` /
  `__str__` skip their materialized values and the legacy flush covers them — superseded by task 2's auto-flush.

**Goal:** Land every container-owned, dimensionless primitive the atom builders consume
(analysis.md "New JobBase / UsageJourneyStep attributes" lists, web + edge), plus
`JobBase.attribution_cells()` — the flat enumeration of a job's `(step, up)` / `(rsn, ef, up)`
cells carrying both share kinds (`hourly_share` with fallback 0, `flat_share` as period-total
scalar) and the `o(rsn, ef, up)/o(rsn, up)` slot multiplicity. Additive only; nothing consumes
them yet.

**Files touched:**
- `efootprint/core/usage/job.py` — web: `get_hourly_avg_occurrences_per_usage_pattern_per_step`,
  `compute_hourly_data_transferred_per_usage_pattern_per_step`, `hourly_data_stored_per_step`,
  `hourly_avg_occurrences_per_usage_journey_step`, `hourly_avg_occurrences_per_usage_journey`;
  edge: the `_per_recurrent_server_need` / `_per_edge_usage_journey` analogues;
  `attribution_cells()`. All attribution-only, so per the eager-vs-lazy rule: `get_*`/`compute_*`
  = plain methods, the rest = `@cached_property` — **none** enters `calculated_attributes`
  (analysis.md's "calculated attribute" wording reads as "cached property" here).
- `efootprint/core/usage/usage_journey_step.py` — `hourly_avg_occurrences_per_usage_pattern`
  (the occupancy primitive — a cached property, same rule).

**Tests added/changed:**
- `tests/usage/test_job.py`, `tests/usage/test_usage_journey_step.py`,
  `tests/usage/edge/test_recurrent_server_need.py` (or a new `tests/usage/test_attribution_primitives.py`)
  — identity tests on a model with web + edge + within-journey reuse (a step repeated in
  `uj_steps`, an RSN reached through several EdgeFunctions):
  - Σ over steps of per-step occurrences + Σ over RSNs of per-RSN occurrences
    = `hourly_avg_occurrences_across_usage_patterns`; same partition for data-stored rates.
  - Step occupancy summed over a journey's steps tiles
    `nb_usage_journeys_in_parallel_per_usage_pattern`.
  - Per-cell `hourly_share`s sum to 1 at every nonzero hour; `flat_share`s sum to 1;
    slot multiplicities partition (`Σ_ef o(rsn, ef, up) = o(rsn, up)`).

**Acceptance:**
- All partition/tiling identities above hold, including the reuse cases.
- Existing suite green; no behaviour change anywhere (pure addition). Cache-flush correctness
  for these cached properties arrives with task 2's auto-flush — safe here because nothing
  consumes them yet.

**Depends on:** none.

---

## Task 2 — Attribution core (`core/attribution/`), auto-flush, first builder (Device)

**Status:** Done

**Implementation notes:**
- Levels are plain ModelingObject classes, not SANKEY_COLUMNS indices: `visible_levels` is a tuple of classes
  and chain filtering is `isinstance`-based, so the core has no SANKEY_COLUMNS dependency (task 6 aligns the
  renderer's columns to class tuples when it cuts over).
- The flushed-memo tiers live in `ModelingObject.render_cache` — a generic cached_property dict on the
  framework base — so the auto-flush sweep wipes fold memos and atom lists with the same mechanism as every
  other cached property, with no framework→attribution back-edge.
- The system-wide sweep is `flush_cached_properties_system_wide` (modeling_object.py): called at the end of
  every `ModelingUpdate.__init__` and from `launch_mod_objs_computation_chain` (which covers the initial
  build via `System.after_init` and `self_delete`). All four registry overrides were dropped (the two
  journey ones named here plus the temporary task-1 ones in job.py / usage_journey_step.py); the legacy
  `invalidate_impact_repartition_cache` walk now delegates to `flush_cached_properties` (strict superset).
- Device's atom stream is named `"single"` (one stream per phase, per the plan's source/stream table).

**Goal:** The whole shared layer, with its simplest real consumer so it is exercised end to end:
the `Atom` value object + `chain()` + level keys, the tier-1 `(source, phase)` atom-list memo,
the tier-2 fold memo (`node_totals_and_links`, `footprint_per_node` + per-source variant,
exclusion = filter), and the MRO-based auto-flush of every `cached_property` replacing the manual
`_attributed_footprint_cached_property_names` registry (and its two per-class overrides in
`usage_journey.py` / `edge_usage_journey.py`) — a strict superset, so legacy flushing keeps
working until task 7. Device gets its atom builder (no shares: ground-up `(step, up)` cells,
CI inside for usage) plus the per-UP fabrication dict analysis.md introduces
(`instances_fabrication_footprint_per_usage_pattern` — this one stays an eager calculated
attribute, since the eager total is re-derived from it; the builder itself and anything
attribution-only follow the cached-property rule).

**Files touched:**
- `efootprint/core/attribution/` (new) — `Atom`, chain/levels, fold, memoized reads, flushed-memo
  infrastructure (per `attribution_sketch.py`).
- `efootprint/abstract_modeling_classes/modeling_object.py` — auto-discovery flush; registry
  dropped (with the `usage_journey.py` / `edge_usage_journey.py` overrides).
- `efootprint/abstract_modeling_classes/modeling_update.py` — system-wide flush sweep over
  `all_linked_objects` at end of update and after initial build.
- `efootprint/core/hardware/device.py` — `attribution_atoms(phase)`, per-UP fabrication dict;
  legacy repartition weights untouched.

**Tests added/changed:**
- `tests/core/attribution/` (new) — the **generic conservation harness** (parameterized over
  sources: Σ atoms per (phase, stream) == that stream's footprint == the eager totals) used by
  every later task; fold structural invariants (Σ incoming == node total == Σ outgoing;
  column-skip equivalence: folding with a level hidden == regrouping the full fold; exclusion =
  filter, no rescale); cache behaviour (memo hit within a query, full flush after ModelingUpdate).
- `tests/hardware/test_device.py` — Device conservation on a multi-pattern, multi-country model;
  per-step energy carries CI[up] per cell (the double-count/smear fix of analysis.md).
- `tests/abstract_modeling_classes/test_modeling_object.py` / `test_modeling_update.py` —
  auto-flush replaces registry behaviour.

**Acceptance:**
- Device atoms conserve per phase; fold invariants hold; flush verified.
- Legacy paths untouched and green (auto-flush is a superset of the registry).

**Depends on:** Task 1 (Device builder consumes the Step occupancy primitive).

---

## Task 3 — ServerBase + external-API atom builders

**Status:** Done

**Implementation notes:**
- The idle/load energy split landed as two eager calculated attributes (`idle_energy_footprint`,
  `load_energy_footprint`) with `update_energy_footprint` overridden on ServerBase to sum them — the eager
  energy total is re-derived from them, per the eager-vs-lazy rule's exception.
- The per-tier helper `on_premise_provisioned_tier_shares` is a module-level pure function on numpy arrays
  (unit-tested in isolation); a tier no hour needs (fixed_nb_of_instances above peak) falls back to
  period-total demand shares, and zero total demand falls back to equal shares so weights always sum to 1.
- The external-API builder lives on `ExternalAPIServer` (base class) over a new
  `job_request_footprint(job, phase)` abstract method; EcoLogits implements it from
  `_spread_over_request_duration`. Stream name is `"single"`.
- The plan §1.2 `J2 | B·US` row is pinned by
  `test_flat_provisioned_share_carries_footprint_at_a_cell_zero_occurrence_hour` (zero dynamic atom, nonzero
  flat provisioned atom at a cell's zero-occurrence hour, on a real web + edge on-premise model).
- Eager-vs-lazy audit: `service_total_job_volumes` moved to a cached property (only consumed by the new
  service-base term and legacy `job_repartition_weights`, which was repointed); no other attribution-only
  calculated attribute found on the touched classes.

**Goal:** The subtlest physics. ServerBase: expose the idle/load energy split as separate
footprints, build `binding_demand_per_job` (binding resource picked by the `raw[h]` max, same
denominators as `update_raw_nb_of_instances`; ServiceJob carries its volume share of its
service's base consumption), `dynamic_share_per_job`, and the per-tier
`provisioned_share_per_job` (flat on-premise weight via tier sets `{h: raw[h] > k−1}`;
autoscaling/serverless collapse to dynamic) — the per-tier helper unit-tested in isolation
(plan §4 risk). Then `attribution_atoms(phase)`: provisioned + dynamic streams over the job's
cells, flat shares for on-premise provisioned, hourly otherwise. EcoLogits external-API servers
get their builder in the same family: a single demand stream over the duration-aware per-job
request footprints. Legacy `job_repartition_weights` stays until task 7.

Eager-vs-lazy: the three shares are cached properties (per the sketch); the idle/load energy
components stay eager (the energy total derives from them). Audit the touched classes'
`calculated_attributes` for attribution-only entries — concretely, `service_total_job_volumes`
is consumed only by `job_repartition_weights` today, so it moves to a cached property feeding
the new service-base term.

**Files touched:**
- `efootprint/core/hardware/server_base.py` (and `infra_hardware.py` / `server.py` if the
  idle/load exposure or server-type predicate lands there).
- `efootprint/builders/external_apis/external_api_base_class.py`,
  `efootprint/builders/external_apis/ecologits/ecologits_external_api.py`.

**Tests added/changed:**
- `tests/hardware/test_server.py` — per-tier helper in isolation (a job present only off-peak
  still pays the lower tiers it requires; tier weights sum to 1; autoscaling == dynamic);
  binding-resource selection (RAM-heavy job on a compute-bound server charges compute);
  service-base term (paid by the service's own jobs only).
- Generic conservation harness on a model with web + edge + on-premise idle hours: Σ atoms ==
  fabrication total; == idle + load energy; a dual-side job splits across web steps and edge
  RSNs; the worked micro-example of plan §1.2 (the `J2 | B·US` flat-share row) as a regression
  fixture.
- `tests/builders/external_apis/ecologits/test_ecologits_generative_ai.py` — conservation of the
  API-server atoms.

**Acceptance:**
- All conservation checks above, per stream — including nonzero provisioned atoms at
  zero-occurrence hours (the always-on bug this revamp fixes).
- Existing suite green (legacy weights still in place).

**Depends on:** Tasks 1–2.

---

## Task 4 — Storage + Network atom builders

**Status:** Done

**Implementation notes:**
- The cumsum-with-dumps helper landed as the module-level `cumulative_storage_need_with_dumps(rate, duration)`
  in `storage.py`; the eager `update_dict_element_in_full_cumulative_storage_need_per_job` is now a thin caller.
- Per-cell retention rates are built as `cell.hourly_share × the job's replicated data-stored rate` (exact —
  the cell's occurrences are zero wherever the job's total is) rather than re-deriving data_stored_per_hour,
  so the builder consumes only public job quantities; linearity then gives Σ cells == per-job cumulative
  exactly (pinned by a unit test on the helper and a real-model test).
- Baseline job weights (`baseline_flat_share_per_job`) fall back to an equal share across the jobs holding at
  least one attribution cell when total occurrences are zero, mirroring the task-1/3 zero-traffic fallbacks.
- Network cells are filtered by `cell.up.network == self` (a job can route through several networks); edge
  cells reuse the task-1 `compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need`
  primitive weighted by the cell's slot multiplicity.
- Eager-vs-lazy audit: `Network.energy_footprint_per_usage_pattern` moved to a cached property (its only
  consumers are the lazy legacy `country_dependent_usage_footprint` paths; the eager energy total sums the
  per-job dict). Storage's `shared_storage_per_job` stays eager — the eager legacy
  `fabrication_impact_repartition_weights` consumes it until task 7.

**Goal:** Storage: the two-stream split (`storage_retention_fabrication_footprint` = F × N /
provisioned_capacity over the job-written cumulative N; `storage_baseline_fabrication_footprint`
= F × (unused + base) / provisioned_capacity), cumsum-with-dumps factored into a reusable helper
(linearity is what makes per-cell retention sum exactly), and `attribution_atoms`: retention by
per-cell cumulative / N (hourly), baseline by flat period-total occurrence shares — across web
steps and edge RSNs. Network: generalize the data→carbon physics into
`energy_footprint_for_data_volume_and_usage_pattern(data, up)` (existing per-job method becomes
a thin caller) and build the single-stream atoms per cell with CI[up] inside. Legacy
`shared_storage_per_*` weights stay until task 7.

Eager-vs-lazy: the two stream footprints and all per-cell retention cumulatives are
attribution-only → cached properties (F and `full_cumulative_storage_need[_per_job]` stay eager:
the sizing graph derives from them). Audit both classes' `calculated_attributes` for entries
only attribution consumes after this task.

**Files touched:**
- `efootprint/core/hardware/storage.py` (+ the cumsum-with-dumps helper, wherever it is factored).
- `efootprint/core/hardware/network.py`.

**Tests added/changed:**
- `tests/hardware/test_storage.py` — streams sum to F exactly (nb_of_instances cancels);
  cumsum linearity (per-cell cumulatives sum to the per-job cumulative); retention conserves
  across web + edge writes; baseline flat shares conserve at idle hours (fallback-0/1 bug fix);
  EdgeStorage-on-server distinction untouched (RecurrentEdgeStorageNeed is task 5's territory).
- `tests/hardware/test_network.py` — physics fn reproduces the old per-job method; Σ atoms ==
  energy footprint; per-cell CI (two patterns with different CI never blended).
- Generic conservation harness entries for both sources.

**Acceptance:**
- Conservation per stream, web + edge; physics-fn equivalence; suite green.

**Depends on:** Tasks 1–2 (independent of task 3 — can land in parallel with it).

---

## Task 5 — EdgeDevice atom builder

**Status:** Done

**Implementation notes:**
- The physics landed as two cached-property dicts keyed `(need, usage_pattern)` —
  `fabrication_atom_value_per_need_and_pattern` / `energy_atom_value_per_need_and_pattern`, both reading
  `demand_share_per_need_and_pattern` — with `atom_value(n, up, phase)` a thin dict read; `attribution_atoms`
  derives the slot counts and `o(n, up)` from one walk of the journey, so the multiplicities partition by
  construction.
- The energy floor needs each component's idle/base power, which is subclass knowledge (base/capacity), so a
  plain `unitary_power_at_zero_recurrent_need` property was added on `EdgeComponent` (NotImplementedError) and
  its CPU / RAM / workload subclasses — three files beyond the task's list, surfaced and justified by
  ownership (conventions: parent-level policy stays on the natural owning object). The dynamic marginal is then
  derived as `(component energy − floor) × demand share` — exact by linearity of the affine power curve — so
  no per-subclass capacity read is needed in the builder. EdgeStorage (power/idle deleted) carries an Empty
  energy atom value.
- Eager-vs-lazy audit: nothing to move — every attribution-flavoured calculated attribute on the touched edge
  classes (`total_unitary_hourly_need_per_usage_pattern`, the impact-repartition weights) is still consumed by
  the eager legacy `_compute_component_need_weight` chain until task 7.
- Conservation caveat — RESOLVED in review (edge-analysis.md fix 4): unused components are part of the
  chassis. Their embodied carbon is deployment-booked in the eager per-pattern totals (device-side, from the
  component's input attributes via `carbon_footprint_fabrication_from_inputs`, because need-less components
  never enter the computation chain) and attributed by an equal split of the pool across the pattern's
  carriers — component needs and `RecurrentServerNeed`s (the latter as `(rsn, ef)` atoms). RSN-only patterns
  send the whole device fabrication through the RSNs; a deployed pattern with booked fabrication and no
  carriers raises. Full-coverage models (all existing fixtures) are numerically unchanged.

**Goal:** The slot-enumeration builder of `edge_device_sketch.py`, carrying the three
edge-analysis.md fixes: (1) zero-demand fallback → explicit equal share (not
`divide_or_fallback(fallback=1)`); (2) EdgeStorage demand = the need's own cumulative **held
volume**, not the net write rate; (3) the idle/base energy floor split off the affine power
curve and shared equally at every hour, dynamic marginal attributed directly. `atom_value(n, up,
phase)` holds the physics (chassis rides as `1/nb_components` with each component, matching the
breakdown axis); `attribution_atoms` enumerates one atom per `(recn, redn, ef, up)` slot with
multiplicity `o(n, slot, up)/o(n, up)`. The `EdgeDevice → EdgeComponent` breakdown axis is
unchanged. Legacy `_compute_component_need_weight` chaining stays until task 7.

Eager-vs-lazy: `atom_value` and the builder are cached properties / methods, never
`calculated_attributes` (the eager per-pattern totals they conserve against are untouched).
Audit the touched edge classes' `calculated_attributes` for attribution-only entries.

**Files touched:**
- `efootprint/core/hardware/edge/edge_device.py` (+ `edge_storage.py` /
  `recurrent_edge_component_need.py` if the held-volume read or occurrence counts need exposing).

**Tests added/changed:**
- `tests/hardware/edge/test_edge_device.py` — conservation: Σ atoms over a pattern == `dev(up)`
  == the eager per-pattern totals, both phases; within-journey reuse splits by the occurrence
  ratios (edge-analysis pairs 7/12 fixtures, ratios summing to 1); equal-share idle floor at
  partial-demand hours on a mostly-idle device; held-volume weight stays correct across delete
  hours; chassis consistency between the atom fold and the breakdown axis.
- Generic conservation harness entry.

**Acceptance:**
- All 21-pair behaviour is reachable as folds of these atoms (spot-checked via the fixtures
  above); the three fixes demonstrated by dedicated tests; suite green.

**Depends on:** Tasks 1–2 (parallel with tasks 3–4).

---

## Task 6 — Sankey renderer cut-over

**Status:** Done

**Implementation notes:**
- The fold's visible levels always include the source-level classes (`SANKEY_COLUMNS[-1]`) even when their
  display column is hidden — phase totals, category aggregation and the breakdown decoration need source
  granularity; hiding leaves is presentation. Container levels are the `SANKEY_COLUMNS[1:-1]` classes minus
  the skipped ones.
- Skipped impact-source classes now conserve totals: the leaf (and its category node) is hidden and the flow
  stops at the finest visible container, with breakdown children still expanded per parent flow (matching the
  legacy probe: hardware-skipped renders kept totals and dropped category nodes). Excluded `ExternalAPI`
  classes map to their `server_class` for the fold's atom filter; `EdgeStorage`-style exclusions keep acting
  on breakdown children only, as before.
- `all_classes_in_order.py` needed no change — `SANKEY_COLUMNS` entries are already the class tuples the
  fold's isinstance filtering consumes.
- Per-column conservation through the renderer holds for every column between root and the leaf column when
  spacer pass-throughs are counted (a Device atom has no Job node; its flow crosses the Job column in a
  spacer) — pinned that way in the regression test; fold-level "every level column sums to the phase total"
  only holds for levels every chain crosses (UJ / UP / Country).
- Per-node diffs vs legacy, all spec-documented: complex fixture's dual-side jobs move ~36 t CO2eq of server
  impact from the edge chain (RSN/EF/EUJ/EUP) to the web steps/patterns (analysis.md Server edge partition);
  edge component-need nodes re-split by the equal-share idle floor and held-volume storage demand
  (edge-analysis fixes 2–3 — storage needs now carry weight, sum per device conserved); ~0.01% server-side
  shifts from binding-resource / per-tier / flat always-on weights. simple / services / edge_group fixtures
  are numerically identical node by node.

**Goal:** Rewrite `ImpactRepartitionSankey` as the column-walk of `sankey_sketch.py`: data layer
= one `attribution.node_totals_and_links(...)` call per life-cycle phase; everything else is
presentation (System root + phase columns, object-category and breakdown-by-source decorations,
`ExternalAPIServer → ExternalAPI` display normalization, small-node aggregation, colors, hovers,
spacers as pure geometry). Delete the recursive `_traverse`, all `resolve_*` consumption and flow
rescaling. **Constructor surface preserved** (`skipped_impact_repartition_classes`,
`excluded_object_types`, `lifecycle_phase_filter`, aggregation/label/display kwargs) so
e-footprint-interface's `sankey_views.py` works unchanged.

**Files touched:**
- `efootprint/utils/impact_repartition/sankey.py` (rewrite).
- `efootprint/all_classes_in_order.py` if `SANKEY_COLUMNS` needs level-key alignment.

**Tests added/changed:**
- `tests/test_impact_repartition_sankey.py` — conservation regression on every fixture model
  (per node Σ incoming == size == Σ outgoing; column sums == phase total minus exclusions);
  skip-column and exclude-source equivalence through the renderer; expectation updates where
  per-node values change.

**Acceptance:**
- System-level totals identical to today on all fixture models (eager totals are untouched).
- Per-node expectation diffs occur **only** where analysis.md / edge-analysis.md documents a
  deliberate fix (binding resource, per-tier provisioning, always-on flat shares, Device
  occupancy, storage stream split, edge equal-share/held-volume) — each diff called out and
  justified in the PR description.
- Interface smoke check: `ImpactRepartitionSankey` instantiates with the exact kwargs
  `sankey_views.py` passes.

**Depends on:** Tasks 3, 4, 5 (a render needs every source family's atoms).

---

## Task 7 — Delete legacy attribution paths, docs

**Goal:** Remove everything the fold replaced, in one mechanical sweep. `ModelingObject`: the
generic `*_impact_repartition*` calculated attributes and update methods,
`attributed_*_footprint_per_source[_resolved]`, `resolve_attributed_footprint_per_source`,
`_merge_rescaled`, `invalidate_impact_repartition_cache` — while the thin
`attributed_fabrication_footprint` / `attributed_energy_footprint` cached properties are
**kept** (see resolved question above), reimplemented as delegations to
`attribution.footprint_per_node` (flushed by task 2's auto-flush like any cached property).
Sources: `job_repartition_weights` (ServerBase),
repartition-weight properties (Storage incl. `shared_storage_per_*`, Network, Device, external
APIs), `_compute_component_need_weight` and the `_impact_repartition` chaining on the edge
containers. Containers: `attributed_energy_footprint_per_usage_pattern`, neutral-remainder
logic, `usage_activity_weight`, repartition weights on UsageJourney / UsagePattern / Country and
edge equivalents. **No JSON schema bump**: only calculated attributes are added/removed, the
input schema is untouched, and the policy is to bump versions only when inputs-only JSONs change.
Docs rewritten to the atom model.

**Files touched:**
- `efootprint/abstract_modeling_classes/modeling_object.py` (net ~300-line deletion).
- `efootprint/core/hardware/server_base.py`, `storage.py`, `network.py`, `device.py`,
  `edge/edge_device.py`; `efootprint/builders/external_apis/…`.
- `efootprint/core/usage/usage_journey.py`, `usage_pattern.py`, `efootprint/core/country.py`,
  `efootprint/core/usage/edge/edge_usage_journey.py`, `edge_usage_pattern.py` (+ the other edge
  containers carrying `_impact_repartition` chaining).
- `specs/architecture.md` (attribution boundary, resolved-attribution, cached-property registry
  sections; plus one line stating the serialization policy: schema versions bump only when
  inputs-only JSONs change, and cross-version loads of with-calculated-attributes JSONs are
  unsupported), `specs/conventions.md` (repartition-weight preferences), `specs/testing.md` if
  the conservation-harness pattern deserves a line.

**Tests added/changed:**
- Round-trip / `json_to_system` tests: inputs-only fixture JSONs load unchanged (input schema
  untouched). Cross-version loads of JSONs saved **with** calculated attributes are unsupported
  (settled 2026-06-10) — no loader guard, no version handler; only the inputs-only path is
  tested across versions.
- Deletion fallout across `tests/abstract_modeling_classes/`, `tests/hardware/`, `tests/usage/`,
  `tests/integration_tests/` (incl. `test_per_usage_pattern_impact_cascade.py`) — legacy-path
  tests removed or repointed at the kept `attributed_*` properties /
  `attribution.footprint_per_node`.
- The kept `attributed_fabrication/energy_footprint` properties tested as exact delegations:
  equal to the object's node value in `footprint_per_node` for each phase, and flushed on
  ModelingUpdate.

**Acceptance:**
- `grep` clean: no `impact_repartition` (outside `utils/impact_repartition/` naming and the
  Sankey constructor kwarg), no `attributed_` except the two kept convenience properties,
  no `resolve_attributed`, no `_merge_rescaled`, no `usage_activity_weight`,
  no `shared_storage_per_` in `efootprint/`.
- Old inputs-only JSON fixtures load unchanged, no version bump; full suite green.
- Final eager-vs-lazy audit: no entry remains in any `calculated_attributes` list whose only
  consumer is the attribution layer.
- Cross-repo follow-up noted for the interface: `modeling_object_web.py:112-113` filters
  repartition-weight attribute names that no longer exist — one-line cleanup PR there.

**Depends on:** Task 6.

---

## Ordering rationale

The strangler sequence settles plan §7's deferred migration question: **build beside, validate,
cut over, delete.** Tasks 1–5 are purely additive — the legacy renderer keeps serving Sankeys
while each source family lands its atoms behind its own conservation gate (Σ atoms == eager
totals, the structural test that makes a missed cell fail loudly). Task 6 is the single
behavioural milestone users see (the renderer reads the fold; documented attribution fixes
surface), and task 7 is the mechanical payoff (net deletion), kept separate from 6
because an 830-line renderer rewrite and a 15-file deletion sweep don't belong in one review pass.

Aggregation choices: the attribution core ships with its first consumer (Device — the simplest
builder, yet it exercises country-dependence and the occupancy primitive), since a fold with no
real atoms has no behavioural pause point. `attribution_cells()` lands with the container
primitives it is built from (task 1), not with its first consumer (task 3), because its
share/multiplicity identities are independently testable and three builder tasks consume it.
Storage and Network share task 4 (both small, both pure web+edge job-leaf sources reusing task
1's data primitives); Server stays alone with the external APIs because the per-tier/binding
physics is the plan's top risk and deserves an undiluted review. Tasks 3, 4, 5 are independent
of each other and can land in parallel once 2 is in.

Seven tasks exceeds the usual 2–5 target deliberately: this revamp spans six source families plus
a framework-layer cut-over, and each builder task is a genuinely independent, parallel-landable
milestone with its own conservation gate — merging them would only enlarge review passes without
removing any boundary.
