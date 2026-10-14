# Conditional input integrity — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: complete; publishable efootprint 26 dependency and lock verified · 2026-10-14

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A · Conditional input integrity | Library rejection, editor repair and display parity, and the version 26 upgrade | [1](#task-1) → [2](#task-2) → [3](#task-3) → [4](#task-4) → [5](#task-5) → [6](#task-6) | Approved [spec](spec.html) and [plan](plan.html); use the editable local library for interface checks. The publishable dependency is a close-out gate. |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1) | Class-level conditional rule lookup and shared choice queries | [Trigger index](plan.html#dependencies), [choice contract](plan.html#validate-input-choice) | e-footprint | hard |
| [2](#task-2) | Final-state validation for construction, live value edits and relationship changes | [Library edit](plan.html#library-edit), [relationship edit](plan.html#relationship-edit) | e-footprint | hard |
| [3](#task-3) | Stable automatic-replacement source after JSON reload | [Replacement provenance](plan.html#plan-update-05) | e-footprint | easy |
| [4](#task-4) | Shared repair and provenance in normal and Simplified edits | [Save in either editor](plan.html#interface-edit) | e-footprint-interface | hard |
| [5](#task-5) | Library-backed form choices and visible normal-save repair feedback | [Forms](plan.html#forms), [save feedback](plan.html#interface-edit) | e-footprint-interface | standard |
| [6](#task-6) | Narrow 25→26 migration and coordinated version/dependency metadata | [Upgrade](plan.html#upgrade), [delivery](plan.html#delivery) | e-footprint; e-footprint-interface dependency | standard |

<a id="task-1"></a>
## Task 1 — Register and query conditional rules

Goal: Derive direct reverse trigger routes at subclass definition; expose `dependent_inputs()`, proposed-state `resolve_input_path()`, and `allowed_values()` as the library's single query contract.
Status: complete
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: e-footprint
Files touched: `efootprint/abstract_modeling_classes/conditional_inputs.py` (new), `modeling_object.py`; `tests/abstract_modeling_classes/test_conditional_inputs.py` (new), `tests/api_utils_tests/test_json_to_system.py`; `specs/architecture/relationships.html`.
Tests: Synthetic class registration, inheritance/override, union annotations, invalid paths, cold and loaded reverse routes, multi-hop/proposed links, bounded traversal, branch/equality semantics.
Acceptance: A later-defined dependent class is found without instance registration; current and proposed links yield the right exact dependent owners; allowed choices preserve declared order, static restrictions, missing versus empty branches, and `input_values_match()` semantics.
Depends on: approved spec and plan.
Implementation: **hard** — A class-level reverse index must route through live backlinks and a proposed-link overlay while excluding stale paths and overridden subclass declarations; the plan fixes the contract, but the traversal and registration mechanism still requires careful reasoning.

<a id="task-2"></a>
## Task 2 — Reject incompatible library changes atomically

Goal: Check every affected conditional input against the complete proposed or applied state, both during passive construction and inside live update rollback.
Status: complete · [construction cleanup decision](plan.html#impl-decision-01)
Brief: [briefs/task-2.md](briefs/task-2.md)
Repository: e-footprint
Files touched: `efootprint/abstract_modeling_classes/modeling_object.py`, `modeling_update.py`; `tests/abstract_modeling_classes/test_modeling_object.py`, `tests/builders/external_apis/ecologits/test_ecologits_video_external_api.py`, `tests/api_utils_tests/test_json_to_system.py`; `specs/architecture/recomputation/lifecycle.html`.
Tests: Controller-only rejection, either batch order, multiple jobs, constructor assignment order and proposed relationship, cold/warm/loaded edits, link rollback and restored results.
Acceptance: An incompatible single edit raises and restores value, link and eager results; a complete compatible batch succeeds in either order; hydration retains its validation bypass; no conditional check depends on calculation history.
Depends on: [Task 1](#task-1).
Implementation: **hard** — Validation must cover both passive pre-attachment and live post-apply states without breaking entangled changes, link attachment, eager guards or rollback. Task 1 supplies discovery and choice queries, but their placement in these two lifecycles remains technically demanding.

<a id="task-3"></a>
## Task 3 — Persist the automatic-replacement source

Goal: Give generated corrections one canonical source identity across inputs-only and cached JSON round-trips.
Status: complete
Brief: [briefs/task-3.md](briefs/task-3.md)
Repository: e-footprint
Files touched: `efootprint/constants/sources.py`, `efootprint/abstract_modeling_classes/explainable_object_base_class.py`, `efootprint/api_utils/json_to_system.py`; `tests/api_utils_tests/test_json_to_system.py`; `specs/architecture/persistence.html`.
Tests: Source ID/name and canonical identity after both snapshot modes; ordinary user and hypothesis sources still re-identify.
Acceptance: `Sources.AUTOMATIC_REPLACEMENT` has ID `automatic_replacement`; a referenced source reloads as that singleton, with no snapshot-structure change.
Depends on: approved plan; precedes Tasks 4 and 6.
Implementation: **easy** — The existing sentinel-source branches provide a direct, bounded mapping; the remaining work is adding one source and proving both load paths.

<a id="task-4"></a>
## Task 4 — Repair and save through one shared editor path

Goal: Have normal and Simplified edits prepare explicit values, repair affected implicit choices in dependency order, record replacement history, and publish only an accepted final batch.
Status: complete
Brief: [briefs/task-4.md](briefs/task-4.md)
Repository: e-footprint-interface
Files touched: `model_builder/domain/object_factory.py`, `model_builder/domain/services/edit_service.py`, `model_builder/application/use_cases/edit_object.py`, `model_builder/application/use_cases/simplified_inputs.py`, `model_builder/templates/model_builder/side_panels/dynamic_form_fields/source_editor.html`; `tests/unit_tests/domain/test_object_factory.py`, `tests/integration/test_simplified_inputs.py`, `tests/integration/test_ecologits_video.py`, `tests/e2e/test_source_metadata.py`; `specs/architecture/forms-and-relationships.html`.
Tests: Two-editor repair parity, explicit conflict and empty-choice rejection with zero final saves, stable labels and old metadata in prepended notes, repeated repair, browser resubmission of a long comment, metadata-only and nested-storage preservation.
Acceptance: Both editors choose the same first valid implicit replacement and apply controller/dependents once; explicit choices never get overwritten; rejected edits leave reloaded values, links, provenance and results unchanged; normal edits retain cascade cleanup and their final save boundary.
Depends on: [Tasks 1](#task-1), [2](#task-2) and [3](#task-3).
Implementation: **hard** — The shared repair path must evaluate a staged multi-owner graph in controller order while preserving explicit submissions and request-local metadata; it then has to integrate with two distinct save flows without publishing partial edits.

<a id="task-5"></a>
## Task 5 — Align forms and show accepted repairs

Goal: Drive editor options from library rules and show every normal-save correction on visible cards and in the save notice.
Status: complete · [notice transport decision](plan.html#impl-decision-02)
Brief: [briefs/task-5.md](briefs/task-5.md)
Repository: e-footprint-interface
Files touched: `model_builder/domain/services/simplified_inputs.py`, `model_builder/domain/conditional_inputs.py` (remove), `model_builder/adapters/forms/form_field_generator.py`, `model_builder/adapters/presenters/htmx_presenter.py`, `theme/static/scripts/model_builder_main.js`; `tests/unit_tests/domain/test_simplified_inputs.py`, `tests/unit_tests/adapters/forms/test_form_field_generator.py`, `tests/unit_tests/adapters/presenters/test_htmx_presenter.py`, `tests/integration/test_simplified_inputs.py`, `tests/e2e/objects/test_video_external_api_objects.py`, `js_tests/model_builder_main.test.js`; `specs/architecture/forms-and-relationships.html`.
Tests: Current/same-object/referenced-object option parity, retained eligibility, source picker behavior, presenter refresh, safe text notices, reopened saved choice, and focused browser API Save.
Acceptance: Both form consumers use the library resolver; rendered options match `allowed_values()`; automatic source is visible when current but unavailable as a new manual choice; repaired cards and notices name all accepted changes, and reopening shows the saved value.
Depends on: [Tasks 1](#task-1) and [4](#task-4).
Implementation: **standard** — The library query and Task 4 result are already defined; remaining work adapts established form, HTMX and toast paths with normal integration judgment.

<a id="task-6"></a>
## Task 6 — Upgrade historical video inputs to version 26

Goal: Correct only incompatible saved video-job resolutions during the existing 25→26 migration, then coordinate library and interface version metadata.
Status: complete
Brief: [briefs/task-6.md](briefs/task-6.md)
Repository: e-footprint for migration/version; e-footprint-interface for publishable dependency when available.
Files touched: `efootprint/api_utils/version_upgrade_handlers.py`, `version.py`, `pyproject.toml`; `tests/api_utils_tests/test_version_upgrade_handlers.py`, `tests/api_utils_tests/test_json_to_system.py`; interface `pyproject.toml`, `poetry.lock` at integration close-out; both `CHANGELOG.md` files at run close-out.
Tests: Supported and unsupported resolutions, disconnected jobs, old source/label/comment preservation, no available branch, full old-file import with fresh calculations, version-26 no-op and publishable dependency resolution.
Acceptance: Only incompatible resolutions with an available choice get the first option and Task 3's source, cleared confidence and prepended history; unchanged inputs retain metadata; 25→26 load recomputes, current-version load skips migration. Library version is 26.0.0 and the interface dependency is publishable before coordinated merge.
Depends on: [Tasks 1](#task-1), [3](#task-3), [4](#task-4), and final cross-repo checks after [Task 5](#task-5).
Implementation: **standard** — The serialized job shape and migration chain are established, and Task 1 supplies branch choices; the remaining work is a narrow payload transformation with round-trip checks.

## Gates and prerequisites

- Run focused tests with each task, then the full library suite with `MPLBACKEND=Agg poetry run pytest` and `poetry run mkdocs build --strict` from e-footprint. Cover modified-object inputs-only and cached JSON round-trips.
- Validate e-footprint-interface against the edited local library: `poetry run pytest tests --ignore=tests/e2e`, `npm run jest`, rebuild edited JavaScript with `npm run build:js:dev`, and run the focused Playwright flows with a local server (`poetry run pytest tests/e2e/objects/test_video_external_api_objects.py tests/e2e/test_source_metadata.py --base-url http://localhost:8000`).
- **Release gate complete:** `efootprint` 26.0.0 was published, and the interface declares and locks the publishable version-26 dependency. Preserve the current uncommitted interface dependency/lock edits; do not reset them mechanically.
