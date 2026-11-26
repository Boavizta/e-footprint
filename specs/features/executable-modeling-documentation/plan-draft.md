# Executable modeling documentation — decisions held before planning

- This feature is driven from the library. Its spec is written here once; implementation plans
  belong in each affected repository under `executable-modeling-documentation`, with cross-repo
  dependencies declared when the pieces exist. No interface plan is created by this spec stage.
- Use Jupytext's `py:percent` format as the authoritative source: `# %%` code cells,
  `# %% [markdown]` prose cells, and cell metadata for selection. Authors edit the Python text;
  notebooks and rendered presentations are derived. Jupytext is development/documentation tooling,
  not a requirement for reading installed examples or using the core library.
- Keep canonical scenario sources under `efootprint/modeling_examples/`, with their packaged JSON
  and catalogue metadata. Reuse the existing introductory/how-to registries and their relationship
  between one scenario and several guides; settle exact paths and any registry simplification
  during planning. Do not maintain a separate handwritten script for the same scenario.
- Construct authored input timeseries throughout tutorials and packaged scenarios with the
  `efootprint.builders.timeseries` classes and their `form_inputs`:
  `ExplainableHourlyQuantitiesFromFormInputs`, `ExplainableRecurrentQuantitiesFromConstant`,
  and `ExplainableRecurrentQuantitiesFromWeeklyPattern`, as the scenario requires. Explain the
  temporal assumptions where each builder is used, including uniform demand within each day for
  the hourly-volume builder; hourly resolution does not imply arbitrary hourly variation.
  Retain only a short note that custom timeseries at hourly resolution are supported, but their
  values cannot be edited manually in the interface and must be updated in Python and re-exported.
  Do not carry custom-array construction or synthetic-array composition into the tutorial/how-to
  migrations. Custom arrays remain a supported option for data the builders cannot express.
- Generate both full documentation/notebooks and a coherent selection without plotting from the
  same source, preserving cell order and source wording apart from presentation and links. Split
  cells that both build the model and plot it. Select the accompanying prose too; chart-dependent
  assertions cannot remain in a reading that omits the chart.
- Start with a small tag vocabulary for visualization and notebook setup, plus stable section
  selection where several pages reuse a scenario. Do not remove Boavizta examples because they
  perform requests. Reading text never executes examples; running a documented example may call
  BoaviztAPI. Conversion is not execution, and saved notebook outputs are not agent-guide inputs.
- The e-commerce pilot should exercise the complete authoring-to-output path before the other
  migrations are detailed: its web tutorial, starter JSON, and the database/server-to-server
  excerpts. Use that review to refine the authoring conventions before IoT, ML and streaming.
  Delivery lots and implementation details await the plan and tasks stages.
- E-commerce's current source is
  `efootprint/modeling_examples/introductory/_authoring/ecommerce.py`; its baseline already uses
  Boavizta-backed web/database servers and editable hourly volumes. It becomes the web tutorial
  scenario. Preserve useful content from `tutorial.ipynb` through that tutorial or focused guides,
  including service builders, comparisons, attribution and explainability; do not keep a competing
  large streaming introduction. Multiple plot variants need not remain on the introductory path.
- The IoT source currently lives in the interface at
  `scripts/intro_example_scenarios/iot_industrial.py`; its JSON and picker registry are under
  `model_builder/domain/reference_data/modeling_examples/introductory/`.
  `scripts/build_intro_examples.py` currently regenerates it. Reuse the factory-sensors,
  cloud-upload and analyst-dashboard scenario, add `EdgeDeviceGroup` so a deployment represents a
  site, and make this the independent edge tutorial. Its server-communication extension also
  teaches a mixed model without requiring the web tutorial's session state.
- Move the IoT source and JSON ownership into the library. The interface consumes the library's
  example through its existing packaged-example lookup, as for e-commerce, and retains its picker
  presentation. The former `edge-example` requirements belong to this feature. The sibling
  checkouts for interface grounding are `../e-footprint-interface` and
  `../e-footprint-interface-worktree`.
- Convert the existing ML source and the streaming service-builder material to the same authoring
  format. The ML source is
  `efootprint/modeling_examples/how_to/_authoring/machine_learning_workflow.py`. Its labels and
  prose describe weekly retraining while the input currently specifies 12 runs per year; planning
  must make the described cadence and actual editable input agree, recording any changed assumption.
- Designate each starter's baseline before scenario experiments. Demonstrate `system_to_json` and
  ordered `systems_to_json` exports; use `duplicate_system` to preserve corresponding object ids.
  Demonstrate `materialize_serialized_state` when saved calculated values are required, without
  presenting it as necessary for interface import. Plots must not determine which values an
  export requires or which scenario becomes the starter.
- Existing authoring scripts expose `build_system()` while notebooks execute sequentially.
  Planning must choose a small explicit generation/execution contract, without forcing one
  pedagogical cell per function or importing an example just to read its source. Current authoring
  entry points overwrite packaged JSON; distinguish regeneration from demonstration exports to a
  user-selected location. Decide whether generated notebooks stay committed for direct use, and
  how stale generated artifacts are detected, in the plan.
- When replacing overlapping definitions in `docs_sources/doc_utils/docs_case.py`, preserve the
  class-reference examples they currently supply to `generate_object_reference.py`. Reuse actual
  scenario objects where useful and keep small explicit supplements for examples the scenarios
  do not supply. Check preservation with that replacement; do not expand tutorials merely to
  satisfy the class catalogue.
- General methodology remains conceptual and links to tutorial result inspection. Shared Python
  conventions have one canonical home; decide whether the remaining common material warrants the
  short `modeling_from_python` page after outlining the two tutorials. Workflow specific to
  collaborating with an AI belongs to `modeling_with_ai`; general export recipes belong to the
  shared executable material.
- This feature delivers reusable content without depending on the agent-guide command. The
  suspended `agent-guidance` plan is resumed using its `resume.md` only after these sources are
  delivered and reviewed; it consumes them and does not recreate them.
