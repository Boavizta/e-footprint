# Task 3 — Schema 27 and interface adoption
Written 2026-10-19 against e-footprint 58966eb1 and e-footprint-interface a12771fe; Tasks 3 and 4 merged on 2026-10-20.
Plan: [1.4 Old files](../plan.html#persistence), [1.5](../plan.html#interface), [PLAN-UPDATE-01](../plan.html#plan-update-01). Task: [tasks.md](../tasks.md#task-3--schema-27-and-interface-adoption).
Status: approved 2026-10-20.

Two parts, one commit in each repository: the library schema bump first, then the interface adoption.

## Start here
Library:
- `upgrade_version_25_to_26` and `VERSION_UPGRADE_HANDLERS` — `efootprint/api_utils/version_upgrade_handlers.py`: the shape and registration to follow.
- `upgrade_system_dict_to_current_version` — `efootprint/api_utils/json_to_system.py`: runs handlers from the file's major version up to the library's.
- Commit `51833ac2` (the 25→26 bump) lists every file a schema bump touched.

Interface:
- `pyproject.toml` — the `efootprint = "26.0.0"` line, with the commented local-dev line above it.
- `specs/architecture/rendering.html` — the "Input-only source inventory" list item.
- `CHANGELOG.md` — the existing `## [Unreleased]` section.
- Unchanged readers: `compute_literal_formula_and_ancestors_mapped_to_symbols_list` and `web_children` in `model_builder/domain/entities/web_abstract_modeling_classes/explainable_objects_web.py`; `display_calculus_graph` and `get_calculated_attribute_explanation` in `model_builder/adapters/views/views.py`.

## Change along the code path
Library (e-footprint):
- Add `upgrade_version_26_to_27(system_dict, efootprint_classes_dict=None)`. It walks every class block's objects and their attribute dicts, including dict-valued attributes' entries, and pops `direct_ancestors_with_id`. Register it under `26`.
- Set the version to 27.0.0 in `efootprint/version.py` and `pyproject.toml` (`tests/test_version_is_up_to_date.py` checks they agree).
- Update the `"efootprint_version"` strings in the committed inputs-only fixtures (`tests/integration_tests/{simple_system,simple_edge_system,complex_system,system_with_services,edge_device_group_system}.json`) and in `efootprint/modeling_examples/how_to/machine_learning_workflow.json` and `introductory/ecommerce.json`. Update the `"26.0.1"` assertion in `test_current_version_video_import_skips_historical_resolution_migration` (`tests/api_utils_tests/test_json_to_system.py`).
- `persistence.html`: add a 26→27 sentence to the paragraph listing the handlers ("The schema version is the major library version…").
- `CHANGELOG.md`: extend the Unreleased entry from Tasks 1 and 2 with the schema bump. Do not date a release.

Interface (e-footprint-interface), no product code changes. Each request rebuilds the model in `ModelWeb.__init__`, so the side panel and the graph page receive the library's derived formula, ancestors and children.
- Add one item to `rendering.html` next to "Input-only source inventory": calculated-attribute explanations resolve stored formulas against the live model and pull the operands they display.
- Add one changelog entry under Unreleased.
- For validation, use the editable library in the interface venv (`<interface-venv>/bin/pip install -e ../e-footprint --no-deps`). Leave `pyproject.toml`/`poetry.lock` uncommitted in their editable state. Once 27.0.0 is published, move the pin to `efootprint = "27.0.0"` and refresh the lock.

## Earlier tasks
Task 2 removed every reader and writer of the key. Before this task, a 26.0.1 file with the key loads trusted and ignores it. Tasks 1–2 give the library behavior the interface relies on.

## Reuse
- The test style of `test_upgrade_25_to_26_only_repairs_unsupported_video_resolutions` in `tests/api_utils_tests/test_version_upgrade_handlers.py`.
- Interface `INSTALL.md` for the editable setup. Check the editable link with a symbol introduced in Task 2's library, because the venv's link can drift to a snapshot.

## Invariants and traps
- Any version change demotes older files' stored values to the comparison baseline (`version_matches` in `json_to_system`). This is expected and not new.
- The handler must not touch `explain_nested_tuples` or the `calculation_graph` section.
- The plan names only `pyproject.toml`; the correct library file list is the one above (commit `51833ac2` shows it).
- Do not commit the interface's editable dependency. Preserve any existing local dependency edits.
- Any other developer working in parallel shares neither the interface venv nor the dev database. Do not run stateful suites concurrently.

## Validation
- A unit test of the handler on a dict with the key on a value and on a dict entry.
- A load test: a dict at `"26.0.1"` carrying the key loads, and `system_to_json` of the result has no `direct_ancestors_with_id`.
- Full library suite.
- Interface test suite per `e-footprint-interface/AGENTS.md`, against the editable library.
- Manual: load the introductory GenAI video example, save, reload. Open the Veo server's instances manufacturing footprint (complete formula, Input Variables, Direct children), the CDN server's use footprint, and the system total's calculus graph page (every ancestor level).

## Out of scope
Publishing to PyPI (a deployment gate, see tasks.md). Interface tests for completeness (removed by PLAN-UPDATE-01). Visual changes.

## Unverified
None.
