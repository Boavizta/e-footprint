# Object Counting / Hierarchical Grouping — Implementation Plan

## Summary

Introduce hierarchical counting for Edge objects via two mechanisms:
1. **EdgeComponent.nb_of_units**: simple attribute on components (e.g., 3 CPU modules in one device)
2. **EdgeDeviceGroup**: new ModelingObject for hierarchical device counting (cabinets, floors, buildings...)

Groups are purely organizational (no own footprint), optional (backward compatible), and connected
to the rest of the system only through the EdgeDevices they reference.

---

## Design Decisions (Resolved)

- Counting always derives from usage journeys. `nb_edge_usage_journeys_in_parallel` = number of ensembles deployed.
  Groups provide an internal multiplier within each ensemble.
- `EdgeComponent.nb_of_units`: simple numerical attribute. Multiplies capacity and footprint.
- `EdgeDeviceGroup` holds counts for its children via `ExplainableObjectDict`:
  - `sub_group_counts: ExplainableObjectDict[EdgeDeviceGroup, count]`
  - `edge_device_counts: ExplainableObjectDict[EdgeDevice, count]`
- Same EdgeDevice (or sub-group) can appear in multiple groups with different counts.
- Without groups, EdgeDevices work as today (default multiplier = 1).
- RecurrentEdgeComponentNeed applies **across** component units (distributed for capacity).
  RecurrentEdgeDeviceNeed applies to **each** EdgeDevice (multiplied by count).
- Each group and EdgeDevice computes its own total count as a calculated attribute.
  The explainability graph makes the counting fully transparent.
- Groups are not in the usage journey chain. They are a side-channel providing multipliers.
- Serialization discovers groups by extending `recursively_write_json_dict` to walk
  `ExplainableObjectDict` keys (generic, not group-specific).
- EdgeComponent refactored to compute only **unitary** values. EdgeDevice handles all aggregation
  (× component.nb_of_units × group_multiplier × nb_ensembles). This avoids a circular dependency
  between EdgeComponent and EdgeDevice.

---

## Dependency Chain (After Implementation)

```
RecurrentEdgeComponentNeed
    → EdgeComponent (unitary footprints only)
        → EdgeDeviceGroup (hierarchical counting)
            → EdgeDevice (aggregation: components × counts × ensembles)
```

No circular dependencies. EdgeDeviceGroup sits between EdgeComponent and EdgeDevice
in CANONICAL_COMPUTATION_ORDER.

---

## Phase 1: Rename EdgeComponent semantics to per-edge-device

**Goal**: Rename EdgeComponent calculated attributes from `instances_*` to
`*_per_edge_device_*` to clarify their semantics. Calculations stay the same —
they multiply by `nb_edge_usage_journeys_in_parallel` (from usage pattern, no
circular dependency). The values represent "footprint across all ensembles,
for ONE edge device's worth of this component".

### 1.1 EdgeComponent (edge_component.py)

**Rename these calculated attributes** (calculations unchanged):
- `instances_fabrication_footprint_per_usage_pattern`
  → `fabrication_footprint_per_edge_device_per_usage_pattern`
- `instances_energy_per_usage_pattern`
  → `energy_per_edge_device_per_usage_pattern`
- `energy_footprint_per_usage_pattern`
  → `energy_footprint_per_edge_device_per_usage_pattern`
- `instances_fabrication_footprint` → `fabrication_footprint_per_edge_device`
- `instances_energy` → `energy_per_edge_device`
- `energy_footprint` → `energy_footprint_per_edge_device`

**Keep unchanged:**
- `unitary_power_per_usage_pattern` (abstract, implemented by subclasses)
- `total_unitary_hourly_need_per_usage_pattern` (for capacity validation)

**Updated `calculated_attributes`:**
```python
["unitary_power_per_usage_pattern",
 "fabrication_footprint_per_edge_device_per_usage_pattern",
 "energy_per_edge_device_per_usage_pattern",
 "energy_footprint_per_edge_device_per_usage_pattern",
 "fabrication_footprint_per_edge_device",
 "energy_per_edge_device", "energy_footprint_per_edge_device",
 "total_unitary_hourly_need_per_usage_pattern"]
```

### 1.2 EdgeComponent subclasses

No changes to subclasses — only the base class attribute names change.

### 1.3 EdgeDevice (edge_device.py)

**Update references** to read from renamed component attributes.

Current methods like `update_dict_element_in_instances_energy_per_usage_pattern` already
read from `component.instances_energy_per_usage_pattern` — update these references to
`component.energy_per_edge_device_per_usage_pattern`.

Same for `energy_footprint_breakdown_by_source` (reads `component.energy_footprint`
→ `component.energy_footprint_per_edge_device`) and `fabrication_footprint_breakdown_by_source`
(reads `component.instances_fabrication_footprint`
→ `component.fabrication_footprint_per_edge_device`).

No calculation changes — just reference renames.

### 1.4 Tests

- Update test assertions to use renamed attributes.
- Integration tests should pass with identical numerical results (pure rename, no behavior change).

---

## Phase 2: Add EdgeComponent.nb_of_units

**Goal**: Each component type can specify how many units exist within its EdgeDevice.
The `nb_of_units` multiplication happens entirely within EdgeComponent — it effectively
makes the component behave as if it had multiplied power, capacity, and fabrication.
EdgeDevice doesn't need to know about `component.nb_of_units`.

### 2.1 EdgeComponent (edge_component.py)

**Add to `__init__`:**
```python
def __init__(self, name, carbon_footprint_fabrication, power, lifespan, idle_power,
             nb_of_units=None):
    ...
    if nb_of_units is None:
        nb_of_units = SourceValue(1 * u.dimensionless)
    self.nb_of_units = nb_of_units.set_label(f"Number of units of {self.name}")
```

**Add to `default_values` in each subclass:**
```python
"nb_of_units": SourceValue(1 * u.dimensionless)
```

**Update EdgeComponent calculations** to multiply by `nb_of_units`:

- `update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern`:
  ```python
  component_fabrication_intensity = (self.carbon_footprint_fabrication / self.lifespan)
      * self.nb_of_units
  nb_instances = ...  # as today
  # rest unchanged
  ```

- `update_dict_element_in_energy_per_edge_device_per_usage_pattern`:
  ```python
  # unitary_power already per single unit, multiply by nb_of_units
  instances_energy = nb_instances * (self.unitary_power_per_usage_pattern[usage_pattern]
      * self.nb_of_units * ExplainableQuantity(1 * u.hour, "one hour"))
  ```

**Capacity validation**: Update each subclass's validation to multiply capacity by nb_of_units.

For EdgeCPUComponent:
```python
available_compute = self.compute * self.nb_of_units - self.base_compute_consumption
```
Base consumption is a fixed overhead for the component, not per-unit.

For EdgeRAMComponent: same pattern with `ram` and `base_ram_consumption`.

For EdgeStorage:
```python
total_capacity = self.storage_capacity * self.nb_of_units
# validate: max_cumulative_need ≤ total_capacity
```

For EdgeWorkloadComponent:
```python
# No capacity validation currently, so nothing to change.
# If added later, multiply by nb_of_units.
```

### 2.2 EdgeDevice (edge_device.py)

**No changes needed.** EdgeDevice already sums component per-edge-device values.
With `nb_of_units` handled inside EdgeComponent, the component's per-edge-device values
already reflect the multiplied power/fabrication. EdgeDevice's aggregation works as-is.

`energy_footprint_breakdown_by_source` and `fabrication_footprint_breakdown_by_source`
also work unchanged — they read component-level totals which now include nb_of_units.

### 2.3 Tests

- Test that nb_of_units=1 produces identical results to before (backward compat).
- Test that nb_of_units=3 triples energy and fabrication for a component.
- Test capacity validation with nb_of_units > 1.
- Test that needs are distributed across units (3 cpu_core need on nb_of_units=3 = 1 per unit).

---

## Phase 3a: Infrastructure — ExplainableObjectDict as Input Attribute

**Goal**: Enable ExplainableObjectDict to work as an `__init__` parameter with full
recomputation and serialization support. **Must be completed before Phase 3b.**

All changes are detailed in
**[explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)**.
Summary of what to implement:

1. **ExplainableObjectDict** (explainable_object_dict.py): Add `trigger_modeling_updates` flag.
   Update `__setitem__`, `__delitem__`, `pop`, `clear` to trigger ModelingUpdate when True.
   (Sections 1)
2. **object_linked_to_modeling_obj.py**: Re-entry guard in
   `replace_in_mod_obj_container_without_recomputation` for dict containers — mirror the
   existing list guard. (Section 1, subsection "Guard Against Re-entry")
3. **ModelingUpdate** (modeling_update.py): dict→ExplainableObjectDict in `parse_changes_list`,
   ExplainableObjectDict branch in `compute_mod_objs_computation_chain`. (Section 2)
4. **ModelingObject** (modeling_object.py): Factor list/dict computation chain into shared
   `_compute_mod_objs_computation_chain_from_old_and_new_collection`, add dict variant.
   Update `after_init` to enable triggers on input dicts. (Sections 3 & 4)
5. **json_to_system.py**: Initialize input ExplainableObjectDicts to empty in `from_json_dict`,
   use `replace_in_mod_obj_container_without_recomputation` in deferred loop, set
   `trigger_modeling_updates` on input dicts after. (Section 7)
6. **system_to_json.py**: Walk ExplainableObjectDict keys and
   `explainable_object_dicts_containers` in `recursively_write_json_dict`. (Section 6)

### 3a.1 Tests

**Unit tests** (tests/abstract_modeling_classes/):
- `test_explainable_object_dict.py`:
  - Test `__setitem__` on existing key triggers ModelingUpdate when `trigger_modeling_updates=True`
  - Test `__setitem__` on new key triggers structural ModelingUpdate
  - Test `__delitem__` triggers structural ModelingUpdate
  - Test no ModelingUpdate when `trigger_modeling_updates=False` (current behavior preserved)
  - Test re-entry guard: `replace_in_mod_obj_container_without_recomputation` inside a
    trigger-enabled dict doesn't loop

**Integration tests** (tests/integration_tests/):
- Serialization round-trip test with a ModelingObject that has an input ExplainableObjectDict
  (will be covered by EdgeDeviceGroup round-trip in Phase 4)

---

## Phase 3b: Create EdgeDeviceGroup

**Goal**: New ModelingObject for hierarchical counting.

### 3.1 New class: EdgeDeviceGroup (efootprint/core/hardware/edge/edge_device_group.py)

**Important:** The init signature uses `ExplainableObjectDict` directly (not
`List[Tuple[..., ExplainableQuantity]]`) to avoid a self-referential type annotation that would
deadlock `compute_classes_generation_order`. See
[explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)
section 5.

```python
class EdgeDeviceGroup(ModelingObject):
    default_values = {}  # No numerical defaults — counts are on the dicts
    classes_outside_init_params_needed_for_generating_from_json = [EdgeDevice]

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

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return list(self.sub_group_counts.keys()) + list(self.edge_device_counts.keys())

    @property
    def calculated_attributes(self):
        return ["counts_validation", "effective_nb_of_units_within_root"]
```

**Validation: `counts_validation`**

Ensures all counts in both dicts are dimensionless and positive:

```python
def update_counts_validation(self):
    for key, count in list(self.sub_group_counts.items()) + list(self.edge_device_counts.items()):
        if not count.value.check("[]"):
            raise ValueError(
                f"Count for {key.name} in {self.name} should be dimensionless "
                f"but has units {count.value.units}")
        if count.value.magnitude < 0:
            raise ValueError(
                f"Count for {key.name} in {self.name} should be positive "
                f"but is {count.value.magnitude}")
```

**Computed attribute: `effective_nb_of_units_within_root`**

```python
def update_effective_nb_of_units_within_root(self):
    parent_groups = self._find_parent_groups()
    if not parent_groups:
        # Root group: effective count is 1
        self.effective_nb_of_units_within_root = ExplainableQuantity(
            1 * u.dimensionless, f"{self.name} is a root group")
    else:
        # Sum contributions from all parents
        effective_nb = sum(
            [parent.sub_group_counts[self] * parent.effective_nb_of_units_within_root
             for parent in parent_groups],
            start=EmptyExplainableObject())
        self.effective_nb_of_units_within_root = effective_nb.set_label(
            f"Effective nb of {self.name} within root group")
```

**Finding parent groups via `explainable_object_dicts_containers`:**

```python
def _find_parent_groups(self):
    parent_groups = []
    for dict_container in self.explainable_object_dicts_containers:
        container = dict_container.modeling_obj_container
        if isinstance(container, EdgeDeviceGroup):
            if self not in dict_container:
                raise ValueError(
                    f"Stale explainable_object_dicts_container: "
                    f"{container.name}.{dict_container.attr_name_in_mod_obj_container} "
                    f"references {self.name} but doesn't contain it as a key")
            if container not in parent_groups:
                parent_groups.append(container)
    return parent_groups
```

**Root group discovery** (used by EdgeComponent to route the computation chain):

```python
def _find_root_groups(self):
    parent_groups = self._find_parent_groups()
    if not parent_groups:
        return [self]  # I am a root group
    root_groups = []
    for parent in parent_groups:
        root_groups += parent._find_root_groups()
    return list(dict.fromkeys(root_groups))
```

**No `after_init` override needed.** The generic `ModelingObject.after_init` sets
`trigger_modeling_updates = True` on the object and its input ExplainableObjectDicts (see
[explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)
section 4). System's computation chain reaches groups via EdgeComponent → root groups
(see section 8 of same doc). Construction order of groups is irrelevant.

### 3.2 EdgeDevice: total_nb_of_units_per_ensemble (edge_device.py)

**Add calculated attribute:**
```python
# In __init__:
self.total_nb_of_units_per_ensemble = EmptyExplainableObject()

# In calculated_attributes (insert before aggregation attributes):
["lifespan_validation", "component_needs_edge_device_validation",
 "total_nb_of_units_per_ensemble",  # ← NEW
 "instances_fabrication_footprint_per_usage_pattern", ...]
```

**Update method:**
```python
def update_total_nb_of_units_per_ensemble(self):
    parent_groups = self._find_parent_groups()
    if not parent_groups:
        self.total_nb_of_units_per_ensemble = ExplainableQuantity(
            1 * u.dimensionless, f"{self.name} has no group (default count = 1)")
        return

    total = sum(
        [group.edge_device_counts[self] * group.effective_nb_of_units_within_root
         for group in parent_groups],
        start=EmptyExplainableObject())
    self.total_nb_of_units_per_ensemble = total.set_label(
        f"Total nb of {self.name} per ensemble")

def _find_parent_groups(self):
    from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
    parent_groups = []
    for dict_container in self.explainable_object_dicts_containers:
        container = dict_container.modeling_obj_container
        if isinstance(container, EdgeDeviceGroup):
            if self not in dict_container:
                raise ValueError(
                    f"Stale explainable_object_dicts_container: "
                    f"{container.name}.{dict_container.attr_name_in_mod_obj_container} "
                    f"references {self.name} but doesn't contain it as a key")
            if container not in parent_groups:
                parent_groups.append(container)
    return parent_groups

def _find_root_groups(self):
    parent_groups = self._find_parent_groups()
    root_groups = []
    for group in parent_groups:
        root_groups += group._find_root_groups()
    return list(dict.fromkeys(root_groups))
```

**Update aggregation methods to multiply by `total_nb_of_units_per_ensemble`:**

The per-edge-device component values (already × nb_ensembles and × nb_of_units from
Phase 2) now get multiplied by `self.total_nb_of_units_per_ensemble` (from groups).

```python
def update_dict_element_in_instances_energy_per_usage_pattern(self, usage_pattern):
    total_energy = EmptyExplainableObject()
    for component in self.components:
        if usage_pattern in component.energy_per_edge_device_per_usage_pattern:
            total_energy += component.energy_per_edge_device_per_usage_pattern[usage_pattern]
    self.instances_energy_per_usage_pattern[usage_pattern] = (
        self.total_nb_of_units_per_ensemble * total_energy
    ).set_label(...)
```

Same pattern for fabrication (including structure × total_nb_of_units_per_ensemble)
and energy footprint calculations.

`energy_footprint_breakdown_by_source` and `fabrication_footprint_breakdown_by_source`
also multiply by `total_nb_of_units_per_ensemble`.

### 3.3 EdgeComponent: Route Computation Chain Through Groups

**Update `modeling_objects_whose_attributes_depend_directly_on_me`** (edge_component.py)
to redirect to root groups when they exist, so that the BFS computation chain goes
EdgeComponent → root groups → child groups → EdgeDevices:

```python
@property
def modeling_objects_whose_attributes_depend_directly_on_me(self):
    if self.edge_device:
        root_groups = self.edge_device._find_root_groups()
        if root_groups:
            return root_groups
        return [self.edge_device]
    return []
```

When no groups exist, behavior is unchanged (EdgeComponent → EdgeDevice directly).

See [explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)
section 8 for the full rationale.

### 3.4 Registration

**all_classes_in_order.py:**
- Add `EdgeDeviceGroup` to `ALL_EFOOTPRINT_CLASSES`
- Add `EdgeDeviceGroup` to `CANONICAL_COMPUTATION_ORDER` between `EdgeComponent` and `EdgeDevice`

### 3b.5 Tests

**Unit tests** (tests/hardware/edge/):

`test_edge_device_group.py`:
- `update_counts_validation`: dimensionless OK, non-dimensionless raises, negative raises, zero OK
- `update_effective_nb_of_units_within_root`: root group = 1, child with one parent,
  child with multiple parents (sum of contributions)
- `_find_parent_groups` and `_find_root_groups`: no parents, one parent, chain of parents

`test_edge_device.py` (additions):
- `update_total_nb_of_units_per_ensemble`: no groups = 1, one group, multiple groups
- `_find_parent_groups` and `_find_root_groups`

`test_edge_component.py` (additions):
- `modeling_objects_whose_attributes_depend_directly_on_me`: returns root groups when they
  exist, returns edge_device when no groups (special logic → needs unit test per tests/AGENTS.md)

**Integration tests** (tests/integration_tests/):

Create a new integration test fixture following the pattern in tests/integration_tests/AGENTS.md:
- `integration_edge_device_group_base_class.py` with `generate_edge_device_group_system()`
  building a system with a building/floor/cabinet group hierarchy + `nb_of_units > 1` on
  some components
- `test_integration_edge_device_group.py` (code variant)
- `test_integration_edge_device_group_from_json.py` (JSON round-trip variant)

Tests to include in the base class:
- `run_test_effective_nb_of_units_within_root` for each group level
- `run_test_total_nb_of_units_per_ensemble` for edge devices
- `run_test_numerical_footprints` verifying component × nb_of_units × group_count × ensembles
- `run_test_all_objects_linked_to_system` includes groups
- `run_test_recomputation_on_count_change`: change a group count, verify cascade
- Backward compat: existing integration tests (without groups) must still pass unchanged

---

## Phase 4: Serialization

The full serialization/deserialization design is in
**[explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)**
sections 6 and 7. Summary of changes:

### 4.1 system_to_json.py

Extend `recursively_write_json_dict` to walk ExplainableObjectDict keys and
`explainable_object_dicts_containers` to discover parent groups. This is fully generic.

### 4.2 json_to_system.py

The existing deferred-dict mechanism (lines 126-132) already handles ExplainableObjectDicts
with ModelingObject keys. Key change: temporarily disable `trigger_modeling_updates` during
the deferred loop so that populating input dicts doesn't fire ModelingUpdate during
deserialization. Then enable `trigger_modeling_updates` on input dicts afterwards.

### 4.3 Version upgrade handler

Add a handler in `version_upgrade_handlers.py` for the new version that:
- Adds `"nb_of_units"` with default value to existing EdgeComponent JSON entries.
- No changes needed for EdgeDeviceGroup (old systems simply don't have groups).

---

## Phase 5: System Integration

### 5.1 System object discovery (system.py)

Groups are discovered for the **computation chain** via EdgeComponent →
`modeling_objects_whose_attributes_depend_directly_on_me` → root groups (Phase 3b.3).
No change needed in System for computation.

However, `all_linked_objects` (used for `_objects_by_category`, footprint summaries, and
validation) must also discover groups. Add to `get_objects_linked_to_edge_usage_patterns`:

```python
edge_device_groups = []
for ed in edge_devices:
    for group in ed._find_parent_groups():
        if group not in edge_device_groups:
            edge_device_groups.append(group)
            for ancestor in group._find_all_ancestor_groups():
                if ancestor not in edge_device_groups:
                    edge_device_groups.append(ancestor)
```

Include the discovered groups in the returned list. Do NOT add `EdgeDeviceGroup` to
`OBJECT_CATEGORIES` — groups are pure organizational helpers with no own impact, not an
analysis axis.

### 5.2 Sankey graphs

No changes needed — groups don't appear in Sankey.
EdgeDevice footprint breakdown by source continues to work as before (components are sources).

---

## Construction Order

Objects must be created in this order:

1. EdgeComponents (with nb_of_units)
2. EdgeDevices (with components list)
3. EdgeDeviceGroups (any order — System's computation chain handles dependencies)
4. RecurrentEdgeComponentNeeds, RecurrentEdgeDeviceNeeds, EdgeFunctions
5. EdgeUsageJourneys, EdgeUsagePatterns
6. System (triggers full computation chain)

---

## File Changes Summary

| File | Phase | Change |
|------|-------|--------|
| `explainable_object_dict.py` | 3a | Add `trigger_modeling_updates`, update mutation methods |
| `object_linked_to_modeling_obj.py` | 3a | Re-entry guard for dict containers |
| `modeling_update.py` | 3a | Dict handling in `parse_changes_list` + `compute_mod_objs_computation_chain` |
| `modeling_object.py` | 3a | Factor list/dict chain logic, `after_init` dict trigger, new dict chain method |
| `json_to_system.py` | 3a | Input dict init in `from_json_dict`, deferred loop via replace |
| `system_to_json.py` | 3a | Walk ExplainableObjectDict keys + containers |
| `edge_component.py` | 1,2,3b | Rename attrs, add `nb_of_units`, route computation chain through groups |
| `edge_cpu_component.py` | 2 | Add `nb_of_units` to defaults, update capacity validation |
| `edge_ram_component.py` | 2 | Add `nb_of_units` to defaults, update capacity validation |
| `edge_storage.py` | 2 | Add `nb_of_units` to defaults, update capacity validation |
| `edge_workload_component.py` | 2 | Add `nb_of_units` to defaults |
| `edge_device.py` | 1,3b | Rename refs, add `total_nb_of_units_per_ensemble`, `_find_parent/root_groups` |
| `edge_device_group.py` | 3b | **NEW** — EdgeDeviceGroup class |
| `all_classes_in_order.py` | 3b | Add EdgeDeviceGroup to `ALL_EFOOTPRINT_CLASSES` + `CANONICAL_COMPUTATION_ORDER` |
| `system.py` | 5 | Discover groups in `all_linked_objects` |
| `version_upgrade_handlers.py` | 4 | Add `nb_of_units` migration |
| Tests | all | Update existing, add infrastructure + group + serialization tests |

---

## Risks and Mitigations

**Risk: EdgeStorage special cases.** Storage has cumulative tracking, per-capacity fabrication,
and Monday-zeroing logic. Verify that the unitary refactor doesn't break these.
**Mitigation**: Dedicated EdgeStorage tests with nb_of_units > 1.

**Risk: ExplainableObjectDict as input attribute.** Currently only used for calculated attributes.
Using it as an __init__ attribute (for group counts) requires infrastructure changes to
recomputation, serialization, and deserialization. **This is the most sensitive part of the
development.** See **[explainable_object_dict_as_input_attribute.md](explainable_object_dict_as_input_attribute.md)**
for the detailed design covering: `trigger_modeling_updates` on dicts, new ModelingUpdate dict
handling, `compute_mod_objs_computation_chain_from_old_and_new_dicts`, init signature (avoiding
self-referential types), serialization object discovery, and deserialization timing pitfalls.

**Risk: `explainable_object_dicts_containers` navigation is fragile.** It's a tracking mechanism,
not a clean API. If containers aren't properly maintained, group discovery fails silently.
**Mitigation**: `_find_parent_groups` (on both EdgeDeviceGroup and EdgeDevice) raises `ValueError`
when it detects a stale container reference (dict listed in `explainable_object_dicts_containers`
but no longer containing the object as a key). This turns silent wrong results into loud failures.

**Risk: `copy_with` on EdgeDeviceGroup.** `_prepare_value_for_copy` does `copy(value)` on
ExplainableObjectDicts, but the copied dict's values are still linked to the original
container → `set_modeling_obj_container` raises `PermissionError`.
**Mitigation**: Add `ExplainableObjectDict` to `_value_requires_manual_override` so that
`copy_with` requires explicit dict overrides. This is consistent with how lists are handled.
