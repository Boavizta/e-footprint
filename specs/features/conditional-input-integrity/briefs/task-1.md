# Task 1 — Register and query conditional rules
Written 2026-10-13 against e-footprint `6cb80af3` and e-footprint-interface `7352ac8a`.
Plan: [trigger index](../plan.html#dependencies), [affected lookup](../plan.html#lookup-affected-inputs), [choice contract](../plan.html#validate-input-choice). Task: [1](../tasks.md#task-1).
Status: under review.

## Start here
- `ModelingObject.conditional_list_values` and `attributes_with_depending_values()` — `efootprint/abstract_modeling_classes/modeling_object.py`; the declaration is authoritative, while the old local reverse map goes away in Task 2.
- `EcoLogitsVideoGenExternalAPIJob.conditional_list_values` and its typed `external_api` constructor — `efootprint/builders/external_apis/ecologits/ecologits_video_external_api.py`; real cross-owner example.
- `get_init_signature_params()` — `efootprint/utils/tools.py`; current constructor annotation lookup. `input_values_match()` — `efootprint/abstract_modeling_classes/input_values.py`; existing semantic equality.
- `resolve_input_path()` — interface `model_builder/domain/conditional_inputs.py`; move its tuple-return behavior into the new library module. Task 5 removes the interface copy.
- `contextual_modeling_obj_containers` and `ContextualModelingObjectAttribute` — library `modeling_object.py` and `contextual_modeling_object_attribute.py`; direct backlinks and wrapper normalization.

## Change along the code path
At subclass definition, `ModelingObject.__init_subclass__()` calls `register_conditional_inputs(cls)`. Add `efootprint/abstract_modeling_classes/conditional_inputs.py` with the private type/path trigger index. Register inherited effective declarations, each terminal controller and each replaceable direct relationship segment. Report malformed paths at class definition. No instance or hydration registration.

`dependent_inputs(changed_addresses, proposed_changes=None)` reads matching index entries and follows only their reverse hops. Confirm the live direct wrapper still occupies the named input, ignore live links overridden by proposed changes, include proposed links, and require the exact dependent class recorded by an entry. Return deduplicated `(owner, attribute)` tuples. `resolve_input_path()` follows current or proposed direct links to the actual controller owner. `allowed_values()` reads the declaration at call time, intersects with static choices, preserves order and distinguishes no branch from an explicitly empty branch. See the [relationship path example](../plan.html#relationship-edit).

## Earlier tasks
None. This task creates the query APIs consumed by Tasks 2, 4, 5 and 6. Do not change the legacy validator or interface consumers yet.

## Reuse
Use constructor annotations from `get_init_signature_params()`, existing backlinks, wrapper normalization and `input_values_match()`. Keep static/conditional option objects as metadata; the helper must not attach them or compute getters.

## Invariants and traps
`conditional_list_values` can be patched after class definition: keep choices read live, with only routing metadata indexed. Inherited declarations and subclass overrides must not leak a parent's obsolete route. Paths through lists/dicts are outside the approved design. A missing path is an error, absence differs from zero, and an empty declared branch permits nothing. Lookup is bounded by matching routes and affected owners, never the whole System.

## Validation
Add `tests/abstract_modeling_classes/test_conditional_inputs.py` with synthetic direct/multi-hop, union annotation, inherited/overridden and later-defined classes; check proposed-link redirection, stale backlink exclusion, deterministic visit counts and all branch cases. Extend `tests/api_utils_tests/test_json_to_system.py` for loaded instances without registration side effects. From e-footprint: `MPLBACKEND=Agg poetry run pytest tests/abstract_modeling_classes/test_conditional_inputs.py tests/api_utils_tests/test_json_to_system.py`. Later full-suite/strict-doc gates are in [tasks.md](../tasks.md#gates-and-prerequisites).

## Out of scope
Live/constructor rejection (Task 2), editor repair (Task 4), interface imports (Task 5), migration (Task 6).

## Unverified
None: the declared API, annotation helper, backlink and existing interface resolver were located in the current checkouts. Implementation tests must prove the proposed-state traversal contract.
