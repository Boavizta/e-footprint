# Roadmap — e-footprint

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/` (when the feature exists in this repo) or under cross-repo specs in `e-footprint-interface/specs/features/` (when the workstream is interface-led).

For **modeling-method questions** — where modeling something *well* needs scientific grounding we don't yet have, so we ship an honest fallback and avoid false precision — see [`modeling_logic_roadmap.md`](modeling_logic_roadmap.md). (First entry: database query resource & energy cost.)

## Active streams

None currently — the tutorial-and-documentation overhaul (cross-repo), SSOT metadata in classes, and the modeling templates public API all shipped and were archived. See `git log` for the shipped commits and the "Not yet wired" note below for one loose end.

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

Currently used for server fabrication (`BoaviztaCloudServer`). Planned expansion to **water (WUE)** and **rare-earth metals**. Will require new modeling primitives to carry multi-impact footprints alongside CO₂-eq.

### Lean base install — optional heavy dependencies (memory optimization)

Driven by the interface's binding Redis-RAM constraint. Move dependencies the interface doesn't need at runtime into optional extras so `pip install efootprint` is lighter and lower-RAM:

- **Visualization** (`matplotlib`, `plotly`, `pyvis`) — the interface renders its own JS charts; these are only needed for notebook/library `.plot()` / Sankey / pyvis use. Gate their imports and ship an `efootprint[viz]` extra. Tension to weigh: the library-first / notebook-usable principle (notebook users would then need `efootprint[viz]`).
- **pandas** — audit how deeply it is used in the core path first; making it optional touches **constitution §4** (Pint/NumPy/Pandas protected) and needs a constitutional note. NumPy stays required (timeseries are `float32` arrays).

Prerequisites: measure the actual RAM win before committing; introduce the optional-extras mechanism in `pyproject.toml`. **Not** the compression codec — a benchmark (2026-06-30) showed `zstandard` is fast and RAM-cheap (≈0 MB to import), so it stays required. Origin: EcoScan feedback packaging discussion + interface memory work.

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

- Core modeling primitives (`Server`, `Storage`, `Network`, `UsageJourney`, `Job`, `EdgeDevice`, etc.).
- JSON serialization layer.
- Explainability / dependency graph layer.

## Out of scope until re-litigated

- Multi-language documentation (constitution §4).
- Alternative serialization formats (constitution §4).
- Backward compatibility for external consumers other than e-footprint-interface (constitution §1.2).
