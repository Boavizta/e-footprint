# Task 5 — Align forms and show accepted repairs

Repositories and implementation ranges:

- `e-footprint-interface`: `24388fed09fda3f7d3b041da0e1f22a8452b3ee0..f6156887ec9edfcee98af438a22860e4ff56b380`.
- `e-footprint`: consumed library revision `34788d4f83b37096aa91b397948aad412bae7816`; no library implementation changes (`34788d4..34788d4`). This handoff is committed separately.

## Review pointers

- `generate_dynamic_form()` queries library `allowed_values()` for fixed current choices and browser cascades. Conditional choices take precedence over static-only rendering so their static intersection is honored; absent branches with a static catalog retain that catalog, while declared empty branches remain empty. Referenced-object cascade keys stay as object IDs. Catalog selection still belongs to the interface; its duplicate resolver is removed.
- `HtmxPresenter.present_edited_object()` consumes Task 4's automatic-change records for notices and affected owners for top-parent/mirror refresh. Canvas OOB coverage suppresses separate card swaps; the existing renderer deduplicates shared top parents. The toast inserts names and notices with `textContent`.
- The approved ownership extension in `tests/unit_tests/domain/entities/web_core/usage/test_job_web.py` makes the snapshot owner fixture hashable with identity semantics and supplies source-valued controller inputs, matching the library query contract. The snapshot payload remains unchanged.
- The shared-API browser flow checks two repaired jobs, a retained job, mirror refresh, reopened saved options and the existing current-source picker behavior. `source_metadata.js` remains at the reviewed Task 4 version.

## Open concerns

- The non-E2E gate's publishable-dependency check remains blocked by the pre-existing editable library requirement in `pyproject.toml`. Dependency and lock edits are preserved and excluded; Task 6 owns the release dependency gate.
