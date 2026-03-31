# Object Counting / Hierarchical Grouping — Design Questions

## Resolved

### Structural count vs usage-based count
**Resolved**: The counting is always derived from usage journeys. `nb_edge_usage_journeys_in_parallel` gives the number of deployed top-level ensembles. The group hierarchy provides an internal multiplier within each ensemble. `hourly_edge_usage_journey_starts` represents units sold/deployed.

### Leaf-level semantics
**Resolved**: Each leaf is an (EdgeDevice, local_count) pair. The EdgeDevice is a single object definition with a count multiplier — no instantiation of separate objects.

### Groups carry own footprint?
**Resolved**: No. Groups are purely organizational. Easy to add later if needed.

### Component nb_of_units
**Resolved**: Simple numerical attribute on EdgeComponent. Multiplies capacity and footprint. Needs apply across units (a 3 cpu_core need on a 3-unit component = 1 core per unit for capacity checks).

### RecurrentEdgeDeviceNeed vs RecurrentEdgeComponentNeed semantics
**Resolved**:
- RecurrentEdgeComponentNeed applies **across** component units (distributed for capacity checks)
- RecurrentEdgeDeviceNeed applies to **each** EdgeDevice (multiplied by device count)

---

## Open Question: Where does the per-device count live?

Each group contains EdgeDevices with a local count. Two options:

### Option A: `nb_of_units` attribute on EdgeDevice itself
```python
class EdgeDevice(ModelingObject):
    def __init__(self, ..., nb_of_units=SourceValue(1 * u.dimensionless)):
        self.nb_of_units = nb_of_units
```
- Simple, consistent with EdgeComponent.nb_of_units
- Limitation: same EdgeDevice object can't appear in two groups with different counts (acceptable per use case)

### Option B: Count stored on the group as a dict
```python
class EdgeDeviceGroup(ModelingObject):
    def __init__(self, ..., edge_devices: List[EdgeDevice],
                 edge_device_counts: ExplainableObjectDict):
        self.edge_devices = edge_devices
        self.edge_device_counts = {device: count for device, count in ...}
```
- Decouples device specs from placement count
- More complex

**Leaning toward Option A** for simplicity and consistency with the component-level pattern.

→ **Preference?**
