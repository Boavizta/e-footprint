# Task 2 — Derive explanation links from formula and slot graph
Written 2026-10-19 against e-footprint 58966eb1; revised 2026-10-20 for the integrated 1.3.
Plan: [1.1](../plan.html#resolver), [1.2](../plan.html#ancestors), [1.3](../plan.html#children), [1.4](../plan.html#persistence) (saving, loading, documentation), [verification map](../plan.html#delivery), [PLAN-UPDATE-03](../plan.html#plan-update-03). Task: [tasks.md](../tasks.md#task-2--derive-explanation-links-from-formula-and-slot-graph).
Status: under review.

## Start here
All in `efootprint/abstract_modeling_classes/explainable_object_base_class.py` unless noted:
- `get_attribute_from_flat_obj_dict` — the resolver; it peeks today.
- `ExplainableObject.__slots__`, `__init__`, `initialize_calculus_graph_data_from_json`, `load_ancestors_and_children_from_json`, the `direct_ancestors_with_id` and `direct_children_with_id` properties, `set_modeling_obj_container`, `add_child_to_direct_children_with_id`, `remove_child_from_direct_children_with_id`, `all_descendants_with_id`, `to_json`.
- `invert_children_links_of_stored_values` and its call under `if trust_stored_values:` in `json_to_system` (`efootprint/api_utils/json_to_system.py`).
- `slot_of_attached_value`, `ReactiveSlot.dependents`, `.calculus_dependencies`, `.on_value_dropped` — `reactive_core/graph.py`.

## Change along the code path
Land everything below as one change. The plan's delivery section explains why it cannot be split.
1. **Resolver** (plan 1.1 snippet). Plain attributes resolve by `getattr`. A key address on a computed dict indexes `descriptor.facade(container)[key]`, with the descriptor taken from `computed_slots(container.efootprint_class)`; this pulls one sub-slot. A key address on an input dict indexes the input dict. Delete the peeking body and its docstring.
2. **Ancestors** (plan 1.2 snippet). Add `_attached_formula_leaves`. For a value with a formula key, `initialize_calculus_graph_data_from_json` sets `_direct_ancestors_with_id = None`. The getter derives the list on first read, deduplicated by id in left-to-right order. Remove the three hydration slots, their `__init__` lines and `load_ancestors_and_children_from_json`. The setter only assigns.
3. **Children** (plan 1.3 snippet). Make it a read-only property: filter on `on_value_dropped is not None` and `slot in dependent.calculus_dependencies`, then pull. Task 1 makes those links current, so no check after the pull. Remove `_direct_children_with_id`, its setter, the add/remove helpers, `all_descendants_with_id`, and both link loops in `set_modeling_obj_container`. Keep the label check, the base call and `finalize_explanation()`.
4. **Save**. `to_json(with_formula=True)` stops writing `direct_ancestors_with_id`; it still writes `explain_nested_tuples_from_json` when set.
5. **Load**. Delete `invert_children_links_of_stored_values` and its call. `rebuild_dependency_graph` is unchanged.
6. **Docs and changelog**. `persistence.html` contract cell and children sentence (plan 1.4 wording). `recomputation.html`: one sentence saying display-time resolution may compute, and bookkeeping never does. `_release_value` docstring: drop "ancestor children links". `CHANGELOG.md`: a new `## [Unreleased]` heading above V26.0.1 with one entry; Task 3 extends it.

## Earlier tasks
Task 1 makes every link current: voided slots have none, failed attempts are linked to their reads, removed and deleted slots are unlinked. Without it, the post-reset loops over `country.average_carbon_intensity.direct_children_with_id` in `integration_simple_system_base_class.py` (`run_test_add_usage_pattern`) and `integration_simple_edge_system_base_class.py` (two scenarios) raise `KeyError`. Consequence for tests: right after an edit, a value's children are only those already recomputed. A test that asserts children after an edit must pull first, as the halfway-save test already does with `system.total_footprint`.

## Reuse
- `observe_computations` (graph.py) for the load, save and display-only assertions.
- `build_calculus_graph` (`efootprint/utils/calculus_graph.py`) for node and edge sets; `compute_formula_as_flat_tuple` for flat formulas.
- Put the round-trip helper in `IntegrationTestBaseClass` as `run_test_*`, so `AutoTestMethodsMeta` runs it on every fixture system in both its code and from-json variants. The services system carries the EcoLogits GenAI external-API server, the shape the plan's "EcoLogits video test system" row aims at. The video test file builds no System, so its existing in-memory ancestor assertions stay as they are.

## Invariants and traps
- No pull during load, save, compute or invalidation. Only `explain_nested_tuples` (display) and the children property may pull. `record_calculus_edges_from_ancestry` reads ancestors of fresh values only, which use their in-memory lists.
- The load order is: `attach_cached_value` runs `set_modeling_obj_container` before `initialize_calculus_graph_data_from_json`. The sentinel `None` must be set by initialize, never read earlier.
- A loaded input (no formula key) keeps `[]`. `explain()` still short-circuits on an empty ancestor list.
- A loaded value whose leaves are all inline constants has no ancestors, as in memory.
- Values pulled for display are not serialize-flagged, so a later save writes the same JSON.
- `all_ancestors_with_id` stays (used by `ExplainableObjectDict`).
- Getter errors from pulled children or operands propagate; add no recovery.

## Validation
- Unit: replace the bookkeeping tests in `test_explainable_object_base_class.py` (`test_set_modeling_obj_container_should_trigger_*`, the `add_child`/`remove_child` tests, `test_all_descendants_with_id`). Rewrite the assertion `assertIn(modeled_child, modeled_value.direct_children_with_id)` in `test_explainable_object_dict.py`: hand-attached values have no children. Flip `assertIn("direct_ancestors_with_id", json_output)` to `assertNotIn` in `test_explainable_quantity.py` and `test_explainable_hourly_quantities.py`. Add a test that children of an input read by a computed-dict key set and by a computed structure contain neither. Add one where a save of a partially computed model computes nothing.
- Integration: round-trip helper comparing before and after `system_to_json`/`json_to_system`: the flat formula token by token (operands compared by id and label), ancestor ids of the total and of one nested saved value, children ids of a job input including void dependents, and node and edge sets of `build_calculus_graph(system.total_footprint)`. Add an `observe_computations` assertion around `json_to_system` in `test_system_calculation_graph_right_after_json_to_system`. Add a test that reading one stored footprint's formula leaves an unrelated stored footprint's operand slots void. Keep the halfway-save test (`job_from_json.data_transferred.direct_children_with_id`) passing.
- `tests/performance_tests/json_size.py`: drop the ancestor and children size lines.
- Commands: `PYTHONPATH=./ <venv>/bin/python -m pytest tests` with `MPLBACKEND=Agg`, then `tests/performance_tests` after regenerating the local `big_system.json` (`tests/performance_tests/generate_big_system.py`).

## Out of scope
Schema version, handler and fixture version strings (Task 3). Interface (Task 4). Stored-topology rendering without pulls.

## Unverified
The plan's latency baseline was measured with addresses pulled through `getattr`. Reading computed-dict elements through the facade should only lower those numbers. Re-measure only if a reviewer asks.
