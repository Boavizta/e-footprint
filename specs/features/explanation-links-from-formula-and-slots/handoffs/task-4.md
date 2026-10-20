# Task 4 — Persist coordinate-keyed sub-slot addresses
Repositories and implementation ranges: e-footprint `e47edc73..1fab268b` (single commit `1fab268b`; `e47edc73`
is an unrelated documentation commit on top of `8c1045ab`).

## Review pointers
- Key protocol: `to_json_key()` / `from_json_key(components, flat_obj_dict)` on `JobOccurrenceCoordinate`
  (`core/usage/job.py`) and `UsageJourneyStepCoordinate` (`core/usage/usage_journey_step.py`) — the second key
  class feeds the step occupancy weight of the same matrix, so it is covered too. Registry
  `COMPUTED_DICT_KEY_CLASSES_DICT` in `all_classes_in_order.py`.
- Node format: `[container id, attribute name, key]` where the key is `null`, an object id, or
  `{"ClassName": {component: id}}`. `system_to_json.py`: `_slot_address` keeps the address hashable (class name,
  component items), `_json_node` writes it, `_key_object_ids` drives the foreign-key skip for both key kinds.
  `json_to_system.py`: `_dict_key_from_json` rebuilds the key by dictionary lookups only (load stays
  zero-compute, asserted by the existing trusted-load test and the new contract test).
- No natural producer for the coordinate foreign-key skip through deletion: `self_delete` prunes the stale
  coordinate sub-slots (`discard_stale_keys`) and an unlinked usage pattern is still written through its
  journey's dict container. The contract test exercises `calculation_graph_section` on the object set minus the
  usage pattern, which is exactly the state the filter guards.
- `run_test_editing_a_reloaded_model_voids_its_stored_summaries` (integration base class, every fixture)
  compares the set of voided stored slots and the recomputed values after reload with an in-memory edit of the
  same input: an edge device's summary legitimately does not depend on a web job's `data_transferred` (complex
  fixture), so unconditional voiding of the summaries would be wrong.
- Big performance system: 386 coordinate-keyed nodes added (3,409 → 3,831 nodes, 2,071 → 2,457 edges), file
  3,395,348 → 3,788,401 bytes (+11.6%); load 0.024 → 0.026 s, save 0.022 → 0.026 s (same code, before/after
  file). The committed inputs-only fixtures carry no graph and are unchanged.
