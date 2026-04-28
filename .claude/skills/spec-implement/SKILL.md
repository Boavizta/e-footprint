---
name: spec-implement
description: Use to execute a single task from an approved tasks.md. Fourth stage of the four-stage spec-driven workflow. Reads spec.md, plan.md, tasks.md, then implements one task at a time, respecting constitution gates.
---

# spec-implement

You are about to implement one task from an approved tasks list.

## Process

1. **Confirm which feature and which task.** Read `specs/features/<feature-name>/tasks.md`. The user must name a specific task or pick the first uncompleted one.

2. **Read the spec, plan, and tasks** for this feature in full. Read `specs/architecture.md` and `specs/conventions.md`. Read `specs/constitution.md` for the quality gates.

3. **Implement the task.** Touch only the files listed in the task. If you need to touch more, stop and surface it.

4. **Run quality gates** from `specs/constitution.md` §2:
   - Tests pass.
   - Any other repo-specific gates (mkdocs build, JSON round-trip, schema migration, CHANGELOG entry).

5. **Update `tasks.md`** to mark the task done (e.g. add a `**Status:** Done` line under it).

6. **Tell the user** what was implemented, what tests pass, what's left in the tasks list.

## Constraints

- One task at a time. Do not chain into the next task without user confirmation.
- If a task reveals a missing dependency or an incorrect plan assumption, **stop and surface it** rather than expanding scope.
- If you discover an unrelated bug, follow constitution §3.1: fix on the spot or surface it. Do not paper over.
