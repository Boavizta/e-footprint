# Object Counting / Hierarchical Grouping — Design Questions

## Resolved

### Structural count vs usage-based count
The counting is always derived from usage journeys. `nb_edge_usage_journeys_in_parallel` gives the number of deployed top-level ensembles. The group hierarchy provides an internal multiplier within each ensemble. `hourly_edge_usage_journey_starts` represents units sold/deployed.

### Leaf-level semantics
Each leaf is an (EdgeDevice, local_count) pair. The EdgeDevice is a single object definition with a count multiplier — no instantiation of separate objects.

### Groups carry own footprint?
No. Groups are purely organizational. Easy to add later if needed.

### Component nb_of_units
Simple numerical attribute on EdgeComponent. Multiplies capacity and footprint. Needs apply across units (a 3 cpu_core need on a 3-unit component = 1 core per unit for capacity checks).

### RecurrentEdgeDeviceNeed vs RecurrentEdgeComponentNeed semantics
- RecurrentEdgeComponentNeed applies **across** component units (distributed for capacity checks)
- RecurrentEdgeDeviceNeed applies to **each** EdgeDevice (multiplied by device count)

### Where does the per-device count live?
**On the group, not the device.** The group holds `edge_device_counts: ExplainableObjectDict[EdgeDevice, count]`. This means:
- Same EdgeDevice can appear in multiple groups with different counts
- Without groups, EdgeDevices work as today (no counting attributes needed)
- Groups are a convenience, optional modeling layer

By the same logic, sub-group counts are on the parent: `sub_group_counts: ExplainableObjectDict[EdgeDeviceGroup, count]`.

---

## Open Question 1: How does the group multiplier reach footprint calculations?

Currently, EdgeComponent uses `nb_instances = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]` to compute energy and fabrication.

With groups, this becomes: `nb_instances = nb_edge_usage_journeys_in_parallel × device_count_in_ensemble`.

**Where `device_count_in_ensemble`** = for a given EdgeDevice, the sum across all groups containing it of (group.edge_device_counts[device] × group.effective_nb_of_units_within_root).

### Proposed mechanism

1. EdgeDeviceGroup computes `effective_nb_of_units_within_root` (product of ancestor counts, 1 for root)
2. EdgeDevice gets a calculated attribute `group_count_per_usage_pattern: ExplainableObjectDict` that aggregates its total count from all groups (per usage pattern, since different patterns could deploy different ensemble types)
3. Footprint calculations multiply by this group count
4. Without groups, the multiplier defaults to 1

### Challenge: same EdgeDevice in multiple groups

Example: same sensor in cabinet (×5) and at floor level (×2):
```
Building (root)
└── Floor (×10)
    ├── Cabinet (×3)
    │   └── Sensor (×5)  → 10×3×5 = 150
    └── Sensor (×2)      → 10×2 = 20
Total sensors per building: 170
```

The aggregation needs to sum across all placements. This means someone (the root group? the device?) computes the total.

**Proposal**: The root group computes `total_edge_device_counts: ExplainableObjectDict[EdgeDevice, count]` by walking its tree. This is the single source of truth for device counts per ensemble.

→ **Does this feel right? And: is the group tree always associated with all usage patterns equally, or could different patterns deploy different ensemble structures?**

---

## Open Question 2: How does the group tree plug into the object graph?

The group is a "side-channel" (not part of the usage journey chain). But it needs to connect somewhere for recomputation to work.

### Option A: Group tree hangs off EdgeDevice
Each EdgeDevice has a reference to its root group. But a device can appear in multiple groups, so this doesn't work cleanly.

### Option B: Group tree hangs off System
System has a list of root groups. The System (or the root group) aggregates device counts and makes them available to footprint calculations.

### Option C: Group tree hangs off EdgeUsageJourney
Each journey deploys one ensemble type. The journey knows about its group, and the group multiplier feeds into the journey's instance count.

**Leaning toward Option C** — the journey already represents "what gets deployed", so attaching the ensemble structure there is natural. It also allows different journeys to deploy different ensemble types.

→ **Preference?**
