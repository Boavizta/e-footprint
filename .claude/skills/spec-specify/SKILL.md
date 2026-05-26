---
name: spec-specify
description: Use when the user wants to start a new feature in this repo. Walks the agent through writing specs/features/<feature-name>/spec.md — the first stage of the four-stage spec-driven workflow (specify → plan → tasks → implement). Read-only on code. May also draft plan.md in the same pass when the kickoff is design-rich.
---

# spec-specify

You are about to start a new feature spec. Do NOT write any code or modify any source files. The primary output is `specs/features/<feature-name>/spec.md`. When the kickoff is design-rich (see Process step 3), you also draft `plan.md` in the same pass so design detail is not lost.

## What goes where

- **`spec.md` = WHAT and WHY.** Capability, audience, why-now, success criteria phrased as user-observable outcomes, in/out scope at the capability level, constraints (mission / constitution / external dependencies).
- **`plan.md` = HOW.** Module layout, class/method/parameter names, defaults, internal hypotheses, refactor steps, code-level patterns to mirror, file paths, unit/mapping tables.

If you can't write a sentence without naming a file, class, or method, it's plan content.

## Process

1. **Confirm the feature name** with the user (kebab-case, descriptive). If the slot already exists at `specs/features/<feature-name>/`, stop and ask whether to overwrite or pick a different name.

2. **Read `specs/mission.md` and `specs/constitution.md`** before drafting. The spec must be in scope per `mission.md` and respect `constitution.md`. If it isn't, surface the conflict before writing.

3. **Classify accumulated context.** Audit the prior conversation for design-level signals: file paths, class/method names, parameter defaults, refactor instructions, citations of existing-code patterns to copy, decisions made about provider/model splits, where-things-live, internal vs external parameters, etc. If load-bearing design content is already in the conversation, drafting only `spec.md` will either (a) discard that content or (b) leak it into the spec. In that case, produce **both** `spec.md` and a draft `plan.md` in this same pass. Tell the user explicitly that you're producing two files and why. If the conversation is purely capability-framed, draft only `spec.md`.

4. **Draft the spec** following the template below. Use AskUserQuestion for any unclear *capability-level* question (audience, user outcome, in/out scope). Do not invent answers. Do **not** ask design-level questions here — those go to `spec-plan`. If the user volunteers a design decision, capture it for `plan.md` instead of folding it into the spec.

5. **Draft the plan (if step 3 triggered it).** Follow the `spec-plan` template. The plan is explicitly marked as a draft and the user is invited to refine it during the `spec-plan` stage (which is now a refinement pass — see that skill).

6. **Self-check.** Re-read the spec. For each bullet in §3, ask: *is this a capability the user experiences, or a how-we-build-it decision?* If the latter, move it to `plan.md`.

7. **Save the file(s).**

8. **Tell the user** the spec (and plan, if drafted) is ready and wait for their review. Do not proceed to tasks.

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

*Capability-level only. File paths, class/method/parameter names, refactor instructions, internal hypotheses, and "mirror pattern X" code-level decisions belong in `plan.md`, not here. If you can't say it without naming a file, class, or method, it's plan content.*

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

- Path(s) of the new file(s) — `spec.md`, and `plan.md` if you drafted one.
- A one-paragraph summary of the spec.
- If a plan was drafted: a one-sentence note that it captured design content from the kickoff conversation and will be refined in the `spec-plan` stage.
- Any open questions surfaced during drafting.
- The next step: human review, then `spec-plan`.
