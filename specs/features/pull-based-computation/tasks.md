# Pull-based computation — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

Cross-repo feature driven from this repo. Tasks 1–8 land in `e-footprint` (library-only releases);
Task 9 lands in `e-footprint-interface` (the one coordinated cross-repo step). Stage numbers refer
to the plan's delivery-stages table.

## Task 1 — Delete simulation machinery and previous-footprint capture (stage 1, part 1)

**Goal:** Shrink the migration surface before touching the engine: remove the unused simulation
machinery and the `previous_*`/`initial_*` footprint capture + `plot_emission_diffs` (per plan §7:
the interface already disables the capture; the tutorial moves to `comparison/system_comparison.py`).
Transactional rollback for ordinary updates (`reset_values` path in `modeling_update.py:86–97`)
**stays** — it is replaced only at stage 3.

**Files touched:**
- `efootprint/abstract_modeling_classes/modeling_update.py` — simulation paths (`:210–402`),
  `compute_previous_system_footprints` parameter and capture calls
- `efootprint/abstract_modeling_classes/modeling_object.py` — old/new swap simulation (`:568–632`),
  ancestor forking, hourly truncation
- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` — twin links
- `efootprint/core/system.py` — `set_initial_and_previous_footprints`, `previous_*`/`initial_*`
  attributes (incl. their entries in the serializable list), `previous_change`, `all_changes`,
  `plot_emission_diffs`
- `efootprint/utils/plot_emission_diffs.py`, `efootprint/utils/plot_baseline_and_simulation_data.py` — deleted
- `tutorial.ipynb` — diff-plot section rewritten on `efootprint/comparison/system_comparison.py`,
  with a pointer to the interface for richer comparison UI
- `../e-footprint-interface/model_builder/domain/object_factory.py:250` — **not touched now**; the
  `compute_previous_system_footprints=False` argument is removed in Task 9 when the interface bumps
  its efootprint dependency

**Tests added/changed:**
- Delete simulation tests (`tests/abstract_modeling_classes/test_modeling_update.py` simulation
  cases, simulation branches in `tests/integration_tests/*_base_class.py`,
  `tests/test_system_diff_plot`-related assets)
- Update `tests/test_notebooks.py` expectations for the rewritten tutorial

**Acceptance:**
- Full suite green; no reference to simulation, twins, `previous_change`, `previous_total_*`,
  `initial_total_*`, or `plot_emission_diffs` remains in library code
- Ordinary `ModelingUpdate` rollback on computation error still passes its existing tests
- `tutorial.ipynb` executes end to end

**Depends on:** none.

**Status:** Done. Note: the generic single-timeseries plotting helpers (`get_time_axis`, `prepare_data`,
single-series plot) survive in a new `efootprint/utils/plot_timeseries.py` (consumed by
`ExplainableHourlyQuantities.plot` and `system_comparison`); `modeling_object.py` needed no
simulation-specific deletions beyond the dead `ModelingUpdate` branch in `to_json` (the old/new swap
preview at `:568–632` is the ordinary relationship-update path, deleted at Task 6 per the plan's ledger).

---

## Task 2 — Regenerate fixtures, parity harness, baseline benchmarks (stage 1, part 2)

**Goal:** Land the measurement and safety infrastructure every later stage gates on: regenerated
performance fixtures (both are drifted; `big_system_with_calc_attr.json` crashes today's loader),
the randomized parity harness run against the **current** engine, and recorded baselines for the
spec §2 performance criteria.

**Files touched:**
- `tests/performance_tests/generate_big_system.py`, `big_system.json`,
  `big_system_with_calc_attr.json` — regenerated post-Task-1 (serialized shape changed)
- `tests/performance_tests/` — benchmark scripts: full build, single edit + eager recompute,
  load-to-ready, 1,000-iteration nudge-and-read loop, peak RSS
- New parity harness module under `tests/integration_tests/`

**Tests added/changed:**
- Parity property test: random mutation sequences (input edits, relinks, list add/remove, object
  add/delete) compared against a from-scratch rebuild, float tolerance — passing trivially on the
  eager engine, becoming the stage-3 gate
- Baseline benchmark results recorded (committed as a reference file the stage-4 gates diff against)

**Acceptance:**
- Both fixtures load with the current engine; parity harness green on the eager engine
- Baseline numbers recorded for every spec §2 criterion that is measurable pre-refactor

**Depends on:** Task 1.

**Status:** Done. Notes: the fixtures turn out to be **gitignored** (repo-wide `*.json` ignore), so
"regenerated" means the `generate_big_system.py` `__main__` now (re)writes them locally with
deterministic name-based ids, and a skip-guarded `test_big_system_fixtures.py` pins "loads + accepts
updates" (the drifted calc-attr fixture loaded but crashed on first update — stale
`usage_impact_repartition_weight_sum`). Baselines committed via `git add -f` in
`tests/performance_tests/baseline_results.json`; regenerated calc-attr fixture weighs 202 MB (not
the spec's 28.2 MB analytical estimate) and full eager build is only 0.4 s — CPU recompute is indeed
non-binding, JSON weight is. Engine-overhead (< 5%) baseline is the one spec §2 number not
measurable pre-refactor. Parity harness: 3 seeds × 18 mutations across 8 op kinds (incl.
usage-pattern add/delete), rebuild comparison after every mutation, per-op coverage asserted so
silently-rejected mutation kinds fail the test. Post-review hardening: only whitelisted engine
rejections count as rollbacks (anything else fails the test), the comparison iterates the
computed-slot registry (survives Task 6's `calculated_attributes` deletion), and the full-build
baseline records cold + warm samples.

---

## Task 3 — Mechanical conversion: update_* bodies become decorated getters (stage 2)

**Goal:** Single-source every computed value behind `@computed_attribute` / `@computed_dict`
descriptors running in an **eager shim** that preserves today's semantics exactly (descriptors
drive the existing chain machinery; no reactive behavior yet). Per plan §7: agent-performed
mechanical edits, no codemod tooling; `@computed_dict(keys="attr_name")` string form;
`ReverseCollection`/`ReverseLink` declarations land as today-equivalent filters.

**Files touched:**
- `efootprint/abstract_modeling_classes/reactive_core.py` — new; descriptors in eager-shim mode +
  `__set_name__` registries (extended into the full engine in Task 5)
- `efootprint/core/**` (~34 files) — 157 `update_*` + 29 `update_dict_element_in_*` functions
  become getters (final assignment → `return`, docstrings kept on getters);
  **`calculated_attributes` lists stay untouched** — they remain the authoritative computation
  order for the unchanged eager engine until Task 6 deletes them with it (no derived ordering, no
  composition rules; `ServerBase`'s interleaved order and `EdgeStorage`'s parent-attr filtering
  keep working as-is). The shim is minimal: `@computed_attribute.__set_name__` registers the slot
  (registry needed from Task 5 on) and synthesizes the old `update_<attr>` method (call getter,
  assign through today's `__setattr__` bookkeeping), so the eager engine runs unmodified.
  Whole-dict orchestrators and init-time `ExplainableObjectDict()` assignments survive this task
  for the same reason (deleted at Task 6); only their per-element bodies move into
  `@computed_dict` getters
- `efootprint/core/hardware/server_base.py`, `efootprint/core/job.py`, etc. — isinstance-filter
  reverse properties → `ReverseCollection("Type")` / `ReverseLink(…)` declarations
- `docs_sources/doc_utils/generate_object_reference.py` — doc-as-code reader re-pointed from
  `update_<attr>` docstrings to getter docstrings

**Tests added/changed:**
- `tests/abstract_modeling_classes/test_reactive_core.py` — descriptor registration + eager-shim
  unit tests
- Registry/list consistency test: per class, `set(calculated_attributes) == set(registry names)`
  — doubles as the conversion-omission detector (transitional, dies with the lists at Task 6)
- Existing suite unchanged (that is the point)

**Acceptance:**
- Full suite green with **zero expected-value changes**; parity harness green
- No `def update_` function remains in `efootprint/core/`; docs build produces the same object
  reference content

**Depends on:** Task 2.

**Status:** Done. Notes: the conversion also covers `efootprint/builders/**` (their update methods
feed the same `calculated_attributes` machinery); the EcoLogits dynamically-generated update
methods became getter factories attached via `add_computed_attribute`. Abstract update methods
became abstract descriptors (`__isabstractmethod__` propagates), and an overriding getter without
its own docstring inherits the parent slot's (preserving today's MRO docstring resolution for docs
and interface readers). The registry/list consistency test carries one documented exemption:
`EdgeStorage` deliberately drops inherited `power`/`idle_power`. Docs-content parity verified by
normalized diff (uuid ids, numeric example values and the `list(set(...))`-ordered backwards-links
section are nondeterministic run to run on unchanged code). Three test files adapted to the new
declarations (abstract test subclasses now declare getters; the Storage two-servers test uses
typed server mocks since `ReverseLink` filters containers by type).

---

## Task 4 — Constitution amendments §1.4 + §2.5 (own commit, via `update-constitution`)

**Goal:** Amend §1.4 (doc-as-code SSOT: authoritative docstrings now live on computed-attribute
getters, not `update_<attr>` methods) and §2.5 (class-registration gate wording: reference the
canonical-class registry derived from `SANKEY_COLUMNS` instead of `CANONICAL_COMPUTATION_ORDER`,
which Task 6 retires). One deliberate commit, separate from feature work, with justification.

**Files touched:**
- `specs/constitution.md`

**Tests added/changed:** none.

**Acceptance:**
- Both amendments in a single dedicated commit; wording consistent with the post-Task-3 code and
  the Task-6 retirement plan

**Depends on:** Task 3 (getter docstrings must exist before §1.4 names them).

**Status:** Done (commit `860a243a`). §2.5 uses role-based wording (canonical-class registry =
flattened `SANKEY_COLUMNS` + breakdown-only + non-Sankey canonical classes) valid before and after
the Task-6 retirement. Noted for Task 6: constitution §1.1's documented chain-optimizer back-edge
paragraph goes stale when the optimizer is deleted — amend in its own commit then.

---

## Task 5 — Reactive core engine (lands unused) (stage 3, part 1)

**Goal:** Implement the full reactive engine in `reactive_core.py` — slot states (cached / void +
one-bit wave marker), the exception-safe contextvar compute stack (doubling as cycle guard with
readable chain errors), the slot-addressed edge registry (calculus + structural), and the deletion
wave — centrally unit-tested, not yet wired into the model classes. Implementation and review
check against the correctness conditions hardened by the signals/Salsa/Adapton literature (plan
§7): dependency edges refreshed on every recompute (conditional dependencies stay correct),
exception-safe push/pop, re-entrancy, cycle reporting with a readable chain, and the
partial-reload state (cached slots below valueless ones) treated as a first-class case.

**Files touched:**
- `efootprint/abstract_modeling_classes/reactive_core.py`

**Tests added/changed:**
- `tests/abstract_modeling_classes/test_reactive_core.py` — slot lifecycle, invalidation waves,
  wave-marker pruning, structural-edge recording, dependency-edge refresh on recompute
  (conditional dependencies), cycle detection, exception safety of push/pop, re-entrancy

**Acceptance:**
- Reactive core fully covered by unit tests on synthetic graphs; production behavior unchanged
  (engine unused); suite green

**Depends on:** Task 3 (descriptors + registries it extends). Can proceed in parallel with Task 4.

**Status:** Done. Notes: engine = `ReactiveSlot` (name + zero-arg getter; `pull`/`attach_cached_value`/
`replace_dependencies`), module-level `record_calculus_dependency` / `record_structural_dependency`
(no-ops outside a computation; pull alone records nothing — production edges come from the ancestry
walk and relationship read hooks) and `invalidate(*slots) -> visited set`. Correctness choices per the
literature checklist: edges are collected per compute frame and committed only on success (a failed
getter keeps the previous edges as a safe over-approximation and leaves the slot void for retry); wave
pruning keys off the marker, not voidness (partial reload legitimately leaves void, unmarked
intermediates above cached slots — the marked-implies-dependents-marked invariant is what makes pruning
sound); the compute stack is an immutable-tuple contextvar with token reset in `finally`;
`invalidate` raises if called during a computation (write-during-compute guard).
`attach_cached_value` + `replace_dependencies` are the stage-4 load-path surface. Descriptors untouched
(still eager shim); full suite and parity harness green.

---

## Task 6 — Engine swap with pull-ALL eager set (stage 3, part 2)

**Goal:** Switch the descriptors from the eager shim to the reactive engine and delete the push
machinery. `ModelingUpdate` becomes apply → invalidate → eagerly pull a transitional **pull-ALL**
set (every slot cached after every update), keeping serialization and interface behavior
observationally identical. Retire `CANONICAL_COMPUTATION_ORDER` (its only ordering consumer, the
chain optimizer, dies here): per plan §7, `CANONICAL_CLASSES` is derived from
`flatten(SANKEY_COLUMNS) + SANKEY_BREAKDOWN_ONLY_CLASSES + NON_SANKEY_CANONICAL_CLASSES`
(`[Service, EdgeDeviceGroup]`), and Sankey sorting keys off `SANKEY_COLUMNS` directly.

**Files touched:**
- `efootprint/abstract_modeling_classes/reactive_core.py` — descriptors switch to pull mode
- `efootprint/abstract_modeling_classes/modeling_object.py` — `__setattr__` split (user writes
  invalidate; computed storage moves into descriptors); delete
  `modeling_objects_whose_attributes_depend_directly_on_me` (all classes),
  `mod_objs_computation_chain`, chain optimizer (+ its §1.1 back-edge),
  `compute_calculated_attributes`, flush helpers
- `efootprint/abstract_modeling_classes/modeling_update.py` — rewrite: apply + invalidate + eager
  pull-ALL + input-restore rollback (rollback = re-invalidation, no snapshots; `reset_values` dies)
- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` — slot-addressed
  ancestry exposure; `attr_updates_chain` deleted
- `efootprint/abstract_modeling_classes/contextual_modeling_object_attribute.py`,
  `list_linked_to_modeling_obj.py`, `object_linked_to_modeling_obj.py` — read hooks (structural
  edges) + typed reverse-slot bumps at container-field transitions
- `efootprint/abstract_modeling_classes/explainable_object_dict.py` — facade over key-set node +
  per-key sub-slots
- `efootprint/all_classes_in_order.py` — `CANONICAL_COMPUTATION_ORDER` →
  derived `CANONICAL_CLASSES` + `NON_SANKEY_CANONICAL_CLASSES`
- `efootprint/utils/impact_repartition/sankey.py` — `_sort_class_names` keys off `SANKEY_COLUMNS`
- `efootprint/utils/object_relationships_graphs.py` — `ALL_CANONICAL_CLASSES_DICT` source updated
- `efootprint/core/**` — residual MOWADDOM property removals

**Tests added/changed:**
- Parity property test (Task 2 harness) now gating the reactive engine
- Recompute-counter variant: one-usage-pattern edits touch only the expected slot cone; also
  counts recomputes yielding a value equal to the one they replaced (feeds the stage-4 early-cutoff
  decision, plan §7)
- Cycle-guard and rollback-on-`InsufficientCapacityError` tests updated to the new mechanics

**Acceptance:**
- Full suite + parity property test green; all existing expected-value integration tests unchanged
- Recursion depth assertion passes on the big fixture
- No reference to MOWADDOM, `attr_updates_chain`, `mod_objs_computation_chain`,
  `CANONICAL_COMPUTATION_ORDER`, or `reset_values` remains

**Depends on:** Tasks 4 and 5.

**Status:** Done. Notes: flush helpers (`flush_cached_properties_system_wide`, `render_cache`) survive
until Task 7 retires the attribution wipe — deleting them here would have left attribution memos stale.
Getters returning another attribute's value object directly (an aliasing pattern the eager engine
re-addressed silently) now raise at attach time; the three edge-component sites derive with `.copy()`.
Loads of calc-attr files rebuild calculus edges from serialized ancestry and defer structural edges to
a one-shot full recompute on the first relationship change. The parity harness needed two hardenings:
a quantization-aware fallback tolerance (live vs JSON-rebuilt systems legitimately iterate collections
in different orders, and float32 reduction noise through `ceil` flips instance counts by one quantum)
and a strict end-of-sequence staleness gate (full in-memory recompute must reproduce the incremental
values — verified bitwise-identical during debugging). Recompute-counter numbers on 3 representative
edits: 103 slot recomputations, 64 (62%) equal-value — input for the stage-4 early-cutoff decision.
Unit tests migrated from `update_*` calls to reads plus `recompute_attribute`/`patch_attribute` helpers
in `tests/utils.py`.

Post-landing review fixes: the staleness gate snapshots dict entries (facades are live views — comparing
them to themselves was vacuous) and compares bitwise, no float tolerance; the live-vs-rebuilt fallback
tolerance narrowed to rtol=1e-4 (scoped to observed float32 reduction noise, ~4e-5 relative; a genuine
quantization flip exceeding it must be examined before any widening); computed-dict facades raise
KeyError for keys outside their key collection (membership read without recording an edge, so per-key
granularity is preserved); assigning a computed attribute on a live model raises — pin via
`patch_attribute` / the descriptor's `attach_cached_value` (mock unit tests migrated accordingly);
inputs-only serialization peeks slots instead of pulling (saving never computes); the loaded-model wipe
hook skips mid-construction objects explicitly instead of swallowing exceptions.

---

## Task 7 — Impact-repartition matrix slot and attribution rework (stage 4, part 1)

**Goal:** Fold impact attribution into the one caching paradigm: attribution memos become ordinary
computed slots, `System.impact_repartition_matrix` lands as a lazy slot whose rows are attribution
atoms reduced to period sums (dict-row encoding first, per plan §7), and the wipe-all flush
(`flush_cached_properties_system_wide` / `render_cache` / `flushed_memo`) retires. Sankey rendering
folds the matrix's summed scalars (no memoization needed).

**Files touched:**
- `efootprint/core/attribution/__init__.py` — atom generation feeds the matrix slot;
  `flushed_memo`/`render_cache` deleted
- `efootprint/core/system.py` — `impact_repartition_matrix` computed slot
- `efootprint/core/hardware/server_base.py` (+ storage, edge devices) — attribution
  `@cached_property` layer → computed slots
- `efootprint/utils/impact_repartition/sankey.py` — folds over the stored matrix

**Tests added/changed:**
- `tests/test_impact_repartition_sankey.py` — expectations preserved (rendering parity)
- Matrix-slot unit tests: row content, invalidation via the graph (no wholesale wipes)

**Acceptance:**
- All Sankey combinations render identically from the matrix; suite green
- A one-input edit invalidates only the matrix rows in its cone (recompute-counter check)

**Depends on:** Task 6.

---

## Task 8 — Serialization contract, lazy default, migration, perf gates (stage 4, part 2)

**Goal:** Narrow the eager set to system total footprints behind the per-call
`ModelingUpdate(…, eager_outputs=…)` parameter (plan §7), and land the minimal persistence
contract as the **single canonical protocol** (`save_calculated_attributes` and the detection flag
die): per-slot `serialize=True` flags, values-free topology section (incl. structural edges;
children inverted at load; formula tuples for serialized slots only), schema version bump +
migration handler. Load is version-aware (plan §7): exact `efootprint_version` match → stored
values attach as trusted caches, zero compute; any mismatch (incl. minor/patch — today's loader
only reacts to major bumps) → schema handlers run, then stored values are **demoted to a retained
"as computed by vX" baseline** (side-band, not slot caches; in-memory and session-scoped, never
serialized — the JSON always carries only current-version values, the old file itself being the
durable baseline) and recompute on pull, so methodology/upstream-data drift surfaces at upgrade
time. The drift *visualization* is a future feature (roadmap); this task ships the protocol and
the `system_comparison`-based hook. Measure
both matrix encodings and **report the numbers to the user** before finalizing (plan §7).

**Files touched:**
- `efootprint/abstract_modeling_classes/modeling_update.py` — `eager_outputs` parameter, default =
  system total footprints
- `efootprint/abstract_modeling_classes/reactive_core.py` — serialize flags on slot declarations
- `efootprint/api_utils/system_to_json.py`, `json_to_system.py` — flag-driven serialization,
  topology section, cached-value attachment on load, no detection flag / `after_init` chains
- `efootprint/api_utils/version_upgrade_handlers.py` — schema bump + upgrade handler
- `tests/performance_tests/` — gates wired against Task-2 baselines

**Tests added/changed:**
- Deserialized-file parity variant: mutation sequences starting from a freshly loaded
  minimal-format file (cached footprints below valueless intermediates)
- Round-trip tests under the new contract; migration-handler test on an old-format file
- Version-trust tests: exact-match load attaches caches with zero compute; mismatched-version load
  demotes to baseline, recomputes on pull, and the baseline-vs-recomputed comparison hook returns
  the drift
- Perf gates from spec §2: file weight ≤ 30%, load ≥ 3× faster, 1,000-iteration loop ≥ 10×,
  engine overhead < 5%, peak memory ≤ eager build

**Acceptance:**
- All spec §2 criteria measurable library-side pass; lazy auditability demonstrated (intermediate
  value + formula on demand after load, no full recompute)
- Both matrix encodings measured on the regenerated fixture; **user consulted on the
  complexity/speed/size tradeoff** and the chosen encoding applied (target ≤ 0.3 MB)
- Equal-value-recompute frequency on representative edits reported alongside the perf numbers
  (same checkpoint), feeding the **user's decision on selective hub-slot early cutoff** — deferred
  knob per plan §5/§7; no cutoff implementation in this task

**Depends on:** Task 7.

---

## Task 9 — Interface adaptation (stage 4, part 3 — lands in e-footprint-interface)

**Goal:** The one coordinated cross-repo step: bump the efootprint dependency and adapt the
interface to the minimal contract — single stored session copy, saved whenever flagged slots
change (edits and lazy Sankey fills), Sankey served from the stored repartition matrix, audit
drill-down computing lazily (brief loading state), canonical-class consumers migrated.

**Files touched (all in `e-footprint-interface/`):**
- `pyproject.toml` / `poetry.lock` — efootprint version bump
- `model_builder/domain/entities/web_core/model_web.py` + session repository — load under the new
  contract (no recompute on load), one copy instead of two, save-on-flagged-change
- `model_builder/domain/object_factory.py` — drop `compute_previous_system_footprints=False`; pass
  default `eager_outputs`
- `model_builder/adapters/views/sankey_views.py` — folds the stored matrix for every
  column/phase/exclusion combination
- `model_builder/domain/services/emissions_calculation_service.py` + calc-graph views — read
  cached/lazy slots; drill-down loading state
- `model_builder/domain/efootprint_to_web_mapping.py`,
  `model_builder/domain/all_efootprint_classes.py` — `CANONICAL_CLASSES` migration
- `tests/performance_tests/` fixtures regenerated in the new format

**Tests added/changed:**
- Interface suite updated to the new session shape; view-latency assertions (load ≥ 3× faster,
  edit request within ± 20%); Sankey combination tests against stored sums

**Acceptance:**
- End-users see identical numbers and screens; all spec §2 interface-side criteria pass
- Session store holds one copy at ≈ ≤ 30% of today's weight; old sessions reload as inputs-only
  and recompute on pull

**Depends on:** Task 8 (released efootprint version carrying the contract).

---

## Ordering rationale

The plan's four delivery stages form a release train — each task leaves the suite green and ships
independently. Stage 1 splits in two because "deletions landed, suite green" is a real pause point
and the parity harness is subtle new test code deserving its own review; fixtures must regenerate
*after* the Task-1 deletions change the serialized shape. Stage 2 stays one task despite touching
~34 files: it is a single mechanical, behavior-identical transform with no pause point between the
descriptors and their consumers (the eager shim only means anything with the bodies converted).
Task 4 is constitutionally required to be its own commit; it follows Task 3 (§1.4 must name
existing getters) and precedes Task 6 (§2.5 wording must not be invalidated by the retirement it
describes). Stage 3 splits at the canonical "infrastructure landed but unused" boundary: the
reactive core is centrally unit-testable alone (Task 5, parallelizable with Task 4), while the
swap + deletions (Task 6) is the risky diff the parity gate exists for — keeping it free of new
engine code makes failures attributable. Stage 4 splits between the attribution/matrix rework
(Task 7, in-memory, behavior-preserving under pull-ALL) and the serialization contract + lazy
default (Task 8) because the contract needs the matrix slot to exist and each is a large,
independently reviewable behavioral milestone. Task 9 is last by definition: it is the only
cross-repo step and consumes the released library contract.
