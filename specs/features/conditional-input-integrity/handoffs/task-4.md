# Task 4 — Repair and save through one shared editor path

Repositories and implementation ranges:

- `e-footprint-interface`: `9f20b01f63817d6a7a64f66009da91c27567e9be..1042775a8958cdfdd72b7f54a2882adc0038c456`. The initially observed baseline was `7352ac8af148097e5ef186f2396a823fa987b181`; unrelated workspace-save-lock documentation was committed concurrently as `9f20b01f` and is excluded from this implementation range.
- `e-footprint`: consumed library revision `2efaa869d7389bb8dee9d9236fc41366633b6505`; no library implementation changes (`2efaa869..2efaa869`). This handoff is committed separately.

## Review pointers

- `model_builder/domain/object_factory.py::apply_input_edits()` stages controller/dependent values using library queries, preserves every explicit value-bearing submission, and applies one final batch. `InputEditResult` exposes `automatic_changes`, `affected_inputs`, and `had_value_changes`; `EditResult` and `EditObjectOutput` carry it as `input_edit_result` for Task 5. The second return item of `edit_object_from_parsed_data()` is now that result.
- Normal nested storage hooks retain their request-local updates and final save boundary. `tests/integration/test_simplified_inputs.py` covers both Server and EdgeComputer nested success/rejection; `test_ecologits_video.py` exercises a connected API with multiple jobs and explicit Provider/Model submission.
- The narrow ownership extension in `tests/unit_tests/adapters/forms/test_form_field_generator.py` adds the declared `model_name` constructor input to `_SyntheticReferencedAPIClass`. Task 1's registration exposed that invalid synthetic declaration; form assertions and production form generation remain unchanged.

## Open concerns

- The full non-E2E gate still fails `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject` because the pre-existing local editable library dependency remains active. `pyproject.toml` and `poetry.lock` were preserved and excluded from this commit; the publishable dependency gate remains for final release coordination.
