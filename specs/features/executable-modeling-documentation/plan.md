# Executable modeling documentation

A scenario is one sequential Jupytext Python source. The baseline is its initial complete
`system`; a starter is the packaged JSON of that model. An experiment duplicates that original
system before changing the duplicate. All experiments run in source order, without cleanup or
independent experiment selection.

## #source-format

Define percent-cell selection for complete tutorials, versions without plots, construction-only generation and the existing focused guides.

Keep the source valid Python. Plot-tagged cells include plotting imports and chart-dependent prose; without-plots also omits notebook setup. Use Jupytext instead of maintaining another parser. Selection accepts only the published views, without dependency inference.

## #catalogue

Extend the existing example and guide registries with source and reading paths, tutorial destinations and explicit guide sections.

Keep introductory examples and how-to scenarios as their existing owners, with several guides allowed per scenario. Output-free Markdown beside each packaged JSON gives installed consumers complete explanations without Jupytext, execution or notebook outputs. Listing metadata and reading paths remain passive.

## #baseline-generation

Regenerate packaged inputs-only JSON explicitly from each source's initial construction, isolated from notebook execution and later experiments.

Fresh kernels set name-based object and source ids before scenario imports, preserving reviewable JSON without leaking process globals. The regenerate command targets the catalogue JSON by scenario id and appends saving after construction. Construction-only execution omits plots and notebook setup.

## #ecommerce-tutorial

Turn the existing e-commerce scenario into the main web tutorial, retaining its initial model and teaching a comparison on a duplicate.

Teach infrastructure, jobs, journeys, geographic demand, numerical results, attribution and explainability with explicit assumptions. Keep Boavizta-backed servers and editable volumes. Review this pilot's generated outputs before migrating IoT, ML and streaming.

## #focused-guides

Replace the database and server-to-server sketches with explicitly selected prose and code from e-commerce.

Select imports and required earlier sections in source order, without inferred dependencies. Explain the same on-premise database and autoscaling web server as the tutorial, replacing the conflicting serverless sketch. Each guide includes its prerequisites and links to the full tutorial for result inspection and delivery; neither invents another model.

## #edge-tutorial

Introduce `EdgeDeviceGroup` as a sensor-site template in the independent Industrial IoT tutorial and packaged example, with one deployment representing one site.

Fifteen sites of fifty sensors preserve the existing 750-sensor rollout: one month of starts, six-year device usage, three-year dashboard demand. Keep these periods and constant recurrent demand explicit. The interface must consume the library entry and retire its local IoT source, JSON and regeneration entry through a companion plan authored there; picker presentation stays.

## #ml-guide

Convert machine learning into a complete executable how-to with editable demand and consistent retraining labels.

Keep training and inference as separate patterns and document the hourly builder's smoothing; do not claim it creates scheduled training bursts.

Keep 12 training runs per year and describe an annual retraining volume spread uniformly across hours, correcting the weekly and monthly labels.

## #streaming-guide

Extract the streaming service-builder lesson into a focused executable scenario and retire the competing introductory notebook.

Retain service installation, derived job resources and an editable demand projection. Explain replacement of the old synthetic daily and seasonal arrays with the hourly-volume builder's smooth projection. Move reusable inspection, comparison, attribution and explainability teaching into e-commerce; move introductory edge teaching into IoT. Multiple chart variants and reset demonstrations need not survive.

## #interface-exports

Teach single-model and ordered comparison exports independently of Python plotting, using duplicates that preserve corresponding object ids.

E-commerce owns the general export explanation; IoT applies it and links back. Set output_dir near the source's start for reader-chosen destinations, separate from package regeneration. Use system_to_json, reference-first systems_to_json and optional materialize_serialized_state when complete calculated values are wanted; inputs-only import remains valid.

## #presentations

Generate downloadable notebooks and output-free readings by conversion, and publish tutorials and guides with executed results through the existing documentation build.

Commit cleared notebooks under notebooks/. Execute documentation in fresh kernels with separate output directories. Replace content-specific regex rewriting with notebook export and explicit resource embedding; a failed execution stops the build.

## #reference-examples

Kind: refactoring

Replace the overlapping broad documentation model with packaged scenario objects and small explicit supplements, preserving the existing class-reference coverage.

Load packaged baselines for reference examples; supplement only classes those tasks do not supply. Select one object per concrete class for page generation, preserving metadata as semantic truth. Consolidation is required to remove competing scenario definitions; it does not depend on the suspended agent guide's completeness or metadata-lookup changes.

## #reference-context

Show the selected example object's name and a link to its originating tutorial or how-to on generated object-reference pages when that origin exists.

Builds on #reference-examples. Keep origin as documentation-only metadata paired with selected objects. Resolve link text and destination from catalogue entries, choosing the scenario's canonical tutorial or how-to. Supplementary objects have no origin and display no context block. Class semantics remain in class metadata; neither modeling objects nor saved JSON acquire provenance fields.

## #generation-narrative

Tell how e-commerce becomes the notebook, reading, packaged model and published documentation as a doc-scoped narrative of the recurring generation pattern.

The source and recorded generation steps give authors the example to follow when adding another scenario. Deliberate selection and execution boundaries are explained where they apply. Architecture retains source ownership and the runtime/development boundary, linking to the narrative. No separate contributor instructions are maintained.

## #shared-guidance

Update existing documentation and links to direct readers to the web and edge tutorials and their relevant modeling sections.

Keep methodology conceptual and link to executable result inspection; construction, comparisons and exports live in the tutorials. Reuse existing explanations and reference pages. Retain the short custom-hourly-timeseries capability and interface-editability note within tutorial content. AI-specific guidance remains for agent-guidance; development authoring patterns belong to the generation narrative.
