# Object Counting / Hierarchical Grouping — Archive for Completed Phases 1 and 2

This file archives the completed parts of
[implementation_plan.md](/Users/vinville/dev/e-footprint-full/e-footprint/feature/object_counting/implementation_plan.md)
so future work can focus on the remaining phases with less context overhead.

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

## Phase 2: Add EdgeComponent.nb_of_units with per-unit inputs

**Goal**: Each component type can specify how many units exist within its EdgeDevice.
All physical component inputs become **per-unit** inputs. Aggregate component attributes
(`carbon_footprint_fabrication`, `power`, `idle_power`, `compute`, `ram`, `storage_capacity`)
are recalculated at the beginning of the component calculation chain from
`*_per_unit × nb_of_units`. EdgeDevice still does not need to know about `component.nb_of_units`.

### 2.1 EdgeComponent (edge_component.py)

**Add to `__init__`:**
```python
def __init__(self, name, carbon_footprint_fabrication_per_unit, power_per_unit, lifespan, idle_power_per_unit,
             nb_of_units=None):
    ...
    if nb_of_units is None:
        nb_of_units = SourceValue(1 * u.dimensionless)
    self.nb_of_units = nb_of_units.set_label(f"Number of units of {self.name}")
    self.carbon_footprint_fabrication_per_unit = ...
    self.power_per_unit = ...
    self.idle_power_per_unit = ...
```

**Add to `default_values` in each subclass:**
```python
"nb_of_units": SourceValue(1 * u.dimensionless)
```

**Add aggregate calculated attributes at the start of `calculated_attributes`:**
```python
["carbon_footprint_fabrication", "power", "idle_power",
 "unitary_power_per_usage_pattern",
 "fabrication_footprint_per_edge_device_per_usage_pattern",
 "energy_per_edge_device_per_usage_pattern",
 "energy_footprint_per_edge_device_per_usage_pattern",
 "fabrication_footprint_per_edge_device",
 "energy_per_edge_device", "energy_footprint_per_edge_device",
 "total_unitary_hourly_need_per_usage_pattern"]
```

**Aggregate attribute formulas:**
- `carbon_footprint_fabrication = carbon_footprint_fabrication_per_unit * nb_of_units`
- `power = power_per_unit * nb_of_units`
- `idle_power = idle_power_per_unit * nb_of_units`

**Update EdgeComponent calculations** to use aggregate attributes only:

- `update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern`:
  ```python
  component_fabrication_intensity = self.carbon_footprint_fabrication / self.lifespan
  nb_instances = ...  # as today
  # rest unchanged
  ```

- `update_dict_element_in_energy_per_edge_device_per_usage_pattern`:
  ```python
  instances_energy = nb_instances * (
      self.unitary_power_per_usage_pattern[usage_pattern] * ExplainableQuantity(1 * u.hour, "one hour"))
  ```

### 2.1.1 EdgeComponent subclasses

Each subclass stores **per-unit** physical inputs and exposes the aggregate attribute as a
calculated attribute.

For EdgeCPUComponent:
```python
compute_per_unit = ...
compute = compute_per_unit * nb_of_units
available_compute = compute - base_compute_consumption
```
`unitary_hourly_compute_need_per_usage_pattern` stays **per component** (not divided by `nb_of_units`).
`unitary_power_per_usage_pattern` uses aggregate `power`, `idle_power`, and `compute`.

For EdgeRAMComponent:
```python
ram_per_unit = ...
ram = ram_per_unit * nb_of_units
available_ram = ram - base_ram_consumption
```
`unitary_hourly_ram_need_per_usage_pattern` stays **per component**.
`unitary_power_per_usage_pattern` uses aggregate `power`, `idle_power`, and `ram`.

For EdgeStorage:
```python
storage_capacity_per_unit = ...
storage_capacity = storage_capacity_per_unit * nb_of_units
# validate: max_cumulative_need ≤ storage_capacity
```
`carbon_footprint_fabrication` is also recomputed from
`carbon_footprint_fabrication_per_storage_capacity × storage_capacity_per_unit × nb_of_units`.

For EdgeWorkloadComponent:
```python
# No capacity validation currently.
power and idle_power become aggregate attributes computed from per-unit inputs.
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
- Test that CPU/RAM needs remain per component (no division by `nb_of_units`).
- Test aggregate attributes are recomputed from per-unit inputs.
