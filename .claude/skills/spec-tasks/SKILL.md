---
name: spec-tasks
description: Use after the user approves a plan.html to break it into ordered, independently-shippable tasks. Third stage of the four-stage spec-driven workflow. Output is tasks.md; still no code execution.
---

# spec-tasks

You are about to decompose an approved plan into ordered tasks. Do NOT write code yet. The output is a single new file: `specs/features/<feature-name>/tasks.md`.

## Process

A task in this skill is a **review-sized unit of change** — one commit / one PR. That is not the same as an atomic unit of work, and conflating the two leads to over-splitting (5+ narrowly-scoped tasks where 2–3 fit the change better). Decompose in two passes:

1. **Confirm which feature.** Both `spec.html` and `plan.html` must exist and be approved.

2. **Read the plan and the spec.** Tasks should map back to plan steps, but a single task may aggregate several plan steps and a plan step may span several tasks.

3. **First pass — enumerate atomic units of work.** Internal scratch, not written to the file. List the smallest meaningful steps: one new module, one config edit, one call-site rewiring, one test file. The goal is completeness — flush out everything the plan requires so nothing is forgotten in the aggregation step.

4. **Second pass — aggregate into review-sized tasks.** Group the atomic units into tasks using these criteria:
   - **Keep tightly-coupled units together.** A new abstraction and its first consumer, an adapter and the tests that exercise it, a JSON edit and the consistency test that guards it — splitting these creates review boundaries with no behavioural pause point.
   - **Split at behavioural pause points, not at layer/directory boundaries.** Good split points: "infrastructure landed but unused," "first user-visible change," "second user-visible change." Bad split points: "domain layer" vs. "adapter layer" vs. "templates" when they all serve one feature delivery.
   - **Each task must leave the system in a working state** — tests green, no half-wired call sites.
   - **Target 2–5 tasks for a typical feature.** Fewer if the feature is small; more only if there are genuinely independent behavioural milestones. If you find yourself at 6+, look for adjacent tasks to merge.
   - **Bias toward fewer, larger tasks.** One task = one commit = one review pass, so each extra task adds review overhead. Only split when there's a concrete reason (independent reviewability, a meaningful pause point, parallel landability).

5. Each aggregated task must:
   - Be independently shippable as one PR.
   - Have clear acceptance criteria.
   - Name the files it touches and the tests it adds.

6. **Save the file** at `specs/features/<feature-name>/tasks.md`.

7. **Tell the user** the tasks file is ready and wait for review.

## Template

```markdown
# <Feature title> — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — <short title>

**Goal:** ...

**Files touched:**
- `...`

**Tests added/changed:**
- `tests/...`

**Acceptance:**
- ...

**Depends on:** none / Task N.

---

## Task 2 — <short title>

(same shape)

---

## Ordering rationale

Brief explanation of why tasks are ordered this way — what depends on what, what can land independently. If two tasks were aggregated from several atomic units, note the criterion that kept them together (e.g. "no behavioural pause point between the protocol and its first consumer").
```

## After writing

Tell the user:

- Path of `tasks.md`.
- Number of tasks and their high-level order.
- The next step: human review, then `task-implement` per task.
