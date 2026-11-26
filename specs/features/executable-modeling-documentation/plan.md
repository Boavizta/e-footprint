# Executable modeling documentation

A scenario is one sequential Jupytext Python source. The baseline is its initial complete
`system`; a starter is the packaged JSON of that model. An experiment duplicates that original
system before changing the duplicate. All experiments run in source order, without cleanup or
independent experiment selection.

## #source-format

Define percent-cell selection for complete tutorials, versions without plots, construction-only generation and the existing focused guides.

Use Jupytext rather than another parser. A baseline-end tag closes construction; plot and notebook-setup tags select both code and accompanying prose. Section tags serve named guides with explicit prerequisites. There is no dependency inference or experiment scheduler.

## #catalogue

Extend the existing example and guide registries with source and reading paths, tutorial destinations and explicit guide sections.

Keep introductory examples and how-to scenarios as their existing owners, with several guides allowed per scenario. Output-free Markdown beside each packaged JSON gives installed consumers complete explanations without Jupytext, execution or notebook outputs. Listing metadata and reading paths remain passive.

## #baseline-generation

Regenerate packaged inputs-only JSON explicitly from each source's initial construction, isolated from notebook execution and later experiments.

Fresh kernels set name-based object and source ids before scenario imports, preserving the existing reviewable JSON convention without leaking process globals. Generation appends the save operation after construction; ordinary tutorial exports use a reader-selected output directory. Existing load, computation, editability and round-trip coverage follows the catalogue.

## #ecommerce-tutorial

Turn the existing e-commerce scenario into the main web tutorial, retaining its initial model and teaching a comparison on a duplicate.

Teach service assumptions, infrastructure, jobs, journeys, geographic demand, numerical results, attribution and explainability before a traffic-change comparison. Keep Boavizta-backed servers and editable volumes. Each experiment starts from the original system; source order remains executable with plots removed. The original model owns the packaged example.

## #focused-guides

Replace the database and server-to-server sketches with explicitly selected prose and code from e-commerce.

Select imports and required earlier sections in source order, without inferred dependencies. Explain the same on-premise database and autoscaling web server as the tutorial, replacing the conflicting serverless sketch. Each guide includes its prerequisites and links to the full tutorial for result inspection and delivery; neither invents another model.

## #edge-tutorial

Introduce `EdgeDeviceGroup` as a sensor-site template in the independent Industrial IoT tutorial and packaged example, with one deployment representing one site.

Reuse sensor processes, uploads and the analyst dashboard. Model 15 sites containing 50 sensors each, replacing 750 individual sensor starts while preserving sensor-equivalent deployment volume. Retain the one-month rollout and six-year usage span explicitly; dashboard demand retains its three-year projection. Explain these different periods and constant weekly demand, rather than silently aligning them.

## #ml-guide

Convert machine learning into a complete executable how-to with editable demand and consistent retraining labels.

Keep training and inference as separate patterns and document the hourly builder's smoothing; do not claim it creates scheduled training bursts.

To confirm: **Keep 12 training runs per year and describe an annual retraining volume spread uniformly across hours, correcting the weekly and monthly labels.** Alternatively change the modeled demand to a weekly equivalent, increasing the training footprint relative to the current saved example.

## #streaming-guide

Extract the streaming service-builder lesson into a focused executable scenario and retire the competing introductory notebook.

Retain service installation, derived job resources and an editable demand projection. Explain replacement of the old synthetic daily and seasonal arrays with the hourly-volume builder's smooth projection. Move reusable inspection, comparison, attribution and explainability teaching into e-commerce; move introductory edge teaching into IoT. Multiple chart variants and reset demonstrations need not survive.

## #interface-exports

Teach single-model and ordered comparison exports independently of Python plotting, using duplicates that preserve corresponding object ids.

E-commerce owns the general executable export explanation; IoT applies it to its own models and links back. Show system_to_json, systems_to_json and optional materialize_serialized_state for complete saved calculated values. Inputs-only import remains valid. Plotting never supplies required export state, and the first comparison model is explicitly the reference.

## #presentations

Generate downloadable notebooks and output-free readings by conversion, and publish tutorials and guides with executed results through the existing documentation build.

Commit cleared notebooks under notebooks/ and packaged readings beside JSON; check their freshness by pure conversion. Documentation execution uses fresh kernels and separate output directories, retaining charts, numerical output and HTML resources. Replace content-specific regex rewriting with notebook export and explicit resource embedding. A failed execution stops the build; no stale-output fallback is introduced.

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

Give shared Python conventions a short canonical entry page, and route methodology and getting-started links to the two executable tutorials.

Serve library users modeling from Python: units, sources, defaults, archetypes and choosing a tutorial, linking to executable demonstrations. Methodology remains conceptual and links to numerical result inspection. Retain only the short custom-hourly-timeseries capability and interface-editability note. AI-specific collaboration guidance remains for agent-guidance; development authoring patterns belong to the generation narrative.

## Selection and execution contract

#source-format, #baseline-generation, #focused-guides and #presentations share a small cell contract.
Use JSON-form cell metadata with tags plot, notebook-setup, baseline-end and section:<name>.
Every cell needed by construction precedes and includes baseline-end; that cell binds system.
Code and prose that depend on a plot carry plot together. Plotting imports and generated chart files
stay within those cells. Notebook setup documents installation; source code remains valid Python.

Full and without-plots runs include every experiment in order. Without-plots also omits notebook
setup, saved outputs and chart-dependent prose. Baseline generation stops at baseline-end and omits
plotting and notebook setup. Guide section lists explicitly include their imports and prerequisites;
they filter in source order. There is no public arbitrary cell-combination API.

The development command is python -m docs_sources.doc_utils.modeling_examples, with convert,
build-docs and regenerate subcommands. Convert writes notebooks, output-free Markdown and runnable
Python to the requested output directory; --check compares committed notebooks and readings without
executing them. Regenerate takes a scenario id and explicitly targets its catalogue JSON. Build-docs
executes notebooks and exports Markdown and resources into the documentation build directory.
Normal scripts and notebooks write demonstration exports beneath an output_dir variable the reader
sets near the beginning. They never target package files. Regeneration and documentation execution
do not depend on each other.

## Content ownership and review

#ecommerce-tutorial proves #source-format, #baseline-generation, #focused-guides,
#interface-exports, #presentations and #generation-narrative together before the later scenario migrations are delivered.
Review that pilot's generated tutorial, notebook, reading, guide excerpts and JSON together. If its
authoring conventions need revision, update this plan before migrating IoT, ML and streaming.
Delivery lots belong to the tasks stage.

Each packaged scenario has a documentation destination: e-commerce uses tutorial.md, IoT uses
tutorial_edge.md, ML retains machine_learning_workflow.md and streaming uses video_streaming.md.
The existing database and server-to-server URLs remain. Retire tutorial.ipynb when the derived
notebooks and replacement lessons exist, updating its README links in the same change.

#shared-guidance keeps modeling_from_python short; modeling_with_ai and installed guide assembly
remain outside this feature. Use the existing efootprint/documentation/modeling_from_python.md
location, copying it into the website without an agent-guide dependency. Preserve the suspended
agent-guidance annotations and tests until its
own replanning, following ../agent-guidance/resume.md. Its proposed reference-system shell is not
used as a dependency or turned into another canonical scenario.

## Planning checks and verification

#catalogue and #reference-examples preserve doc-as-code and the upward dependency direction:
scenario loading stays above api_utils, and development notebook tooling never enters core imports.
#ecommerce-tutorial, #edge-tutorial, #ml-guide and #streaming-guide consume existing modeling and
timeseries APIs; they change no getters, dependency rules, guards, units or object lifecycle APIs.
Their values retain units, sources and explanations, with declared hypotheses for illustrative inputs.

#baseline-generation and #interface-exports use existing serialization, duplication and
materialization APIs. No JSON format, schema version, migration or modeling class is added.
The editable-input check must accept the constant and weekly-profile recurrent builders, preserve
their form_inputs through load/save, and stop assuming every hourly input spans three years.

The selected-example-runs owner replaces the single-notebook execution test with fresh-session
execution of every published sequence in full and without plots, including generated plain Python.
Use fixed API responses at the external-request boundary in automated execution, preserving real
model construction and calculations. Published builds and manual runs use normal Boavizta behavior;
external failures remain visible, without extra retries or a new response-cache mechanism.

The starter-baseline owner consolidates the two authoring/JSON equality cases: compare regenerated
construction with committed inputs and compare the original model after complete runs in both
presentations. Generation uses isolated deterministic ids. Existing editable-input, load and compute
tests extend to the new catalogue entries rather than adding a duplicate scenario suite.

The generation-is-explicit owner exercises metadata listing and text reading in a fresh process
without notebook or plotting tooling, refusing external requests and file creation. A conversion
freshness case covers notebooks/readings; reference preservation is checked with its replacement.
These remain ordinary rule owners. #generation-narrative adds one representative e-commerce case
that converts the source, regenerates its initial model and publishes executed documentation,
asserting the resulting artifacts with real modeling and fixed external responses. Its steps
explain the pattern at the generation code, with direct links to the source to follow. It is
declared as intended, not observed, until implemented; no existing narrative's behavior changes.

## Interface handoff

#edge-tutorial publishes iot_industrial through the library's existing introductory-example lookup.
The interface must switch its IoT picker path to that library entry and remove its local IoT source,
JSON and regeneration entry, retaining its picker presentation and other starters. Its existing
e-commerce lookup is the precedent. This requires a plan in the interface checkout, authored there
before coordinated delivery; none exists yet, so no invented cross-repository piece is linked here.
Library preparation can proceed independently; the shared-starter handoff is not complete until
that companion change is planned, approved, implemented and checked against this library checkout.

