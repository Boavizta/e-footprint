---
name: bug-fixes
description: Diagnose a batch of reported bugs before implementation. Creates one evidence-backed diagnostic per report and an ordered tasks.md that feature-implement can execute later. Use for a conversational batch of bugs, not for a single quick fix.
---

# bug-fixes

Run a diagnosis-only session for a batch of bug reports. The output is a self-contained working set under `specs/features/`; implementation happens later through `feature-implement`.

Keep the roles separate:

- The main agent owns intake, user decisions, task synthesis, and ordering. Read the reference docs needed to assess findings, but preserve context by delegating product-code investigation.
- Diagnostic sub-agents investigate one bug each. They may edit only their assigned diagnostic file; product code remains read-only.

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
   - `e-footprint-interface`: `specs/architecture.md`.
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
   - flag constitution invariants, migrations or serialization changes, cross-repository ordering, and validation that cannot run locally;
   - return only a terse verdict, fix direction, and user decision forks. The full evidence stays in the diagnostic file.
4. Check the verdict against the loaded architecture and constitution before relaying it. Challenge findings that conflict with a documented invariant or place modeling logic in the interface.
5. Resolve genuine product or UX forks with the user. Have the diagnostic sub-agent record settled choices under `## Decisions`.
6. Add one task to `tasks.md` for each confirmed bug. Split a report only when its independently shippable parts have distinct acceptance criteria or land in different repositories; express their ordering with `Depends on`. Drop reports shown to be expected behavior, and tell the user why.

A `PLAUSIBLE` diagnosis is allowed when local evidence cannot prove a device-, browser-, data-, or environment-specific cause. Rank the hypotheses and make its task staged: first add the minimum observation or discriminating test, then pause for the result before applying the outcome-specific fix.

## Diagnostic template

```markdown
# <Symptom>: <root-cause characterization>

- **Status:** CONFIRMED | PLAUSIBLE | NOT A BUG
- **Confidence:** high | medium | low — <basis>
- **Reported:** <faithful report and whether its hypothesis held>

## Root cause
<Mechanism with repository/path:line evidence.>

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

```markdown
## Task N — <short title>

**Goal:** <correct behavior, including settled decisions>

**Diagnostic:** [`diagnostics/<bug-slug>.md`](diagnostics/<bug-slug>.md)

**Repository:** `e-footprint` | `e-footprint-interface`

**Files touched:**
- `<repository/path>` — <intended change>

**Tests added/changed:**
- `<repository/path>` — <regression case>

**Acceptance:**
- <Observable result>

**Depends on:** none | Task N
```

Task numbers follow arrival order and remain stable. Put uncertainty, user validation, or a required cross-repository dependency directly in the task rather than relying on conversation history.

## Close the batch

1. Offer an optional read-only smell sweep over the surfaces implicated by several reports. Its `smell-sweep.md` ranks findings by risk and effort, marks overlap with existing tasks, and records suspicious-looking code that is actually sound. Add only user-approved refactors as final tasks.
2. Replace the execution-plan placeholder with:
   - a deduplication verdict showing that each task has a distinct cause;
   - ordered `feature-implement` runs, normally no more than about eight tasks each;
   - data-loss and silent-correctness fixes first, then contained UI fixes, larger or staged work, and finally behavior-preserving smell-sweep refactors;
   - the task numbers in execution order for each run, plus dependency, shared-file, cross-repository, and user-validation notes.
3. Verify every confirmed report has a diagnostic and exactly one task unless the split is explained. Verify every task links a diagnostic.
4. Commit the diagnosis working set when the user wants it finalized, using `[ADD] bug-fixes-<YYYY-MM>: diagnosed working set` and including the task/diagnostic counts in the commit body.

Hand off each planned run to a fresh `feature-implement` session. The linked diagnostics replace `spec.html` and `plan.html` for these bug-batch tasks. Use `feature-archive` after all tasks have shipped and durable knowledge has been promoted to the live reference docs.

## Guardrails

- Do not implement fixes during this skill, including apparent one-liners.
- Do not accept an uncited root-cause claim or silently preserve a disproven user hypothesis.
- Do not use destructive operations to prove a diagnosis. Move such confirmation into a staged task and surface the gate.
- Do not create duplicate working sets across repositories for a cross-repository batch.
