# AGENTS — e-footprint

This file orients agents and contributors. It is intentionally short. Substance lives under `specs/`.

## Read this first

1. **`specs/constitution.md`** — the project's immutable rules. Every change respects them.
2. **`specs/mission.md`** — what e-footprint is and isn't.

## Where things live

| If you need... | Read |
|---|---|
| Architecture and core patterns (modeling structure, ExplainableObject, dependency graph) | `specs/architecture.md` |
| Code style, modeling refactor preferences, agent behaviour rules | `specs/conventions.md` |
| Testing patterns and what TO / NOT TO test | `specs/testing.md` |
| Tech stack and version bounds | `specs/tech_stack.md` |
| What's planned and in flight | `specs/roadmap.md` |
| The spec-driven workflow (specify → plan → tasks → implement) | `specs/workflow.md` |
| Active feature work | `specs/features/<feature-name>/` |
| Past investigations and dated decisions | `archives/` |

## Dev commands

```bash
poetry install --with dev
poetry run pytest                              # full suite
poetry run pytest tests/path/to/test_file.py   # single test
mkdocs serve                                   # local docs preview
```

For full setup, see [`INSTALL.md`](INSTALL.md). For release, see [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

## Spec-driven workflow at a glance

Feature work follows four stages, each gated by your review:

1. **Specify** — write `specs/features/<name>/spec.md` (problem, scope, success criteria). Skill: `spec-specify`.
2. **Plan** — write `plan.md` (approach, affected modules, risks). Skill: `spec-plan`.
3. **Tasks** — write `tasks.md` (ordered, independently-shippable steps). Skill: `spec-tasks`.
4. **Implement** — execute one task at a time, respecting constitution gates. Skill: `task-implement`.

Investigations and ad-hoc design work are exempt; the four-stage flow is for features that ship.

## Documentation upkeep

When you implement a non-trivial pattern (new relationship type, new calculated-attribute pattern, serialization change), update the relevant spec file (`specs/architecture.md`, `specs/conventions.md`, or `specs/testing.md`) — a one-line mention in the right section is enough. The goal is to keep specs accurate so future agents don't rediscover patterns from code.
