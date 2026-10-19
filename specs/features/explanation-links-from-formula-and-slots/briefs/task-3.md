# Task 3 — Schema 27: drop the stored ancestor key
Written 2026-10-19 against e-footprint 58966eb1.
Plan: [1.4 Old files](../plan.html#persistence). Task: [tasks.md](../tasks.md#task-3--schema-27-drop-the-stored-ancestor-key).
Status: under review.

## Start here
- `upgrade_version_25_to_26` and `VERSION_UPGRADE_HANDLERS` — `efootprint/api_utils/version_upgrade_handlers.py`: the shape and registration to follow.
- `upgrade_system_dict_to_current_version` — `efootprint/api_utils/json_to_system.py`: runs handlers from the file's major version up to the library's.
- Commit `51833ac2` (the 25→26 bump) lists every file a schema bump touched.

## Change along the code path
- Add `upgrade_version_26_to_27(system_dict, efootprint_classes_dict=None)`. It walks every class block's objects and their attribute dicts, including dict-valued attributes' entries, and pops `direct_ancestors_with_id`. Register it under `26`.
- Set the version to 27.0.0 in `efootprint/version.py` and `pyproject.toml` (`tests/test_version_is_up_to_date.py` checks they agree).
- Update the `"efootprint_version"` strings in the committed inputs-only fixtures (`tests/integration_tests/{simple_system,simple_edge_system,complex_system,system_with_services,edge_device_group_system}.json`) and in `efootprint/modeling_examples/how_to/machine_learning_workflow.json` and `introductory/ecommerce.json`. Update the `"26.0.1"` assertion in `test_current_version_video_import_skips_historical_resolution_migration` (`tests/api_utils_tests/test_json_to_system.py`).
- `persistence.html`: add a 26→27 sentence to the paragraph listing the handlers ("The schema version is the major library version…").
- `CHANGELOG.md`: extend Task 2's Unreleased entry with the schema bump. Do not date a release.

## Earlier tasks
Task 2 removed every reader and writer of the key. Before this task, a 26.0.1 file with the key loads trusted and ignores it.

## Reuse
The test style of `test_upgrade_25_to_26_only_repairs_unsupported_video_resolutions` in `tests/api_utils_tests/test_version_upgrade_handlers.py`.

## Invariants and traps
- Any version change demotes older files' stored values to the comparison baseline (`version_matches` in `json_to_system`). This is expected and not new.
- The handler must not touch `explain_nested_tuples` or the `calculation_graph` section.
- The plan names only `pyproject.toml`; the correct file list is the one above (commit `51833ac2` shows it).

## Validation
- A unit test of the handler on a dict with the key on a value and on a dict entry.
- A load test: a dict at `"26.0.1"` carrying the key loads, and `system_to_json` of the result has no `direct_ancestors_with_id`.
- Full library suite.

## Out of scope
Publishing to PyPI (a deployment gate, see tasks.md). Interface pin (Task 4).

## Unverified
None.
