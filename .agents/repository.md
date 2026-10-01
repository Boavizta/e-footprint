# Repository-specific workflow guidance — e-footprint

This file is local to this repository; the synchronization script never overwrites it.

- Architecture entry point: `specs/architecture/index.html`; read the index, then only the owning pages. The interface uses the same entry-point convention.
- Standards: `specs/constitution.md`, `specs/conventions.md`, `specs/testing.md`. These remain authoritative; the shared skills do not weaken their gates.
- Modeling truth lives here. Preserve units, explainability, dependency invalidation, transaction rollback, and serialization contracts. Do not add compatibility branches for hypothetical consumers.
- Validation: `MPLBACKEND=Agg poetry run pytest`; documentation changes affecting the published docs use `poetry run mkdocs build --strict` where configured. Apply the constitution's conditional round-trip, schema-migration, registry and changelog gates.
- FULL review surfaces: `efootprint/abstract_modeling_classes/`, `efootprint/api_utils/`, footprint/unit/attribution calculations, schema migrations, and changes to library/interface contracts. A path sets review depth, not automatically implementation difficulty.
- Cross-repository work: one working set in the driving repo, explicit file ownership, one baseline and commit range per affected repo. Interface validation uses the edited library via an editable dependency; preserve existing local dependency edits and restore a publishable dependency deliberately before merge, never by discarding someone else's changes.
- Documentation promotion: owning pages under `specs/architecture/`, conventions, testing and published documentation. Keep `CHANGELOG.md` and the roadmap accurate.

Workflow/tooling instructions and commands: `specs/agent-tooling.md`.
