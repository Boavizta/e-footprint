# Phase-Specific Impact Repartition Refactor Plan

## Goal

Split the current single `impact_repartition` mechanism into two parallel mechanisms:

- `fabrication_impact_repartition`
- `usage_impact_repartition`

This allows classes such as `Device` and `EdgeDevice` to use different attribution logic for fabrication and usage,
while keeping both repartitions equal by default for the rest of the model.


## Design Constraints

- No JSON migration is needed because repartition fields are calculated attributes, not persisted input fields.
- Existing behavior should stay unchanged by default for classes that do not override phase-specific logic.
- Sankey and other downstream consumers should keep using:
  - `attributed_fabrication_footprint_per_source`
  - `attributed_energy_footprint_per_source`
- The recent Sankey DAG traversal fix remains valid and should not be reverted.
- For classes overriding `calculated_attributes`, prefer relying on `super().calculated_attributes` as much as
  possible instead of hardcoding `ModelingObject`-managed attribute names. The refactor should reduce duplication and
  make subclasses robust to future base-class changes.


## Target Data Model

For each `ModelingObject`, replace the current single trio:

- `impact_repartition_weights`
- `impact_repartition_weight_sum`
- `impact_repartition`

with two parallel trios:

- `fabrication_impact_repartition_weights`
- `fabrication_impact_repartition_weight_sum`
- `fabrication_impact_repartition`

- `usage_impact_repartition_weights`
- `usage_impact_repartition_weight_sum`
- `usage_impact_repartition`


## Patch Steps

### 1. Refactor `ModelingObject` base repartition infrastructure

File:

- `efootprint/abstract_modeling_classes/modeling_object.py`

Changes:

- Replace `_impact_repartition_cached_property_names` with phase-specific cached names:
  - `attributed_fabrication_footprint_per_source`
  - `attributed_fabrication_footprint`
  - `attributed_energy_footprint_per_source`
  - `attributed_energy_footprint`
- Update the initialization/reset logic so the 6 new repartition attributes are created where appropriate.
- Replace the current generic methods:
  - `update_dict_element_in_impact_repartition_weights`
  - `update_impact_repartition_weights`
  - `update_impact_repartition_weight_sum`
  - `update_dict_element_in_impact_repartition`
  - `update_impact_repartition`
- Introduce phase-specific versions:
  - `update_dict_element_in_fabrication_impact_repartition_weights`
  - `update_fabrication_impact_repartition_weights`
  - `update_fabrication_impact_repartition_weight_sum`
  - `update_dict_element_in_fabrication_impact_repartition`
  - `update_fabrication_impact_repartition`
  - `update_dict_element_in_usage_impact_repartition_weights`
  - `update_usage_impact_repartition_weights`
  - `update_usage_impact_repartition_weight_sum`
  - `update_dict_element_in_usage_impact_repartition`
  - `update_usage_impact_repartition`
- Keep default implementations of the fabrication and usage weight builders identical to the current generic logic:
  - sum child/container weights
  - multiply by `nb_of_occurrences_per_container`
- Update cache invalidation so both phase-specific repartition dicts invalidate downstream attribution caches.
- Update `attributed_fabrication_footprint_per_source` to read from `fabrication_impact_repartition`.
- Update `attributed_energy_footprint_per_source` to read from `usage_impact_repartition`.

Implementation note:

- Keep method bodies small by extracting shared logic into private helpers if needed, but preserve the external method
  names above because subclasses will override them.


### 2. Update calculated attribute declarations across the model

Files to inspect and patch:

- `efootprint/abstract_modeling_classes/modeling_object.py`
- classes overriding `calculated_attributes`, notably:
  - `efootprint/core/hardware/storage.py`
  - `efootprint/core/hardware/server_base.py`
  - `efootprint/builders/external_apis/ecologits/ecologits_external_api.py`
  - any other class that currently lists `impact_repartition_weights`, `impact_repartition_weight_sum`,
    or `impact_repartition`

Changes:

- Replace the old single repartition attribute names with the 6 new phase-specific names.
- Remove all references to the old generic names from `calculated_attributes`.
- Ensure dependency ordering still makes sense:
  - weights before sums
  - sums before repartition dicts
  - repartition dicts before attributed footprint cached-property consumers
- Prefer implementations of the form:
  - subclass-specific attributes
  - `+ super().calculated_attributes`
- Only hardcode base-class-managed repartition attribute names in subclasses when there is no practical alternative.


### 3. Update all classes that currently override repartition methods

Files to inspect and patch:

- `efootprint/core/country.py`
- `efootprint/core/usage/usage_pattern.py`
- `efootprint/core/usage/edge/edge_usage_pattern.py`
- `efootprint/core/usage/usage_journey.py`
- `efootprint/core/usage/edge/edge_usage_journey.py`
- `efootprint/core/hardware/device.py`
- `efootprint/core/hardware/network.py`
- `efootprint/core/hardware/server_base.py`
- `efootprint/core/hardware/edge/edge_device.py`
- `efootprint/builders/external_apis/external_api_base_class.py`
- `efootprint/builders/external_apis/ecologits/ecologits_external_api.py`

Changes:

- Rename existing overrides to the appropriate phase-specific method(s).
- For classes where fabrication and usage logic should remain identical, implement one method body and call it from
  both phase-specific methods.

Expected class behavior:

- `Country`, `UsagePattern`, `EdgeUsagePattern`, `UsageJourney`, `EdgeUsageJourney`, `Network`, `ServerBase`,
  `ExternalAPI`, `EcoLogits`:
  - fabrication and usage repartitions remain equal for now
- `Device`:
  - fabrication repartition should remain activity/time-based
  - usage repartition should become carbon-intensity-aware
- `EdgeDevice`:
  - fabrication repartition should remain based on fabrication impact and component-need allocation
  - usage repartition should become carbon-intensity-aware


### 4. Implement `Device` phase-specific logic

File:

- `efootprint/core/hardware/device.py`

Fabrication repartition:

- Keep current logic shape:
  - step weight based on `user_time_spent`
  - usage-pattern starts
  - step occurrences within the usage journey

Usage repartition:

- Build weights from actual per-usage-pattern device usage impact, not just raw activity.
- For each `UsagePattern` used by the device:
  - compute that pattern's device energy footprint contribution with its country carbon intensity
  - distribute that pattern contribution across `UsageJourneyStep`s by time share within the journey
- Recommended helper structure:
  - private helper to compute a step share within one usage pattern
  - `update_dict_element_in_usage_impact_repartition_weights`

Formula target:

- `pattern_energy_impact = nb_parallel_journeys_for_pattern * power * 1 hour * country_carbon_intensity`
- `step_share = step.user_time_spent * step_occurrences_in_journey / total_usage_journey_duration`
- `step_usage_weight += pattern_energy_impact * step_share`

Reason:

- two countries with equal activity but different electricity carbon intensity must no longer get equal usage shares.


### 5. Implement `EdgeDevice` phase-specific logic

File:

- `efootprint/core/hardware/edge/edge_device.py`

Fabrication repartition:

- Keep the current allocation principle:
  - component fabrication impact
  - allocated across sibling recurrent needs for the same component by demand share

Usage repartition:

- Use component energy footprint per usage pattern instead of total all-pattern impact.
- For each `RecurrentEdgeComponentNeed`:
  - iterate over its `edge_usage_patterns`
  - for each pattern, compute this need's share of sibling demand for the same component in that pattern
  - allocate that pattern's component energy footprint accordingly
- Sum across all usage patterns

Needed helper behavior:

- derive per-pattern demand for one recurrent component need from `unitary_hourly_need_per_usage_pattern`
- derive sibling per-pattern demand for all recurrent needs attached to the same component
- use `component.energy_footprint_per_usage_pattern[usage_pattern]` as the usage impact source

Formula target:

- `need_usage_weight += component_energy_impact_for_pattern * need_pattern_demand / sibling_pattern_demand`

Reason:

- usage-country attribution must change when electricity carbon intensity changes, because component energy impact per
  usage pattern already includes the country's carbon intensity upstream.


### 6. Remove or bridge old generic repartition names

Files:

- all touched files

Decision for implementation:

- Prefer a full rename and remove the old generic names from production code rather than keeping long-term aliases.
- Temporary compatibility properties are acceptable only during the refactor if they reduce breakage while tests are
  updated in the same patch.
- Final state should not leave ambiguous dual APIs in place.


## Test Plan

### A. Base modeling behavior

File:

- `tests/abstract_modeling_classes/test_modeling_object.py`

Add/update tests to cover:

- fabrication and usage repartition weights are both initialized and updated
- default base behavior keeps fabrication and usage repartitions equal when not overridden
- attribution reads from the correct repartition dict per phase
- cache invalidation works for both phase-specific repartitions


### B. `Device`

File:

- `tests/hardware/test_device.py`

Keep existing tests, but rename their assertions to the new attribute names.

Add:

- one test proving fabrication and usage repartition methods can diverge
- one test with two usage patterns with equal activity and different carbon intensity
  - fabrication weights should remain equal if activity is equal
  - usage weights should differ according to carbon intensity


### C. `EdgeDevice`

File:

- `tests/hardware/edge/test_edge_device.py`

Keep current fabrication-style allocation test, moved to fabrication repartition naming.

Add:

- one test with two edge usage patterns with identical demand and different carbon intensity
- confirm fabrication weights stay demand-based
- confirm usage weights change with carbon intensity via `energy_footprint_per_usage_pattern`


### D. Other repartition override classes

Files to update as needed:

- `tests/hardware/test_network.py`
- `tests/hardware/test_server.py`
- `tests/builders/external_apis/ecologits/test_ecologits_generative_ai.py`
- `tests/usage/test_usage_journey.py`
- `tests/usage/edge/test_edge_usage_journey.py`

Goal:

- adapt tests to the renamed phase-specific APIs
- preserve old expectations where fabrication and usage repartitions should remain equal


### E. Sankey regression safety

File:

- `tests/test_impact_repartition_sankey.py`

Goal:

- ensure Sankey still builds from phase-specific attributed footprints without behavior regressions
- keep the shared-DAG conservation regression test added during the current debugging session


## Execution Order

1. Refactor `ModelingObject` infrastructure and attributed footprint readers.
2. Update calculated attribute declarations and override method names repo-wide.
3. Make all non-specialized classes compile and pass with equal fabrication/usage repartitions.
4. Implement `Device` specialized usage repartition.
5. Implement `EdgeDevice` specialized usage repartition.
6. Update and run focused unit tests.
7. Run Sankey tests and a smart-building manual repro to verify:
   - usage split differs between France and US where expected
   - no conservation regression in Sankey


## Suggested Verification Commands

Run after implementation:

```bash
pytest tests/abstract_modeling_classes/test_modeling_object.py
pytest tests/hardware/test_device.py
pytest tests/hardware/edge/test_edge_device.py
pytest tests/hardware/test_network.py
pytest tests/hardware/test_server.py
pytest tests/test_impact_repartition_sankey.py
```

Optional manual repro:

```bash
python efootprint/utils/impact_repartition/sankey.py
```


## Expected Outcome

- The model supports separate fabrication and usage repartitions.
- Existing classes keep identical repartitions by default unless explicitly specialized.
- `Device` and `EdgeDevice` usage attribution becomes carbon-intensity-aware.
- The Sankey uses the corrected phase-specific attribution without conservation regressions.
