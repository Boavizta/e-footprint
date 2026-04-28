---
name: spec-tasks
description: Use after the user approves a plan.md to break it into ordered, independently-shippable tasks. Third stage of the four-stage spec-driven workflow. Output is tasks.md; still no code execution.
---

# spec-tasks

You are about to decompose an approved plan into ordered tasks. Do NOT write code yet. The output is a single new file: `specs/features/<feature-name>/tasks.md`.

## Process

1. **Confirm which feature.** Both `spec.md` and `plan.md` must exist and be approved.

2. **Read the plan and the spec.** Tasks should map directly back to plan steps.

3. **Decompose into tasks.** Each task must be:
   - Independently shippable as one PR.
   - Have clear acceptance criteria.
   - Name the files it touches and the tests it adds.

4. **Save the file** at `specs/features/<feature-name>/tasks.md`.

5. **Tell the user** the tasks file is ready and wait for review.

## Template

```markdown
# <Feature title> — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.md`](spec.md). **Plan:** [`plan.md`](plan.md).

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

Brief explanation of why tasks are ordered this way — what depends on what, what can land independently.
```

## After writing

Tell the user:

- Path of `tasks.md`.
- Number of tasks and their high-level order.
- The next step: human review, then `spec-implement` per task.
