# Task 3 — Persist the automatic-replacement source
Written 2026-10-13 against e-footprint `6cb80af3`.
Plan: [replacement provenance](../plan.html#plan-update-05), [upgrade use](../plan.html#upgrade). Task: [3](../tasks.md#task-3).
Status: under review.

## Start here
- `Sources.USER_DATA` and `Sources.HYPOTHESIS` — `efootprint/constants/sources.py`; existing stable-ID source examples.
- `_resolve_sentinel_source()` — `efootprint/abstract_modeling_classes/explainable_object_base_class.py`; input metadata resolution.
- `build_sources_dict_from_system_dict()` — `efootprint/api_utils/json_to_system.py`; top-level Sources block resolution.
- `TestJsonToSystem` — `tests/api_utils_tests/test_json_to_system.py`; existing load and version-aware round-trip tests.

## Change along the code path
Define `Sources.AUTOMATIC_REPLACEMENT` with ID `automatic_replacement` and name `automatic replacement`. Add its ID to the two existing canonical-source resolution points, so an input referencing it and the Sources block both resolve to the same singleton. Standard source serialization already carries referenced sources; keep the snapshot shape unchanged. Document this source identity in `specs/architecture/persistence.html`.

## Earlier tasks
No runtime dependency on Tasks 1–2. Task 4 will assign the source to generated editor values, and Task 6 will write its ID and payload into migrated JSON.

## Reuse
Mirror the existing user-data/hypothesis source handling and `Source.to_json()`/`from_json_dict()` contracts. Do not create a second Source object for each automatic correction.

## Invariants and traps
The stable ID is the contract; name and link are display metadata. Existing source identities must remain unchanged. Load both inputs-only and cached snapshots; no migration handler or new persisted field is needed in this task.

## Validation
Extend `tests/api_utils_tests/test_json_to_system.py` with source identity assertions after both snapshot modes, plus existing sentinel-source regressions. From e-footprint: `MPLBACKEND=Agg poetry run pytest tests/api_utils_tests/test_json_to_system.py`. Run `poetry run mkdocs build --strict` for the edited architecture page.

## Out of scope
Formatting repair comments, interface source-picker behavior and version 25 correction belong to Tasks 4–6.

## Unverified
None: all three source-resolution locations were found in the current library.
