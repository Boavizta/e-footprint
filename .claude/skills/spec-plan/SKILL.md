---
name: spec-plan
description: Use after the user approves a spec.md to write the corresponding plan.md. Second stage of the four-stage spec-driven workflow. Plan answers HOW the spec becomes code; respects architecture.md. Still no code execution.
---

# spec-plan

You are about to write a plan for a feature whose spec is approved. Do NOT write any code yet. The output is a single new file: `specs/features/<feature-name>/plan.md`.

## Process

1. **Confirm which feature** with the user. The corresponding `specs/features/<feature-name>/spec.md` must exist and be approved.

2. **Read the spec, plus `specs/architecture.md` and `specs/constitution.md`.** The plan must respect both. If the plan requires deviating from architecture, the deviation is called out explicitly with rationale.

3. **Draft the plan** following the template below. Use AskUserQuestion for material decisions (which approach, where to put a new module, etc.).

4. **Save the file** at `specs/features/<feature-name>/plan.md`.

5. **Tell the user** the plan is ready and wait for their review. Do not proceed to tasks.

## Template

```markdown
# <Feature title> — Implementation plan

**Status:** Plan — under review.
**Date:** <YYYY-MM-DD>.
**Spec:** [`spec.md`](spec.md).

## 1. Approach

One- or two-paragraph summary of how the spec becomes code. Name the key abstractions or files.

## 2. Affected modules

| Module / file | Change type | Note |
|---|---|---|
| `efootprint/...` | new / modified | ... |

## 3. Cross-cutting concerns

- **Tests:** what test layers (unit / integration / e2e) are affected, and what the new test coverage looks like at a glance.
- **Migrations:** if JSON schema or DB schema change, identify the migration path.
- **Docs:** what spec files (`architecture.md`, `conventions.md`) need to follow.

## 4. Risks

- Risk 1 — what could go wrong, mitigation.
- Risk 2 — ...

## 5. Alternatives considered

- Alternative A — why rejected.
- Alternative B — why rejected.

## 6. Constitutional notes

If the plan touches anything mentioned in constitution §1–§4, note it here. If anything in §4 is being relaxed, that's a constitutional amendment — stop and use `update-constitution` first.

## 7. Open questions

- Should be resolved before tasks are emitted.
```

## After writing

Tell the user:

- Path of the new plan file.
- A one-paragraph summary of the approach.
- Any constitutional / architectural notes worth flagging.
- The next step: human review, then `spec-tasks`.
