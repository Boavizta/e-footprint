# Explanation links from formula and slots — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: under review. Tasks 1 and 2 are provisional until [PLAN-UPDATE-02](plan.html#plan-update-02) and [PLAN-UPDATE-03](plan.html#plan-update-03) are decided.

## Implementation runs
| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | Saved explanations complete after reload in the library and the interface, schema 27 | [1](#task-1--sever-edges-of-slots-that-leave-the-model), [2](#task-2--derive-explanation-links-from-formula-and-slot-graph), [3](#task-3--schema-27-drop-the-stored-ancestor-key), [4](#task-4--interface-adopts-library-27) | Decisions on PLAN-UPDATE-02 and -03. Task 4 validates against the editable library; merge waits for the 27.0.0 release (see gates) |

## Overview
| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| 1 | Slots popped as stale dict keys or owned by a deleted object no longer appear as dependents | [PLAN-UPDATE-02](plan.html#plan-update-02) (a) | e-footprint | easy |
| 2 | Formula, ancestors, children and calculus graph of a saved value complete after reload; load and save compute nothing | [1.1](plan.html#resolver)–[1.4](plan.html#persistence) (save/load parts), PLAN-UPDATE-02 (b), PLAN-UPDATE-03 | e-footprint | standard |
| 3 | Files at schema 26 upgrade by dropping the ancestor key; library at 27.0.0 | [1.4](plan.html#persistence) (old files) | e-footprint | easy |
| 4 | Interface pinned to library 27 with its architecture and changelog lines; GenAI example checked by hand | [1.5](plan.html#interface) | e-footprint-interface | easy |

## Plan amendments to review
[Amendment index in the plan](plan.html#plan-updates)
- [PLAN-UPDATE-02](plan.html#plan-update-02) — slots that leave the model sever their edges; children re-checked after pull. Affects Tasks 1 and 2.
- [PLAN-UPDATE-03](plan.html#plan-update-03) — resolve a computed-dict operand through its element. Affects Task 2.

## Task 1 — Sever edges of slots that leave the model
Goal: a slot removed from the model (stale computed-dict key, or any slot of a deleted object) drops its own dependency edges, so `dependents` lists only live consumers.
Status: provisional — pending [PLAN-UPDATE-02](plan.html#plan-update-02)
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: e-footprint
Files touched: `efootprint/abstract_modeling_classes/reactive_core/computed_slots.py` (`discard_stale_keys`), `efootprint/abstract_modeling_classes/modeling_object.py` (`self_delete`), `tests/abstract_modeling_classes/test_reactive_core.py`, `tests/abstract_modeling_classes/test_modeling_object.py`, `specs/architecture/recomputation.html` (one clause).
Tests: new unit tests: a pruned stale sub-slot is absent from its former dependencies' `dependents`; no slot of a deleted object remains a dependent of a surviving slot. Full library suite including `test_randomized_mutation_parity.py`.
Acceptance: the add-usage-pattern replay in the brief leaves only live dependents on the country's carbon intensity; the full library suite passes unchanged.
Depends on: PLAN-UPDATE-02 accepted.
Implementation: easy — two call sites, a verified prototype, and the invariant (only unreachable slots lose edges) already argued in the amendment.

## Task 2 — Derive explanation links from formula and slot graph
Goal: a saved value resolves its formula on display (pulling void operands), derives its direct ancestors from the formula's attached leaves and its children from the slot's calculus dependents; the stored ancestor list, the hydration state, the children bookkeeping and the loader's inversion pass go.
Status: provisional — pending [PLAN-UPDATE-02](plan.html#plan-update-02) (b) and [PLAN-UPDATE-03](plan.html#plan-update-03)
Brief: [briefs/task-2.md](briefs/task-2.md)
Repository: e-footprint
Files touched: `efootprint/abstract_modeling_classes/explainable_object_base_class.py`, `efootprint/api_utils/json_to_system.py`, `efootprint/abstract_modeling_classes/reactive_core/computed_slots.py` (`_release_value` docstring), the four unit test files named in the plan, `tests/integration_tests/integration_test_base_class.py`, `tests/integration_tests/test_integration_simple_system_from_json.py`, `tests/performance_tests/json_size.py`, `specs/architecture/persistence.html` (contract cell and children sentence), `specs/architecture/recomputation.html`, `CHANGELOG.md`.
Tests: round-trip completeness (flat formula, ancestor ids, children ids, calculus graph nodes and edges) on every integration fixture system; load and save observed with `observe_computations`; display computes only what it shows; structural and computed-structure dependents excluded; unit assertions on the ancestor key flipped; hand-built bookkeeping tests rewritten. Full library suite and performance gates.
Acceptance: the plan's [verification map](plan.html#delivery) rows for the library hold; no load-time or save-time computation; stored values re-serialize byte-for-byte after a display.
Depends on: Task 1; amendments accepted.
Implementation: standard — the plan supplies the resolver, ancestor and children code and verifies the no-pull paths; what remains is ordinary integration and test rewriting.

## Task 3 — Schema 27: drop the stored ancestor key
Goal: a 26→27 upgrade handler pops `direct_ancestors_with_id` from every stored value; the library moves to 27.0.0.
Status: under review
Brief: [briefs/task-3.md](briefs/task-3.md)
Repository: e-footprint
Files touched: `efootprint/api_utils/version_upgrade_handlers.py`, `tests/api_utils_tests/test_version_upgrade_handlers.py`, `efootprint/version.py`, `pyproject.toml`, the committed inputs-only fixtures under `tests/integration_tests/` and the two packaged examples under `efootprint/modeling_examples/` (version string), `tests/api_utils_tests/test_json_to_system.py` (version assertion), `specs/architecture/persistence.html` (handler sentence), `CHANGELOG.md` (same entry as Task 2).
Tests: handler unit test; a V26 dict carrying the key loads and round-trips without it; `tests/test_version_is_up_to_date.py`; full suite.
Acceptance: plan row "Old files load" holds; version strings agree.
Depends on: Task 2.
Implementation: easy — a key-pop handler on the established handler pattern plus version-string updates.

## Task 4 — Interface adopts library 27
Goal: the interface runs on the new library with its architecture line and changelog entry; the GenAI video example is checked by hand.
Status: under review
Brief: [briefs/task-4.md](briefs/task-4.md)
Repository: e-footprint-interface
Files touched: `pyproject.toml` (library pin), `specs/architecture/rendering.html`, `CHANGELOG.md`.
Tests: interface suite against the editable library; manual check of the Veo instances manufacturing footprint, CDN use footprint and system total graph page.
Acceptance: interface suite passes; the three displays are complete after reload; no view, presenter or template change.
Depends on: Tasks 1–3.
Implementation: easy — a dependency pin and two documentation lines; no product code.

## Gates and prerequisites
- Blocks implementation: decisions on PLAN-UPDATE-02 and PLAN-UPDATE-03 (Tasks 1 and 2).
- Blocks deployment only: efootprint 27.0.0 published to PyPI before the interface's pin moves from the editable dependency to `27.0.0` and merges. Validate Task 4 with the editable library in the interface venv, then restore a publishable dependency deliberately.
- After the run: manual GenAI video check on the interface (Task 4) against the editable library; regenerate the gitignored local `tests/performance_tests/big_system.json` before running the performance gates.
- Not part of this feature: the uncommitted save-threshold edit in `tests/performance_tests/test_big_system_from_and_to_json_performance.py`.
