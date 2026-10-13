# Task 4 — Repair and save through one shared editor path
Written 2026-10-13 against e-footprint `6cb80af3` and e-footprint-interface `7352ac8a`, plus current local dependency edits.
Plan: [save in either editor](../plan.html#interface-edit), [staged choice read](../plan.html#staged-choice-read), [replacement provenance](../plan.html#plan-update-05). Task: [4](../tasks.md#task-4).
Status: under review.

## Start here
- `prepare_input_changes()` and `edit_object_from_parsed_data()` — interface `model_builder/domain/object_factory.py`; conversion, per-request source lookup, metadata-only edits and current one-batch call.
- `EditSimplifiedInputUseCase.execute()` — `model_builder/application/use_cases/simplified_inputs.py`; the repair loop to extract and its one final `persist_to_cache()`.
- `EditObjectUseCase.execute()` and `EditService.edit_with_cascade_cleanup()` — `model_builder/application/use_cases/edit_object.py` and `model_builder/domain/services/edit_service.py`; normal final-save boundary and cascade cleanup.
- `_apply_metadata()` — factory module; source/confidence/comment patch semantics. `source_editor.html` — `model_builder/templates/model_builder/side_panels/dynamic_form_fields/`; 2,000-character comment cap and current-source display.

## Change along the code path
Add shared `apply_input_edits()` beside the factory preparer. Convert all submitted fields with shared `available_sources`/`pending_sources`; record explicit value-bearing addresses even when unchanged, excluding metadata-only patches. Stage proposed `(owner, attribute) → value` changes. Walk Task 1 `dependent_inputs()` transitively, resolving controllers against proposed links/values before dependents. Keep allowed proposed values. Reject an explicit incompatible value or empty allowed set; otherwise prepare the first allowed option for the actual owner, one replacement per address. Do not attach a shared option object or copy its metadata.

For each generated replacement, retain the field label, set Task 3's source, clear confidence and prepend a note with previous/new values, the controller reason, prior source label/link, prior confidence and the previous comment verbatim. Build the proposed controller and correction batch and call one `ModelingUpdate`; translate membership failures to `InputValidationError`. Return automatic-change records, affected addresses (including valid values with changed options) and value-change status. Carry that result through `EditResult` and `EditObjectOutput`; leave presentation to Task 5.

Replace the Simplified loop with this helper and retain its one final save. Use the same helper in normal editing before existing successful cascade cleanup and `persist_structural_change()`. Keep `ServerWeb.pre_edit()` and `EdgeComputerWeb.pre_edit()` request-local nested edits and name/metadata behavior. Remove the source-editor comment length cap so generated history can be viewed and resubmitted; show the automatic source when current without offering it as a new manual choice.

## Earlier tasks
Task 1 supplies direct/proposed path and choice queries; Task 2 makes the final library batch the authority for acceptance/rollback; Task 3 supplies the canonical source identity. The helper must use these APIs rather than the old Simplified catalog branch loop.

## Reuse
Use `prepare_input_changes()` for owner-specific conversion and metadata, `ModelingUpdate` for atomic model changes, `FieldAddress` only at the interface boundary, and existing final save methods. Retain `EditService` cascade behavior and the source picker's existing current-source state.

## Invariants and traps
Normal forms explicitly submit Provider and Model: an incompatible submitted Model is an error, while unsubmitted linked job resolutions may be repaired. Metadata-only and same-value edits must not trigger spurious repair, but an unchanged explicit value remains explicit if another submitted controller makes it incompatible. Rejection must leave reloaded inputs, provenance, relationships, results and final-save count unchanged. A second repair prepends history without truncating old text.

## Validation
Extend `tests/unit_tests/domain/test_object_factory.py` for staged graph order, explicit/implicit distinction, two repairs and exact provenance. Extend `tests/integration/test_simplified_inputs.py` for two-editor parity, rejection before save, metadata-only and nested edits; use `tests/integration/test_ecologits_video.py` for the real shared-API normal edit. From e-footprint-interface with the edited library installed: `poetry run pytest tests/unit_tests/domain/test_object_factory.py tests/integration/test_simplified_inputs.py tests/integration/test_ecologits_video.py`. Extend the existing `tests/e2e/test_source_metadata.py` source-editor flow to verify a generated note over 2,000 characters can be viewed and resubmitted; with a local server run `poetry run pytest tests/e2e/test_source_metadata.py --base-url http://localhost:8000`.

## Out of scope
HTMX/toast/card feedback and form option migration are Task 5. The version 25 snapshot handler is Task 6.

## Unverified
No separate publication mechanism is assumed for `pre_edit()` nested changes; the current use case calls it before the final save. Focused integration checks must confirm failure remains request-local.
