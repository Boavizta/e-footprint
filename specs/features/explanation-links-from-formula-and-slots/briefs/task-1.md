# Task 1 — Engine keeps dependency links current
Written 2026-10-20 against e-footprint 58966eb1 (feature specs at bfdc44f6).
Plan: [1.3, engine invariant](../plan.html#children) (PLAN-UPDATE-02, accepted), [PLAN-UPDATE-04](../plan.html#plan-update-04) (purpose query removal, accepted). Task: [tasks.md](../tasks.md#task-1--engine-keeps-dependency-links-current).
Status: approved 2026-10-20.

## Start here
- `invalidate` — `efootprint/abstract_modeling_classes/reactive_core/graph.py` — the deletion wave; voids slots and keeps their links today.
- `ReactiveSlot._compute` — same file — installs `frame.calculus_reads` / `frame.structural_reads` only after the getter returns; on observer rejection restores `previous_calculus_dependencies` / `previous_structural_dependencies`.
- `ReactiveSlot.replace_dependencies` — same file — the only writer of links; called with no arguments it unlinks the slot from every dependency.
- `computed_dict.discard_stale_keys` — `reactive_core/computed_slots.py` — pops stale sub-slots (`stale_slot = registry.pop(...)`).
- `ModelingObject.self_delete` — `efootprint/abstract_modeling_classes/modeling_object.py` — the `for slot in list(instance_slot_registry(self).values()): slot._drop_value()` loop.
- `computation_slots_for_purpose` and `ComputationPurpose` — `reactive_core/computed_slots.py` — removed by this task, with every `purposes=` declaration.

## Change along the code path
Follow the plan's snippet in 1.3.
1. `invalidate`: after `work.extend(slot._dependents)`, call `slot.replace_dependencies()`. The extend must come first, because the cut removes the slot from its dependencies' `_dependents`, not from its own.
2. `_compute`: move `self.replace_dependencies(frame.calculus_reads, frame.structural_reads)` into the `finally`, so it runs whether the getter returns or raises. In the observer `except`, keep `_drop_value()` and `raise`; delete the restore and the `previous_*` bookkeeping.
3. `discard_stale_keys`: `stale_slot.replace_dependencies()` after the pop. `self_delete`: `slot.replace_dependencies()` after `slot._drop_value()`.
4. Docstrings and pages: the `ReactiveSlot` docstring ("A failed computation keeps the previous edges — over-invalidation is safe…"), the `observe_computations` docstring ("the slot's previous dependency edges are restored"), `recomputation/computed-surfaces.html` ("keeps previous edges after failure as a safe over-approximation"), and `recomputation/lifecycle.html` (observer boundary paragraph; "Previous edges survive a failed getter" invariant). State the invariant once: a slot's links are the reads of its current state (cached value, last failed or rejected attempt, value installed at load, or an evicted transient structure's last value); a voided, removed or deleted slot has none.

5. Purpose query removal (PLAN-UPDATE-04, the callout lists every location): delete `ComputationPurpose`, `computation_slots_for_purpose`, the `purposes` parameter and attribute of `computed_attribute.__init__` and `computed_dict.__init__` with the docstring sentence, and both exports in `reactive_core/__init__.py`. Drop `purposes={ComputationPurpose.FOOTPRINT}` and the now-unused import in the eight model files (`grep -rln ComputationPurpose efootprint`). Keep `serialize=True`, which shares those decorators. Delete `ReactiveCorePurposeHolder` and the three purpose tests in `test_reactive_core.py` (`test_purpose_query_derives_membership_from_materialized_output_ancestors`, `test_purpose_query_keeps_invalidated_materialized_topology`, `test_declared_physical_footprint_outputs_are_tagged`). Remove the `#computation-purpose` section of `lifecycle.html`, the purposes paragraph of `computed-surfaces.html`, the purposes row of `blocks/computed-attribute.html` and the purposes sentence of the slot-flags bullet in `specs/conventions.md`.
6. `CHANGELOG.md`: add a `## [Unreleased]` heading above V26.0.1 with a Changed entry for the link invariant and a Removed entry for `computation_slots_for_purpose`, `ComputationPurpose` and the `purposes` slot parameter. Tasks 2 and 3 extend it.

Expected result: after any edit, every slot the wave visited has empty dependency sets until it recomputes; after `self_delete` or pruning, no surviving slot lists a removed slot among its `dependents`.

## Earlier tasks
None.

## Reuse
- `replace_dependencies()` keeps the reverse index consistent in both directions. Never edit `_dependents` by hand.
- Fixtures: `self.a` / `self.values` / bare `ReactiveSlot` getters in `test_reactive_core.py` (see `test_failed_compute_clears_marker_so_next_wave_reaches_fallback_caching_dependent`), and the `ReactiveCore*` model classes at the top of that file. `ReactiveCoreObserverGuard` covers observer rejection inside a guard.
- `ServerBase.nb_of_instances` / `fixed_nb_of_instances_validation` for the branch-switch and rollback case (`ServerTypes.on_premise()` vs `ServerTypes.autoscaling()`; the capacity guard raises `InsufficientCapacityError`).

## Invariants and traps
- `computed_structure.evict_cached_value` drops a value without invalidating. It must keep its links, so do not move the cut into `_drop_value`.
- Loaded void intermediates keep the links `rebuild_dependency_graph` installed until a wave reaches them; the same wave voids the stored values above them.
- Wave pruning stays sound: a marked slot's dependents are marked in the same wave before its links are cut, and the next compute clears the marker on success or failure.
- `CircularDependencyError` is raised before the frame is pushed; nothing to install there.
- `reactive_core` is a FULL review surface (`.agents/repository.md`).

## Validation
- `test_failed_recompute_keeps_previous_edges_and_leaves_slot_void_and_unmarked`: its getter raises before reading `a`, so assert empty dependencies and `a.dependents` without the slot. Rename the test to match.
- The three purpose tests are deleted, not rewritten. `grep -rn "ComputationPurpose\|computation_slots_for_purpose\|purposes" efootprint tests specs/architecture specs/conventions.md` returns nothing except unrelated prose.
- New: invalidation leaves voided slots unlinked and recompute relinks them. A getter that reads X and then raises is linked to X. An observer-rejected slot is void and linked to the rejected attempt's reads. The fallback test passes unchanged. Branch switch plus capacity-guard failure plus rollback leaves the guard and `nb_of_instances` with on-premise links after recompute (next to `test_observer_failure_during_guard_recomputation_preserves_transactional_rollback`). A pruned stale sub-slot and a deleted object's slots are absent from surviving `dependents`.
- Replay check (prototype was `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full/d9e42849-33d3-4a0d-961d-63fea7d042be/scratchpad/deleted_dependents_patched.py`, may be gone): after `run_test_add_usage_pattern`'s rollback and `self_delete`, the carbon intensity's explainable calculus dependents are all live and pull without error.
- `PYTHONPATH=./ <venv>/bin/python -m pytest tests/abstract_modeling_classes tests/integration_tests` (venv: `/Users/vinville/Library/Caches/pypoetry/virtualenvs/efootprint-6BqlWvzT-py3.13`, check it exists), then the full suite with `MPLBACKEND=Agg`, then `tests/performance_tests`. Measured during preparation: +1 ms on a 36 ms edit-and-recompute.

## Out of scope
Children derivation and anything in `explainable_object_base_class.py` (Task 2). The serializer's dead-slot filter in `calculation_graph_section` stays as it is.

## Unverified
A stale sub-slot whose key-set slot no invalidation wave has visited stays registered, though under the invariant without links once voided. Check that the integration post-reset scenarios leave no such slot linked.
