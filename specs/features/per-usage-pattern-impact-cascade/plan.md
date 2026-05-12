# Per-UsagePattern impact cascade — Implementation plan

**Status:** Plan — under review.
**Date:** 2026-05-13.
**Type:** Bug fix with attribution refactor (no separate `spec.md` — problem and success criteria are folded into §0 below).

## 0. Problem and success criteria

### Bug

When a system has multiple `UsagePattern`s in different countries that share the same `UsageJourney`, the
`UsageJourney -> UsagePattern` usage attribution can produce wrong country totals.

Root cause: `UsageJourney.update_dict_element_in_usage_impact_repartition_weights`
(`efootprint/core/usage/usage_journey.py`) builds a single scalar weight per `UsagePattern` by multiplying
usage volume by `usage_pattern.country.average_carbon_intensity`. That scalar is then applied to the whole
`UsageJourney.attributed_energy_footprint`, even though the journey can contain mixed usage-impact families:

- user-country-dependent sources (`Device`, `Network`) whose footprint already varies by `UsagePattern` country;
- non-user-country-dependent sources (`Server`, cloud/server-side storage, `EcoLogitsGenAIExternalAPI`) whose
  footprint should usually split by request/activity volume, not by the end-user country's grid intensity.

A single generic volumetric-carbon weight is therefore not a correct aggregate rule for a shared
`UsageJourney`.

The same pattern exists in `EdgeUsageJourney.update_dict_element_in_usage_impact_repartition_weights`, where
edge-device impacts are user-country-dependent but recurrent server/API work is not.

### Success criteria

1. `UsagePattern.attributed_energy_footprint` is correct for a shared `UsageJourney` spanning countries with
   different grid intensities: server-side usage impact splits by activity volume, while `Device` and `Network`
   usage impact keeps the user-country grid-intensity dependence.
2. `EdgeUsagePattern.attributed_energy_footprint` follows the analogous rule: edge-device/component usage impact
   keeps edge-country dependence, while recurrent server-side usage impact splits by activity volume.
3. `total_footprint` of every existing test system is unchanged within numerical noise; this is a redistribution
   fix, not a magnitude change.
4. The first implementation step fixes aggregate attributed totals without changing the public attribution API or
   the Sankey renderer's skipped/excluded traversal.
5. The second implementation step moves skipped/excluded attribution resolution out of the Sankey traversal and
   into `ModelingObject` parametrized attribution methods, so skipped nodes preserve parent-context attribution
   instead of being unfolded from their global child/source mix.
6. Sankey flows with skipped or excluded columns remain numerically consistent with the corrected aggregate
   attribution, including the common case where `UsageJourney` or `EdgeUsageJourney` is hidden from the rendered
   diagram.

## 1. Approach

The fix is deliberately split into two layers.

### Task 1: corrected aggregate `UsageJourney -> UsagePattern` usage repartition

Treat `UsageJourney -> UsagePattern` usage attribution as a domain-specific aggregate edge, not as a generic
weight-normalization edge. `UsageJourney.usage_impact_repartition` should be computed from the correct total
usage impact for each `UsagePattern`, then normalized by the sum of those totals.

The corrected per-UP total is source-family-aware:

- `Device`: use the device's existing `energy_footprint_per_usage_pattern[up]` for devices attached to the UP.
- `Network`: use or add `energy_footprint_per_usage_pattern[up]`, derived from the jobs/data transfer routed by
  that UP and the UP country grid intensity.
- Server-side hardware, storage, services, and external APIs: use neutral activity-volume attribution to the UP.
  Do not invent final per-UP source footprints on server/storage classes; they do not own the downstream
  `Job -> UsageJourneyStep -> UsageJourney -> UsagePattern` chain.

The implementation can bypass `usage_impact_repartition_weights` and `usage_impact_repartition_weight_sum` for
`UsageJourney` usage attribution if that keeps the formula clearer. Fabrication attribution stays on the existing
activity-volume rule.

`EdgeUsageJourney` gets the same aggregate correction for edge usage:

- edge devices/components keep their existing edge-country-dependent usage footprint;
- recurrent server/API work is attributed by neutral edge activity volume.

This task intentionally targets aggregate attributed totals. It does not try to make Sankey skipped-column
unfolding correct by itself.

### Task 2: model-owned resolved attribution for skipped/excluded rendering

Move skipped/excluded attribution semantics into `ModelingObject` instead of keeping them embedded in
`ImpactRepartitionSankey`.

Today Sankey recursively traverses `attributed_footprint_per_source`, rescales child flows, and has custom logic
for skipped/excluded objects. That duplicates attribution semantics outside the model layer and can be wrong in a
generic way: when an object is reached through a specific parent/context, its local child/source mix may differ
from its global attributed mix. Skipping that object by multiplying the current parent flow by the object's global
child proportions loses the repartition information carried by the skipped column.

The `UsageJourney` case from Task 1 is one concrete failure mode: a skipped `UsageJourney` below one
`UsagePattern` must unfold according to that UP's corrected attribution, not according to global journey
proportions. The same issue can appear anywhere a skipped object has multiple parents or context-dependent
incoming flows.

Add parametrized attribution methods on `ModelingObject`, for example:

```python
attributed_energy_footprint_per_source_resolved(
    skipped_object_types=(),
    excluded_object_types=(),
)

attributed_fabrication_footprint_per_source_resolved(
    skipped_object_types=(),
    excluded_object_types=(),
)
```

The exact names can follow local style, but the contract should be:

- default arguments reproduce today's `attributed_*_footprint_per_source` values;
- skipped object types are traversed through, preserving the attribution context of the current parent flow rather
  than re-normalizing the skipped object's global source mix;
- excluded object types are removed while preserving attribution to remaining descendants where possible;
- `UsagePattern` / `EdgeUsagePattern` resolution through a skipped `UsageJourney` / `EdgeUsageJourney` uses the
  corrected aggregate attribution from Task 1.

Then simplify `ImpactRepartitionSankey` so it asks model objects for resolved attribution and focuses on layout,
labels, colors, thresholds, and Plotly graph construction.

## 2. Affected modules

| Module / file | Change type | Note |
|---|---|---|
| `efootprint/core/usage/usage_journey.py` | modified | Compute `usage_impact_repartition` directly from corrected per-UP aggregate usage totals. Keep fabrication on the existing activity-volume rule. |
| `efootprint/core/usage/edge/edge_usage_journey.py` | modified | Apply the analogous corrected aggregate usage repartition for `EdgeUsagePattern`. |
| `efootprint/core/hardware/network.py` | possibly modified | Add or verify `energy_footprint_per_usage_pattern`, because network usage is inherently user-country-dependent and is needed by Task 1's aggregate formula. |
| `efootprint/builders/external_apis/ecologits/ecologits_external_api.py` | possibly modified | Add a small activity-volume helper if Task 1 needs explicit API-side per-UP usage volume for aggregate attribution. Do not introduce a mandatory per-UP leaf contract. |
| `efootprint/abstract_modeling_classes/modeling_object.py` | modified in Task 2 | Add resolved/parametrized attribution methods for skipped and excluded object types. Existing cached properties remain as default wrappers or default behavior. |
| `efootprint/utils/impact_repartition/sankey.py` | modified in Task 2 | Stop owning attribution traversal semantics. Consume model-resolved attribution and keep rendering responsibilities. |
| `efootprint/utils/impact_repartition/_graph.py` | possibly modified | Only layout/graph storage changes if Sankey data shape changes. |
| `specs/architecture.md` | updated in Task 2 | Document corrected aggregate UJ/EUJ attribution and the new model-owned resolved attribution API. |
| `specs/conventions.md` | updated in Task 2 | Add a short convention that attribution semantics belong in `ModelingObject` / domain objects, not in renderers. |

## 3. Tests

- Unit tests for `UsageJourney.usage_impact_repartition` with two countries sharing one UJ:
  - equal request/device volumes but different country carbon intensities;
  - server-side contribution splits evenly by activity;
  - device/network contribution keeps country-intensity dependence;
  - `UsagePattern.attributed_energy_footprint` matches a hand-computed total.
- Unit or integration tests for `EdgeUsageJourney` with one edge-device contribution and one recurrent server/API
  contribution, asserting the analogous corrected `EdgeUsagePattern.attributed_energy_footprint`.
- Regression tests that `System.total_footprint` and source aggregate footprints are unchanged.
- Task 2 tests for the new resolved attribution API:
  - default resolved attribution equals existing `attributed_*_footprint_per_source`;
  - skipping a simple intermediate object returns the same aggregate total but exposes the next descendants;
  - skipping `UsageJourney` after Task 1 preserves corrected per-UP totals;
  - excluding an object removes it without renderer-specific traversal code.
- Sankey tests should assert that rendered link values match the resolved model attribution API rather than
  independently recomputing attribution in the renderer.

## 4. Risks

- **Risk: source-family hardcoding in `UsageJourney` becomes opaque.** Mitigation: keep the domain rule local,
  explicit, and tested with hand-computed totals. The specificity belongs at the aggregate UP attribution boundary.
- **Risk: Task 1 fixes totals but not skipped-column explanations.** Mitigation: state that explicitly and follow
  with Task 2, which fixes the generic parent-context loss in skipped/excluded attribution resolution.
- **Risk: `ModelingObject` resolved attribution becomes too generic.** Mitigation: start with the concrete
  Sankey needs (`skipped_object_types`, `excluded_object_types`) and preserve today's default properties as the
  simple API.
- **Risk: framework/core dependency direction.** `abstract_modeling_classes/modeling_object.py` already has a
  documented back-edge to core. Do not add broad new imports there; prefer local type checks by configured classes
  passed in from callers, or small overridable hooks on core objects.

## 5. Alternatives considered

- **Remove `country.average_carbon_intensity` from `UsageJourney` weights.** Rejected: fixes server-side usage
  impact but breaks device/network aggregate attribution.
- **Make every impact source expose final per-UP footprints.** Rejected: forces server/storage classes to know or
  duplicate downstream `Job -> UsageJourneyStep -> UsageJourney -> UsagePattern` attribution logic.
- **Change the whole cascade to carry per-UP dicts everywhere.** Rejected for now: larger than needed for the
  aggregate bug and risks moving domain logic away from the objects that own it.
- **Keep skipped/excluded Sankey traversal in the renderer.** Rejected for Task 2: skipped/excluded attribution is
  model semantics. The current renderer approach can unfold skipped nodes from global child proportions, which is
  not generally equivalent to preserving the current parent flow's attribution context.

## 6. Constitutional notes

No constitutional change is required. The plan preserves the existing layer responsibilities more cleanly than the
previous leaf-contract design: domain objects own domain-specific attribution, `ModelingObject` owns generic
resolved attribution, and Sankey rendering owns only visualization concerns.
