# Object Counting / Hierarchical Grouping — Design Questions

## Context

The goal is to introduce a generic hierarchical counting structure for EdgeDevices, enabling models like:

```
Building (count=1)
├── Floor (count=10)
│   ├── Cabinet (count=3)
│   │   ├── Sensor EdgeDevice (count=5)        → total: 1×10×3×5 = 150
│   │   └── Controller EdgeDevice (count=1)     → total: 1×10×3×1 = 30
│   └── FloorController EdgeDevice (count=1)    → total: 1×10×1 = 10
└── BuildingController EdgeDevice (count=1)      → total: 1×1 = 1
```

The structure must be generic (not hardcoded to building/floor/cabinet) and compatible with e-footprint's recomputation semantics.

---

## Question 1: How does the structural count interact with usage-based instance count?

Currently, the "number of instances" of an EdgeDevice is derived from `nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern`. This is a temporal measure: how many journeys overlap at any given hour.

With the structural count, we have a **physical multiplier** (e.g., 150 sensors exist in the building).

**Two possible compositions:**

### Option A: Structural count multiplies the per-device journey count
- Each sensor has its own usage journey (e.g., "read every 5 min" → ~0.003 concurrent journeys per sensor)
- Total concurrent journeys = structural_count × per_device_concurrent_journeys = 150 × 0.003 = 0.45
- The structural count feeds into `hourly_edge_usage_journey_starts` as a multiplier

### Option B: Structural count replaces the journey-based instance count for energy/fabrication
- The structural count IS the number of physical devices
- Energy = structural_count × per_device_power × hours
- Fabrication = structural_count × per_device_fabrication_footprint
- The journey-based concurrency is only used for capacity validation (CPU/RAM/workload), not for counting devices

**My intuition**: Option B seems more natural for physical infrastructure — a sensor exists and consumes power whether a journey is running or not. But this may be a fundamental change to how Edge footprints work.

→ **Which model is correct for your smart building use case?**

---

## Question 2: What exactly sits at leaf level?

The user mentioned "that many EdgeDevices (different counts for different objects) per cabinet". This means a group contains **(EdgeDevice, local_count)** pairs, not just EdgeDevices.

**Sub-question**: Can the same EdgeDevice type appear in multiple groups with different counts? For example:
- Cabinet A has 5× SensorTypeA
- Cabinet B has 3× SensorTypeA

If so, are these the same EdgeDevice object (shared) or different instances? This matters for:
- Recomputation: changing a SensorTypeA property should update both cabinets
- Footprint attribution: each group needs its own count for the same device

→ **Can the same EdgeDevice appear in multiple places in the tree with different counts?**

---

## Question 3: Does the group structure connect to EdgeUsagePatterns?

Currently: `EdgeUsagePattern → EdgeUsageJourney → EdgeFunction → RecurrentEdgeDeviceNeed → EdgeDevice`

With groups, where does the pattern attach?
- **Option A**: Usage patterns still link to individual EdgeDevices. Groups are purely a counting/structural overlay.
- **Option B**: Usage patterns link to the group, and all devices within inherit the pattern.

→ **How do usage patterns relate to the group hierarchy?**

---

## Question 4: Are groups themselves ModelingObjects?

If yes, they participate in recomputation: changing a floor count triggers recalculation of all downstream device footprints.

If no, they're just a convenience layer for setting up the model, and the effective counts are baked into EdgeDevices at construction time.

**Recommendation**: They should be ModelingObjects for full reactivity.

→ **Confirmed?**

---

## Question 5: Do groups have their own physical properties?

For example, does a "floor" have its own carbon footprint (structural steel, concrete, etc.) that should be attributed? Or is the footprint purely from the EdgeDevices and their components?

→ **Are groups purely organizational, or do they carry their own environmental footprint?**
