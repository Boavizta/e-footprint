# Spec-driven workflow

This file is **canonical in e-footprint**. The version in `e-footprint-interface/specs/workflow.md` is a mirror — keep them identical. A test in each repo asserts content equality.

When updating: edit this file, then run `scripts/sync_workflow.sh` (or copy manually).

---

## When to use this workflow

For **features that ship**: any change that adds capability, refactors a substantial pattern, or affects the user experience.

Exempt:

- Bug fixes that don't introduce a pattern.
- Small refactors with no API surface change.
- Investigations and design exploration. Live freely under `archives/investigations/` or in scratch files.

## The four stages

### 1. Specify

**Output:** `specs/features/<feature-name>/spec.md`.

A spec answers:

- What problem are we solving? Who for?
- Success criteria (testable).
- Scope: what's in / out.
- Open questions (will resolve in plan).

A spec does **not** prescribe code structure. It is read-only against the existing codebase.

Skill: `spec-specify` walks you through a template.

**Gate:** human reviews and approves the spec before plan starts.

### 2. Plan

**Output:** `specs/features/<feature-name>/plan.md`.

A plan answers:

- Approach: how does the spec become code?
- Affected modules and files.
- Risks and alternatives considered.
- Cross-cutting concerns (tests, migrations, docs).

The plan respects `specs/architecture.md`. If it requires deviating from architecture, the deviation is called out and resolved before the plan ships.

Skill: `spec-plan` walks you through a template.

**Gate:** human reviews and approves the plan before tasks are emitted.

### 3. Tasks

**Output:** `specs/features/<feature-name>/tasks.md`.

A tasks file lists:

- Ordered, independently-shippable steps.
- For each step: files to touch, tests to add, acceptance criteria.

Each task should be small enough to ship as one PR.

Skill: `spec-tasks` walks you through a template.

**Gate:** human reviews task ordering and completeness before implementation begins.

### 4. Implement

For each task in `tasks.md`:

1. Implement.
2. Run quality gates from `specs/constitution.md`.
3. Mark the task done in `tasks.md` and commit.
4. Run `task-review` on the commit — review findings with the agent, address what's worth fixing before moving on.
5. Open PR titled `[<feature-name>] <task summary>`.

Each task ships independently. The feature is complete when all tasks are done.

Skills: `task-implement` picks up a task and executes it. `task-review` reviews the resulting commit.

## Skills location

Skills live at `.claude/skills/` in each repo. Canonical versions are in e-footprint; mirrors in e-footprint-interface.

## Investigations and ad-hoc work

Use the `archives/investigations/` folder. No spec required. When the investigation produces a feature decision, that decision can become the spec for a new feature.

## Constitution amendments

Constitutional changes use the `update-constitution` skill. They go in their own commit, separate from feature work. See `specs/constitution.md` §5.
