---
name: bug-fixes
description: Diagnose a batch of reported bugs before implementation. Creates one evidence-backed diagnostic per report and an ordered tasks.md that feature-implement can execute later. Use for a conversational batch of bugs, not for a single quick fix.
---

# bug-fixes

Run a diagnosis-only session for a batch of bug reports. The output is a self-contained working set under `specs/features/`; `bug-fixes-plan` then writes the review plan, and implementation happens through `feature-implement`.

Keep the roles separate:

- The main agent owns intake, user decisions, task synthesis, and ordering. Read the reference docs needed to assess findings, but preserve context by delegating product-code investigation.
- The `diagnostician` role investigates one bug per sub-agent. They may edit only their assigned diagnostic file and its reproduction test; product code remains read-only.

If the batch contains only one or two small bugs, suggest diagnosing and fixing them directly with `task-implement`-style discipline instead of creating a batch workspace.

## Choose the driving repository

- Library-only bugs are driven from `e-footprint`.
- Interface bugs and cross-repository bugs are driven from `e-footprint-interface`.
- A cross-repository batch has one working set in the driving repository. Diagnostics and tasks identify which repository owns each change.

## Set up the working set

1. Create `specs/features/bug-fixes-<YYYY-MM>/`, adding a numeric suffix if that name exists, and a `diagnostics/` directory beneath it.
2. Create `tasks.md` with an empty execution-plan section and this marker:

   ```markdown
   <!-- Tasks appended during diagnosis; final ordering pass pending. -->
   ```

3. Load the driving repository's `specs/constitution.md`, `specs/conventions.md`, `specs/testing.md`, and architecture entry point:
   - `e-footprint`: `specs/architecture/index.html`, then the owning pages.
   - `e-footprint-interface`: `specs/architecture/index.html`, then the owning pages.
   Read `.agents/repository.md` in each affected repository.
4. For cross-repository reports, also load the companion repository's constitution and relevant architecture pages. Use the library as the source of truth for modeling behavior.

## Diagnose each report

For every independently observable bug:

1. Capture the report faithfully: symptoms, reproduction context, expected behavior, and the user's hypothesis. Ask only for information required to identify the affected surface.
2. Spawn one diagnostic sub-agent per bug, in parallel where reports are independent. Give it the verbatim report, the target `diagnostics/<bug-slug>.md`, and the template below.
3. Require the sub-agent to:
   - trace the behavior through real code and tests, citing `repository/path:line` for every material claim;
   - test the user's hypothesis and state plainly when it is disproven;
   - inspect both repositories when ownership is unclear;
   - identify the smallest correct fix direction without implementing it;
   - write the [reproduction test](#reproduction-test), run it, and record its failing output in the diagnostic;
   - flag constitution invariants, migrations or serialization changes, cross-repository ordering, and validation that cannot run locally;
   - return only a terse verdict, fix direction, and user decision forks. The full evidence stays in the diagnostic file.
4. Check the verdict against the loaded architecture and constitution before relaying it. Challenge findings that conflict with a documented invariant or place modeling logic in the interface.
5. Resolve genuine product or UX forks with the user. Have the diagnostic sub-agent record settled choices under `## Decisions`.
6. Add one task to `tasks.md` for each confirmed bug. Split a report only when its independently shippable parts have distinct acceptance criteria or land in different repositories; express their ordering with `Depends on`. Drop reports shown to be expected behavior, and tell the user why.

A `PLAUSIBLE` diagnosis is allowed when local evidence cannot prove a device-, browser-, data-, or environment-specific cause. Rank the hypotheses and make its task staged: first add the minimum observation or discriminating test, then pause for the result before applying the outcome-specific fix.

## Reproduction test

Every confirmed bug gets one committed test that asserts the expected behavior and fails on the
current branch for the diagnosed reason. It is the executable form of the evidence, the fix's
acceptance criterion, and the task's complete test change: the fix is done when the test passes
with its marker removed, and the implementer adds no further tests. Size it to the acceptance
surface, parametrizing over every affected class, example or panel the diagnostic names, and
assert at the supported boundary, never inside a helper the fix may introduce. Refactor tasks are
behavior-preserving and rely on the existing suite; a bug found during a fix is a new report with
its own reproduction.

- Mark it as a strict expected failure so the suite stays green while the bug exists and the fix
  cannot land without flipping it: `@pytest.mark.xfail(strict=True, reason="bug-fixes-<YYYY-MM> Task N")`,
  or `test.failing(...)` in Jest. The reason string is the one allowed task reference in test code;
  it leaves with the marker.
- Choose the cheapest layer in `specs/testing.md` that reproduces the real failure, through the
  supported entry point (view, use case, browser), following the repository's fixture conventions.
- Prefer an existing test as the home for a new failure mode over a new file. Add a parametrized
  case with `pytest.param(..., marks=pytest.mark.xfail(strict=True, reason=...))` when the test
  is parametrized; otherwise add the tightened assertion as a sibling test beside the existing
  one, reusing its setup, and note that it folds back into the existing test when the marker goes.
  Never wrap an existing passing test in the marker: that masks the coverage it already gives.
- Run it and record the failing assertion or traceback in the diagnostic. A test that passes on
  the current branch, or fails for another reason, is not a reproduction. When a scratch prototype
  of the fix exists, use it to check that the test discriminates; do not commit the prototype.
- When a product fork is still open, assert only the undisputed invariant (no raw 500, the object
  is gone) and state in the diagnostic how the assertion tightens once the decision is settled.
- Write none for a report shown to be expected behavior, a cleanup with no observable defect, or a
  `PLAUSIBLE` cause whose staged observation step already plays this role. Say why in the diagnostic.

## Diagnostic template

```markdown
# <Symptom>: <root-cause characterization>

- **Status:** CONFIRMED | PLAUSIBLE | NOT A BUG
- **Confidence:** high | medium | low — <basis>
- **Reported:** <faithful report and whether its hypothesis held>

## Root cause
<Mechanism with repository/path:line evidence.>

## Reproduction
- `<repository/path>::<test>` — <layer>; fails on `<branch>@<commit>` with <assertion or error>. | none — <reason>

## Fix approach
<Concrete direction and meaningful alternatives rejected.>

## Files to touch
- `<repository/path>` — <change, with a line anchor where useful>

## Tests
- <Regression case and appropriate unit, integration, JS, or E2E location.>

## Acceptance criteria
- <Observable behavior.>

## Risks and side effects
- <Adjacent behavior and intended trade-offs.>

## Flags
- <Invariants, cross-repo ordering, migration/serialization, local-only validation, or none.>

## Decisions
- <Decision and date, when applicable.>
```

## Task format

Keep every task usable from cold context and compatible with `task-implement` and `feature-implement`:
classify remaining work using [implementation difficulty](../spec-tasks/SKILL.md#implementation-difficulty),
accounting for the completed diagnosis rather than the bug's impact.

```markdown
## Task N — <short title>

**Goal:** <correct behavior, including settled decisions>

**Diagnostic:** [`diagnostics/<bug-slug>.md`](diagnostics/<bug-slug>.md)

**Repository:** `e-footprint` | `e-footprint-interface`

**Files touched:**
- `<repository/path>` — <intended change>

**Tests added/changed:**
- `<repository/path>::<test>` — reproduction; remove its expected-failure marker. No other tests unless a new public contract is named here.

**Acceptance:**
- The reproduction passes with its marker removed
- <Observable result>

**Depends on:** none | Task N

**Implementation:** easy | standard | hard — brief reason
```

Task numbers follow arrival order and remain stable. Put uncertainty, user validation, or a required cross-repository dependency directly in the task rather than relying on conversation history.

## Close the batch

1. Offer an optional read-only smell sweep over the surfaces implicated by several reports. Its `smell-sweep.md` ranks findings by risk and effort, marks overlap with existing tasks, and records suspicious-looking code that is actually sound. Add only user-approved refactors as final tasks.
2. Leave the execution-plan placeholder in place: `bug-fixes-plan` writes the execution plan in `plan.html` and replaces the placeholder with a pointer. That plan follows these rules:
   - a deduplication verdict showing that each task has a distinct cause;
   - ordered `feature-implement` runs, normally no more than about eight tasks each;
   - data-loss and silent-correctness fixes first, then contained UI fixes, larger or staged work, and finally behavior-preserving smell-sweep refactors;
   - the task numbers in execution order for each run, plus dependency, shared-file, cross-repository, and user-validation notes.
3. Verify every confirmed report has a diagnostic and exactly one task unless the split is explained. Verify every task links a diagnostic, and that each confirmed bug has a committed reproduction or a stated reason for none.
4. Commit the diagnosis working set when the user wants it finalized, using `[ADD] bug-fixes-<YYYY-MM>: diagnosed working set` and including the task/diagnostic counts in the commit body.

Hand off to `bug-fixes-plan` in a fresh session: the diagnostics replace `spec.html`, and that skill writes the `plan.html` that groups the bugs by mechanism and orders the `feature-implement` runs. Use `feature-archive` after all runs have shipped and durable knowledge has been promoted to the live reference docs.

## Guardrails

- Do not implement fixes during this skill, including apparent one-liners.
- Do not accept an uncited root-cause claim or silently preserve a disproven user hypothesis.
- Do not commit a reproduction that passes on the current branch, fails for a reason other than the diagnosed one, or wraps an existing passing test.
- Do not use destructive operations to prove a diagnosis. Move such confirmation into a staged task and surface the gate.
- Do not create duplicate working sets across repositories for a cross-repository batch.

Role configuration, telemetry and gate classification follow `specs/agent-tooling.md` and
`feature-implement`. Preserve missing-evidence gates rather than guessing a diagnosis.
