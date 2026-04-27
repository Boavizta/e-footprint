# Roadmap — e-footprint

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/` (when the feature exists in this repo) or under cross-repo specs in `e-footprint-interface/specs/features/` (when the workstream is interface-led).

## Active streams

### Tutorial-and-documentation overhaul (cross-repo, in flight)

The interface holds the primary spec at `../../e-footprint-interface/specs/features/tutorial-and-documentation/`. Library-side deliverables drive several library workstreams below.

Status: Step 1 (disabled-instead-of-error UX) shipped on the interface side. Library CI workflow is the next library-side deliverable.

### Library CI workflow (planned, near-term)

- `.github/workflows/ci.yml` running pytest on every push (Python 3.12).
- Add `mkdocs build --strict` once SSOT content is written.
- Source: tutorial-and-documentation Step 1 + Step 4.

### SSOT metadata in classes (planned, near-term)

- `param_descriptions` dict, class docstrings, `update_<attr>` docstrings on every concrete class.
- `tests/test_descriptions.py` enforcing completeness.
- `generate_object_reference.py` upgraded to consume the new metadata.
- Source: tutorial-and-documentation Step 2.
- Enforced by constitution §1.4 (doc-as-code SSOT).

### Modeling templates public API (planned, mid-term)

- `efootprint.modeling_templates` package shipped with PyPI release.
- `how_to/` sub-package with serialized scenarios + Python registry.
- Public API: `list_how_to_templates()`, `get_template()`.
- Source: tutorial-and-documentation Step 4.

## Mid-term horizon

### Boavizta API expansion

Currently used for server fabrication (`BoaviztaCloudServer`). Planned expansion to **water (WUE)** and **rare-earth metals**. Will require new modeling primitives to carry multi-impact footprints alongside CO₂-eq.

## Far horizon (no commitment)

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
