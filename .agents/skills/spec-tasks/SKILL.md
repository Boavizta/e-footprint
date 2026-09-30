---
name: spec-tasks
description: Decompose an approved plan into review-sized tasks, verified implementer briefs, and explicit plan-amendment proposals. Planning only; use a fresh session.
---

# spec-tasks

Start in a fresh session from the approved spec and plan, plus `.agents/repository.md`. If decisions exist only in conversation, make the gap explicit. For a bug batch use `bug-fixes` and its diagnostics instead.
Collect and bind this session and brief writers using `specs/agent-tooling.md`, with the driving
repo, feature and `tasks` stage. Collect again at close-out; report missing telemetry without blocking work.

`tasks.md` is the user's concise overview; `briefs/task-<n>.md` is the implementer's code map. Keep the plan as the reviewed design. Finding a gap while decomposing never authorizes silently redesigning it.

1. Identify the driving repo and approved documents. Read the delivery/verification sequence separately from the plan's reading order.
2. Enumerate atomic changes privately, then aggregate into independently reviewable tasks. Keep abstractions with their first consumer and tests; split at useful behavioral milestones rather than directory boundaries. Aim for 2–5 tasks when that fits; larger features may have named runs with explicit dependencies. Do not force arbitrary counts.
3. Give every task a goal, plan links, repository ownership, files, tests, acceptance, dependencies, and `Risk: normal` or `Risk: high — reason`. High means delicate invariant enforcement, data migration, security change, a new cross-cutting mechanism, or unresolved root cause; size alone is not risk.
4. Write a verified brief using [the template](references/brief.md). For three or more tasks, delegate one `brief-writer` per task, within available concurrency. Give each the whole decomposition, its task and relevant plan sections. Writers own separate briefs and do not change code or shared application state. For fewer tasks, write the briefs directly.
5. Reconcile their pointers and dependency assumptions. Put proposed amendments in `plan.html` using the review format below. Keep the approved design intact while proposals are pending; mark affected tasks and briefs provisional and link them to the decisions they need.
6. Classify any outstanding checks: blocks later implementation, blocks deployment only, or can be checked after the run. Evidence-dependent work ships only its evidence-collection stage until the evidence exists. Include the environment/build against which a check must run.
7. Commit the working set when requested, stage exact files, and present the overview with links to the plan's amendment index. The user can approve amendments and the task breakdown in the same review. Implementation begins after approval, in a fresh session.

## Plan amendments for review

Put each proposal beside the affected passage in `plan.html`, in a visually distinct, expanded
callout. Its visible heading is **`[PLAN-UPDATE-01] — PROPOSED`**, with anchor `plan-update-01`.
Increment the number for new proposals and keep IDs stable during review. Keep the label and its
enclosing section visible so Ctrl+F `PLAN-UPDATE` works in the rendered plan.

Add a small linked index near the top of the plan, anchored as `plan-updates`, showing each
proposal's number, short title and status. Preserve the existing plan layout. Omit the index and
callouts when there are no proposals; do not add empty placeholders to a feature plan.

Each proposed callout follows this shape, with concrete content and real links:

```html
<aside id="plan-update-01">
  <p><strong>[PLAN-UPDATE-01] — PROPOSED</strong></p>
  <p><strong>Current plan:</strong> The approved decision this would change.</p>
  <p><strong>Proposed change:</strong> The precise replacement or addition.</p>
  <p><strong>Why:</strong> Linked code evidence and the relevant trade-off.</p>
  <p><strong>Affected tasks:</strong> Links to the affected tasks.</p>
</aside>
```

`tasks.md` links to these callouts and identifies provisional tasks; the proposal explanation
lives in the plan. Brief writers return findings to the coordinator, who owns plan edits and
amendment IDs. Pending proposals are not implementation instructions.

After explicit acceptance, integrate the change into the plan and synchronize affected tasks
and briefs, then mark the callout and index **ACCEPTED**. Shorten the accepted callout to the
decision and rationale so it does not compete with the updated plan text. For a rejected proposal,
mark **REJECTED**, retain a brief reason, and align affected tasks/briefs with the unchanged design.
A task remains provisional until all amendments it depends on are resolved.

Use this shape, omitting empty optional sections:

```markdown
# Feature — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: under review

## Overview
| Task | Delivered behavior | Plan section | Repository | Risk |
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
Risk: normal / high — reason

## Runs and gates
Order, cross-repo dependencies, required evidence, deployment prerequisites.
```

Role setup and usage attribution: `specs/agent-tooling.md`. Attribute the brief-writing cost to the tasks stage; include it when evaluating downstream savings.
