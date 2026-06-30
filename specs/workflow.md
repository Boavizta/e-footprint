# Spec-driven workflow

This file is **canonical in e-footprint**. The version in `e-footprint-interface/specs/workflow.md` is a mirror — keep them identical.

When updating: edit this file, then copy it over the interface mirror.

---

## When to use this workflow

For **features that ship**: any change that adds capability, refactors a substantial pattern, or affects the user experience.

Exempt:

- Bug fixes that don't introduce a pattern.
- Small refactors with no API surface change.
- Investigations and design exploration. Live freely under `archives/investigations/` or in scratch files.

## The four stages

**Document formats.** `spec` and `plan` are authored as **self-contained HTML** (`spec.html`, `plan.html`) — they are write-once review documents where mockups, diagrams, tables, and collapsible sections aid review; the `spec-specify` / `spec-plan` skills carry the template (classless CSS inlined, no frameworks/CDNs). `tasks` stays **Markdown** (`tasks.md`): it is a living checklist edited as tasks are marked done, where clean one-line diffs matter more than rich rendering. All three are committed during the feature's life and deleted at archive (stage 5); durable insight is promoted to the live `.md` specs.

### 1. Specify

**Output:** `specs/features/<feature-name>/spec.html`.

A spec answers:

- What problem are we solving? Who for?
- Success criteria (testable).
- Scope: what's in / out.
- Open questions (will resolve in plan).

A spec does **not** prescribe code structure. It is read-only against the existing codebase.

Skill: `spec-specify` walks you through a template.

**Gate:** human reviews and approves the spec before plan starts.

### 2. Plan

**Output:** `specs/features/<feature-name>/plan.html`.

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

Skills: `task-implement` picks up a task and executes it. `task-review` reviews the resulting commit. Or run `feature-implement` to orchestrate the whole `tasks.md` end to end — it loops over tasks, spawning the implement and review sub-agents and pausing once per task for your decisions.

### 5. Archive

**Output:** the `specs/features/<feature-name>/` folder is deleted. **No archive summary file is ever written** — git history preserves the original spec / plan / tasks if anyone ever needs them, and a per-feature summary only duplicates the code or the live reference specs.

When all tasks have shipped:

1. **Promote durable insight into the live reference docs first — and keep them up to date.** Any decision, convention, or constraint that a future contributor or agent would need to make a sound call belongs in the live reference specs (`architecture.md` / `conventions.md` / `testing.md`), never in an archive nobody reads. Most of this should already have happened during implementation; this step is the final check that the reference docs reflect reality. This is the whole point of archiving: once the durable parts live where they belong, the spec folder is disposable.
2. **Delete `specs/features/<feature-name>/`** (including any untracked `spec.html` / `plan.html` — a tracked-files delete leaves those behind). Git history preserves everything.
3. **Update `CHANGELOG.md`** if not already done.

For cross-repo features, this happens in the driving repo (same rule as the feature folder).

## Skills location

Skills live at `.agents/skills/` in each repo. `.claude/skills` is a compatibility symlink. Canonical versions are in e-footprint; mirrors in e-footprint-interface.

## Investigations and ad-hoc work

Use the `archives/investigations/` folder. No spec required. When the investigation produces a feature decision, that decision can become the spec for a new feature.

## Constitution amendments

Constitutional changes use the `update-constitution` skill. They go in their own commit, separate from feature work. See `specs/constitution.md` §5.
