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
5. Reconcile their pointers and dependency assumptions. List proposed plan amendments separately with code evidence, trade-offs and affected tasks. Tasks describe the approved plan until the user accepts an amendment; then update the plan, tasks and briefs together.
6. Classify any outstanding checks: blocks later implementation, blocks deployment only, or can be checked after the run. Evidence-dependent work ships only its evidence-collection stage until the evidence exists. Include the environment/build against which a check must run.
7. Commit the working set when requested, stage exact files, and present the overview and amendments for review. Implementation begins after approval, in a fresh session.

Use this shape, omitting empty optional sections:

```markdown
# Feature — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: under review

## Overview
| Task | Delivered behavior | Plan section | Repository | Risk |
|---|---|---|---|---|

## Proposed plan amendments
Evidence, proposal, trade-off and affected tasks.

## Task N — title
Goal: ...
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
