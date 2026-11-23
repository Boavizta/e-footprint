# Agent guidance — technical decisions held before the plan

Decisions as they stand, and what the trial runs established. The plan stage turns them into pieces
and deletes this file.

## The command and the guide

- The entry point is a module, `efootprint/agent_guide/`, run as `python -m efootprint.agent_guide`.
  An argument is tried as `examples`, then as a class name, then as a topic.
- The guide is a hand-written Markdown file shipped as package data. Non-Python package data is
  listed in `[tool.poetry] include` of `pyproject.toml`.
- It is written in documentation voice, never "You are…": an agent treats command output as data,
  and system-prompt voice inside a package reads as prompt injection.
- Its one model is small. `efootprint/modeling_examples/introductory/_authoring/ecommerce.py` is
  about 1.4k tokens by itself and stays an example the guide points at.
- The guide tells agents to read the `_authoring` scripts, not to run them: their `__main__` block
  rewrites the example's JSON in the installed package.
- Its export section names `system_to_json`, `systems_to_json`, `duplicate_system` and
  `materialize_serialized_state`. The interface's import computes what a file lacks, so an agent
  need not materialize for it; it does when the saved values are the point.
- Form-input timeseries are recommended as a library fact: their human parameters are kept, and
  the input diff of a comparison reads them instead of arrays.

## Where each piece of content goes

| Content | Home |
|---|---|
| Anything owned by one class | That class's `pitfalls` / `interactions`, reached through the class lookup |
| A cross-class how-to that has a documentation page | The page, shipped in the package and printed as a topic |
| What is left | The guide |

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
- Not shipped: `why_efootprint.md`, `get_started.md`, `methodology.md` (its loop is condensed in
  the guide), the tutorial, `docs_sources/doc_utils/docs_case.py`.
- The guide's page on the site includes the package's file through `pymdownx.snippets`, already
  enabled in `mkdocs.yml`.

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
  - the `form_inputs` constraint goes to the timeseries builders' descriptions;
  - `system_to_json` and the comparison recipe go to the guide's export section;
  - reading the scale of the emissions goes to the guide's results section;
  - its behavioural lines become the way of working.
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
