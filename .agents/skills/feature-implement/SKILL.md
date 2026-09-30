---
name: feature-implement
description: Complete an approved feature or bug-batch run autonomously through implementation and review, recording only consequential decisions in context in the plan.
---

# feature-implement

Supervise the approved tasks; delegate implementation and independent review. Read `.agents/repository.md`, `task-implement`, `task-review` and `specs/agent-tooling.md` once. Resolve the feature/run from the request; use the first unfinished run when unambiguous. Do not ask again for authority already supplied.

An approved run is authorization to proceed end-to-end through task implementation, fixes and
global review. Own technical trade-offs within the agreed outcomes, including internal interface
and mechanism changes. A reviewer's `STRUCTURING-DECISION` label goes to you for resolution; it
does not create a human approval gate. User intervention is exceptional.

## Setup

- Read the approved spec/plan (or linked bug diagnostics), tasks, constitution and relevant architecture pages. Check that acceptance and dependencies are usable without inventing product decisions. Keep a single working set in the driving repo.
- Record starting commits and existing dirty files in every affected repo. Agree file ownership with parallel work; commit only exact owned paths. A shared checkout need not become globally clean.
- Keep consequential decisions in the plan using the format below. Keep task status and any unresolved prerequisites in `tasks.md`. Do not create judgement files, gate journals, or replacement bookkeeping files.
- Use configured roles: Sol/medium implementer; Astra/high hard implementer and reviewer. The supervisor is preferably Astra/high. Respect explicit user model choices; report actual configuration instead of claiming a role pin worked. See `specs/agent-tooling.md` for Claude equivalents and runtime dispatch.
- Collect local usage and register this session/each subagent with the feature, owner, stage, run, role and task where its runtime exposes an ID. Missing telemetry never blocks implementation and is reported as missing.

## Per-task loop

1. Spawn `implementer` for exactly one task, or `implementer-hard` for a concrete high-risk task. Supply task/brief paths, repository roots, dependency changes, owned file boundaries and role instructions. Defer the consolidated changelog to the supervisor. Require implementation commits, a minimal handoff, and any consequential decisions or unresolved concerns.
2. Spawn an independent `reviewer` over the explicit implementation range(s), not whatever `HEAD` happens to be after handoff commits. Give the same intent and handoff path, and authorize evident scoped corrections in the same assignment. The reviewer chooses its depth, applies routine fixes, and returns only material choices or unresolved concerns alongside the final commit range.
3. Resolve the material choices yourself within the approved outcomes. Resume the reviewer for fixes needing that direction. Capture only consequential decisions in the plan; no routine-fix inventory or review-tier log. Continue without requesting user approval for ordinary implementation choices.
4. Keep check execution with the implementer and reviewer. Use their completion status and outstanding concerns to decide whether the task is complete; resume the responsible agent for missing checks or in-scope failures. Keep unresolved failures or unavailable required checks explicit. Do not copy passing test results, command transcripts or resolved routine fixes into plans, handoffs, reports or logs.
5. Update task status and any actual blockers; commit exact owned files and continue. Keep user updates focused on meaningful progress or exceptions, with no per-task success checklist. Add handoff leads only for material cross-task concerns.

## Consequential decisions in the plan

Update the relevant plan passage or snippet to reflect the implemented design. Beside it, add a
visible, expanded **`[IMPL-DECISION-01] — APPLIED`** callout with anchor `impl-decision-01`.
Use stable, increasing IDs across the feature's runs, and a small linked index near the top with
anchor `impl-decisions`. Ctrl+F `IMPL-DECISION` must find the visible callouts.

Keep each callout short: the choice made or retained, why it matters (evidence and trade-off),
and the run/task plus a useful code or commit link. Include a rejected review suggestion only when
retaining the existing design is itself a consequential choice. Link to the decision from tasks or
handoffs when needed; do not duplicate its explanation. The supervisor owns these plan edits.

`APPLIED` is the normal state after implementation. Reserve **PROPOSED** for exceptional decisions
that actually require the user's authority; keep the current design intact while those are pending.
When accepted and implemented, integrate the change and mark it APPLIED. If rejected, remove the
proposal; keep a concise APPLIED callout only if the decision to retain the design merits review.

Do not annotate routine fixes, passing checks or ordinary choices. If there are no consequential
decisions, add no callouts or index. For a bug batch without a plan, use the same tags beside the
relevant task in `tasks.md`; do not manufacture another document.

## Recovery and decisions

Resume the same agent once for a diagnosed scoped failure. If implementation difficulty remains, escalate once to `implementer-hard` with the failed attempt's evidence. A missing dependency or wrong plan is not fixed by spending more reasoning.

If still blocked, park that task and its transitive dependents in `tasks.md`, record what is needed and continue independent tasks. Keep completed work and preserve unrelated dirty files. Never label a failed or unverified change complete.

Interrupt the user only for a major blocker that prevents further useful authorized work, a
necessary change to agreed product scope or constitutional rules, or an operation needing authority
not already granted. Explain the concrete obstacle and why you cannot resolve it within the approved
run. Continue independent work while a decision is pending. Do not infer approval from silence.

Keep only outstanding prerequisites beside the affected tasks: distinguish those blocking code
work, deployment-only conditions and later human checks, with the needed environment and observable
result. A deployment or human check does not block independent implementation. Clear resolved
routine blockers instead of turning them into a history of successful checks.

## Close-out

- Run a fresh `reviewer` on both repositories' cumulative feature/run ranges, with the same authority for evident scoped fixes. Assign it final validation, including cross-repository integration and any checks needed after its corrections. Reuse completed checks that still cover the final changes; additional runs need a relevant change, failure or coverage gap. Start with any material handoff leads and diff statistics; resolve consequential findings without a routine user checkpoint.
- Write a consolidated `CHANGELOG.md` entry for the delivered behavior in each affected repo. Resolve outstanding validation through the responsible agent before closing the run. Surface only unresolved failures or unavailable required checks, with enough context to act.
- Collect usage again and give a compact feature/run summary, separating API-equivalent estimates from Codex credits and identifying material coverage gaps or model deviations. Detailed breakdowns remain available through the usage tool. The closing snapshot is not an exact final invoice.
- Commit the final working set. Report the delivered outcome, link to the plan's decision index when present, and list only outstanding blockers or parked work. Omit routine fixes, successful test results and a duplicate decision narrative. Suggest explicit `feature-archive` after shipping and resolution of outstanding work. Do not merge, deploy, archive, or create a new user task merely because the loop ended.

## Optional bounded shadow-review experiment

Only run when the user explicitly requests the experiment or approves its feature-local protocol. Compare Astra/high with Sol/high on identical immutable task ranges, starting independently with the same brief and no access to the other's findings. Shadow only the initial task review, not fixes or global review. Limit to five named runs, then stop for a decision; never make the second review permanent by accident.

For this experiment, keep both initial reviews read-only until their findings are captured;
then let the primary reviewer apply the scoped fixes. This preserves the common comparison state.

The shadow is read-only and may not run stateful suites or shared-cache writers. A failed shadow does not block normal review. Record reviewer IDs, tiers, matched findings, approved material misses, useful shadow-only findings, noise, durations and INITIAL-review cost (not the primary reviewer's later fix work). Act on a genuine shadow-only defect through normal triage. Book experiment cost separately. Use evidence about misses and completed-task cost to decide whether to keep, split or change the reviewer role.
