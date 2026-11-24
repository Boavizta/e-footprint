# Repository-specific workflow guidance — e-footprint

This file is this repository's own: no synchronization writes it. The skills under
`.agents/skills/` and the roles under `.agents/roles/` are written for any project and read what
is particular to this one here. `AGENTS.md` stays the entry point and wins where the two differ.

## Documents

- **Rules**: `specs/constitution.md` (§1 the engineering principles, §2 the quality gates, §3 the
  agent-facing rules), `specs/conventions.md`, `specs/testing.md`. They are authoritative; no
  skill weakens a gate.
- **Architecture**: `specs/architecture/index.html` is the entry point. Read the index, then only
  the owning pages; never invent a documentation path.
- **Feature shaping**: apply
  [the mission's eco-design and feature priorities](../specs/mission.md#eco-design-and-feature-choices)
  before fixing scope. Prefer lean capabilities and negligible extra user effort over complex
  convenience machinery; preserve modeling correctness, and assess runtime and resource costs
  separately.
- **Modeling truth lives here.** Preserve units, explainability, dependency invalidation,
  transaction rollback and the serialization contracts. No compatibility branch for a
  hypothetical consumer (constitution §1.2).
- **A feature folder** is `specs/features/<feature>/`. What is in flight: `specs/roadmap.md`
  § "Active streams", which names each folder and its stage. Re-touch its entry at each stage.
- **Parked work**: a topic folder under `specs/backlog/`, or a horizon of `specs/roadmap.md`;
  a modeling-method question goes to `specs/modeling_logic_roadmap.md`.
- **Tooling**: `specs/agent-tooling.md` (the shared files and their synchronization, the roles'
  adapters, the usage ledger).

## The stack

The Python stack of the comprehension harness is written to its contract
(`comprehension_harness/stack.md`), and `comprehension.config.json` names its commands. Two narratives
are told, the edit of a live model (`tests/narratives/test_model_edit.py`) and a system saved
and loaded back (`tests/narratives/test_system_file.py`); the others are missing. A feature in flight on `plan.html` and `tasks.md` is finished by hand or
ported; a bug batch is planned in pieces too (`bug-fixes`, `bug-fixes-plan`).

| The method says | Here |
|---|---|
| The calls | `from efootprint.narrate import narrate, event, planned, built`, always by name. The file is this project's copy of `comprehension_harness/python/narrate.py`, held identical by a test and never edited here; it ships in the published package and imports the standard library alone. Inert unless a test run of this repository installed the collector: the interface's test runs never receive these calls. The sentence is a literal string and the watch a lambda, `narrate("…", lambda: {"count": n})`: the index refuses anything Python would compute in production |
| Where a call may stand | Anywhere that runs once per action of the modeler: a constructor, an update transaction, an import, an export. **Not in the reactive core's per-slot code** (`ReactiveSlot.pull`, `_compute`, the dependency recorders, a getter): an inert call there is still a function call on the hottest path. A narrative that needs one is measured first, against `tests/performance_tests/` |
| A place that changes, a place that goes, a shell | `planned("<feature>#<slug>:<place>", "<sentence>")` on existing code, the place a short kebab-case name of the site's own within its piece; `planned.remove("<feature>#<slug>", "<sentence>")` in a function that goes, which names no place; a shell is a new function whose whole body, under an optional docstring, is the `planned("<feature>#<slug>:<place>", …)` call then `raise NotImplementedError("planned: <feature>#<slug>")`. One call a line |
| A place that is code | `built("<feature>#<slug>:<place>")` on a line of its own where the change is, `built` imported from `efootprint.narrate` as `planned` was. It is a statement of a block that holds something else: never an expression's operand, nor all a block holds, which the strip refuses. The same rule as every call: none in the reactive core's per-slot code |
| Evidence of a bug, and what a place should see | `planned.evidence("<feature>#<slug>", "<what is seen here today>", lambda: {…}, expect={…})`, on the line the bug shows at; `expect=` on a `planned(…)` call too. `expect` is a literal dict, a key of the watch each, or a lambda giving one where the right value depends on the crossing. `distinct="<key>"`, or a tuple of keys, on either call: the keys of the watch each crossing should see a value of its own for. The same rule as every call: none in the reactive core's per-slot code |
| A reproduction | `@reproduces("<feature>#<slug>: <title> [<rule>]")` of `comprehension_harness/python/declare.py` on a written test that fails today: a run expects the failure, strictly. Built, it becomes `@titled("…")` under the same title. It observes, then asserts once at its end, and is not parametrized |
| A planned test | `@planned_test("<feature>#<slug>: <title> [<rule>]")` of `comprehension_harness/python/declare.py` on a test function with an empty body: skipped by a run, listed by the plan |
| A written test of a plan | The same title under `@titled("…")` once the body is written: `@planned_test` refuses a body. A test with neither is titled by its function's name, and a parametrized case adds pytest's `[case]` |
| A narrative, its reference case | A test class under `@narrative("<title>")` of the same `declare.py`, in a file under `tests/narratives/`; `@narrative.mechanism("<title>")` for a mechanism, which is what a narrative of the engine (`efootprint/abstract_modeling_classes/`) is. Its summary is the first paragraph of the class docstring. Its reference case is its first test, or the one marked `@canonical`; a reference case is not parametrized. A narrative test builds real objects, never mocks: the steps are what the code did |
| The prose a narrative replaces | A section of a page under `specs/architecture/`. It goes, and a link stands where it was: `../comprehension_harness/narratives/<slug>.html` for a narrative, `../comprehension_harness/mechanisms/<slug>.html` for a mechanism, one page a narrative, listed by `specs/comprehension_harness/index.html`. The pages are generated and read locally, after `npm run comprehension:render` |
| What each test crossed | `comprehension_harness/python/collector.py`, a pytest plugin `tests/conftest.py` loads for every run: one story file a test file under `node_modules/.cache/comprehension_harness/stories/` |
| The source index, the test titles, the watch, the strip | `source_index.py`, `titles.py`, `watch.py` and `strip.py` of `comprehension_harness/python/`: the four commands of the configuration, standard library only, run as `python3 -m comprehension_harness.python.<name>` |
| A symbol in a sentence | A name the index can place: an import of the file, a local of the function, a top-level declaration. A method or a dotted name stays plain: name its class. A backticked name shaped like a declaration (`CamelCase`, or words joined by `_`) that the index cannot place fails `--check`, so a dict key, a field or a method is written without backticks |
| A journey | None: the library has no screen. A feature's spec is its `spec.md` |
| The tier of a test | Where its file stands: narrative under `tests/narratives/`, unit otherwise. There is no browser tier |
| Product code | `efootprint/` |
| The proposed migration of a plan | None is drawn. A change of the JSON schema is a piece like another, and its upgrade handler is committed with it (constitution §2.4) |

## Commands

| For | Run |
|---|---|
| The map | `npm run map -- <verb> …` (the `code-map` skill) |
| The pages, once; the check | `npm run comprehension:render`; `npx tsx comprehension_harness/render.ts --check` |
| The pages served, with the answer buttons | `npm run comprehension` |
| The approval, on the reviewer's word only | `npx tsx comprehension_harness/render.ts --approve <feature>` |
| The archive gate | `npx tsx comprehension_harness/render.ts --check --archive <feature>` |
| The strip of an archive, once the gate passes | `npx tsx comprehension_harness/render.ts --strip <feature>`, with `--dry-run` to list what it would take off and write nothing. It edits files under `efootprint/` and `tests/`, and § "Gates" says what runs after it |
| The whole suite | `MPLBACKEND=Agg poetry run pytest` (the stack's own tests are collected with it) |
| The tests of what changed | `MPLBACKEND=Agg poetry run pytest <test files>` |
| The comprehension tools' own tests | `npx vitest run comprehension_harness` |
| The Python stack's tests | `poetry run pytest comprehension_harness/python/tests` |
| The narrative tests | `poetry run pytest tests/narratives` |
| The performance baselines | The scripts under `tests/performance_tests/` |
| The published documentation | `poetry run mkdocs build --strict` |
| The links of a `plan.html` | `python3 .agents/skills/feature-implement/scripts/vscode_review_links.py <plan.html> --in-place` |
| The ledger | `python3 ai-usage/usage.py collect`, then `python3 ai-usage/usage.py report --owner e-footprint --feature <feature> [--run <x>]` |

Node is development tooling only (`package.json`): `npm install` once. The library itself needs
none, and nothing of Node runs in CI.

## Gates

- **An edit of a plan or a doc**: the check. Nothing of the product runs for a document.
- **A piece's commit**: the test files of what it changed.
- **A lot, and the end of a run**: the whole suite once (constitution §2.1), before the last
  commit. Not on the last lot of a supervised delivery: the end-of-run gate runs it once the
  global review's fixes are in.
- **The strip of an archive**: the whole suite once, which also rewrites the stories of the
  retitled tests.
- **A modified `ModelingObject`**: its JSON round-trip is preserved (§2.3).
- **The JSON schema changed**: an upgrade handler in
  `efootprint/api_utils/version_upgrade_handlers.py` and the schema version bumped (§2.4).
- **A new `ModelingObject` class**: registered in `efootprint/all_classes_in_order.py` (§2.5).
- **Production code delivered**: one consolidated entry under `## [Unreleased]` of
  `CHANGELOG.md`, written at the end of the run. Production changes only: no spec, plan,
  tooling or test (§2.6).
- **A change of what the published documentation says**: `poetry run mkdocs build --strict`.
- **Never**: a hook skipped with `--no-verify` (§3.2), a failing test passed by a retry, a bug
  met on the way worked around in silence (§3.1).
- A reviewer's fix is verified narrowly: the test files of what it touched.
- A commit stages its files by name, and its message opens with a tag of `AGENTS.md` § "Git
  commit style".

## Planning checks

For each change a plan follows, say which of these it touches:

- **Constitution §1**: the three layers and their upward dependency direction
  (`abstract_modeling_classes/`, then `core/`, then `api_utils/`), doc-as-code as the truth of
  an object's meaning. A change in how one of them is enforced is a point to confirm, never a
  side effect.
- **The reactive contract**: which values a getter reads and which links it follows, so which
  edges it records; what an edit invalidates; which slot is a guard, and whether an invalid
  state fails at update time. Read `specs/architecture/recomputation/lifecycle.html` first.
- **The object lifecycle boundary**: what runs passively during construction and what runs
  once the instance is live (`specs/conventions.md` § "Modeling refactor preferences").
- **Saved state**: the shape of the JSON, what is serialized of a computed slot, the upgrade
  handler and the test that holds it.
- **Units and explainability**: every new quantity carries its unit and its label; a formula
  stays readable in the calculation graph.
- **The interface**: a change of a public method, property or dict attribute the interface
  consumes changes both repositories. Each holds its own plan of the feature, under the same
  name, with its own baseline, commit range and approval; the interface's plan points at the
  piece here it relies on (`specs/workflow-formats.md` § "A feature that changes two
  repositories"). Test the interface against the intended library checkout.

## Lots

What belongs in one lot here:

- A change of the JSON schema with its upgrade handler and its version bump.
- A new `ModelingObject` class with its registry entries.

Nothing else is particular to this project: the rules of `spec-tasks` apply.

## Review surfaces

- **FULL**: `efootprint/abstract_modeling_classes/`, `efootprint/api_utils/`, footprint, unit
  and attribution calculations, schema migrations, a contract between the library and the
  interface.
- **LIGHT** is open to docs, copy, tests and a builder's default values. A path sets the depth
  of a review; it does not by itself make a lot hard to implement.
- The size test counts source only: `-- . ':!tests' ':!specs' ':!docs_sources' ':!*.md'`.
- **Added to the checklist**: a new `narrate`, `event`, `planned` or `built` call stands where
  the table of "The stack" allows one.

## Autonomy

Granted to a run with nobody there: everything local. The suite, local commits.

Never without the user's word for that instance: a release (a version bump, a tag, a
publication to PyPI or of the documentation), a force push, a branch deletion or a hard reset
(constitution §3.3).

## Sub-agents and the ledger

- A role's model and effort are pinned in its runtime adapter, `.claude/agents/<role>.md` or
  `.codex/agents/<role>.toml`, and named nowhere else (`specs/agent-tooling.md` § "Agent roles").
- A spawn is labelled `<feature>--impl-lot-<lot>`, `--review-lot-<lot>`, `--review-global`,
  `--gate-full`, `<lot>` being the lot's slug; a bug batch adds `--diag-<bug>` and
  `--smell-sweep`, and a `plan.html` of the earlier form `--plan-review-guide`. The ledger reads the
  feature and the role from the label.
- In Claude Code the label opens the spawn's description, and a spawn takes no name: a named
  agent inherits the session's effort and loses its own. Under Codex, bind the session
  (`specs/agent-tooling.md` § "Attribute current work").
- A stateful test suite is never shared between parallel agents.

## Diagnosis

- **The repository that drives a batch**: bugs of the library alone are driven from here; interface
  bugs and bugs that cross the two from `e-footprint-interface`, whose working set then holds this
  repository's diagnostics too, and whose pieces here are planned in a session run here. The
  library is the truth of modeling.
- **The layers open to a reproduction** are those of `specs/testing.md`. The tools run every
  reproduction themselves, by `commands.tests`; there is no browser tier. A reproduction never
  stands in `tests/performance_tests/`: a timing is no failure a run expects strictly.

## Archive

- **An archive runs in any checkout that holds the stories of a test run**: on one that has
  none, the whole suite first. The reproductions its gate and its check run, another feature's
  included, need the test process alone.
- **Where a load-bearing decision goes**: the owning page of `specs/architecture/`,
  `specs/conventions.md`, `specs/testing.md`, and the published documentation under
  `docs_sources/` when what a user reads changes. It is written as what holds now and why,
  never as the story of the choice.
- **Where the reason of one object goes**: the docstring of its declaration, which doc-as-code
  already makes the truth of an object's meaning (constitution §1), or the comment beside a
  field or a constant.
- **The narrative pages a reference doc links to**, in place of prose that told a flow's steps:
  `specs/comprehension_harness/narratives/<slug>.html` and `…/mechanisms/<slug>.html`, one a
  narrative, listed by `specs/comprehension_harness/index.html`. They are generated and not
  committed: the link is written by the page's path, as `specs/architecture/persistence.html`
  does.
- **What the strip leaves outside the code** is settled before the folder goes: a link into the
  folder from a reference doc, an entry of `specs/roadmap.md`.
- **`CHANGELOG.md` and the roadmap stay accurate**: the feature leaves `specs/roadmap.md`
  § "Active streams".
- **Unfinished work** goes to a topic folder of `specs/backlog/` or to a horizon of the roadmap.
- **Never retired with a feature**: a test of a serialization upgrade handler.
- A feature that changed both repositories is archived in each, its plan with its code.
