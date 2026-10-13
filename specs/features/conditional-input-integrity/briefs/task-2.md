# Task 2 — Reject incompatible library changes atomically
Written 2026-10-13 against e-footprint `6cb80af3`.
Plan: [library edit](../plan.html#library-edit), [constructor validation](../plan.html#read-controlling-input), [relationship edit](../plan.html#relationship-edit). Task: [2](../tasks.md#task-2).
Status: under review.

## Start here
- `ModelingUpdate.__init__()`, `parse_changes_list()`, `apply_changes()`, `pull_eagerly()` and `rollback()` — `efootprint/abstract_modeling_classes/modeling_update.py`; current transaction and eager guard boundary.
- `ModelingObject.check_belonging_to_authorized_values()`, `_set_input_passively()` and `__setattr__()` — `efootprint/abstract_modeling_classes/modeling_object.py`; old local reverse checks and passive/live split.
- `ModelingObject.from_json_dict()` — same module; hydration deliberately passes `check_input_validity=False` for restored relationships.
- `TestCheckBelongingToAuthorizedValues` — `tests/abstract_modeling_classes/test_modeling_object.py`; existing direct-call tests use instance-level synthetic declarations and must be updated to the class-level rule contract.

## Change along the code path
After `parse_changes_list()` normalizes and removes no-ops, capture each old attached value's `(owner, attribute)` before applying. Following complete apply/invalidation, check changed and Task 1 `dependent_inputs()` addresses exactly once against the final graph, then call the existing `pull_eagerly()`. Keep this inside the existing try/rollback boundary; retain `collect_newly_linked_mod_objs()` guard behavior. A controller-only incompatible edit rejects, while both orders of a complete batch accept.

Simplify `check_belonging_to_authorized_values(name, proposed_changes=None)` to validate one input via Task 1 `resolve_input_path()` and `allowed_values()`, then remove `attributes_with_depending_values()`. In `_set_input_passively()`, stage the new `(self, name)` value, validate it and already assigned affected dependents against that proposed state before attaching. Skip unassigned dependent fields, but do not silently accept a dependent whose required controller path is absent. Leave hydration's explicit bypass intact.

## Earlier tasks
Task 1 supplies `dependent_inputs()`, `resolve_input_path()` and `allowed_values()`; its index finds cross-owner dependents without calculation history. Do not rebuild a second reverse map here.

## Reuse
Keep `parse_changes_list()` for type/unit checks, entangled additions and no-op handling; keep eager guard pulls and existing rollback. `input_values_match()` remains the choice comparison. The new error should identify dependent owner/input/value, controller owner/input/value and permitted choices.

## Invariants and traps
Capture addresses while old values still know their containers. A rejected relationship change restores old backlinks, and later edits follow accepted current links only. Constructor checks see proposed values without attaching them. Cold, calculated and loaded objects must agree; ordinary type/unit/positivity checks stay at their current boundary. Conditional queries must not pull unrelated computed getters.

## Validation
Extend `tests/abstract_modeling_classes/test_modeling_object.py` with constructor order, controller-only and both batch orders, shared job fan-out, direct and intermediate relationship replacement, rollback and restored eager results; update direct calls to the simplified validator. Add real video coverage in `tests/builders/external_apis/ecologits/test_ecologits_video_external_api.py` and loaded/cached checks in `tests/api_utils_tests/test_json_to_system.py`. From e-footprint: `MPLBACKEND=Agg poetry run pytest tests/abstract_modeling_classes/test_modeling_object.py tests/abstract_modeling_classes/test_conditional_inputs.py tests/builders/external_apis/ecologits/test_ecologits_video_external_api.py tests/api_utils_tests/test_json_to_system.py`.

## Out of scope
Automatic repair belongs to the interface in Task 4. Historical invalid files are addressed narrowly in Task 6; generic import validation is excluded.

## Unverified
None: the two lifecycle entry points and rollback path were verified. Focused regressions must establish preservation of entangled and newly linked behavior after the edit.
