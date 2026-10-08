---
name: spec-tasks
description: Prepare a task breakdown and verified briefs autonomously in one fresh session, collecting any plan-amendment proposals for a single review. Planning only.
---

# spec-tasks

Start in a fresh session from the approved spec and plan, plus `.agents/repository.md`. If decisions exist only in conversation, make the gap explicit. For a bug batch use `bug-fixes` and its diagnostics instead.
Collect and bind this session using `specs/agent-tooling.md`, with the driving
repo, feature and `tasks` stage. Collect again at close-out; report missing telemetry without blocking work.

`tasks.md` is the user's concise overview; `briefs/task-<n>.md` is the implementer's code map. Keep the plan as the reviewed design. Finding a gap while decomposing never authorizes silently redesigning it.

One agent owns the complete task breakdown, all briefs and any plan-amendment callouts in this
session. Work autonomously through the full preparation pass, collecting ordinary design questions
as proposals for one combined review at the end. Resolve routine decomposition choices within the
approved plan yourself. Continue preparing affected tasks under clearly labelled provisional
assumptions linked to their proposal IDs; acceptance remains pending until the user's review.

Interrupt only for a major blocker: missing required documents/code, or a fundamental scope
contradiction that prevents a coherent, reviewable working set even with explicit provisional
assumptions. First complete any unaffected preparation, then explain what is missing and why it
cannot wait for the final review. A pending amendment alone does not interrupt this pass.

1. Identify the driving repo and approved documents. Read the delivery/verification sequence separately from the plan's reading order.
2. Enumerate atomic changes privately, then aggregate into independently reviewable tasks. Keep abstractions with their first consumer and tests; split at useful behavioral milestones rather than directory boundaries. Aim for 2–5 tasks when that fits; do not force arbitrary counts. Default to one implementation run for fewer than six tasks. Split a smaller feature into runs only for a concrete boundary, such as a user-validated gate or an evidence outcome that must be reviewed before later tasks proceed; ordinary task dependencies and cross-repo ownership do not justify separate runs. Larger features may have named runs with explicit dependencies.
3. Give every task a goal, plan links, repository ownership, files, tests, acceptance, dependencies, and `Implementation: easy | standard | hard — brief reason`, using the difficulty rules below. Finalize the tier after grounding the brief.
4. Write every brief yourself in task dependency order using [the template](references/brief.md). Distinguish existing code from what preceding tasks will introduce: interfaces, helpers, ownership and validation assumptions. Keep product code and shared application state unchanged.
5. Check all briefs together: code pointers must be verified, and each dependent task's assumptions must match its predecessors' planned outputs. Put any proposed amendments in `plan.html` using the review format below. Keep the approved design intact while proposals are pending; mark affected tasks and briefs provisional and link them to the decisions they need. Complete the full set before asking for amendment decisions.
6. Classify any outstanding checks: blocks later implementation, blocks deployment only, or can be checked after the run. Evidence-dependent work ships only its evidence-collection stage until the evidence exists. Include the environment/build against which a check must run.
7. Commit the working set when requested, stage exact files, and present the complete overview and briefs with links to the plan's amendment index when present. The user can review all proposals and approve them with the task breakdown in one pass. Implementation begins after approval, in a fresh session.

## Implementation difficulty

Classify the work remaining for the implementer after accounting for the approved plan, verified
brief, existing helpers and preceding tasks' outputs. Use one `Implementation` field with a short,
concrete reason; replace legacy `Risk` labels when reassessing, rather than mapping them mechanically.

| Tier | Remaining implementation work |
|---|---|
| easy | Clear, bounded transformation or known-cause fix with little design judgment and explicit acceptance checks. A systematic rename can qualify across many files or repositories when its mapping and semantic boundaries are clear. |
| standard | Default: ordinary feature work or integration of established mechanisms, requiring normal implementation judgment within the prepared design. |
| hard | An intrinsically difficult mechanism or substantial technical uncertainty remains: for example, designing coupled state transitions, changing transaction/rollback semantics, or resolving a genuinely unknown cause. Name the particular challenge that remains despite preparation. |

Consequences of a bug, a sensitive path, file count, cross-repository breadth, or a long test list
do not by themselves raise implementation difficulty. Breadth determines verification coverage.
A task consuming a hard predecessor's established mechanism does not inherit its tier. Detailed
planning can reduce uncertainty without making an intrinsically difficult mechanism easy.
Assign tiers independently, with no target distribution; do not split tasks just to fit a model.

Justify the tier by the remaining implementation difficulty, not by restating delivered behavior.
For `hard`, identify the specific reasoning or coordination challenge: what the plan, existing
mechanisms and preceding tasks already solve, what remains to work out, and why that remaining
work is technically demanding. Required behavior, invariants and failure consequences alone are
not a justification. Keep the reason to one or two sentences, grounded in verified code or the
brief's account of planned dependencies; use the existing brief for supporting detail.

“Not yet investigated” does not establish difficulty. Resolve straightforward code questions
during brief preparation, correct stale assumptions, then classify. If a material unknown cannot
be resolved during preparation, describe the specific uncertainty and why it is difficult to
settle; do not default to `hard` merely because the relevant code has not been read.

Routing is easy → `implementer-easy`, standard → `implementer`, hard → `implementer-hard`;
model/effort settings live in `specs/agent-tooling.md`. Review depth is independently chosen by
`task-review` from the actual changes and local review surfaces. An easy task may require FULL
review; every tier retains applicable constitution gates and independent review.

## Plan amendments for review

When adding or resolving a `PLAN-UPDATE`, follow the shared
[plan-link convention](../spec-plan/references/plan-review-links.md) and
[decision callout format](../spec-plan/references/plan-decision-callouts.md).

Put each proposal beside the affected passage in `plan.html`. Its visible heading is
**`[PLAN-UPDATE-01] — PROPOSED`**, with anchor `plan-update-01`.
Increment the number for new proposals and keep IDs stable during review. Keep the label and its
enclosing section visible so Ctrl+F `PLAN-UPDATE` works in the rendered plan.

Add a small linked index near the top of the plan, anchored as `plan-updates`, showing each
proposal's number, short title and status. Preserve the existing plan layout. Create an index and
callouts only for actual proposals; do not add empty placeholders to a feature plan.
Zero proposed plan changes is a valid outcome: leave `plan.html` unchanged, omit the amendments
section from `tasks.md`, and state “No plan changes proposed” in the handoff. Do not manufacture
amendments to fill the review format.

Each proposed callout states the current plan, the precise proposed change, why it is needed
with linked code evidence and trade-offs, and the affected tasks. Use the shared HTML format and
its code-artifact link audit before handoff.

`tasks.md` links to these callouts and identifies provisional tasks; the proposal explanation
lives in the plan. Assign amendment IDs consistently across the plan, tasks and briefs as you
prepare the working set. Pending proposals are not implementation instructions.

After explicit acceptance, integrate the change into the plan and synchronize affected tasks
and briefs, then mark the callout and index **ACCEPTED**. Shorten the accepted callout to the
decision and rationale so it does not compete with the updated plan text. For a rejected proposal,
mark **REJECTED**, retain a brief reason, and align affected tasks/briefs with the unchanged design.
A task remains provisional until all amendments it depends on are resolved.

## Tasks file layout

Put the implementation runs immediately after the title, spec/plan links and overall status,
before the task overview and individual tasks. For each run, show its name, delivered milestone,
linked task numbers in execution order, and prerequisites, including earlier runs or cross-repo
dependencies. Every task belongs to one run. For a single-run feature, show one row; do not split
work merely to fill the table. If a feature with fewer than six tasks needs multiple runs, state the concrete boundary in the run prerequisites. Keep the run sequence here rather than repeating it at the bottom.

Use this shape, omitting empty optional sections:

```markdown
# Feature — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: under review

## Implementation runs
| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|

## Overview
| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|

## Plan amendments to review
[Amendment index in the plan](plan.html#plan-updates)
Links to individual proposals and their affected tasks; explanations stay in plan.html.

## Task N — title
Goal: ...
Status: under review / provisional — pending linked plan amendment(s)
Brief: [briefs/task-N.md](briefs/task-N.md)
Repository: ...
Files touched: ...
Tests: ...
Acceptance: ...
Depends on: ...
Implementation: easy / standard / hard — brief reason

## Gates and prerequisites
Outstanding required evidence, deployment prerequisites and their verification environment.
```

Usage attribution: `specs/agent-tooling.md`. Attribute the brief-writing cost to the tasks stage; include it when evaluating downstream savings.
