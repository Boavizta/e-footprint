# Prompt: Populate `contextual_modeling_obj_containers` for Structural Input Dict Relationships

## Goal

Fix the modeling layer so that **structural dict relationships passed through `__init__`**
populate `contextual_modeling_obj_containers`, just like structural list and direct
modeling-object relationships already do.

This is needed because `contextual_modeling_obj_containers` is the semantically correct
source of parent/context information, and downstream code relies on it to recover the
structural parent of an updated object.

Today, dict-backed structural parentage is only partially visible through
`explainable_object_dicts_containers`, which is too broad:

- it tracks generic dict-key membership
- it does **not** discriminate structural input dicts from calculated/support dicts
- it is therefore the wrong abstraction for UI mirroring / structural parent recovery

## Why This Matters

This fix is needed for two reasons:

1. **`ModelingUpdate` / structural parent recovery**
   The updated object should be able to recover its structural parent context through
   `contextual_modeling_obj_containers`, even when that parent relationship comes from
   an `ExplainableObjectDict` used as an `__init__` parameter.

2. **Future interface work**
   The interface will soon need generic mirrored-card resolution for grouped edge
   devices/components. That work should consume `contextual_modeling_obj_containers`,
   not `explainable_object_dicts_containers`.

So the missing semantics should be fixed in `e-footprint`, not worked around in the UI.

## Desired Invariant

After this change:

- if a `ModelingObject` is structurally contained by another object through an
  `__init__` parameter, that relationship must appear in
  `contextual_modeling_obj_containers`
- this must hold whether the init parameter is:
  - a direct `ModelingObject`
  - a list of `ModelingObject`s
  - an `ExplainableObjectDict` whose **keys** are structural `ModelingObject`s
- calculated/support dicts must **not** pollute `contextual_modeling_obj_containers`
- `explainable_object_dicts_containers` should remain the generic bookkeeping
  mechanism for dict-key membership, but it should not be the only source of
  structural parentage for init dicts

## Problem Restated More Precisely

The "dict-as-init-parameter" pattern was introduced after the original
`contextual_modeling_obj_containers` concept.

As a result:

- direct and list relationships already update contextual containers
- init dict relationships update `explainable_object_dicts_containers`
- but structural dict key membership does **not** currently show up in
  `contextual_modeling_obj_containers`

That is semantically inconsistent.

## What To Implement

### 1. Identify structural input dicts

Use the owning modeling object's `__init__` signature to determine whether a dict
attribute is a true input relationship.

The structural case we care about is:

- the attribute name is an `__init__` parameter
- the current attribute value is an `ExplainableObjectDict`
- the dict keys are `ModelingObject`s representing structural children / members

This should **not** apply to calculated `ExplainableObjectDict`s such as impact
repartition dicts or other support/calculated containers.

### 2. Populate `contextual_modeling_obj_containers` for keys of structural input dicts

When a structural input dict is attached to a modeling object, its keys should gain
the same kind of contextual parent reference that list/direct child relationships get:

- modeling object container = the owning object
- attribute name = the dict attribute name in the owner

This contextual relationship should be added/removed/updated consistently when:

- the object is initialized
- a dict is attached via attribute assignment
- a dict entry is inserted
- a dict entry is removed
- a whole dict is replaced through `ModelingUpdate`
- a system is loaded from JSON

### 3. Keep calculated/support dicts out of contextual containers

Do **not** indiscriminately mirror all `ExplainableObjectDict` key memberships into
`contextual_modeling_obj_containers`.

The contextual relationship must only exist for dict attributes that are structural
init parameters.

### 4. Preserve existing dict membership bookkeeping

Do not break the current semantics of `explainable_object_dicts_containers`.

It should remain valid and bidirectionally consistent for generic dict membership.
We are adding the missing structural/contextual layer, not replacing the generic one.

## Likely Files To Inspect / Modify

- `efootprint/abstract_modeling_classes/modeling_object.py`
- `efootprint/abstract_modeling_classes/explainable_object_dict.py`
- `efootprint/abstract_modeling_classes/contextual_modeling_object_attribute.py`
- `efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py`
- `efootprint/abstract_modeling_classes/modeling_update.py`
- `efootprint/api_utils/json_to_system.py`

You may find that the cleanest design is to add helper methods in `ModelingObject`
or `ExplainableObjectDict` to decide whether a dict attribute is a structural input
dict and to synchronize contextual container references centrally.

## Design Guidance

- Prefer a **single coherent modeling-layer rule** over a local patch in one code path.
- The key distinction is not "all dicts" versus "no dicts"; it is:
  - structural init dicts
  - non-structural calculated/support dicts
- Be careful with replacement flows:
  `replace_in_mod_obj_container_without_recomputation`, `ModelingUpdate.apply_changes`,
  and JSON deferred dict attachment all need consistent behavior.
- Avoid duplicating contextual container entries for the same `(parent, attr_name)` pair.
- Be careful not to introduce re-entrant update loops when dict replacement/setitem
  synchronizes contextual containers.

## Edge Cases To Think Through

1. Replacing one structural input dict by another:
   old keys should lose the contextual parent if they are no longer present; new keys
   should gain it.

2. A key present in several structural input dict containers:
   it should legitimately accumulate several contextual parent references.

3. Replacing a calculated/support dict:
   should continue to update `explainable_object_dicts_containers` as today, but must
   not add contextual parents.

4. Loading from JSON:
   the reconstructed object graph must end up with correct contextual container state
   for structural init dict relationships.

5. `ModelingUpdate` flows:
   after updating a structural input dict, parent discovery through
   `contextual_modeling_obj_containers` should work immediately on the updated keys.

## Tests To Add

Add focused tests. Prefer compact fixtures and `create_mod_obj_mock` where mocking is enough.

### Unit tests

Likely under `tests/abstract_modeling_classes/`.

1. **Structural input dict populates contextual containers**
   Create a small modeling object class with an `ExplainableObjectDict` init parameter.
   Verify that each key gains a contextual container pointing to the owner and attr name.

2. **Calculated/support dict does not populate contextual containers**
   Use a calculated `ExplainableObjectDict` attribute and verify its keys do not gain
   structural contextual parents from that dict.

3. **Replacing structural dict updates contextual containers**
   Replace one structural dict with another and verify old/new keys are updated correctly.

4. **Dict entry insertion/removal keeps contextual containers in sync**
   For a structural input dict, verify `__setitem__` / `__delitem__` maintain contextual
   parent references correctly.

5. **`ModelingUpdate` replacement preserves parent recovery**
   After a structural dict update through `ModelingUpdate`, verify the updated key can
   recover the owner through `contextual_modeling_obj_containers`.

### Integration test

Add one realistic integration test using an existing structural dict pattern such as
`EdgeDeviceGroup.sub_group_counts` / `edge_device_counts`.

Verify that:

- grouped device / subgroup keys have the expected contextual parent relationship
- after a dict update, that relationship remains correct
- calculated dicts still do not masquerade as structural contextual parents

## Acceptance Criteria

1. Structural init dict relationships populate `contextual_modeling_obj_containers`.
2. Calculated/support dicts do not.
3. Replacing/updating structural dicts keeps contextual parent references correct.
4. JSON loading reconstructs the same contextual parentage.
5. `ModelingUpdate` can rely on `contextual_modeling_obj_containers` for objects
   contained through structural input dicts.
6. Existing `explainable_object_dicts_containers` behavior remains valid.

## Deliverable

Please implement the fix, add the tests, run the relevant test files, and report:

- the modeling-layer design you chose
- the files changed
- the tests run
- any residual ambiguity or follow-up work you think remains
