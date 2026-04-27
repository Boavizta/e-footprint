# Big System JSON Weight Analysis

**Date:** March 19, 2026
**Artifact analyzed:** `tests/performance_tests/big_system_with_calc_attr.json`
**Context:** `test_big_system_from_and_to_json_performance`

---

## Executive Summary

The 371 MB size of `big_system_with_calc_attr.json` comes almost entirely from calculated attributes.

- `big_system.json`: 0.45 MB
- `big_system_with_calc_attr.json`: 371.78 MB
- Delta caused by calculated attributes: 371.33 MB

The dominant source is not generic explainability metadata. It is serialized hourly or recurrent timeseries payloads, mostly in `compressed_values`.

- Total timeseries payload: 367.43 MB
- Total explainability graph payload: 3.19 MB

The recent impact repartition logic is the main direct contributor. The 6 repartition-related attributes alone account for 223.17 MB, or about 60.0% of the whole file.

---

## Method

The analysis was done directly on the generated JSON artifact already present in the repository:

- `tests/performance_tests/big_system_with_calc_attr.json`
- `tests/performance_tests/big_system.json`

For each serialized modeling-object attribute, I measured:

- total serialized byte size
- number of embedded timeseries objects
- total size of `compressed_values`
- total size of explainability graph fields:
  - `direct_ancestors_with_id`
  - `direct_children_with_id`
  - `explain_nested_tuples`

I also inspected the serialization and repartition code paths:

- [`efootprint/api_utils/system_to_json.py`](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/api_utils/system_to_json.py)
- [`efootprint/abstract_modeling_classes/modeling_object.py`](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/modeling_object.py)
- [`efootprint/abstract_modeling_classes/explainable_hourly_quantities.py`](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/explainable_hourly_quantities.py)

---

## Main Findings

### 1. The file is heavy because calculated attributes are persisted

`system_to_json()` simply calls each modeling object’s `to_json()` and includes calculated attributes when `save_calculated_attributes=True`.

The baseline file without calculated attributes is tiny:

- `big_system.json`: 451,228 bytes
- `big_system_with_calc_attr.json`: 371,779,731 bytes

So the weight problem is entirely in calculated attributes, not in the structural object graph.

### 2. The weight is almost entirely repeated timeseries data

Across the whole file:

- total timeseries payload: 367.43 MB
- total `compressed_values` payload: 363.70 MB
- total explainability graph payload: 3.19 MB
- total serialized timeseries count: 3515

This means the problem is overwhelmingly the duplication of full hourly series, not labels or dependency-graph metadata.

### 3. Impact repartition is the main source

The generic repartition attributes are introduced by default on `ModelingObject` in
[`modeling_object.py`](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/modeling_object.py#L425).

These 6 attributes dominate the file:

| Attribute | Size (MB) |
| --- | ---: |
| `fabrication_impact_repartition_weights` | 60.64 |
| `usage_impact_repartition_weights` | 47.17 |
| `usage_impact_repartition_weight_sum` | 45.27 |
| `fabrication_impact_repartition_weight_sum` | 44.35 |
| `fabrication_impact_repartition` | 13.01 |
| `usage_impact_repartition` | 12.73 |

Combined:

- repartition attributes total: 223.17 MB
- share of full file: 60.03%
- embedded timeseries count: 2016
- `compressed_values` within that bucket: 221.07 MB

The explainability graph overhead inside these attributes is small:

- `fabrication_impact_repartition_weights`: 0.33 MB graph payload
- `usage_impact_repartition_weights`: 0.29 MB
- `usage_impact_repartition_weight_sum`: 0.19 MB
- `fabrication_impact_repartition_weight_sum`: 0.17 MB
- `fabrication_impact_repartition`: 0.19 MB
- `usage_impact_repartition`: 0.21 MB

So the repartition issue is specifically about duplicated timeseries values.

### 4. The repartition code materializes the same information several times

The current default logic in
[`modeling_object.py`](/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/abstract_modeling_classes/modeling_object.py#L710)
serializes three related layers for each phase:

1. `*_impact_repartition_weights`
2. `*_impact_repartition_weight_sum`
3. `*_impact_repartition`

This means the same hourly information is stored:

- once as per-child weights
- again as the summed weight series
- again as normalized attribution ratios

That is why the repartition logic has such a large multiplicative effect on file size.

---

## Largest Non-Repartition Precursors

The repartition logic is the main direct cause, but it is amplifying already-large upstream timeseries.

Largest precursor attributes:

| Attribute | Size (MB) |
| --- | ---: |
| `total_hourly_need_across_usage_patterns` | 24.43 |
| `cumulative_unitary_storage_need_per_usage_pattern` | 12.70 |
| `hourly_avg_occurrences_per_usage_pattern` | 10.91 |
| `hourly_data_transferred_per_usage_pattern` | 10.80 |
| `full_cumulative_storage_need_per_job` | 8.47 |
| `energy_footprint_per_job` | 7.92 |
| `job_repartition_weights` | 7.57 |
| `hourly_avg_occurrences_across_usage_patterns` | 7.49 |
| `hourly_data_transferred_across_usage_patterns` | 7.41 |
| `hourly_occurrences_per_usage_pattern` | 6.93 |

Combined precursor bucket measured for the main upstream timeseries:

- precursor attributes total: 139.86 MB
- share of full file: 37.62%
- embedded timeseries count: 1297
- `compressed_values` within that bucket: 138.32 MB

---

## Biggest Class / Attribute Hotspots

Largest class-attribute pairs:

| Class / attribute | Size (MB) |
| --- | ---: |
| `EdgeComputer.fabrication_impact_repartition_weights` | 18.57 |
| `RecurrentEdgeProcessStorageNeed.total_hourly_need_across_usage_patterns` | 11.43 |
| `RecurrentEdgeProcessStorageNeed.cumulative_unitary_storage_need_per_usage_pattern` | 10.52 |
| `Storage.full_cumulative_storage_need_per_job` | 8.47 |
| `Network.energy_footprint_per_job` | 7.92 |
| `VideoStreamingJob.hourly_avg_occurrences_per_usage_pattern` | 6.60 |
| `RecurrentEdgeProcess.fabrication_impact_repartition_weights` | 6.52 |
| `RecurrentServerNeed.fabrication_impact_repartition_weights` | 6.51 |
| `RecurrentEdgeProcessStorageNeed.fabrication_impact_repartition_weights` | 6.51 |
| `RecurrentEdgeProcessRAMNeed.fabrication_impact_repartition_weights` | 6.51 |
| `RecurrentEdgeProcessCPUNeed.fabrication_impact_repartition_weights` | 6.51 |
| `RecurrentEdgeProcessCPUNeed.total_hourly_need_across_usage_patterns` | 6.50 |
| `RecurrentEdgeProcess.usage_impact_repartition_weights` | 6.35 |
| `RecurrentServerNeed.usage_impact_repartition_weights` | 6.34 |
| `RecurrentEdgeProcessStorageNeed.usage_impact_repartition_weights` | 6.34 |
| `RecurrentEdgeProcessRAMNeed.usage_impact_repartition_weights` | 6.34 |
| `RecurrentEdgeProcessCPUNeed.usage_impact_repartition_weights` | 6.34 |
| `EdgeComputer.usage_impact_repartition_weights` | 6.19 |
| `EdgeComputer.fabrication_impact_repartition` | 5.35 |
| `Network.usage_impact_repartition` | 4.42 |

This confirms that the edge path is a major driver, but web/job/network repartition also contributes significantly.

---

## Biggest Classes By Total Serialized Size

| Class | Total size (MB) |
| --- | ---: |
| `RecurrentEdgeProcessStorageNeed` | 47.82 |
| `EdgeComputer` | 41.89 |
| `VideoStreamingJob` | 35.01 |
| `RecurrentEdgeProcessCPUNeed` | 32.35 |
| `RecurrentEdgeProcessRAMNeed` | 32.34 |
| `GPUJob` | 26.15 |
| `Job` | 26.14 |
| `RecurrentEdgeProcess` | 25.85 |
| `RecurrentServerNeed` | 25.83 |
| `Network` | 15.98 |
| `Server` | 12.90 |
| `Storage` | 12.36 |

---

## Interpretation

The recent repartition logic is the main direct source of the JSON explosion.

More precisely:

- the file is not heavy because of object graph metadata
- the file is not heavy because of scalar calculated attributes
- the file is heavy because the new repartition logic persists a large number of hourly dictionaries
- it also persists multiple derived layers of the same hourly information

The largest structural issue is that for many objects we serialize:

- the per-target weights
- the sum of those weights
- the normalized repartition values

When those values are hourly series, that multiplies storage cost very quickly.

---

## Conclusion

The suspicion was correct.

The main cause of the 371 MB file is the impact repartition logic recently introduced, especially:

- `*_impact_repartition_weights`
- `*_impact_repartition_weight_sum`
- `*_impact_repartition`

These attributes alone account for about 223 MB of the file. Most of the remaining weight comes from the upstream timeseries those repartition attributes depend on.

If the goal is to reduce saved JSON size substantially, the highest-leverage area is to stop serializing all repartition layers with full timeseries payload when they can be recomputed or derived from a smaller subset.
