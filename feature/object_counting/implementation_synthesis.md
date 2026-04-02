# Object Counting / Hierarchical Grouping - Implementation Synthesis

## Scope Delivered

The feature is implemented in the codebase and covers three linked changes:

1. `EdgeComponent.nb_of_units` for intra-device component multiplicity
2. `EdgeDeviceGroup` for hierarchical edge-device counting
3. infrastructure changes so `ExplainableObjectDict` can be used as a live input attribute, including recomputation and JSON round-trips

The resulting counting model is:

- usage journeys still define how many ensembles are deployed through `nb_edge_usage_journeys_in_parallel`
- groups define how many edge devices exist inside one ensemble
- component `nb_of_units` defines how many physical units of a given component exist inside one edge device

In practice, the total footprint multiplier is split across layers:

- `EdgeComponent`: per-edge-device values, already including component `nb_of_units`
- `EdgeDevice`: multiplies component and structure values by grouped device count per ensemble
- `EdgeUsageJourney`: still provides the deployment count across ensembles

## Main Implementation

### 1. Edge components now model per-unit inputs

Implemented in [edge_component.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_component.py) and subclasses:

- [edge_cpu_component.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_cpu_component.py)
- [edge_ram_component.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_ram_component.py)
- [edge_storage.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_storage.py)
- [edge_workload_component.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_workload_component.py)

What changed:

- edge components now accept `nb_of_units`, defaulting to `1`
- physical inputs were moved to per-unit semantics (`*_per_unit`)
- aggregate component attributes are recomputed from `per_unit * nb_of_units`
- former `instances_*` semantics were clarified into `*_per_edge_device*`

Important consequence:

- component calculations now produce values for one edge device across usage patterns
- `EdgeComponent` no longer tries to aggregate device-group counts itself
- the dependency chain routes from component to root groups when groups exist, otherwise directly to the owning device

### 2. EdgeDeviceGroup introduces hierarchical device counting

Implemented in [edge_device_group.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_device_group.py).

The object is a pure organizational modeling object with:

- `sub_group_counts: ExplainableObjectDict`
- `edge_device_counts: ExplainableObjectDict`
- `counts_validation`
- `effective_nb_of_units_within_root`

Behavior:

- root groups have effective count `1`
- child groups inherit the product of ancestor counts
- when a group is reachable through multiple parents, contributions are summed
- counts must be dimensionless and non-negative

The implementation relies on `explainable_object_dicts_containers` to find parent groups and root groups dynamically.

### 3. EdgeDevice aggregates grouped device counts

Implemented in [edge_device.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/hardware/edge/edge_device.py).

Key additions:

- `total_nb_of_units`
- `_find_parent_groups()`
- `_find_root_groups()`

Behavior:

- if a device is not attached to any group, `total_nb_of_units = 1`
- if it belongs to one or more groups, its total is the sum of `group.edge_device_counts[self] * group.effective_nb_of_units_within_root`

This multiplier is applied to:

- structure fabrication footprint per usage pattern
- component fabrication footprint aggregation
- energy aggregation
- energy footprint aggregation

This means the delivered layering is:

- component level: per-edge-device
- device level: per-ensemble grouped device count
- usage journey level: number of ensembles deployed

## Modeling Infrastructure Changes

The feature required `ExplainableObjectDict` to become a first-class input attribute rather than only a calculated attribute.

### 1. Live dict updates

Implemented in [explainable_object_dict.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/explainable_object_dict.py).

Added:

- `trigger_modeling_updates`
- update-triggering behavior on `__setitem__`, `__delitem__`, `pop`, `clear`, and `update`

The dict now distinguishes:

- value updates on an existing key
- structural updates when keys are added or removed

### 2. Safe replacement during recomputation

Implemented in [object_linked_to_modeling_obj.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py).

When a recomputation replaces a value inside a trigger-enabled dict, the container trigger is temporarily disabled to avoid recursive `ModelingUpdate` loops.

### 3. Dict-aware computation-chain resolution

Implemented in:

- [modeling_update.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/modeling_update.py)
- [modeling_object.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/modeling_object.py)

Changes:

- plain `dict` inputs are normalized to `ExplainableObjectDict`
- `ModelingUpdate` now computes recomputation chains for dict changes
- `ModelingObject` now has shared collection-chain logic for both lists and dicts
- `after_init()` enables update triggering on input `ExplainableObjectDict` attributes

## Serialization, Registration, and Migration

### 1. Class registration and computation order

Implemented in [all_classes_in_order.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/all_classes_in_order.py).

`EdgeDeviceGroup` was added to:

- `ALL_EFOOTPRINT_CLASSES`
- `CANONICAL_COMPUTATION_ORDER`

It sits between `EdgeComponent` and `EdgeDevice`, which matches the runtime dependency chain.

### 2. JSON serialization and deserialization

Implemented in:

- [system_to_json.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/api_utils/system_to_json.py)
- [json_to_system.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/api_utils/json_to_system.py)

What was added:

- recursive serialization now discovers modeling objects referenced as keys in `ExplainableObjectDict`
- deferred JSON reconstruction now rebuilds input `ExplainableObjectDict` attributes safely
- input dict triggers are only enabled after reconstruction is complete

This is what makes `EdgeDeviceGroup` round-trip correctly through JSON.

### 3. System object discovery

Implemented in [system.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/core/system.py).

`System.get_objects_linked_to_edge_usage_patterns()` now discovers:

- groups directly containing edge devices
- all ancestor groups above them

This makes groups part of `all_linked_objects` and system-level recomputation/validation flows, while still keeping them out of object categories and footprint analysis axes.

### 4. Version upgrade support

Implemented in [version_upgrade_handlers.py](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/api_utils/version_upgrade_handlers.py).

The upgrade to version 19:

- renames old aggregate edge-component inputs to per-unit inputs
- backfills `nb_of_units = 1` on existing edge components

No migration is needed for groups because older systems simply do not contain them.

## Semantics of the Delivered Design

The implemented behavior resolves the main design questions this way:

- counting still originates from usage journeys for ensemble deployment
- groups are optional and purely organizational
- groups do not carry their own footprint
- the same edge device can appear in multiple groups
- the same sub-group can appear under multiple parents, with additive contributions
- `RecurrentEdgeComponentNeed` remains expressed at component level, while device count multiplication happens later at `EdgeDevice`

## Test Coverage Added or Updated

The implementation is covered by unit and integration tests, notably:

- [test_explainable_object_dict.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/abstract_modeling_classes/test_explainable_object_dict.py)
- [test_edge_device_group.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/hardware/edge/test_edge_device_group.py)
- [test_edge_device.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/hardware/edge/test_edge_device.py)
- [test_edge_component.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/hardware/edge/test_edge_component.py)
- [integration_edge_device_group_base_class.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/integration_tests/integration_edge_device_group_base_class.py)
- [test_integration_edge_device_group.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/integration_tests/test_integration_edge_device_group.py)
- [test_integration_edge_device_group_from_json.py](/Users/vinville/dev/e-footprint-full/e-footprint/tests/integration_tests/test_integration_edge_device_group_from_json.py)

Covered behaviors include:

- dict-trigger infrastructure
- group parent and root discovery
- effective group counts
- device total counts
- backward compatibility when no groups exist
- system discovery of groups
- JSON round-trip with preserved counts and recalculated derived attributes

## Short Conclusion

The feature is fully integrated rather than isolated to the `feature/object_counting` notes.
It changes both the edge hardware model and the modeling infrastructure:

- edge components now model multiplicity inside a device
- edge devices now model multiplicity inside an ensemble
- groups provide hierarchical counting with transparent recomputation and serialization support

The implementation is consistent with the design notes, with the final code also including the required `System` integration and version-migration support.
