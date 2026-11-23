# Agent guidance — feature seed

Status: **pre-spec seed** (written 2026-11-18, updated 2026-11-23). No `spec.md` or `plan.md` yet.
This file captures the outcome of two design discussions so the feature can be picked up from a fresh session.
Next step: the cold-agent runs below, on the maintainer's signal, then `spec-specify` on this folder.
Library-only feature, so it lives here in `e-footprint/specs/features/`.

It comes after [`comparison-file`](../comparison-file/spec.md): the guide's lines on handing over a comparison
need that export.

## Goal

Let coding agents (GitHub Copilot, Claude Code, Codex, …) use the efootprint library efficiently, with guidance that
ships inside the package. The user-side instruction to an agent should shrink to: "pip install the latest efootprint,
then fetch its agent guide and follow it".

## Why ship it in the wheel

Version lock. Guidance that lives on GitHub `main` or on the docs site can be ahead of the version the agent actually
installed. Guidance inside the wheel always matches the installed code.

A package cannot set an agent's system prompt. What we ship is a **guide the agent fetches with one command**, and
the user's own instruction line is what gives it authority.

## Current state

Checked on 2026-11-18 (version 27.0.2) unless a line says otherwise.

- `ai_skills/ai_base_prompt_web_chat.md` is the existing prompt for web-chat use. It points at `docs_case.py` on GitHub
  `main` and at the docs site, so it is not version-locked. It is also interface-oriented (JSON export for upload,
  `form_inputs` timeseries constraint, comparison of two systems).
- `ai_skills/HOWTO try e-footprint with AI/` (the folder name holds a narrow no-break space) is a kit for
  non-technical users of a web chat: two prompts, a spreadsheet template and a beginner HTML page, all specific to
  GenAI video workflows.
- `docs_sources/doc_utils/docs_case.py`, the script that demonstrates all objects, is outside the package and therefore
  not in the wheel.
- Classes already carry agent-useful metadata: `param_descriptions`, `pitfalls`, `interactions`, `default_values`,
  `list_values`, `conditional_list_values`, plus the class docstring.
- The renderer that turns this metadata into the object reference is
  `docs_sources/doc_utils/generate_object_reference.py`, also outside the wheel. Descriptions use `{doc:<topic>}`
  placeholders resolved through `docs_sources/doc_utils/doc_topic_registry.py`, which registers six topics;
  `tests/test_descriptions.py` validates them.
- `efootprint/modeling_examples/` ships example JSON files (`introductory/ecommerce.json`,
  `how_to/machine_learning_workflow.json`) with registries, and `_authoring/` Python scripts next to them. The
  scripts are in the 27.0.2 wheel and read well as examples (checked 2026-11-23). Their `__main__` block rewrites the
  example JSON, so the guide tells agents to read them, not run them.
- Non-Python package data must be listed in `[tool.poetry] include` in `pyproject.toml`.
- `mkdocs.yml` already enables `pymdownx.snippets`, so a docs page can include a file of the package.
- `json_to_system` is version-aware (checked 2026-11-23): a file saved by another version is upgraded and
  recomputed, and its saved values are kept as a baseline. Exports carry saved values by default, and the guide says
  so.
- 27.1.0 made `viz` and `boaviztapi` optional: `pip install efootprint` is the lean core.

## Decided

### Where each piece of content goes

The hand-written guide is the residue: only what has no better home.

| Content | Home |
|---|---|
| Anything owned by one class | That class's `pitfalls` / `interactions`, reached through the per-class lookup |
| A cross-class how-to that already has a doc page | The doc page itself, shipped in the wheel and printed on demand |
| What is left | The hand-written guide |

### Doc topics ship in the wheel

The sources of the cross-class pages move into the package, so mkdocs and the command read the same files. This
mirrors moving the class renderer into the library. A `{doc:<topic>}` placeholder renders, in command output, as the
lookup command for that topic.

Topics to ship: `web_vs_edge`, `database_modeling`, `server_to_server_interaction`, `serverless_modeling`,
`machine_learning_workflow`, `usage_edge_index`.

Left out of the guide: `why_efootprint.md` and `get_started.md` (written to persuade and organise people), the
tutorial, and `docs_case.py`.

### What the guide holds

Targeting roughly 1–2k tokens, in documentation voice:

1. What efootprint models, in three lines.
2. The object graph: the web chain and the edge chain, built bottom-up.
3. The conventions common to every class: `SourceValue` with units, `from_defaults`, sources, countries, the
   timeseries builders.
4. A recommended workflow: a coarse model first, then refinement; an overview before any code; asking the user for
   the scale and, for AI, the model type. Condensed from `methodology.md` and the base prompt.
5. One small end-to-end snippet, executed by a test. `ecommerce.py` is about 1.4k tokens by itself, so it stays an
   on-demand example.
6. Reading the results: where the totals are, how to read the scale of the emissions, the over-provisioning check.
7. Export.
8. How to look up everything else: a class, a topic, the examples.

### No interface section

The library does not know the interface. The two facts the base prompt framed as interface rules are library facts:

- **Form-input timeseries.** The library keeps their human parameters (start date, growth rate), and the input diff
  of a comparison reads those instead of arrays. The guide recommends them on that ground.
- **Handing over a comparison.** Build a system, `duplicate_system`, change the copy, export both with the
  `comparison-file` export.

"Open the file in the interface" belongs to the interface's own prompt (its `start-from-ai-agent` feature).

### The `ai_skills/` folder is decommissioned

- **`ai_base_prompt_web_chat.md`**: harvested, then deleted.
  - The `raw_nb_of_instances` against `nb_of_instances` over-provisioning check goes to the server classes'
    `pitfalls`.
  - The `form_inputs` constraint goes to the timeseries builders' own descriptions.
  - `system_to_json` and the comparison recipe go to the guide's export section.
  - Reading the scale of the emissions goes to the guide's "reading the results" section.
  - Its behavioural lines become the recommended workflow.
- **The HOWTO kit**: deleted; git history keeps it. Its successor is the interface feature, where the prompts
  collapse into the bootstrap line plus the user's description.

### Other decisions

- **Command**: a module entry point, so agents never have to locate site-packages.
  ```bash
  python -m efootprint.agent_guide            # prints the guide
  python -m efootprint.agent_guide Server     # prints one class's reference
  python -m efootprint.agent_guide examples   # lists the shipped modeling examples
  ```
  A topic is looked up the same way. The name is still open (below).
- **Per-class reference generated from class metadata**, never hand-written. The rendering logic moves from
  `docs_sources/doc_utils/generate_object_reference.py` into the library so mkdocs and the command share one renderer.
- **The guide is published on the docs site** from the same file, through `pymdownx.snippets`.
- **Discovery pointers**: one line in the `efootprint/__init__.py` module docstring and at the top of the README
  (which is also the PyPI page): "AI agents: run `python -m efootprint.agent_guide`".
- **User-side bootstrap**: a two-line snippet users paste into `.github/copilot-instructions.md` or `AGENTS.md`
  (install efootprint, run the command, follow its output before writing modeling code). Documented in the README.

## Before the spec: cold-agent runs

Write the guide from failures, not from the docs. Give a cold agent only `pip install efootprint` and three briefs (a
web service, a GenAI feature, an edge fleet), and note what it gets wrong. The guide is the shortest text that fixes
those failures, and the same briefs become the spec's acceptance check.

Not run yet: they wait for the maintainer's signal, after the lean package release. Include the case of a web chat
with a sandbox but no shell of the user's own, which was the base prompt's scenario.

## Design principles

- **Progressive disclosure.** A small entry point plus on-demand lookups, not one big prompt that costs context on
  every task and grows with the library.
- **Documentation voice, not system-prompt voice.** Agents treat file and command output as data. Text written as
  "You are…" inside a package can look like prompt injection; plain "how to use this library" documentation does not.
- **Single source of truth.** Class metadata and the topic pages feed the docs site, the command and any `llms.txt`.
  No third hand-maintained copy.
- **Library-first.** The guide is about the library and names no consumer of its files.

## Alternatives considered

- **`llms.txt` on the docs site**: worthwhile complement for web-chat agents that have no shell. Generated from the
  same source. Not version-locked, which is acceptable there.
- **Agent Skill (`SKILL.md`)**: auto-triggers without the bootstrap line, but a copy in the user's repo drifts from
  the installed version. If added, keep it a stub that only runs the command.
- **MCP server**: rejected. Coding agents can already write Python against the library, so it would add a second API
  to maintain for no gain.

## Open questions for the spec stage

- Module and command name: `python -m efootprint.agent_guide`, or a subcommand of `python -m efootprint`?
- Scope: is `llms.txt` part of this feature or a follow-up? Same question for the skill stub.
- The registry also holds `methodology` and `why_efootprint`. A placeholder that points at one of them has to render
  in command output: ship those two pages as topics too, or reword the descriptions that cite them?
- Whether the per-class command output should also expose calculated attributes, or only inputs.
- Is the HOWTO kit linked from anywhere public (a post, a talk)? If so, its GitHub paths have to keep working until
  the interface entry exists.
- Which web chats can install efootprint in their sandbox, now that the core install is lean.
