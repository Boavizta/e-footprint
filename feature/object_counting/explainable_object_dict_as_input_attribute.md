# ExplainableObjectDict as Input Attribute — Detailed Design

This document covers the infrastructure changes needed for `ExplainableObjectDict` to work as
an `__init__` parameter (not just a calculated attribute) on `EdgeDeviceGroup`, with full support
for live recomputation and serialization round-trips.

---

## Current State

- `ExplainableObjectDict` is **only** used as calculated attributes (initialized empty, populated
  by `update_*` methods).
- It has no `trigger_modeling_updates` flag — mutations never trigger `ModelingUpdate`.
- `ModelingUpdate.compute_mod_objs_computation_chain` handles `ContextualModelingObjectAttribute`
  and `ListLinkedToModelingObj`, but **not dicts**.
- `WeightedModelingObjectsDict` attempted dict-level ModelingUpdate triggering but is **unused**
  and its approach wouldn't work with the current `parse_changes_list` (plain dict new_values
  fail the `ObjectLinkedToModelingObjBase` assertion).

---

## 1. ExplainableObjectDict: Add `trigger_modeling_updates`

**File:** `efootprint/abstract_modeling_classes/explainable_object_dict.py`

Add a flag (default `False`) so that calculated-attribute dicts stay passive while
init-parameter dicts trigger recomputation after `after_init`.

### `__init__` change

```python
def __init__(self, input_dict=None):
    super().__init__()
    self.trigger_modeling_updates = False
    if input_dict is not None:
        for key, value in input_dict.items():
            self[key] = value
```

### `__setitem__` change

Two cases when `trigger_modeling_updates=True`:

1. **Existing key (value update):** The old ExplainableQuantity's `attr_updates_chain` already
   traces forward through the computation graph to find downstream dependents. Fire:
   `ModelingUpdate([[self[key], new_value]])`.

2. **New key (structural change):** A new ModelingObject key adds a dependency edge. Fire:
   `ModelingUpdate([[self, ExplainableObjectDict({**self, key: value})]])` — full dict
   replacement so `compute_mod_objs_computation_chain_from_old_and_new_dicts` can diff keys.

```python
def __setitem__(self, key, value: ExplainableObject):
    if not isinstance(value, ExplainableObject) and not isinstance(value, EmptyExplainableObject):
        raise ValueError(...)

    if self.trigger_modeling_updates:
        if key in self:
            # Value update on existing key
            ModelingUpdate([[self[key], value]])
        else:
            # Structural change: new key
            new_dict = ExplainableObjectDict()
            for k, v in self.items():
                new_dict[k] = v
            new_dict[key] = value
            new_dict.trigger_modeling_updates = self.trigger_modeling_updates
            ModelingUpdate([[self, new_dict]])
        return

    # Original passive logic (unchanged)
    if key in self and self.modeling_obj_container is not None:
        self[key].set_modeling_obj_container(None, None)
    super().__setitem__(key, value)
    if self.modeling_obj_container is not None:
        value.set_modeling_obj_container(
            new_modeling_obj_container=self.modeling_obj_container,
            attr_name=self.attr_name_in_mod_obj_container)
    self._add_self_to_key_containers(key)
```

### `__delitem__` change

Structural change: full dict replacement.

```python
def __delitem__(self, key):
    if self.trigger_modeling_updates:
        new_dict = ExplainableObjectDict()
        for k, v in self.items():
            if k != key:
                new_dict[k] = v
        new_dict.trigger_modeling_updates = self.trigger_modeling_updates
        ModelingUpdate([[self, new_dict]])
        return

    # Original passive logic (unchanged)
    if self.modeling_obj_container is not None:
        self[key].set_modeling_obj_container(None, None)
    super().__delitem__(key)
    self._remove_self_from_key_containers(key)
```

### `pop`, `clear`, `update`

Follow the same pattern: delegate to `__delitem__`/`__setitem__` when
`trigger_modeling_updates=True`, which now handle triggering.

### `replace_in_mod_obj_container_without_recomputation`: Guard Against Re-entry

**File:** `efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py`

When `ModelingUpdate.apply_changes()` replaces a value inside an ExplainableObjectDict via
`replace_in_mod_obj_container_without_recomputation`, it calls
`dict_container[self.key_in_dict] = new_value` (line 183). If `trigger_modeling_updates=True`
on the dict, this re-enters `__setitem__` and triggers another `ModelingUpdate` → infinite loop.

The fix mirrors the existing list guard (lines 188-192): temporarily disable
`trigger_modeling_updates` on the dict container:

```python
if dict_container is not None:
    if self.key_in_dict not in dict_container:
        raise KeyError(...)
    initial_trigger = dict_container.trigger_modeling_updates
    dict_container.trigger_modeling_updates = False
    dict_container[self.key_in_dict] = new_value
    dict_container.trigger_modeling_updates = initial_trigger
```

This is needed regardless of whether the dict is an input or calculated attribute — it's
a general safety guard for any ExplainableObjectDict with `trigger_modeling_updates=True`.

---

## 2. ModelingUpdate: Dict Handling

**File:** `efootprint/abstract_modeling_classes/modeling_update.py`

### `parse_changes_list` (line ~125)

Add dict → ExplainableObjectDict conversion, like list → ListLinkedToModelingObj:

```python
if isinstance(new_value, list):
    from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
    self.changes_list[index][1] = ListLinkedToModelingObj(new_value)
if isinstance(new_value, dict) and not isinstance(new_value, ExplainableObjectDict):
    self.changes_list[index][1] = ExplainableObjectDict(new_value)
```

### `compute_mod_objs_computation_chain` (line ~153)

Add a third branch:

```python
def compute_mod_objs_computation_chain(self):
    from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
    mod_objs_computation_chain = []
    for old_value, new_value in self.changes_list:
        if isinstance(old_value, ContextualModelingObjectAttribute):
            mod_objs_computation_chain += (
                old_value.modeling_obj_container
                    .compute_mod_objs_computation_chain_from_old_and_new_modeling_objs(
                        old_value, new_value, optimize_chain=False))
        elif isinstance(old_value, ListLinkedToModelingObj):
            mod_objs_computation_chain += (
                old_value.modeling_obj_container
                    .compute_mod_objs_computation_chain_from_old_and_new_lists(
                        old_value, new_value, optimize_chain=False))
        elif isinstance(old_value, ExplainableObjectDict):
            mod_objs_computation_chain += (
                old_value.modeling_obj_container
                    .compute_mod_objs_computation_chain_from_old_and_new_dicts(
                        old_value, new_value, optimize_chain=False))
    ...
```

---

## 3. ModelingObject: Factor List/Dict Computation Chain Logic

**File:** `efootprint/abstract_modeling_classes/modeling_object.py`

`compute_mod_objs_computation_chain_from_old_and_new_lists` (line 566-592) and the new dict
variant share identical structure. Extract the common logic into a private method, then have
both delegate to it:

```python
def _compute_mod_objs_computation_chain_from_old_and_new_collection(
        self, old_value, input_value, old_mod_objs, new_mod_objs,
        optimize_chain=True) -> List[Type["ModelingObject"]]:
    removed_objs = [obj for obj in old_mod_objs if obj not in new_mod_objs]
    added_objs = [obj for obj in new_mod_objs if obj not in old_mod_objs]

    mod_objs_computation_chain = []
    for obj in removed_objs + added_objs:
        if self not in obj.modeling_objects_whose_attributes_depend_directly_on_me:
            mod_objs_computation_chain += obj.mod_objs_computation_chain

    # Compute self.mod_objs_computation_chain for both old and new states, because
    # dynamic properties on self may discover different objects depending on the
    # collection contents. Old state catches objects being removed, new state
    # catches objects being added.
    mod_objs_computation_chain += self.mod_objs_computation_chain
    attr_name = old_value.attr_name_in_mod_obj_container
    self.__dict__[attr_name] = input_value
    mod_objs_computation_chain += self.mod_objs_computation_chain
    self.__dict__[attr_name] = old_value

    if optimize_chain:
        return optimize_mod_objs_computation_chain(mod_objs_computation_chain)
    return mod_objs_computation_chain

def compute_mod_objs_computation_chain_from_old_and_new_lists(
        self, old_value, input_value, optimize_chain=True):
    return self._compute_mod_objs_computation_chain_from_old_and_new_collection(
        old_value, input_value,
        old_mod_objs=list(old_value), new_mod_objs=list(input_value),
        optimize_chain=optimize_chain)

def compute_mod_objs_computation_chain_from_old_and_new_dicts(
        self, old_value, input_value, optimize_chain=True):
    old_mod_obj_keys = [k for k in old_value if isinstance(k, ModelingObject)]
    new_mod_obj_keys = [k for k in input_value if isinstance(k, ModelingObject)]
    return self._compute_mod_objs_computation_chain_from_old_and_new_collection(
        old_value, input_value,
        old_mod_objs=old_mod_obj_keys, new_mod_objs=new_mod_obj_keys,
        optimize_chain=optimize_chain)
```

The only difference: lists use elements directly, dicts extract ModelingObject keys.

---

## 4. ModelingObject.after_init: Enable Dict Triggers

**File:** `efootprint/abstract_modeling_classes/modeling_object.py`

After `trigger_modeling_updates = True` is set on the ModelingObject, also enable it on
ExplainableObjectDicts that are NOT calculated attributes:

```python
def after_init(self):
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
    self.trigger_modeling_updates = True
    for attr_name, attr_value in self.__dict__.items():
        if (isinstance(attr_value, ExplainableObjectDict)
                and attr_name not in self.calculated_attributes):
            attr_value.trigger_modeling_updates = True
```

This is generic — any future ModelingObject with an input ExplainableObjectDict will
automatically get live recomputation.

---

## 5. Init Signature: Avoid Self-Referential Type

### Problem

`compute_classes_generation_order` (json_to_system.py:16-61) does topological sort of classes
by `__init__` parameter type annotations. If EdgeDeviceGroup's init has
`sub_groups_with_counts: List[Tuple[EdgeDeviceGroup, ExplainableQuantity]]`, it creates a
self-dependency → infinite loop in the topological sort.

### Solution

Take `ExplainableObjectDict` directly:

```python
class EdgeDeviceGroup(ModelingObject):
    def __init__(self, name: str,
                 sub_group_counts: ExplainableObjectDict = None,
                 edge_device_counts: ExplainableObjectDict = None):
        super().__init__(name)
        if sub_group_counts is None:
            sub_group_counts = ExplainableObjectDict()
        if edge_device_counts is None:
            edge_device_counts = ExplainableObjectDict()
        self.sub_group_counts = sub_group_counts
        self.edge_device_counts = edge_device_counts
        self.effective_nb_of_units_within_root = EmptyExplainableObject()
```

`ExplainableObjectDict` is not a `ModelingObject` → invisible to the topological sort.

For deserialization ordering, add EdgeDevice to
`classes_outside_init_params_needed_for_generating_from_json` so that devices exist before
groups are populated:

```python
classes_outside_init_params_needed_for_generating_from_json = [EdgeDevice]
```

---

## 6. Serialization

### `system_to_json.py`: Object Discovery

**File:** `efootprint/api_utils/system_to_json.py`

In `recursively_write_json_dict`, after handling ModelingObject attributes and lists, walk
ExplainableObjectDict keys:

```python
elif isinstance(value, ExplainableObjectDict):
    for key in value:
        if isinstance(key, ModelingObject):
            recursively_write_json_dict(output_dict, key, save_calculated_attributes)
```

Also walk `explainable_object_dicts_containers` on each object to discover parent groups:

```python
for dict_container in mod_obj.explainable_object_dicts_containers:
    container = dict_container.modeling_obj_container
    if container is not None and isinstance(container, ModelingObject):
        recursively_write_json_dict(output_dict, container, save_calculated_attributes)
```

### `to_json` on ModelingObject

Input dicts should always be serialized (not gated by `save_calculated_attributes`). Need to
verify the existing `to_json` implementation handles this — input dicts are NOT in
`calculated_attributes`, so they shouldn't be filtered out.

---

## 7. Deserialization: Timing Pitfall

### Problem

In `json_to_system` (json_to_system.py:95-141):

1. Objects created via `from_json_dict` (uses `__new__`, skips `__init__`)
2. `after_init()` called per object (line 119) → sets `trigger_modeling_updates = True`
3. **Later**, deferred dicts populated (lines 126-132) via `__setattr__`

For EdgeDeviceGroup: step 2 enables `trigger_modeling_updates`. Step 3 calls
`__setattr__("sub_group_counts", dict, check_input_validity=False)`. Since it's not a
calculated attribute and `trigger_modeling_updates = True`, this enters the `ModelingUpdate`
branch — but `current_attr` is `None` → crash.

### Solution

Initialize input ExplainableObjectDicts to empty during `from_json_dict`, so they exist
before `after_init`. In `from_json_dict` (modeling_object.py:~187), after the calculated
attribute initialization:

```python
# Initialize input ExplainableObjectDicts that were deferred
for (obj, attr_key) in explainable_object_dicts_to_create_after_objects_creation:
    if obj is new_obj and attr_key not in new_obj.calculated_attributes:
        new_obj.__setattr__(attr_key, ExplainableObjectDict(), check_input_validity=False)
```

Then in the deferred loop (json_to_system.py:126-132), the empty dict exists as the
attribute. Use `replace_in_mod_obj_container_without_recomputation` to swap it for the
populated dict — no `ModelingUpdate` fires, no wasted computation. This is safe because
either the calculated values are loaded from JSON, or System's `after_init` triggers the
full computation chain anyway.

```python
for (modeling_obj, attr_key), attr_value in explainable_object_dicts_to_create_after_objects_creation.items():
    explainable_object_dict = ExplainableObjectDict(
        {flat_obj_dict[key]: ExplainableObject.from_json_dict(value) for key, value in attr_value.items()})

    current_dict = getattr(modeling_obj, attr_key)
    current_dict.replace_in_mod_obj_container_without_recomputation(explainable_object_dict)

    for explainable_object_item, explainable_object_json \
            in zip(explainable_object_dict.values(), attr_value.values()):
        explainable_object_item.initialize_calculus_graph_data_from_json(
            explainable_object_json, flat_obj_dict)
```

**Note:** `replace_in_mod_obj_container_without_recomputation` on an ExplainableObjectDict
falls into the else branch (line 193-196 of object_linked_to_modeling_obj.py): unsets old
container, sets `explainable_object_dict` directly on the ModelingObject, sets new container.
The re-entry guard from section 1 is not needed here because the replacement happens at the
attribute level, not inside a dict.

**Enabling `trigger_modeling_updates` on the new dict:** `after_init` was already called
before the deferred loop, so the generic logic from section 4 already ran (on the empty
dict). The replacement dict needs its flag set explicitly:

```python
    # Enable live updates on input dicts
    if attr_key not in modeling_obj.calculated_attributes:
        explainable_object_dict.trigger_modeling_updates = True
```

---

## 8. Computation Chain: Discovery and Ordering

### Problem

System's `after_init` builds the computation chain via BFS from
`self.mod_objs_computation_chain`, which traverses
`modeling_objects_whose_attributes_depend_directly_on_me`. The current BFS path is:

```
System → EdgeUsagePattern → ... → RecurrentEdgeComponentNeed → EdgeComponent → EdgeDevice → []
```

EdgeDeviceGroup is unreachable — never computed during System init.

### Solution: Correct Dependency Chain

The semantically correct dependency direction is:

- **EdgeDeviceGroup → EdgeDevice**: EdgeDevice's `total_nb_of_units` genuinely
  depends on group attributes (`effective_nb_of_units_within_root`, `edge_device_counts`).
- **Parent EdgeDeviceGroup → child EdgeDeviceGroup**: child's `effective_nb` depends on parent's.
- **EdgeComponent → root EdgeDeviceGroups**: EdgeComponent is the natural handoff point — it's
  the last object before EdgeDevice in the chain. When groups exist, it redirects to root groups
  instead of EdgeDevice (since groups will chain to EdgeDevice themselves).

```python
# EdgeComponent (edge_component.py)
@property
def modeling_objects_whose_attributes_depend_directly_on_me(self):
    if self.edge_device:
        root_groups = self.edge_device._find_root_groups()
        if root_groups:
            return root_groups
        return [self.edge_device]
    return []

# EdgeDeviceGroup (edge_device_group.py)
@property
def modeling_objects_whose_attributes_depend_directly_on_me(self):
    return list(self.sub_group_counts.keys()) + list(self.edge_device_counts.keys())
```

This gives the BFS chain:
```
... → EdgeComponent → root_groups → [child_groups, edge_devices] → ...
```

After `optimize_mod_objs_computation_chain` reorders by `CANONICAL_COMPUTATION_ORDER`:
root groups → child groups → edge devices. Correct.

When no groups exist, EdgeComponent → EdgeDevice directly (current behavior preserved).

### Within-Class Ordering: Why It Works

When multiple root groups share sub-groups, the within-class ordering of EdgeDeviceGroup
instances must be topologically correct (parents before children). This is guaranteed by
the existing BFS + dedup-keep-last mechanism in `mod_objs_computation_chain` and
`optimize_mod_objs_computation_chain`:

1. **BFS re-insertion**: The BFS queue check (`if mod_obj not in
   mod_objs_with_attributes_to_compute`) only checks the **remaining** queue, not
   already-processed objects. So if a child group was processed prematurely (before all
   parents), a later parent re-adds it to the queue, causing a second occurrence in the chain.

2. **Dedup-keep-last**: `optimize_mod_objs_computation_chain` deduplicates by keeping the
   **last** occurrence. The premature (early) occurrence is discarded; the late one — which
   is after all parents — is kept.

3. **Canonical reorder preserves within-class order**: The reorder by
   `CANONICAL_COMPUTATION_ORDER` iterates the dedup'd chain per class, preserving the
   relative order within each class.

This produces correct topological ordering for any DAG. It would only fail with cycles,
which are structurally impossible in a group hierarchy (a group cannot be its own ancestor).

**Defensive comment to add in the implementation** (in EdgeDeviceGroup's
`modeling_objects_whose_attributes_depend_directly_on_me`):

```python
@property
def modeling_objects_whose_attributes_depend_directly_on_me(self):
    # Child groups and edge devices depend on this group's effective_nb_of_units_within_root.
    # When sub-groups are shared across multiple roots, the BFS + dedup-keep-last mechanism
    # in mod_objs_computation_chain / optimize_mod_objs_computation_chain guarantees
    # topological ordering (parents computed before children). This relies on:
    # - BFS re-adding already-processed objects when discovered from a later parent
    # - Dedup keeping the last occurrence, which is after all parents
    # Cycles are structurally impossible (a group cannot be its own ancestor).
    return list(self.sub_group_counts.keys()) + list(self.edge_device_counts.keys())
```

### Helper Methods for Root Group Discovery

```python
# EdgeDevice (edge_device.py)
def _find_root_groups(self):
    parent_groups = self._find_parent_groups()
    root_groups = []
    for group in parent_groups:
        root_groups += group._find_root_groups()
    return list(dict.fromkeys(root_groups))

# EdgeDeviceGroup (edge_device_group.py)
def _find_root_groups(self):
    parent_groups = self._find_parent_groups()
    if not parent_groups:
        return [self]  # I am a root group
    root_groups = []
    for parent in parent_groups:
        root_groups += parent._find_root_groups()
    return list(dict.fromkeys(root_groups))
```

### No `after_init` Override Needed on EdgeDeviceGroup

The original plan proposed overriding `after_init` on EdgeDeviceGroup to call
`compute_calculated_attributes()` before System init, with top-down construction order.

With the infrastructure described above, this is unnecessary:

- During normal construction: `ABCAfterInitMeta` calls `after_init` which sets
  `trigger_modeling_updates = True` on the object and its input dicts. Calculated attributes
  start as `EmptyExplainableObject`. When System's `after_init` runs, it launches the full
  computation chain which reaches groups via EdgeComponent → root groups, computing
  `effective_nb_of_units_within_root` in the right order.

- Construction order (top-down vs bottom-up) becomes irrelevant because the computation
  chain handles ordering.

- During deserialization: same flow — System's `after_init` (or loaded calculated values)
  handles everything.

---

## Summary: Execution Order

### Normal construction flow
1. Create EdgeDeviceGroups with populated ExplainableObjectDicts
2. `ABCAfterInitMeta` calls `after_init` → `trigger_modeling_updates = True` on object + dicts
3. Create remaining objects (needs, journeys, patterns)
4. Create System → `after_init` → BFS chain via EdgeComponent → root groups → child groups →
   edge devices → `effective_nb_of_units_within_root` and `total_nb_of_units`
   computed in correct order

### Live mutation flow (after System exists)
- **Value change** (e.g. `group.sub_group_counts[child] = new_count`):
  `ModelingUpdate([[old_count, new_count]])` — the SourceValue's `attr_updates_chain` traces
  through the ExplainableObject computation graph (old_count → child.effective_nb →
  edge_device.total_nb → ...). No BFS needed.
- **Structural change** (key add/remove):
  `ModelingUpdate([[old_dict, new_dict]])` — `compute_mod_objs_computation_chain_from_old_and_new_dicts`
  diffs keys, builds chain from added/removed objects + container's chain in both states.

### Deserialization flow
1. All objects created via `from_json_dict` + `after_init` per object
2. Deferred dicts populated via `replace_in_mod_obj_container_without_recomputation`
3. Dict `trigger_modeling_updates` set to True for input dicts
4. System's `after_init` triggers full computation chain (or values loaded from JSON)
