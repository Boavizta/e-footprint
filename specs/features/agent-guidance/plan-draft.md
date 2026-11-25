# Agent guidance — technical decisions held before the plan

Decisions as they stand, and what the trial runs established. The plan stage turns them into pieces
and deletes this file.

## The command and the guide

- The entry point is a module, `efootprint/agent_guide/`, run as `python -m efootprint.agent_guide`.
  An argument is tried as `examples`, then as a class name, then as a topic.
- All substantive guidance is authored in its owning documentation, including a page on modeling
  with an AI agent. Class semantics stay in doc-as-code metadata; runnable examples and recipes
  stay in executable sources also used by the documentation. No substantive advice or independent
  summaries are maintained only for the agent guide.
- The guide assembles those sources. Only selection, reading order, minimal transitions and link
  rendering are specific to the assembly. The plan chooses the simplest mechanism and when it
  runs. The sources needed by the command ship as package data, listed in `[tool.poetry] include`
  of `pyproject.toml`.
- Around 10,000 tokens is a starting allowance, not a hard ceiling. Planning measures the preview;
  coverage and reading order decide what stays. The trial briefs check whether the resulting
  guide prevents mistakes and reduces further exploration.
- It is written in documentation voice, never "You are…": an agent treats command output as data,
  and system-prompt voice inside a package reads as prompt injection.
- Include one full system script demonstrating broad web and edge object usage and the recommended
  modeling practices. Planning evaluates porting `docs_sources/doc_utils/docs_case.py` into the
  package as the canonical example, with the documentation generator consuming the same source.
  Examples and API recipes are included from executable sources and checked against the library,
  rather than copied into Markdown.
- `docs_case.py` currently demonstrates object coverage, not every modeling pattern: it uses
  random hourly volumes and raw recurrent arrays, leaves its device group outside the final
  system, and lacks results inspection and export. Plan its adaptation to editable timeseries,
  connected relationships and a complete modeling-to-export flow; settle optional integrations
  against the core-install and runnable-example rules. Remove redundant `source=None` at the
  canonical source if useful, rather than transforming the guide's copy; demonstrate meaningful
  sources for assumptions too.
- The guide tells agents to read the `_authoring` scripts, not to run them: their `__main__` block
  rewrites the example's JSON in the installed package.
- Its export section names `system_to_json`, `systems_to_json`, `duplicate_system` and
  `materialize_serialized_state`. The interface's import computes what a file lacks, so an agent
  need not materialize for it; it does when the saved values are the point. Document one single-system
  JSON file or one two-system comparison file, reference first and compared second, preserving
  corresponding object ids through duplication.
- The AI-modeling documentation owns the recommendation to use timeseries classes from
  `builders.timeseries` that retain `form_inputs`: their human parameters remain editable in the
  interface and readable in comparison input diffs. Custom arrays remain viewable but are not
  editable there; the workflow explains this tradeoff to the user before choosing them. The
  builders' own descriptions hold their class-specific constraints.

## The guide's reading order

- The reason for being and scope of the library, followed by its modeling methodology.
- The workflow with the user, from boundaries and consequential assumptions to an agreed model
  overview before coding; AI workloads include a question about the model being used.
- Web versus edge modeling and their object relationships.
- Builders: what defaults, external data or object wiring they supply, and what remains to check.
- Shared conventions, including units, sources, defaults, countries and the editable-timeseries
  recommendation before the example.
- The full maintained system script, with broad object usage and recommended modeling practices.
- How-tos by title and lookup command; class lookup commands for inputs, defaults, allowed values,
  pitfalls, interactions and computed attributes. Generate titles and commands from the registries.
- A short public explanation of lazy calculation, dependency tracking and recomputation. Ordinary
  modeling uses the public API; engine internals are relevant when investigating a suspected bug.
- Bug-report guidance: installed version, minimal reproducer, expected and actual behavior, and
  a likely explanation only when supported. Propose reporting to
  `https://github.com/Boavizta/e-footprint`; the user decides whether to submit.
- Results interpretation: totals, overall scale, dominant contributors, uncertainty and possible
  overprovisioning; finish with the single-system or ordered comparison-file output recipe.
- Other examples stay available through `examples` when needed. The default guide need not carry
  a second catalogue; object coverage in the full script does not establish coverage of every
  modeling pattern.

## Where each piece of content goes

| Content | Home |
|---|---|
| Anything owned by one class | That class's `pitfalls` / `interactions`, reached through the class lookup |
| Shared concepts, methodology and cross-class how-tos | The owning documentation page or section, reused in the guide where needed and printed as a topic where offered |
| User workflow, timeseries editability and output conventions | A canonical documentation page on modeling with an AI agent |
| Builders and public reactive-engine context | Owning user-facing documentation sections |
| Bug reporting | Contributor or support documentation |
| Runnable examples and API recipes | Executable sources shared by the documentation and the guide |
| How-to titles and lookup commands | Generated from the corresponding registries |
| Selection, reading order, minimal transitions and link rendering | The guide's assembly; the site shows the same assembled guide |

## The planning preview

- During planning, assemble a reviewable preview of the proposed default command output from the
  existing documentation and examples, in reading order. It shows the actual text, not just a
  table of contents, and marks missing sections explicitly.
- The plan identifies the source of each included part, gaps to fill, changes needed in the owning
  documentation, and checks for shared text and executable examples. Every substantive part must
  have a canonical documentation home, including newly authored guidance. Review the preview for
  repetition, missing context, website-only navigation and approximate token count.
- The preview is a planning artifact: it does not wire the command or change product behavior.
  Implementation improves the owning documentation, fills the marked gaps and builds the shared
  assembly. The preview is not a separately maintained copy of the shipped guide.

## The class reference

- It is generated from class metadata, never hand-written: the docstring, `param_descriptions`,
  `default_values`, `list_values`, `conditional_list_values`, `pitfalls`, `interactions`,
  `disambiguation`, and the docstrings of the computed attributes.
- The rendering logic moves from `docs_sources/doc_utils/generate_object_reference.py` into the
  library, so that mkdocs and the command share one renderer. It must import nothing of the
  optional groups nor of mkdocs.
- A `{class:X}` or `{doc:<topic>}` placeholder renders, in command output, as the lookup command.
  Only `{doc:web_vs_edge}` is used in descriptions today, four times.
  `docs_sources/doc_utils/doc_topic_registry.py` and `tests/test_descriptions.py` hold the
  placeholders.

## The topics

- The sources of the topic pages move from `docs_sources/mkdocs_sourcefiles/` into the package,
  and mkdocs reads them from there.
- Agreed list: `web_vs_edge`, `database_modeling`, `server_to_server_interaction`,
  `serverless_modeling`, `machine_learning_workflow`, `usage_edge_index`. Candidates the plan
  settles: `attributing_footprint` (a how-to of the site's navigation) and `hardware_edge_index`.
- `why_efootprint.md`, the scope documentation, `methodology.md` and `web_vs_edge.md` supply the
  opening explanations. Planning settles which complete pages or sections to include and what
  needs improving. These sources and the new guidance pages ship where needed by the assembly;
  planning settles which also become topic lookups. Source location does not change their status
  as canonical documentation.
- `get_started.md` and the tutorial stay outside the shipped topics. `docs_case.py` is a candidate
  for the shared package example, no longer excluded from package content.
- The guide's page on the site and the command use the same assembled content. Reuse the existing
  `pymdownx.snippets` support where it fits; the plan settles the rendering and inclusion mechanism.

## Pointers

- One line in the module docstring of `efootprint/__init__.py` and near the top of `README.md`:
  "AI agents: run `python -m efootprint.agent_guide`".
- The two lines for the user go in `README.md`, for `.github/copilot-instructions.md` or an
  `AGENTS.md`.
- `README.md` links `INSTALL.md` and `tutorial.ipynb` by relative path; neither is in the wheel,
  and neither resolves from PyPI.

## The `ai_skills/` folder goes

- `ai_base_prompt_web_chat.md` is harvested, then deleted:
  - the `raw_nb_of_instances` against `nb_of_instances` over-provisioning check goes to the server
    classes' `pitfalls`;
  - class-specific `form_inputs` constraints go to the timeseries builders' descriptions; the
    editability recommendation and user tradeoff go to the AI-modeling documentation;
  - `system_to_json` and the comparison recipe go to maintained executable sources included in
    the AI-modeling documentation and the guide's export section;
  - reading the scale of the emissions goes to the owning documentation, reused in the guide's
    results section;
  - its behavioural lines become the user workflow in the AI-modeling documentation, reused as
    the guide's way of working.
- `HOWTO try e-footprint with AI/` (the folder name holds a narrow no-break space) is deleted. Git
  history keeps it, nothing public links to it, and the interface's `start-from-ai-agent` is its
  successor.

## What the trial runs established

Three agents on efootprint 27.1.0 from PyPI, each with the installed package to read, no web and no
access to this checkout. No script failed. Each run cost about 20 tool calls and 127k to 136k
tokens. The five files they wrote pass the interface's import service on 27.1.0.

The briefs, to run again as the feature's acceptance check:

- **Web.** A booking platform for sports classes: 400,000 bookings a year in France, growing 15 %
  a year, mostly smartphones on mobile network, a Python API on autoscaling cloud VMs and a
  Postgres database on one dedicated server. Three years, a file for the interface with editable
  volumes, where the emissions come from and whether anything is oversized.
- **GenAI.** A support web app with 50,000 conversations a month from laptops on wifi, in France
  and Germany; an assistant adding about 6 calls of 800 output tokens to a mid-size hosted model.
  The journey compared without and with the assistant over two years, to open in the interface.
- **Edge.** Smart-building kits: one gateway (industrial PC, 4 cores, 8 GB) and 40 wired sensors of
  a few watts a building, 500 buildings a year for three years in France, eight years of service,
  an hourly upload to a small cloud server. What dominates: sensors, gateways or cloud.

What gave a wrong or fragile number silently, to become pitfalls of the owning class:

- `BoaviztaCloudServer` defaults `idle_power` to 0 W and `average_carbon_intensity` to 400 g/kWh
  whatever the usage pattern's country (`efootprint/builders/hardware/boavizta_cloud_server.py`).
- `ExplainableHourlyQuantitiesFromFormInputs` spreads a day's volume evenly over its 24 hours, so
  a "peak" is the average hour of the busiest day, and counts a month as 30 days and a year as 365.
- An edge device's `lifespan` must be at least the pattern's `usage_span`, and manufacturing is
  amortised over `lifespan`: a longer one counts only part of it.

The defects, fixed as one piece:

- The INFO log "Imported BoaviztaCloudServer in …" at the end of
  `efootprint/builders/hardware/boavizta_cloud_server.py` is removed.
- `initial_volume_unit` leaves the docstring of `ExplainableHourlyQuantitiesFromFormInputs`, and
  the two tests that pass it (`tests/api_utils_tests/test_source_serialization.py`,
  `tests/abstract_modeling_classes/test_explainable_object_base_class.py`). Nothing reads it, in
  the library or in the interface.
- A plain number where a `SourceValue` is expected fails today with
  `AttributeError: 'int' object has no attribute 'set_label'` (reproduced on `Job`).
- A second `System` on the objects of a first fails with a `PermissionError` from
  `check_no_object_to_link_is_already_linked_to_another_system` that does not mention
  `duplicate_system`.

Seen and left as it is: what `system_to_json` writes depends on what was read before, by design
(`materialize_serialized_state`). One agent's file went from 162 kB to 294 kB for an unchanged
model.

Limits of the runs: one a brief, on a strong model told it could read the package, so closer to a
ceiling than to an average agent. A web chat with a sandbox and no shell was not tried.
