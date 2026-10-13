# Task 5 — Align forms and show accepted repairs
Written 2026-10-13 against e-footprint `6cb80af3` and e-footprint-interface `7352ac8a`, plus current local dependency edits.
Plan: [configure and render choices](../plan.html#forms), [normal feedback](../plan.html#interface-edit). Task: [5](../tasks.md#task-5).
Status: under review.

## Start here
- `build_catalog()` — interface `model_builder/domain/services/simplified_inputs.py`; current selection edges and imported `resolve_input_path()`.
- `generate_dynamic_form()` — `model_builder/adapters/forms/form_field_generator.py`; current `values_by_conditional_value` conversion, current-controller, same-object and dotted cascades.
- `resolve_input_path()` — `model_builder/domain/conditional_inputs.py`; duplicate to remove after both imports move.
- `HtmxPresenter.present_edited_object()` — `model_builder/adapters/presenters/htmx_presenter.py`; current top-parent/mirror card refresh and toast payload.
- `displayToastAndHighlightObjects` handler — `theme/static/scripts/model_builder_main.js`; current edit toast writes `innerHTML`.

## Change along the code path
Move catalog and form imports to Task 1's library resolver, then delete the interface duplicate. Keep catalog eligibility and forced-companion selection owned by the interface. In form generation, call `allowed_values()` for the current controller, each same-object controller choice, and each referenced object in a dotted cascade. Preserve the existing form payload shape and referenced-object ID keys. Reopening a job must select its accepted saved resolution.

Consume Task 4's automatic-change and affected-input result in normal edit presentation. Render notices naming owner, existing label and accepted value; refresh repaired owners' top-parent/mirror cards, deduplicated against a canvas OOB region. Append notices as text in the edit toast, without changing existing recomputation triggers or rejection modals. The source editor must display the automatic source on a repaired field but exclude it from new manual source choices.

## Earlier tasks
Task 1 defines resolver and allowed choices. Task 4 carries repair records through `EditObjectOutput`; use those records rather than rediscovering changes in the presenter. Task 3's source ID drives source-picker filtering.

## Reuse
Retain `FieldAddress`, `complete_selection()`, existing dynamic-list payload keys, `_render_top_parent_cards()`, `render_oob_regions()` and current HTMX triggers. Keep text insertion safe; do not interpolate correction text into `innerHTML`.

## Invariants and traps
An absent conditional branch and an explicitly empty branch differ; the library helper owns that distinction. A displayed option must match what the library accepts. Dotted cascades stay keyed by referenced ID. Refresh all repaired jobs sharing an API, including mirrors, but avoid duplicate card OOB swaps. The existing `source_editor.html` current-source display and Task 4's long comment must round-trip together.

## Validation
Extend `tests/unit_tests/domain/test_simplified_inputs.py`, `tests/unit_tests/adapters/forms/test_form_field_generator.py`, `tests/unit_tests/adapters/presenters/test_htmx_presenter.py`, and `js_tests/model_builder_main.test.js`; use `tests/integration/test_simplified_inputs.py` for reopened options/source and `tests/e2e/objects/test_video_external_api_objects.py` for real API Save, notice, card and job editor state. From e-footprint-interface: `poetry run pytest tests/unit_tests/domain/test_simplified_inputs.py tests/unit_tests/adapters/forms/test_form_field_generator.py tests/unit_tests/adapters/presenters/test_htmx_presenter.py tests/integration/test_simplified_inputs.py`; `npm run build:js:dev`; `npm run jest`. With the local server running: `poetry run pytest tests/e2e/objects/test_video_external_api_objects.py --base-url http://localhost:8000`.

## Out of scope
Changing Simplified eligibility or adding a job-redirection control. Task 6 owns historical migration and dependency release metadata.

## Unverified
No new renderer is presumed. The presenter's existing OOB region and top-parent behavior were located; focused E2E verifies the final combined swaps and toast in a browser.
