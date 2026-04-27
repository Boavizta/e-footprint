---
name: spec-specify
description: Use when the user wants to start a new feature in this repo. Walks the agent through writing specs/features/<feature-name>/spec.md — the first stage of the four-stage spec-driven workflow (specify → plan → tasks → implement). Read-only on code.
---

# spec-specify

You are about to start a new feature spec. Do NOT write any code or modify any source files. The output is a single new file: `specs/features/<feature-name>/spec.md`.

## Process

1. **Confirm the feature name** with the user (kebab-case, descriptive). If the slot already exists at `specs/features/<feature-name>/`, stop and ask whether to overwrite or pick a different name.

2. **Read `specs/mission.md` and `specs/constitution.md`** before drafting. The spec must be in scope per `mission.md` and respect `constitution.md`. If it isn't, surface the conflict before writing.

3. **Draft the spec** following the template below. Use AskUserQuestion for any unclear scope or audience question; do not invent answers.

4. **Save the file** at `specs/features/<feature-name>/spec.md`.

5. **Tell the user** the spec is ready and wait for their review. Do not proceed to plan.

## Template

```markdown
# <Feature title>

**Status:** Spec — under review.
**Date:** <YYYY-MM-DD>.

## 1. Problem and audience

- What user problem does this solve?
- Who experiences it (user persona, frequency, severity)?
- Why is it worth solving now?

## 2. Success criteria

How do we know this feature is done? Each criterion must be testable.

- ...
- ...

## 3. Scope

### In scope

- ...

### Out of scope (this iteration)

- ...

## 4. UX / interface (if applicable)

If the feature has a user-facing surface, describe it at the conceptual level — not implementation.

## 5. Constraints

- Performance, compatibility, dependencies, regulatory, etc.
- References to constitution.md or architecture.md if applicable.

## 6. Open questions

- ...

## 7. Resuming from cold context

1. Read this file end to end.
2. Read `plan.md` (when written) for ordered steps and test gates.
3. Re-read the relevant spec files (`specs/architecture.md`, `specs/conventions.md`) for code-style and architectural constraints.
```

## After writing

Tell the user clearly:

- Path of the new spec file.
- A one-paragraph summary of the spec.
- Any open questions surfaced during drafting.
- The next step: human review, then `spec-plan`.
