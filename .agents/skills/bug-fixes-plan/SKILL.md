---
name: bug-fixes-plan
description: Write or refine plan.html for a diagnosed bug batch after bug-fixes closes. Group the confirmed bugs by failure mechanism, digest each root cause and fix from its diagnostic, attach the refactors they motivate, and order the feature-implement runs. Planning only; no fixes.
---

# bug-fixes-plan

Help the reviewer discover a bug batch: what is broken, why, what changes, and in what order.
The diagnostics already hold the evidence; the plan is their digest and the single owner of
run ordering and later implementation decisions. It is not a third copy of the diagnostics.

Input: `specs/features/bug-fixes-<YYYY-MM>/tasks.md`, its `diagnostics/*.md` and, when present,
`smell-sweep.md`. Output: `plan.html` beside them, in the driving repository.

Start in a fresh session after `bug-fixes` has closed the batch. Refine an existing plan in place.
Read `.agents/repository.md` for local adaptations. Use the collection/binding commands in
`specs/agent-tooling.md` at stage start and close-out; attribute the session to the driving repo,
the batch folder as feature and the `plan` stage.

Shared ground with `spec-plan`, owned there and never restated here:

- Grounding in repository docs and code: [spec-plan's grounding rules](../spec-plan/SKILL.md#ground-the-plan-before-writing).
- Complexity audit for proposed mechanisms and refactors: [spec-plan's audit](../spec-plan/SKILL.md#audit-complexity-before-human-review).
- Walkthrough writing, HTML surface, iteration and handoff audit: [plan review surface](../spec-plan/references/plan-review-surface.md).
- Source links and the right-click diff menu: [plan-review-links](../spec-plan/references/plan-review-links.md).
- Decision indexes and callouts: [plan-decision-callouts](../spec-plan/references/plan-decision-callouts.md).
- Page layout: [the HTML starter](../spec-plan/assets/plan.html).

This skill owns what a bug-batch plan contains and in which order.

## Ground the plan

- Read `tasks.md` in full, every diagnostic and the smell sweep. Note the commit each diagnostic
  was traced on; code may have moved since. Verify every line you link, and re-trace only where a
  claim needs a line the diagnostics do not give or where two documents disagree. Do not
  re-diagnose a confirmed cause.
- Check the batch is closed: every `CONFIRMED` or `PLAUSIBLE` diagnostic has exactly one task,
  every task links a diagnostic or a smell-sweep finding, and every user-approved refactor has a
  task. A diagnostic without a task is a gap: append the task to `tasks.md` in the
  [bug-fixes task format](../bug-fixes/SKILL.md#task-format) with the next number, and tell the
  user. Do not drop a diagnosed bug silently and do not renumber.
- Settled `## Decisions` in a diagnostic stay settled. Open forks go to the plan's decisions
  section, linked from the bug that raises them.

## Reading order

Cluster the tasks by failure mechanism: the same code path, the same mistaken assumption, or the
same files. Order clusters with the [bug-fixes ordering rule](../bug-fixes/SKILL.md#close-the-batch):
data-loss and silent-correctness first, then contained UI fixes, then larger or staged work, then
behavior-preserving refactors, with test-only locks last. Task numbers stay as stable labels;
reading position is not task number, and the navigation shows both.

Open each cluster with one paragraph on the mechanism as it exists today, linked to code, that
explains all of the cluster's bugs. No architecture teaching; link the owning page.

### Bug step

One `data-step` article per task, in this order and scaled to the bug. An easy one-line fix can
take five lines; do not pad a step to fill the shape.

1. Heading `Task N · <title>` with chips: verdict (`CONFIRMED` or `PLAUSIBLE`, the latter styled
   `data-chip="review"`), repository, implementation difficulty. Link the diagnostic.
2. **Symptom**: what the user sees, in one or two sentences.
3. **Root cause**: one paragraph with deep links to the lines that produce the behavior. When the
   reporter's hypothesis was disproven, say so here.
4. **Fix**: the narrated anticipated diff. Add a snippet only where prose would leave the shape
   of the change unclear; mark existing versus proposed code.
5. **Tests**: the regression and its layer.
6. **Settled** decisions as plain text, **open** forks as a link to the decisions section, and the
   diagnostic's flags (invariants, cross-repository ordering, serialization, local-only validation).
   For a `PLAUSIBLE` task, state the staged gate: the observation to add first, then the
   outcome-specific fix.

### Refactor step

Place each refactor at the end of the cluster that motivates it, labelled with its smell-sweep
finding ids. Explain it through the shared refactor rule: what happens today, what is extracted
and who uses it, which bugs above it would have prevented or which next one it prevents. Mark the
parts that deliberately change behavior. When the cluster does not earn the refactor's cost, say so
as a review decision with the smaller alternative; do not drop an approved refactor silently.

### Execution plan

A dedicated `#execution-plan` section owns run ordering. For each `feature-implement` run, list the
task numbers in order with dependency, shared-file, cross-repository and user-validation notes,
following the run-size and ordering rules in [bug-fixes](../bug-fixes/SKILL.md#close-the-batch).
Add a one-line deduplication verdict for each pair of tasks that could be the same cause. Draw a
small dependency diagram when the dependencies are not a straight line, labelling hard
dependencies, soft ordering and shared files distinctly.

Replace the execution-plan placeholder in `tasks.md` with a one-line pointer to
`plan.html#execution-plan`. The plan is the only place that orders runs.

A verification table is useful when several tasks share one new test file or harness; otherwise
the per-step tests suffice.

### Changed-file tree

Steps are tasks, so `data-steps` lists task ids and the tree highlights the files of the selected
task. A file touched by several tasks lists all of them; that is where run ordering and conflicts
are decided.

## Header and decisions

The header links `tasks.md`, `smell-sweep.md` when present, and the changed-file tree; there is no
spec. Keep a decisions section only for open forks and refactor cost calls, each grounded in a
concrete scenario from a diagnostic.

## Handoff

Run the [shared handoff audit](../spec-plan/references/plan-review-surface.md#handoff-audit).
Report the plan path, the clusters, tasks added to `tasks.md`, and open decisions. Wait for review.
After approval, hand each run to a fresh `feature-implement` session; it reads the run's steps and
their diagnostics, and records `IMPL-DECISION` callouts beside the affected step using the shared
format. `plan-review-guide` applies at close-out as for a feature plan. Use `feature-archive`
after all runs have shipped.

## Guardrails

- Do not implement fixes or edit product code, including apparent one-liners.
- Do not reopen settled diagnostic decisions or reinterpret a disproven hypothesis as open.
- Do not duplicate diagnostic evidence; link it.

## Maintaining this skill

The library repository's `.agents/skills/bug-fixes-plan/` is canonical; the interface copy is a
mirror. Rules shared with `spec-plan` live in `spec-plan/references/` and `spec-plan/assets/`:
change them there and synchronize both repositories. Keep only bug-batch content rules here.
