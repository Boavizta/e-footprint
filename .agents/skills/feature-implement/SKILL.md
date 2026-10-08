---
name: feature-implement
description: Complete an approved feature or bug-batch run autonomously through implementation and review, recording only consequential decisions in context in the plan.
---

# feature-implement

Supervise the approved tasks; delegate implementation and independent review. Read `.agents/repository.md` and the role/usage sections needed from `specs/agent-tooling.md` once. Implementers and reviewers read their own detailed skills; consult `task-implement` or `task-review` yourself only for a material workflow question. Resolve the feature/run from the request; use the first unfinished run when unambiguous. Do not ask again for authority already supplied.

An approved run is authorization to proceed end-to-end through task implementation, fixes and
global review. Own technical trade-offs within the agreed outcomes, including internal interface
and mechanism changes. A reviewer's `STRUCTURING-DECISION` label goes to you for resolution; it
does not create a human approval gate. User intervention is exceptional.

## Setup

- Read the constitution, task overview and only the approved spec/plan or bug-diagnostic passages and architecture pages needed for the active task. Follow further references when a material decision needs them; leave detailed code tracing to the assigned agents. Check that acceptance and dependencies are usable without inventing product decisions. Keep a single working set in the driving repo.
- Record starting commits and existing dirty files in every affected repo. Agree file ownership with parallel work; commit only exact owned paths. A shared checkout need not become globally clean.
- Keep consequential decisions in the plan using the format below. Keep task status and any unresolved prerequisites in `tasks.md`. Do not create judgement files, gate journals, or replacement bookkeeping files.
- Use configured roles: GPT-6 Luna/high easy implementer; GPT-6.1 Sol/medium standard implementer; Astra/high hard implementer; GPT-6.1 Sol/high per-task and global reviewer. The supervisor is preferably Astra/high. Respect explicit user model choices; report actual configuration instead of claiming a role pin worked. See `specs/agent-tooling.md` for Claude equivalents and runtime dispatch.
- Collect local usage at run start and register this session/each subagent with the feature, owner, stage, run, role and task where its runtime exposes an ID. Do not repeatedly collect or report usage during an unchanged run; missing telemetry never blocks implementation and is reported as missing.

## Completion-driven supervision

This run is autonomous. While an implementer or reviewer works, continue only useful independent
supervisor-owned work; otherwise wait for its handoff or an actionable request. Do not poll the
agent, checkout or clock merely to produce progress reports, and do not ask agents for routine
progress messages. Use an event wait rather than repeated short status checks. If the runtime
requires periodic user updates, use a bounded event wait and the minimum update needed without
separate clock checks. Surface consequential progress, exceptions and the final outcome.

## Per-task loop

1. Spawn exactly one task's implementation role from its `Implementation` tier: easy → `implementer-easy`, standard → `implementer`, hard → `implementer-hard`. Use the [difficulty rules](../spec-tasks/SKILL.md#implementation-difficulty); if the tier is missing, legacy, or contradicted by new evidence, reassess and update it with a brief reason. Review-risk surfaces and predecessor tiers do not automatically require a stronger implementer. Supply task/brief paths, repository roots, dependency changes, owned file boundaries and role instructions. Defer the consolidated changelog to the supervisor. Require implementation commits, a minimal handoff, and any consequential decisions or unresolved concerns.
2. Spawn an independent `reviewer` over the explicit implementation range(s), not whatever `HEAD` happens to be after handoff commits. Give the same intent and handoff path, and authorize evident scoped corrections in the same assignment. The reviewer chooses its depth, applies routine fixes, and returns only material choices or unresolved concerns alongside the final commit range.
3. Resolve the material choices yourself within the approved outcomes. Resume the reviewer for fixes needing that direction. Capture only consequential decisions in the plan; no routine-fix inventory or review-tier log. Continue without requesting user approval for ordinary implementation choices.
4. Keep check execution with the implementer and reviewer. Use their completion status and outstanding concerns to decide whether the task is complete; resume the responsible agent for missing checks or in-scope failures. Keep unresolved failures or unavailable required checks explicit. Do not copy passing test results, command transcripts or resolved routine fixes into plans, handoffs, reports or logs.
5. Update task status and any actual blockers. Commit supervisor-owned updates with the next substantive change or at close-out instead of making status-only commits. Add handoff leads only for material cross-task concerns; no per-task success checklist.

Use the implementer's handoff and explicit commit range to dispatch review, then the reviewer's final range and outstanding concerns to decide the next step. The reviewer owns full source tracing. Inspect diff statistics and narrow hunks only when a material choice or an APPLIED plan claim requires direct evidence; do not duplicate completed review or reload whole plans, skills and unrelated dirty diffs at every handoff.

## Consequential decisions in the plan

Once consequential choices have stabilized, update their relevant plan passages together to reflect the implemented design. Beside each, add a
visible **`[IMPL-DECISION-01] — APPLIED`** callout with anchor `impl-decision-01`, following the
[shared decision index and callout format](../spec-plan/references/plan-decision-callouts.md).
Use stable, increasing IDs across the feature's runs, and a small linked index near the top with
anchor `impl-decisions`. Ctrl+F `IMPL-DECISION` must find the visible callouts.

Make each callout self-contained for plan review. State whether it fixes a pre-existing defect,
fills a plan gap, changes behavior introduced by this feature, or retains a contested design;
describe the concrete failure or constraint and why the choice matters. Link the affected files
and name the key functions or methods. Explain what changed along the code path and its observable
effect, including relevant state or metadata that is preserved, remapped, or discarded. Give the
run/task and the decisive evidence or trade-off. Keep this focused on the consequential choice,
not a file inventory or a copy of task checks. Include a rejected review suggestion only when
retaining the existing design is itself consequential. Link to the decision from tasks or handoffs
when needed; do not duplicate its explanation. The supervisor owns these plan edits.

When several functions or repositories participate, map each distinct change from its previous
behavior to its current behavior at the named call site; separate a shared helper from the callers
that use it. Say which path actually failed and which already handled the case, so one broad claim
does not imply every path had the same bug. Use short paragraphs or bullets when that makes the
mapping easier to review. For a superseded decision, name the specific mismatch that ended and
any generic mechanism that remains.

Check every APPLIED claim against the final code, especially whether a helper reads, copies, or
derives its inputs. Distinguish implemented behavior from a possible cleanup or remaining gap;
label the latter explicitly when material. Use specific titles in the index so a reviewer can
identify the issue without opening every callout.

For every `IMPL-DECISION` and changed plan passage, follow
[the shared plan-link convention](../spec-plan/references/plan-review-links.md) for source links,
the right-click diff menu and link refresh. Refresh review links after the consolidated plan edit,
unless a link problem requires another pass. The supervisor owns these plan edits.

Keep the plan's left reading-order and changed-file column collapsible during review. Use the
native `details/summary` pattern in `spec-plan/assets/plan.html`: collapsing it should leave a
narrow visible control and give the walkthrough more width beside an editor. Check that the
control stays reachable at narrow widths, works by keyboard, and does not hide the file tree in
print. When editing an older plan, preserve its existing navigation and decision anchors.

`APPLIED` is the normal state after implementation. Reserve **PROPOSED** for exceptional decisions
that actually require the user's authority; keep the current design intact while those are pending.
When accepted and implemented, integrate the change and mark it APPLIED. If rejected, remove the
proposal; keep a concise APPLIED callout only if the decision to retain the design merits review.

Do not annotate routine fixes, passing checks or ordinary choices. If there are no consequential
decisions, add no callouts or index. For a bug batch without a plan, use the same tags beside the
relevant task in `tasks.md`; do not manufacture another document.

## Recovery and decisions

Resume the same agent once for a diagnosed scoped failure. If the task exceeds its implementation
tier, move to the appropriate stronger role using the existing work and concrete failure or
complexity evidence: easy normally moves to `implementer`; use `implementer-hard` when the remaining
work meets the hard criteria. Update the task's tier and reason. Do not cycle through repeated
attempts at the same tier or require a failed attempt before correcting a clearly wrong tier.
Each stronger tier gets at most one escalation attempt. A missing dependency or wrong plan is
not fixed by spending more reasoning.

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
- Collect usage at close-out and give a compact feature/run summary, separating API-equivalent estimates from Codex credits and identifying material coverage gaps or model deviations. Include costs by task type (role) and agent type (actual model/effort combination), with shared overhead separate; when shadows ran, briefly assess their finding coverage, cost and time against the primary reviewer. The closing snapshot is not an exact final invoice.
- Commit the final working set. Report the delivered outcome, link to the plan's decision index when present, and list only outstanding blockers or parked work. Omit routine fixes, successful test results and a duplicate decision narrative. Suggest explicit `feature-archive` after shipping and resolution of outstanding work. Do not merge, deploy, archive, or create a new user task merely because the loop ended.
