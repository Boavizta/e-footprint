# Multiple usage journeys per pattern — Tasks

**Status:** Tasks — under review.  
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — Land the plural library model and migration

**Status:** Done.

**Goal:** Deliver the complete e-footprint domain change as one coherent schema/API transition: weighted web journeys,
unweighted edge functionality bundles, journey-aware web coordinates, aggregate edge need calculations, conservative
attribution, comparison support, and migration of existing one-journey JSON.

**Files touched:**

- `efootprint/core/usage/usage_pattern.py`
- `efootprint/core/usage/usage_journey.py`
- `efootprint/core/usage/usage_journey_step.py`
- `efootprint/core/usage/job.py`
- `efootprint/core/usage/edge/edge_usage_pattern.py`
- `efootprint/core/usage/edge/edge_usage_journey.py`
- `efootprint/core/usage/edge/recurrent_edge_component_need.py`
- `efootprint/core/usage/edge/recurrent_server_need.py`
- Related edge builders and recurrent-need subclasses under `efootprint/builders/usage/edge/` and
  `efootprint/core/usage/edge/`
- `efootprint/core/hardware/device.py`
- `efootprint/core/hardware/edge/edge_component.py` and its concrete subclasses
- `efootprint/core/hardware/edge/edge_device.py`
- `efootprint/core/hardware/server_base.py`
- `efootprint/core/hardware/storage.py`
- `efootprint/core/hardware/network.py`
- `efootprint/builders/external_apis/external_api_base_class.py`
- `efootprint/core/attribution/__init__.py`
- `efootprint/core/system.py`
- `efootprint/comparison/system_comparison.py` if the generic relationship diff needs adaptation
- `efootprint/api_utils/version_upgrade_handlers.py`
- `efootprint/version.py`, `pyproject.toml`, dependency/export metadata affected by the major version
- Library builders, modeling templates, examples, fixtures, and generated documentation sources that construct or
  name either pattern type
- `specs/architecture/relationships.html`
- `specs/architecture/attribution.html`
- `specs/architecture/persistence.html`
- Relevant recomputation/modeling architecture pages and `CHANGELOG.md` according to the chosen implementation workflow

**Tests added/changed:**

- `tests/usage/test_usage_pattern.py`
- `tests/usage/test_usage_journey.py`
- `tests/usage/test_usage_journey_step.py`
- `tests/usage/test_attribution_primitives.py`
- `tests/usage/edge/test_edge_usage_pattern.py`
- `tests/usage/edge/test_edge_usage_journey.py`
- `tests/usage/edge/test_recurrent_edge_component_need.py`
- `tests/usage/edge/test_recurrent_server_need.py`
- `tests/hardware/test_device.py`, `test_network.py`, `test_storage.py`, and relevant server tests
- `tests/hardware/edge/test_edge_device.py` and relevant edge-component tests
- `tests/builders/external_apis/` attribution coverage
- `tests/core/attribution/test_attribution.py` and `tests/core/attribution/conservation.py`
- `tests/test_system.py` and `tests/test_system_comparison.py`
- `tests/api_utils_tests/test_json_to_system.py`
- `tests/api_utils_tests/test_minimal_serialization_contract.py`
- `tests/api_utils_tests/test_version_upgrade_handlers.py`
- Integration fixtures/tests under `tests/integration_tests/`
- Big-system generation, recomputation, and cache-scaling assertions under `tests/performance_tests/`

**Acceptance:**

- `UsagePattern` exposes a non-empty `usage_journeys` weighted relationship with strictly positive fractional weights,
  `hourly_occurrences`, and `utc_hourly_occurrences`; web relationship keys remain intrinsically unique.
- Journey weights scale concurrency, device occupancy, job calls, network traffic, storage/server demand, and footprint.
  A shared step or job has distinct stable web coordinates per actual `(pattern, journey, child)` path, with precise
  invalidation and stale-key pruning.
- `EdgeUsagePattern` owns `usage_span`, `hourly_deployment_starts`, `utc_hourly_deployment_starts`, and
  `nb_deployments_in_parallel`, and exposes a non-empty, duplicate-free `edge_usage_journeys` list. Constructor, live
  mutation, and raw-load validation enforce the invariant atomically.
- One typed, non-serialized `EdgeContainmentInventory` enumerates only actual server-need and component-need paths with
  `nb_occurrences`. Recurrent calculations retain `nb_of_occurrences_of_self_within_usage_pattern`, obtained by summing
  those paths.
- Each edge recurrent need caches one unitary hourly series per `(pattern, need)`. The deployment series supplies the
  calendar range; active deployments are multiplied downstream. Shared bundle paths increase the need's occurrence
  count without creating per-bundle hourly arrays.
- Fixed edge hardware fabrication and idle/base energy are counted once per deployed hardware, while distinct and
  repeated bundle needs add before component capacity/power physics. Reversing the edge-journey list leaves physical
  totals and attribution folds unchanged.
- Job attribution cells and every emitting source carry explicit journey identity. Web cells use journey-aware base
  coordinates; edge cells share `(edge pattern, recurrent server need)` base caches and split them by
  `path.nb_occurrences / nb_of_occurrences_of_self_within_usage_pattern`. All attribution conservation tests pass.
- System traversal includes every selected journey without cloning. Comparison reports web journey membership/weight
  changes with the label “Journeys per pattern occurrence”.
- The next major JSON handler migrates singular relationships at weight 1 / one-item list, renames occurrence and
  deployment fields, copies edge usage span with source metadata to every former owning pattern, removes obsolete
  calculated state/coordinates, and preserves an appropriate version baseline. Inputs-only and calculated-state files
  round-trip under the new schema; representative old models recompute equivalently.
- Cache-count tests show web hourly caches scale with actual web paths and edge hourly caches with distinct
  `(pattern, need)` pairs, never a Cartesian product or edge bundle-path count. Existing transient attribution-source
  eviction behavior remains intact.
- The complete library test suite and strict documentation build pass.

**Depends on:** none.

---

## Task 2 — Establish library-native memory benchmarks and harden cache scaling

**Status:** Done.

**Goal:** Move model-engine memory/performance work close to its source implementation in e-footprint, profile the new
multi-journey/shared-child topology immediately after Task 1, and make focused library refinements if the evidence
reveals avoidable cache growth or source-retention pressure.

**Files touched (in `e-footprint`):**

- New canonical model-engine laboratory under `performance/memory/`, including a native profiler script, README,
  topology/scenario helpers, ignored-artifact policy, and dated result evidence
- Existing reusable generators and deterministic performance assertions under `tests/performance_tests/`
- `efootprint/api_utils/json_to_system.py`, public footprint/attribution APIs, and reactive inspection helpers only as
  consumers of the benchmark—not through benchmark-only production hooks
- Task 1 calculation/cache modules only when a measured result justifies a focused optimization
- Relevant performance/recomputation architecture documentation if profiling establishes a durable new rule
- `CHANGELOG.md` according to the chosen implementation workflow

**Tests added/changed:**

- Deterministic tests for the native synthetic topology: journeys are distinct and selected once while lower-level
  steps/functions/needs are intentionally shared rather than cloned.
- Cache/slot-count assertions for actual web paths, distinct edge `(pattern, need)` pairs, and scalar attribution rows.
- Existing recomputation and attribution-source eviction tests after any evidence-driven optimization.
- Fresh-process benchmark scenarios remain evidence, not platform-independent pass/fail memory thresholds.

**Acceptance:**

- `e-footprint/performance/memory/` is the documented canonical home for future model-engine memory benchmarks.
- The native profiler loads models through e-footprint without Django or `ModelWeb` and can vary modeled hours, pattern
  count, journeys per pattern, and shared-child topology.
- Native scenarios cover hydration, total footprint, cold/warm attribution matrix, result-primed attribution matrix,
  direct manufacturing/usage attribution, and repeated retained attributed results.
- Runs report topology dimensions, reactive callback counts, materialized coordinate/cache-slot counts where observable,
  peak RSS/PSS/USS or available process/cgroup equivalents, and retained/post-GC memory.
- Evidence confirms web hourly caches scale with actual `(pattern, journey, child)` paths, while edge recurrent arrays
  scale with distinct `(pattern, need)` pairs even when scalar containment paths/rows increase.
- Existing transient source helpers are still released after source reduction. Any meaningful regression or
  largest-single-source pressure is either corrected in this task or brought back for explicit review; no
  `computed_dict` transient mechanism is introduced without separate measured justification.
- Historical interface evidence remains untouched; the new library README links to it while distinguishing production
  runtime measurements from model-engine benchmarks.
- The library test suite, deterministic performance gates, and strict documentation build pass after any refinement.

**Depends on:** Task 1.

---

## Task 3 — Adapt the interface and deliver the plural-pattern UX

**Status:** Done.

**Goal:** Adopt the performance-validated library contract throughout e-footprint-interface, expose the agreed creation,
editing, validation, and canvas behavior, and retain only interface-specific production profiling concerns.

**Files touched (in `e-footprint-interface`):**

- `model_builder/domain/entities/web_core/usage/usage_pattern_web.py`
- `model_builder/domain/entities/web_core/usage/edge/edge_usage_pattern_web.py`
- `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py`
- `model_builder/domain/entities/web_core/model_web.py` and `model_web_utils.py` where plural traversal is required
- `model_builder/adapters/forms/form_field_generator.py`
- `model_builder/adapters/forms/form_context_builder.py`
- `model_builder/adapters/forms/form_data_parser.py`
- Relevant form strategies/configuration under `model_builder/adapters/forms/` and `model_builder/adapters/ui_config/`
- `model_builder/templates/model_builder/side_panels/` weighted-dict and multi-select form fragments as needed
- `model_builder/templates/model_builder/components/model_canvas_content.html` and related canvas/link rendering code
- `model_builder/domain/services/system_validation_service.py`
- `scripts/intro_template_scenarios/` and other committed examples/fixtures using the renamed fields
- `performance/memory/scripts/profile_model.py` and `performance/memory/README.md`, slimmed or clarified around Django
  imports, `ModelWeb`/session hydration, rendered Sankey payloads, computation-memory monitoring, cgroup enforcement,
  and production-container calibration; historical evidence remains in place
- `specs/architecture.md`, relevant pages under `specs/design/`, user-facing help text, and `CHANGELOG.md` according to
  the chosen implementation workflow
- Interface dependency metadata only when adopting a released library version; use the sibling editable checkout for
  local co-development and restore temporary path dependency changes before committing

**Tests added/changed (in `e-footprint-interface`):**

- `tests/unit_tests/domain/entities/web_core/usage/test_usage_pattern_web.py`
- `tests/unit_tests/domain/entities/web_core/usage/test_edge_usage_pattern_web.py`
- `tests/unit_tests/domain/entities/web_core/usage/test_usage_pattern_web_base_class.py`
- Relevant `tests/unit_tests/domain/entities/web_core/test_model_web*.py`
- `tests/unit_tests/adapters/forms/test_form_field_generator.py`
- `tests/unit_tests/adapters/forms/test_form_context_builder.py`
- `tests/unit_tests/adapters/forms/test_form_data_parser.py`
- `tests/unit_tests/domain/services/test_system_validation_service.py`
- Relevant integration form/create/edit/delete and result-view smoke tests
- `tests/e2e/objects/test_usage_patterns.py`
- `tests/e2e/objects/test_usage_journeys.py` if shared-journey behavior requires it
- One focused weighted-web flow and one focused multi-bundle edge flow in the appropriate E2E modules
- Existing computation-memory monitor and Sankey-profiler tests after the responsibility split

**Acceptance:**

- Web pattern forms use the existing weighted-dict UX to select several journeys and edit positive weights labelled
  “Journeys per pattern occurrence”; creation preselects the first journey at weight 1.
- Edge pattern forms use a unique multi-select for functionality bundles and expose pattern-owned usage span and
  deployment starts. Creation preselects the first available journey.
- The UI prevents removal of the final journey and presents domain validation errors for malformed submissions, while
  the library remains the source of truth for non-empty, positive-weight, and duplicate-free invariants.
- Pattern cards stay top-level and draw one canvas relationship to every selected journey; journeys are reused rather
  than cloned or nested under the pattern.
- All labels, tooltips, form payloads, selectors, examples, and wrappers use `usage_journeys`,
  `edge_usage_journeys`, `hourly_occurrences`, and `hourly_deployment_starts` consistently.
- Existing/new JSON sessions hydrate through the library migration path; no Django database migration is introduced.
- Results and Sankey views render successfully for weighted web journeys, multiple edge bundles, and journeys shared
  by several patterns.
- Interface profiling remains capable of measuring production-only overhead and memory-guard behavior, while its docs
  direct core calculation/cache investigations to the library laboratory. Existing historical result files are not
  relocated or rewritten.
- Interface unit/integration suites, memory-monitor tests, and the two non-redundant E2E flows pass against the sibling
  library checkout.

**Depends on:** Tasks 1 and 2.

---

## Ordering rationale

Task 1 is intentionally broad because the plural constructors, calculation graph, attribution coordinates, serialized
schema, migration, fixtures, and semantic documentation have no safe behavioural pause point: splitting them would
leave the library unable to load its existing models or would expose incorrect partial calculations. Task 2 is the
first safe behavioural pause point: the complete library contract exists, so its model-engine memory behavior can be
measured and refined in the same repository before downstream adaptation. Task 3 is then the user-visible interface
delivery against that performance-validated contract. Production/container profiling stays with the interface, while
future calculation/cache benchmarks and deterministic scaling gates stay close to e-footprint.
