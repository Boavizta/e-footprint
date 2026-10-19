# Task 1 — Sever edges of slots that leave the model
Written 2026-10-19 against e-footprint 58966eb1.
Plan: [PLAN-UPDATE-02](../plan.html#plan-update-02) part (a). Task: [tasks.md](../tasks.md#task-1--sever-edges-of-slots-that-leave-the-model).
Status: provisional — pending PLAN-UPDATE-02.

## Start here
- `computed_dict.discard_stale_keys` — `efootprint/abstract_modeling_classes/reactive_core/computed_slots.py` — pops each stale sub-slot from the registry (`stale_slot = registry.pop(...)`) and leaves its edges in place.
- `ModelingObject.self_delete` — `efootprint/abstract_modeling_classes/modeling_object.py` — drops every slot's value in the `for slot in list(instance_slot_registry(self).values())` loop, keeps edges.
- `ReactiveSlot.replace_dependencies` — `reactive_core/graph.py` — called with no arguments, it removes the slot from every former dependency's `_dependents` and clears its own sets.

## Change along the code path
1. In `discard_stale_keys`, after popping `stale_slot`, call `stale_slot.replace_dependencies()`.
2. In `self_delete`, in the existing drop loop, call `slot.replace_dependencies()` after `slot._drop_value()`.
Result: `slot.dependents` of a surviving input or computed slot contains no slot that was popped or belongs to a deleted object.

Prototype (monkeypatch in `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full/d9e42849-33d3-4a0d-961d-63fea7d042be/scratchpad/deleted_dependents_patched.py`, a scratch copy that may be gone): replaying `run_test_add_usage_pattern` (simple integration base class) with a ModelingUpdate, rollback, then `self_delete` of the added pattern, the country's `average_carbon_intensity` went from 6 explainable calculus dependents (one stale sub-slot whose pull raises `KeyError`) to 3 live ones. The deleted pattern's `utc_hourly_occurrences` no longer hangs off the country's `timezone`.

## Earlier tasks
None.

## Reuse
`replace_dependencies()` already maintains the reverse index both ways; do not hand-edit `_dependents`. Tests: `TestComputedDict.test_key_set_change_drops_stale_entries_and_adds_new_ones` in `tests/abstract_modeling_classes/test_reactive_core.py` (it calls `discard_stale_keys` directly) and the `ReactiveCore*` fixture classes in that file; the delete tests in `tests/abstract_modeling_classes/test_modeling_object.py`.

## Invariants and traps
- Only slots unreachable from the model lose edges. A popped sub-slot is never returned again: if its key comes back, `sub_slot()` creates a new slot. A deleted object's slots are never read again.
- Do not sever the slot's incoming side (its own `_dependents`). Readers keep it in their dependency sets until they recompute, which is harmless.
- Leave detached objects that were not deleted untouched (for example a network left behind by a rollback). They are live consumers.
- `reactive_core` is a FULL review surface (`.agents/repository.md`); constitution gates apply.

## Validation
- Add a unit test in `test_reactive_core.py`: with a `ReactiveCoreHolder` computed dict whose element reads a leaf input, compute, remove the key, trigger pruning, then assert the popped sub-slot is not in the leaf node's `dependents`.
- Add a unit or integration test: after `self_delete`, no slot in `instance_slot_registry(o)` of any surviving object `o` lists a slot of the deleted object among its `dependents`.
- `PYTHONPATH=./ /Users/vinville/Library/Caches/pypoetry/virtualenvs/efootprint-6BqlWvzT-py3.13/bin/python -m pytest tests/abstract_modeling_classes tests/integration_tests` then the full `MPLBACKEND=Agg` suite. Check first that this venv still exists.

## Out of scope
Changing children derivation (Task 2). Pruning stale keys more eagerly than today.

## Unverified
A stale sub-slot whose key-set slot was never visited by an invalidation wave stays registered with its edges. Settling it: in the Task 1 tests, check whether any integration post-reset scenario leaves such a slot. Expected outcome: none, because a sub-slot only acquires edges once its key set has been materialized.
