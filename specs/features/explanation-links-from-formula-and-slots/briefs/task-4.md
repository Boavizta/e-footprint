# Task 4 — Interface adopts library 27
Written 2026-10-19 against e-footprint-interface a12771fe.
Plan: [1.5](../plan.html#interface), [PLAN-UPDATE-01](../plan.html#plan-update-01). Task: [tasks.md](../tasks.md#task-4--interface-adopts-library-27).
Status: under review.

## Start here
- `pyproject.toml` — the `efootprint = "26.0.0"` line, with the commented local-dev line above it.
- `specs/architecture/rendering.html` — the "Input-only source inventory" list item.
- `CHANGELOG.md` — the existing `## [Unreleased]` section.
- Unchanged readers: `compute_literal_formula_and_ancestors_mapped_to_symbols_list` and `web_children` in `model_builder/domain/entities/web_abstract_modeling_classes/explainable_objects_web.py`; `display_calculus_graph` and `get_calculated_attribute_explanation` in `model_builder/adapters/views/views.py`.

## Change along the code path
No product code changes. Each request rebuilds the model in `ModelWeb.__init__`, so the side panel and the graph page receive the library's derived formula, ancestors and children.
- Add one item to `rendering.html` next to "Input-only source inventory": calculated-attribute explanations resolve stored formulas against the live model and pull the operands they display.
- Add one changelog entry under Unreleased.
- For validation, use the editable library in the interface venv (`<interface-venv>/bin/pip install -e ../e-footprint --no-deps`). Leave `pyproject.toml`/`poetry.lock` uncommitted in their editable state. Once 27.0.0 is published, move the pin to `efootprint = "27.0.0"` and refresh the lock.

## Earlier tasks
Tasks 1–3: library 27.0.0 behavior and version.

## Reuse
`INSTALL.md` for the editable setup. Check the editable link with a symbol introduced in Task 2's library, because the venv's link can drift to a snapshot.

## Invariants and traps
- Do not commit the editable dependency. Preserve any existing local dependency edits.
- Any other developer working in parallel shares neither this venv nor the dev database. Do not run stateful suites concurrently.

## Validation
- Interface test suite per `e-footprint-interface/AGENTS.md`, against the editable library.
- Manual: load the introductory GenAI video example, save, reload. Open the Veo server's instances manufacturing footprint (complete formula, Input Variables, Direct children), the CDN server's use footprint, and the system total's calculus graph page (every ancestor level).

## Out of scope
Interface tests for completeness (removed by PLAN-UPDATE-01). Visual changes.

## Unverified
None.
