# Per-UsagePattern impact cascade — Tasks

**Status:** Tasks — under review.
**Spec:** folded into [`plan.md`](plan.md) §0 (no separate `spec.md` for this bug fix). **Plan:**
[`plan.md`](plan.md).

## Task 1 — Correct aggregate UJ/EUJ usage attribution totals

**Goal:** Fix `UsagePattern.attributed_energy_footprint` and `EdgeUsagePattern.attributed_energy_footprint` for
shared journeys across countries by making the `UsageJourney -> UsagePattern` and
`EdgeUsageJourney -> EdgeUsagePattern` usage attribution aggregate-aware. This task fixes totals only; Sankey
skipped/excluded unfolding remains on the existing renderer logic until Task 2.

**Implementation direction:**
- In `efootprint/core/usage/usage_journey.py`, override or bypass the generic
  `usage_impact_repartition_weights -> usage_impact_repartition_weight_sum -> usage_impact_repartition` path for
  usage attribution.
- Compute each UP's corrected aggregate usage total explicitly:
  - `Device` contribution uses existing device per-UP energy footprints.
  - `Network` contribution uses per-UP network energy footprint; add `Network.energy_footprint_per_usage_pattern`
    if absent.
  - Server-side hardware, storage/service overhead, and external API usage contributions split by neutral activity
    volume, not by user-country carbon intensity.
- Normalize corrected per-UP totals into `usage_impact_repartition[usage_pattern]`.
- Preserve fabrication attribution behavior.
- Apply the analogous correction in `efootprint/core/usage/edge/edge_usage_journey.py`:
  - edge device/component usage keeps edge-country dependence;
  - recurrent server/API work splits by neutral edge activity volume.
- Do not add a mandatory `*_per_usage_pattern` leaf contract for every impact source.
- Do not make `Server` or `Storage` walk downstream usage objects to synthesize final per-UP footprints.

**Tests added/changed:**
- Add an integration test with two or three countries, one shared `UsageJourney`, one server-side source, and one
  device/network source. Assert hand-computed `UsagePattern.attributed_energy_footprint` totals.
- Add the analogous edge test with one edge-device contribution and one recurrent server/API contribution.
- Assert `System.total_footprint` is unchanged for the scenario before and after redistribution.
- Keep existing golden totals unchanged except for expected attributed-per-UP redistribution assertions.

**Acceptance:**
- Shared-journey `UsagePattern.attributed_energy_footprint` totals are correct.
- Shared-edge-journey `EdgeUsagePattern.attributed_energy_footprint` totals are correct.
- No server/storage final per-UP footprint contract is introduced.
- Existing tests pass, except tests that intentionally asserted the previous buggy per-UP attribution.

**Depends on:** none.

**Status:** Not started.

---

## Task 2 — Move skipped/excluded attribution resolution into ModelingObject

**Goal:** Make skipped/excluded attribution a model-layer capability instead of renderer-specific traversal logic.
`ImpactRepartitionSankey` should consume resolved attribution from `ModelingObject` and focus on rendering.
This fixes the generic skipped-column issue where unfolding a skipped object from its global child/source mix can
lose the attribution context carried by the specific parent flow currently being rendered.

**Implementation direction:**
- In `efootprint/abstract_modeling_classes/modeling_object.py`, add parametrized attribution methods for both
  phases, such as:
  - `attributed_energy_footprint_per_source_resolved(skipped_object_types=(), excluded_object_types=())`
  - `attributed_fabrication_footprint_per_source_resolved(skipped_object_types=(), excluded_object_types=())`
- Preserve current properties as default/no-argument behavior.
- Ensure skipping an object traverses through it using model attribution semantics for the current parent flow,
  not the skipped object's global renderer proportions.
- Ensure excluding an object removes it while preserving remaining attributable descendant flows where possible.
- Ensure skipped `UsageJourney` / `EdgeUsageJourney` rendering after Task 1 uses corrected aggregate attribution,
  not global child proportions. Treat this as one regression case for the generic skipped-column bug, not as the
  only special case.
- Refactor `efootprint/utils/impact_repartition/sankey.py` to call the resolved attribution API instead of owning
  recursive attribution semantics itself.
- Keep Sankey layout concerns in the Sankey module: labels, colors, columns, aggregation thresholds, category
  nodes, and Plotly graph assembly.
- Update `specs/architecture.md` to describe the corrected aggregate UJ/EUJ rule and model-owned resolved
  attribution.
- Update `specs/conventions.md` with the convention that attribution semantics belong in model/domain objects,
  not renderers.

**Tests added/changed:**
- Unit tests for resolved attribution default behavior matching existing `attributed_*_footprint_per_source`.
- Unit tests for skipping a simple intermediate object while preserving total attributed footprint.
- Unit tests where one skipped object is reached through two parents with different descendant mixes; each
  parent-to-descendant flow must preserve its own context instead of using the skipped object's global mix.
- Tests for skipping `UsageJourney` / `EdgeUsageJourney` in a country-shared setup, asserting corrected per-UP
  link values.
- Tests for excluded object types that currently exercise Sankey traversal, moved or mirrored at the
  `ModelingObject` API level.
- Update Sankey tests to assert renderer output matches model-resolved attribution.

**Acceptance:**
- Sankey no longer implements independent attribution traversal for skipped/excluded objects.
- Skipped/excluded Sankey flows preserve parent-context attribution and are numerically consistent with Task 1
  corrected aggregate attribution.
- Existing public no-argument attribution properties keep today's behavior.
- Specs document the new responsibility boundary.

**Depends on:** Task 1.

**Status:** Not started.

---

## Ordering rationale

Task 1 is the smallest correctness fix: it addresses the wrong aggregate per-UP usage totals where the bug lives,
without changing the broad attribution API or Sankey renderer.

Task 2 then fixes explanation/rendering architecture. Skipped or excluded Sankey columns need to unfold according
to model attribution semantics for the current parent flow, not according to the skipped object's global child
mix. Moving that logic into `ModelingObject` avoids a second attribution engine in the renderer and gives the
behavior direct tests outside Plotly/Sankey concerns.
