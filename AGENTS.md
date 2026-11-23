# AGENTS — e-footprint

This file orients agents and contributors. It is intentionally short. Substance lives under `specs/`.

## Read this first

1. **`specs/constitution.md`** — the project's immutable rules. Every change respects them.
2. **`specs/mission.md`** — scope, audience, and eco-design priorities for weighing user value against complexity.

## Where things live

| If you need... | Read |
|---|---|
| Architecture and core patterns (modeling structure, ExplainableObject, dependency graph) | `specs/architecture/index.html` |
| Conditional input rules, final-batch validation, and failed-construction cleanup | `specs/architecture/relationships.html#conditional-inputs` and `specs/architecture/recomputation/lifecycle.html` |
| Derived internal-parent relationships and live contextual wrappers | `specs/architecture/relationships.html` |
| Ready-made modeling examples and guides | `efootprint/modeling_examples/` and `specs/architecture/layers-and-modeling.html` |
| Code style, modeling refactor preferences, agent behaviour rules | `specs/conventions.md` |
| Testing patterns and what TO / NOT TO test | `specs/testing.md` |
| Tech stack and version bounds | `specs/tech_stack.md` |
| Adjacent/complementary tools and ecosystem positioning | `specs/adjacent_tools.md` |
| What's planned and in flight | `specs/roadmap.md` |
| Modeling-method questions needing scientific grounding (ship honest fallback, avoid false precision) | `specs/modeling_logic_roadmap.md` |
| Lifecycle-phase and "embodied" definitions (sourced, digital/ICT scope) | `docs_sources/mkdocs_sourcefiles/environmental_footprint_definitions.md` |
| The spec-driven workflow (specify → plan → tasks → implement → archive) and the forms of a feature's files | `specs/workflow.md`, `specs/workflow-formats.md` |
| The comprehension tools (the narrative and plan pages, the map), how they are installed, and what this project gives them | [`comprehension_harness/README.md`](comprehension_harness/README.md), `comprehension.config.json`, `.agents/repository.md` § "The stack" |
| Active feature work | `specs/features/<feature-name>/` |
| A bug batch's `plan.html`: source links, one-click reproduction debugging, decision indexes and callouts | `.agents/skills/spec-plan/references/plan-review-links.md` and `.agents/skills/spec-plan/references/plan-decision-callouts.md` |
| A bug batch's final plan review guide (preserved structure, implementation links, consolidated decisions) | `.agents/skills/plan-review-guide/SKILL.md`; delegated at `feature-implement` close-out to the `plan-review-guide` agent, with supervisor-owned decisions |
| Past investigations and dated decisions | `archives/` |

In a bug batch's plan, HTML documentation links open in a new browser tab; production source links (including HTML templates) open in VS Code. See the plan-link convention above.

## Dev commands

```bash
poetry install --with dev --all-extras   # all-extras: viz + boaviztapi optional groups
poetry run pytest                              # full suite
poetry run pytest tests/path/to/test_file.py   # single test
mkdocs serve                                   # local docs preview

# Development tooling only (the comprehension harness): the library itself needs no Node
npm install
npm run map                                    # the narratives, one line each
npm run comprehension:render                   # the narrative and plan pages, under specs/comprehension_harness/
```

For full setup, see [`INSTALL.md`](INSTALL.md). For release, see [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

## Spec-driven workflow at a glance

Feature work follows five stages, with a person approving between them. `specs/workflow.md` says
what each is for and who approves what.

1. **Specify** — `specs/features/<name>/spec.md`: the problem, the change, the rules no test shows by itself. Skill: `spec-specify`.
2. **Plan** — the plan is written into the code as pieces (planned calls, planned tests) and a short `plan.md`; the reviewer reads the plan page generated from them and approves it. Skill: `spec-plan`.
3. **Tasks** — the delivery: the pieces cut into lots, with the unit tests of each. Skill: `spec-tasks`.
4. **Implement** — one lot a run: built, checked against the approved plan, reviewed. Skills: `feature-implement`, `task-implement`, `task-review`.
5. **Archive** — durable facts promoted to the reference docs, the feature folder deleted. Skill: `feature-archive`.

Stages 2 to 4 run on the Python stack of the comprehension tools: the `narrate`, `event` and
`planned` calls of `efootprint/narrate.py`, and the test declarations and the three commands of
`comprehension_harness/python/` (`.agents/repository.md` § "The stack" says how each is spelled,
and where a call may stand). `efootprint/narrate.py` is this project's copy of the stack's
reference file: the library imports the calls from it, and nothing of the harness. A feature in
flight on `plan.html` and `tasks.md` is finished by hand.

Investigations and ad-hoc design work are exempt; the staged flow is for features that ship.
Conversational bug batches use `bug-fixes` (diagnostics plus `tasks.md`), then `bug-fixes-plan` (`plan.html` grouping the bugs and ordering the runs), followed by the implement, review and archive stages.

## Documentation upkeep

When you implement a non-trivial pattern (new relationship type, new calculated-attribute pattern, serialization change), update the owning page under `specs/architecture/`, `specs/conventions.md`, or `specs/testing.md` — a one-line mention in the right section is enough. The goal is to keep specs accurate so future agents don't rediscover patterns from code.

## Git commit style

Prefix your commit messages with the relevant tag among [FIX], [REFACTO], [ADD], [REMOVE], [OPTIM], [UPDATE]. The user might specify another tag. Always use brackets and uppercase. Example: `[FIX] Handle missing data in timeseries rendering`.

## Parked: Docker Hub publish

Publishing the Docker image to Docker Hub was judged premature (2026-07-01) and parked. The `Dockerfile` itself landed (local `docker build`/`docker run` works, no registry needed) but `.github/workflows/docker-publish.yml` and the Docker Hub prose in `README.md`/`RELEASE_PROCESS.md` were removed. **Revisit in October 2026** — re-read `specs/features/packaging-and-dx/spec.html` (Task 3) before re-adding the publish workflow.

## Shared agent tooling

Workflow roles, synchronization and private usage collection: [`specs/agent-tooling.md`](specs/agent-tooling.md).
Repository-specific skill adaptations: [`.agents/repository.md`](.agents/repository.md).
