# Retire `trigger_modeling_updates` — Tasks

**Status:** Tasks — under review.
**Scope:** Targeted behavior-preserving framework refactor; intentionally starts at `tasks.md` without separate spec or plan artifacts.

The public mutable `trigger_modeling_updates` flag currently conflates object lifecycle, input-container
activation, and temporary re-entry suppression. Pull-based computation no longer needs a caller-controlled
switch for eager work, but the framework must preserve the real boundary: construction and hydration write
passively, while mutations of a live model are transactional, invalidate reactive slots, run guards, and roll
back on failure.

## Task 1 — Give relationship containers explicit passive mutation primitives

**Status:** Done

**Goal:** Stop suppressing recursive `ModelingUpdate` calls by temporarily toggling container flags. Make the
distinction between public/live mutation and framework-owned passive storage explicit, while leaving the
existing object activation flag in place until Task 2.

**Implementation notes:**
- Add complete private passive mutation primitives to `ListLinkedToModelingObj`, matching the existing
  `_set_entry_passively` / `_drop_entry_passively` direction in `ExplainableObjectDict`. They must perform all
  forward-link, reverse-link, container, ordering, and structural-node bookkeeping, but must never create a
  `ModelingUpdate`.
- Route `ModelingUpdate.apply_changes()` and `rollback()`, deserialization population, computed-dict slot
  attachment/removal, and `ObjectLinkedToModelingObjBase.replace_in_mod_obj_container_without_recomputation()`
  through explicit passive primitives. Remove every save/disable/restore dance around
  `container.trigger_modeling_updates`.
- Keep public list/dict operations behaviorally unchanged in this task: mutations of active input containers
  still create exactly one `ModelingUpdate`; construction of unattached containers and computed-facade writes
  remain passive.
- Preserve concrete container types, especially `WeightedExplainableObjectDict`, through replacement,
  rollback, copying, and JSON hydration.
- Do not add compatibility wrappers for obsolete internal mutation paths.

**Files touched:**
- `efootprint/abstract_modeling_classes/list_linked_to_modeling_obj.py`
- `efootprint/abstract_modeling_classes/explainable_object_dict.py`
- `efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py`
- `efootprint/abstract_modeling_classes/modeling_update.py`
- `efootprint/api_utils/json_to_system.py`
- Related framework tests and `tests/utils.py` only if its pinning helpers need to use the new passive API

**Tests added/changed:**
- `tests/abstract_modeling_classes/test_list_linked_to_modeling_obj.py`
- `tests/abstract_modeling_classes/test_explainable_object_dict.py`
- `tests/abstract_modeling_classes/test_modeling_update.py`
- Integration coverage for relationship replacement, rollback, deletion, dict ordering, and weighted dicts

**Acceptance:**
- Each public list/dict mutation launches at most one `ModelingUpdate`; passive framework mutation launches none.
- Apply and rollback cannot re-enter `ModelingUpdate`.
- Container/reverse-link integrity and reactive invalidation are unchanged.
- Input and computed dictionaries remain distinguishable through computed-facade binding, not mutation-mode
  guesswork.
- No production code temporarily changes a `trigger_modeling_updates` value to suppress re-entry.
- Full tests pass after this task; production behavior and JSON schema are unchanged.

**Depends on:** none.

---

## Task 2 — Replace the public flag with a private object-lifecycle boundary

**Status:** Done

**Goal:** Remove `trigger_modeling_updates` from modeling objects and relationship containers. Framework-owned
construction/hydration writes remain passive; once an object graph is live, ordinary assignments and container
mutations always use `ModelingUpdate`.

**Implementation notes:**
- Make `AfterInitMeta` own the construction lifecycle: the complete `__init__` plus subclass `after_init()` phase
  is passive, then the instance becomes live exactly once. Builder `after_init()` methods may create defaults or
  replace constructor inputs before that transition without manually enabling/disabling updates.
- Give JSON hydration an explicit passive path. Objects and relationship containers become live only after all
  objects, deferred input dictionaries, stored values, ancestry links, and serialized dependency edges have
  been rebuilt. Loading must never compute or launch a `ModelingUpdate`.
- Use a private lifecycle mechanism or explicit passive setter—not a public caller-controlled boolean. The live
  transition must be idempotent and framework-owned. Do not merely rename the flag to `updates_enabled`.
- Once live, `ModelingObject.__setattr__` always routes input replacement through `ModelingUpdate`. Public
  mutation of an attached input list/dict does the same; unattached containers used during construction remain
  passive. Computed dict facades continue to route through their descriptor binding.
- Remove `enable_modeling_updates`, `set_trigger_modeling_updates_to_true`, every production/test assignment to
  `trigger_modeling_updates`, and container flag propagation in `EdgeDeviceGroup` and elsewhere.
- Replace tests that disable updates to arrange computed-getter inputs with `tests.utils` passive pin/attach
  helpers. Tests must exercise the production interface rather than retaining a general update-bypass switch.
- Preserve lazy outputs: a successful live mutation invalidates ordinary computed slots but does not pull them;
  guards retain current eager validation and rollback semantics.
- Update the architecture pages and conventions to describe construction/hydration versus live transactional
  mutation. Add an Unreleased changelog entry. No JSON migration or interface adaptation should be necessary.

**Files touched:**
- `efootprint/abstract_modeling_classes/modeling_object.py`
- `efootprint/abstract_modeling_classes/list_linked_to_modeling_obj.py`
- `efootprint/abstract_modeling_classes/explainable_object_dict.py`
- `efootprint/api_utils/json_to_system.py`
- `efootprint/core/hardware/edge/edge_device_group.py`
- Any builder `after_init()` methods whose sequencing becomes simpler
- `tests/utils.py` and tests currently assigning `trigger_modeling_updates`
- `specs/architecture/layers-and-modeling.html`
- `specs/architecture/relationships.html`
- `specs/architecture/recomputation/lifecycle.html`
- `specs/conventions.md`
- `CHANGELOG.md`

**Tests added/changed:**
- Framework lifecycle tests proving constructor and subclass `after_init()` writes are passive and a later write
  is transactional.
- JSON tests proving hydration performs zero computation/update transactions and the returned graph is live.
- Update/guard tests proving invalid live mutations roll back while ordinary invalidated outputs remain void.
- List/dict tests covering every public mutator before attachment and after attachment to a live owner.
- Existing randomized mutation parity, serialization-contract, relationship-integrity, and integration suites.

**Acceptance:**
- `rg "trigger_modeling_updates" efootprint tests specs` returns no live references.
- There is no public general-purpose switch that lets callers bypass invalidation or validation on a live model.
- Construction, builder default creation, and JSON hydration launch no `ModelingUpdate` and perform no unintended
  computation.
- Every ordinary mutation of a live object/input container invalidates the correct dependency cone, eagerly
  checks guards, and rolls back on failure; ordinary outputs stay lazy.
- Apply, rollback, computed-facade attachment, and deserialization use explicit passive framework APIs without
  recursive updates.
- Same-version cached JSON round-trips and inputs-only rebuilds preserve their existing behavior and schema.
- Full pytest and `mkdocs build --strict` pass.

**Depends on:** Task 1.

---

## Ordering rationale

Task 1 first removes temporary flag toggling from the most re-entry-sensitive code while preserving the existing
activation policy, giving reviewers a working behavioral pause point and explicit passive primitives to audit.
Task 2 can then remove the flag itself without simultaneously inventing container storage operations. Tests and
documentation move with the behavior they protect; a separate cleanup task would leave no independently useful
pause point.
