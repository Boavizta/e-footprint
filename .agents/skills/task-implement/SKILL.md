---
name: task-implement
description: Execute one task from an approved tasks.md, using spec.html and plan.html for a feature or a linked diagnostic for a bug batch, while respecting constitution gates.
---

# task-implement

You are about to implement one task from an approved tasks list.

## Process

1. **Confirm which feature and which task.** Read `specs/features/<feature-name>/tasks.md`. The user must name a specific task or pick the first uncompleted one.

2. **Load the task's intent.** Read `tasks.md` in full. For a normal feature, read `spec.html` and `plan.html` in full. For a bug-fix batch with neither file, the selected task must contain a `**Diagnostic:**` link; read that diagnostic in full instead. If the feature has neither spec/plan nor a linked diagnostic, stop. Start at `specs/architecture/index.html`, follow its task routing to the owning architecture pages, and read `specs/conventions.md`. Read `specs/constitution.md` for the quality gates.

3. **Implement the task.** Touch only the files listed in the task. If you need to touch more, stop and surface it.

4. **Run quality gates** from `specs/constitution.md` §2:
   - Tests pass.
   - Any other repo-specific gates (mkdocs build, JSON round-trip, schema migration, CHANGELOG entry).
   - **CHANGELOG entry:** add it now if you are running standalone. If you were briefed by `feature-implement` to skip it, don't — the supervisor writes one consolidated `## [Unreleased]` entry for the whole feature once every task is done.

5. **Update `tasks.md`** to mark the task done (e.g. add a `**Status:** Done` line under it).

6. **Commit the task.** Stage all changes and commit with a message following the repo convention:
   - Prefix: pick one of `[ADD]`, `[UPDATE]`, `[FIX]`, `[REFACTO]`, `[REMOVE]` based on the nature of the task.
   - Body: `<feature-name>: <task title from tasks.md>`.
   - Example: `[ADD] source-block: hoist inline sources to top-level Sources block`.
   This scopes the diff so `task-review` can analyse it cleanly.

7. **Tell the user** what was implemented, what tests pass, what's left in the tasks list. Also remind the user to run the `task-review` skill on the task.

## Constraints

- One task at a time. Do not chain into the next task without user confirmation.
- If a task reveals a missing dependency or an incorrect plan or diagnostic assumption, **stop and surface it** rather than expanding scope.
- If you discover an unrelated bug, follow constitution §3.1: fix on the spot or surface it. Do not paper over.
- **Never reference spec documents in code comments or any production/test file.** Do not mention task numbers (e.g. "Task 3"), spec section markers (e.g. "§4.2"), plan paragraphs, or feature names from the spec workflow (e.g. "model-comparison Task 4"). Spec documents are deleted after the archiving step; any such reference becomes a dangling pointer and leaks implementation-process noise into the codebase. Describe the *why* of the code in plain terms instead.
