# Agent guidance — feature seed

Status: **pre-spec seed** (written 2026-11-18). No `spec.html`, `plan.html` or `tasks.md` yet.
This file captures the outcome of a design discussion so the feature can be picked up from a fresh session.
Next step: run `spec-specify` on this folder. Library-only feature, so it lives here in `e-footprint/specs/features/`.

## Goal

Let coding agents (GitHub Copilot, Claude Code, Codex, …) use the efootprint library efficiently, with guidance that
ships inside the package. The user-side instruction to an agent should shrink to: "pip install the latest efootprint,
then fetch its agent guide and follow it".

## Why ship it in the wheel

Version lock. Guidance that lives on GitHub `main` or on the docs site can be ahead of the version the agent actually
installed. Guidance inside the wheel always matches the installed code.

Reframing agreed in the discussion: a package cannot set an agent's system prompt. What we ship is a **guide the agent
fetches with one command**, and the user's own instruction line is what gives it authority.

## Current state (checked on 2026-11-18, version 27.0.2)

- `ai_skills/ai_base_prompt_web_chat.md` is the existing prompt for web-chat use. It points at `docs_case.py` on GitHub
  `main` and at the docs site, so it is not version-locked. It is also interface-oriented (JSON export for upload,
  `form_inputs` timeseries constraint, comparison of two systems).
- `docs_sources/doc_utils/docs_case.py`, the script that demonstrates all objects, is outside the package and therefore
  not in the wheel.
- Classes already carry agent-useful metadata: `param_descriptions`, `pitfalls`, `interactions`, `default_values`,
  `list_values`, `conditional_list_values`, plus the class docstring.
- The renderer that turns this metadata into the object reference is
  `docs_sources/doc_utils/generate_object_reference.py`, also outside the wheel. Descriptions use `{doc:<topic>}`
  placeholders resolved through `docs_sources/doc_utils/doc_topic_registry.py`; `tests/test_descriptions.py` validates
  them.
- `efootprint/modeling_examples/` ships example JSON files (`introductory/ecommerce.json`,
  `how_to/machine_learning_workflow.json`) with registries, and `_authoring/` Python scripts next to them.
- Non-Python package data must be listed in `[tool.poetry] include` in `pyproject.toml`.

## Design seeds

These are starting points for the plan stage, not decisions.

1. **Short hand-written guide** shipped as package data, e.g. `efootprint/agent_guide/AGENTS.md`, targeting roughly
   1–2k tokens. Content: mental model of the object graph, modeling workflow, rules that span several classes, how to
   export a system to JSON, and how to look up everything else.
2. **CLI entry point** so agents never have to locate site-packages:
   ```bash
   python -m efootprint.agent_guide            # prints the guide
   python -m efootprint.agent_guide Server     # prints one class's reference
   python -m efootprint.agent_guide examples   # lists the shipped modeling examples
   ```
3. **Per-class reference generated from existing class metadata**, never hand-written. Move the rendering logic from
   `docs_sources/doc_utils/generate_object_reference.py` into the library so mkdocs and the CLI share one renderer.
4. **Runnable examples in the wheel**: point the guide at the `modeling_examples/*/_authoring` scripts instead of
   `docs_case.py`.
5. **A test that executes every code snippet in the guide**, so the guide cannot rot.
6. **Discovery pointers**: one line in the `efootprint/__init__.py` module docstring and at the top of the README
   (which is also the PyPI page): "AI agents: run `python -m efootprint.agent_guide`".
7. **User-side bootstrap**: a two-line snippet users paste into `.github/copilot-instructions.md` or `AGENTS.md`
   (install efootprint, run the command, follow its output before writing modeling code). Document it in the README.

## Design principles

- **Progressive disclosure.** A small entry point plus on-demand class lookups, not one big prompt that costs context
  on every task and grows with the library.
- **Documentation voice, not system-prompt voice.** Agents treat file and command output as data. Text written as
  "You are…" inside a package can look like prompt injection; plain "how to use this library" documentation does not.
- **Single source of truth.** Class metadata feeds the docs site, the CLI reference and any `llms.txt`. No third
  hand-maintained copy.
- **Library-first.** The guide is about the library. Interface export is one section of it, not its framing.

## Alternatives considered

- **`llms.txt` on the docs site**: worthwhile complement for web-chat agents that have no shell (the use case of the
  existing prompt). Generated from the same source. Not version-locked, which is acceptable there.
- **Agent Skill (`SKILL.md`)**: auto-triggers without the bootstrap line, but a copy in the user's repo drifts from
  the installed version. If added, keep it a stub that only runs the CLI.
- **MCP server**: rejected. Coding agents can already write Python against the library, so it would add a second API
  to maintain for no gain.

## Open questions for the spec stage

- Module and command name: `python -m efootprint.agent_guide`, or a subcommand of `python -m efootprint`?
- Scope: is `llms.txt` part of this feature or a follow-up? Same question for the skill stub.
- What happens to `ai_skills/ai_base_prompt_web_chat.md`: rewrite it on top of the guide, keep it separate, or retire
  it?
- How much interface-specific guidance (editable timeseries, two-system comparison) belongs in a library guide.
- How `{doc:<topic>}` placeholders render in CLI output: docs URL, plain text, or dropped.
- To verify: that the `_authoring` scripts are actually included in the built wheel, and that they read well as
  examples for an agent (otherwise a dedicated example script is needed).
- Whether the per-class CLI output should also expose calculated attributes, or only inputs.
