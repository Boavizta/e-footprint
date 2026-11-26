# Roadmap — e-footprint

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/` (when the feature exists in this repo) or under cross-repo specs in `e-footprint-interface/specs/features/` (when the workstream is interface-led).

For **modeling-method questions** — where modeling something *well* needs scientific grounding we don't yet have, so we ship an honest fallback and avoid false precision — see [`modeling_logic_roadmap.md`](modeling_logic_roadmap.md). (First entry: database query resource & energy cost.)

## Active streams

### Comprehension harness — installed, one flow narrated

The spec-driven workflow moved to plans written into the code as pieces and delivered in lots
([`workflow.md`](workflow.md)), as in the interface. The tools, the stage skills and the roles
are installed ([`comprehension_harness/README.md`](../comprehension_harness/README.md)), with the
Python stack they read (`.agents/repository.md` § "The stack"). One flow is narrated, the edit of
a live model: `tests/narratives/test_model_edit.py` tells the update transaction, from the
assignment to the guards. Next: the first feature planned in pieces, and the other flows narrated
as they are touched. The first read of a computed value sits in the reactive core's per-slot
code: its narrative waits for a measure against the performance baselines. A feature in flight on
`plan.html` and `tasks.md` (`edge-networks`, `workflow-improvements`) is finished by hand.

### Executable modeling documentation — plan drafted, awaiting review

[`features/executable-modeling-documentation/`](features/executable-modeling-documentation/spec.md):
one Jupytext Python source per scenario produces its notebook, documentation, packaged model and
reusable content for agents. E-commerce and Industrial IoT become independent web and edge
tutorials; focused guides reuse those sources. Absorbs the former edge-example feature, including
the IoT device group and interface starter handoff. Changes both repositories; the spec and library
plan are here. The interface companion plan must be authored in its own checkout before the
shared-starter handoff is delivered.

### Agent guidance — on hold for executable modeling documentation

[`features/agent-guidance/`](features/agent-guidance/spec.md): a short guide for coding agents ships
in the package, and `python -m efootprint.agent_guide` prints it, a class's reference, a how-to
topic or the list of examples. The how-to pages move into the package, the earlier web-chat prompt
and kit leave the repository, and the defects three trial runs met are fixed. Library-only.
Resume only after executable modeling documentation is delivered and reviewed, following
[`resume.md`](features/agent-guidance/resume.md): revise the spec, plan, source annotations and
preview to consume its canonical examples before seeking approval again.

### Not yet wired: `mkdocs build --strict` in CI

SSOT metadata content (`param_descriptions`, docstrings, `tests/test_descriptions.py`) shipped, and `mkdocs build --strict` runs clean locally (verified 2026-07-01) — but the follow-up step, wiring it into `.github/workflows/ci.yml`, was never done. Just add the step; no doc fixes needed first.

## Mid-term horizon

### Upgrade-time drift visualization

Builds on the shipped pull-based-computation serialization contract (stored footprints are
trusted caches only on exact `efootprint_version` match; any
mismatch demotes them to a retained "as computed by vX" baseline and recomputes on pull, with a
`system_comparison`-based hook returning the drift). This feature adds the user-facing layer:
visualize how a library methodology change or upstream-data update (Boaviztapi, EcoLogits) shifted
a saved model's footprints at upgrade time — notebook output first, interface view later. The
in-memory baseline is session-scoped and never serialized; if this feature needs the comparison to
survive past the upgrade session (e.g. interface toast shown later), persist the condensed drift
summary (~kB of per-source deltas), not old timeseries. Goal: trust through transparency of
calculus-methodology evolution. Decided 2026-07-02 during pull-based-computation tasks review.

### Boavizta API expansion

Currently used for server manufacturing (`BoaviztaCloudServer`). Planned expansion to **water (WUE)** and **rare-earth metals**. Will require new modeling primitives to carry multi-impact footprints alongside CO2-eq.

## Far horizon (no commitment)

- **SystemTimeline — modeling systems that evolve across time.** Append-only ledger of dated,
  statused change entries over a base system; piecewise evaluation into a version series;
  settlement frontier between observed and forecast usage; what-if simulation reintroduced as
  timeline branches (replacing the deleted `simulation_date` in a more flexible form). Design
  record: [`explorations/system_timeline.html`](../explorations/system_timeline.html)
  (2026-07). Converges with `System.fork()` (calibration fit loops want the same primitive) and
  the pull engine; composes with upgrade-time drift visualization for change attribution.
  Incubate through calibration missions before any spec.
- Transportation and end-of-life lifecycle phases. Currently considered negligible; reopen if Boavizta data appears.
- Other non-CO₂ environmental impacts beyond water and rare earth.

## Stable / not in flight

- The [Astra/Sol shadow-review experiment](features/workflow-improvements/shadow-review.md) ended early by user decision; Codex task and global reviews use GPT-6.1 Sol/high.
- Core modeling primitives (`Server`, `Storage`, `Network`, `UsageJourney`, `Job`, `EdgeDevice`, etc.).
- JSON serialization layer.
- Explainability / dependency graph layer.

## Out of scope until re-litigated

- Multi-language documentation (constitution §4).
- Alternative serialization formats (constitution §4).
- Backward compatibility for external consumers other than e-footprint-interface (constitution §1.2).
