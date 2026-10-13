# Task 6 — Upgrade historical video inputs to version 26
Written 2026-10-13 against e-footprint `6cb80af3` and e-footprint-interface `7352ac8a`, plus existing local dependency/lock edits.
Plan: [version 26 upgrade](../plan.html#upgrade), [delivery and verification](../plan.html#delivery). Task: [6](../tasks.md#task-6).
Status: under review.

## Start here
- `upgrade_system_dict_to_current_version()` and `json_to_system()` — library `efootprint/api_utils/json_to_system.py`; existing migration chain and mismatch cache handling.
- `upgrade_version_24_to_25()` and `VERSION_UPGRADE_HANDLERS` — `efootprint/api_utils/version_upgrade_handlers.py`; handler signature and registry.
- `EcoLogitsVideoGenExternalAPIJob.conditional_list_values` — `efootprint/builders/external_apis/ecologits/ecologits_video_external_api.py`; saved job type, controller and option catalog.
- `Sources.AUTOMATIC_REPLACEMENT` — Task 3 output in `efootprint/constants/sources.py`; canonical ID/payload.
- `tests/api_utils_tests/test_version_upgrade_handlers.py` and `test_json_to_system.py`; current handler and full-import coverage. Interface `pyproject.toml` currently has an editable `../e-footprint` dependency, and both repos have local lock/dependency edits.

## Change along the code path
Add `upgrade_version_25_to_26()` and register key 25. Walk the serialized video-job collection, including disconnected jobs. Resolve each saved `external_api` ID to the saved API, read its `model_name`, then call Task 1 `allowed_values(job_class, "resolution", saved_model)`. If the current resolution is unsupported and choices exist, write the first choice into that job's resolution payload, retain its label and links, set Task 3's source ID, clear confidence and prepend the same history fields used by Task 4. Read the prior source label/link from the existing Sources block before overwriting the ID; add the automatic source payload to that block when needed. Leave supported values, absent/empty branches and other authored fields untouched.

Advance `efootprint/version.py` and library `pyproject.toml` to 26.0.0. The normal version-aware loader must demote old cached outputs and compute fresh results. Version-26 files must bypass the handler. At cross-repo close-out, replace the interface's local editable dependency with a publishable version-26 requirement and resolve its lock when available, preserving unrelated local edits. Consolidate unreleased changelog entries for both repositories after the run.

## Earlier tasks
Task 1 supplies the exact choice logic; Task 3 supplies stable source identity; Task 4 establishes the replacement note policy to mirror in serialized migration. Task 5's editor checks complete final interface parity. No generic import graph validation is introduced.

## Reuse
Use the supplied class registry or the API layer's existing fallback; stay inside the established migration chain and Source serialization. Do not hydrate a temporary graph to decide choices. Keep the loader's original-file-version cache rule.

## Invariants and traps
Only `EcoLogitsVideoGenExternalAPIJob` resolutions are in scope. Preserve labels, relationship IDs, supported input metadata and earlier comment text verbatim. A missing source or confidence is recorded as “none” in the note. Do not repair malformed provider/model pairs, introduce new snapshot fields or run the handler for current-version files. The interface dependency/lock cannot be reset mechanically because they already contain local edits.

## Validation
Extend `tests/api_utils_tests/test_version_upgrade_handlers.py` with direct 25→26 cases: supported, incompatible, disconnected, missing/empty branch, provenance, repeated-note preservation and unaffected fields. Extend `tests/api_utils_tests/test_json_to_system.py` for full old-file import, fresh calculation, automatic source identity and current-version no-op. From e-footprint: `MPLBACKEND=Agg poetry run pytest tests/api_utils_tests/test_version_upgrade_handlers.py tests/api_utils_tests/test_json_to_system.py`; then full library pytest and `poetry run mkdocs build --strict`. At cross-repo close-out run interface unit/integration, Jest and focused E2E against the edited local library, then verify a publishable dependency resolves with the interface lock.

## Out of scope
Actual PyPI publication, app deployment, generic import revalidation and recovery UI.

## Unverified
Availability of a publishable `efootprint` 26 package is an external close-out condition, not required for local implementation with the editable library. Verify dependency resolution before coordinated merge; preserve current local files until then.
