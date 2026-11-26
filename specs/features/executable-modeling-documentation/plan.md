# Executable modeling documentation

A scenario is one sequential Jupytext Python source. The baseline is its initial complete
`system`; a starter is the packaged JSON of that model. An experiment duplicates that original
system before changing the duplicate. All experiments run in source order, without cleanup or
independent experiment selection.

## #source-format

Define percent-cell selection for complete tutorials, versions without plots, construction-only generation and the existing focused guides.

Keep the source valid Python. Plot-tagged cells include plotting imports and chart-dependent prose; without-plots also omits notebook setup. Use Jupytext instead of maintaining another parser. Selection accepts only the published views, without dependency inference.

## #presentation-tools

Convert selected cells into cleared notebooks and output-free readings, and execute documentation in fresh kernels with isolated output directories.

Keep conversion independent of execution. Preserve notebook-exported outputs and explicitly embed generated chart and graph resources; execution failures propagate. These functions accept scenario metadata before the website switches to them.

Changed: **Build conversion and execution before switching the website.** The approved plan grouped notebook conversion, documentation execution and website integration in one piece. Separate the generation functions so they can produce the e-commerce pilot's notebook, reading and executed documentation for review first. Keep website integration for the final publication lot, after the other scenarios have been converted.

## #catalogue

Extend the existing example and guide registries with source and reading paths, tutorial destinations and explicit guide sections.

Keep introductory examples and how-to scenarios as their existing owners, with several guides allowed per scenario. Output-free Markdown beside each packaged JSON gives installed consumers complete explanations without Jupytext, execution or notebook outputs. Listing metadata and reading paths remain passive.

## #baseline-tools

Execute the selected construction in a fresh kernel with deterministic object and source ids, then save inputs-only JSON to the explicit destination.

Set both id flags before scenario imports. Tests use a small real model to verify stable serialization and process isolation; catalogue-wide equality belongs to #baseline-generation.

Changed: **Test isolated construction before replacing the existing constructors.** The approved plan grouped the new regeneration function with removal of the old constructor-based writers. Build and test the function first using a small model. Later, remove each writer when its last scenario is converted. This lets us verify deterministic ids and kernel isolation before changing how the packaged examples are constructed.

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

Extract the streaming service-builder lesson into a focused executable scenario.

Retain service installation, derived job resources and an editable demand projection. Explain replacement of the old synthetic daily and seasonal arrays with the hourly-volume builder's smooth projection. Move reusable inspection, comparison, attribution and explainability teaching into e-commerce; move introductory edge teaching into IoT. Multiple chart variants and reset demonstrations need not survive.

Changed: **Keep the old notebook until the final publication lot.** The approved streaming piece also retired the introductory notebook. Extract the focused streaming scenario first, while retaining that notebook for its existing execution test. Move retirement into the publication piece, where the replacement test will execute all published sequences. Deleting the notebook earlier would leave the old test pointing at a missing file.

## #interface-exports

Teach single-model and ordered comparison exports independently of Python plotting, using duplicates that preserve corresponding object ids.

E-commerce owns the general export explanation; IoT applies it and links back. Set output_dir near the source's start for reader-chosen destinations, separate from package regeneration. Use system_to_json, reference-first systems_to_json and optional materialize_serialized_state when complete calculated values are wanted; inputs-only import remains valid.

## #edge-exports

Apply the e-commerce export lesson to the IoT source, producing single-model and ordered comparison files independently of plotting.

Keep the shared export explanation in e-commerce and link back from IoT. Land this after #edge-tutorial so its source and duplicates already exist.

Changed: **Deliver the two export lessons with their respective tutorials.** The approved plan grouped e-commerce and IoT exports in one piece. Complete and review the e-commerce export lesson during the web pilot, then add IoT exports after constructing its tutorial in the next lot. This lets the pilot include the complete web lesson without requiring the IoT source to be converted before the pilot review.

## #presentations

Generate downloadable notebooks and output-free readings by conversion, and publish tutorials and guides with executed results through the existing documentation build.

Commit cleared notebooks under notebooks/. Execute documentation in fresh kernels with separate output directories. Replace content-specific regex rewriting with notebook export and explicit resource embedding; a failed execution stops the build. Retire the old tutorial notebook with its execution-test replacement.

Changed: **Retire the old notebook together with its execution test.** The approved publication piece replaced the single-notebook test with execution checks for every published sequence, but left notebook retirement in the earlier streaming piece. Move retirement here so the old file and its test disappear in the same commit. Until that replacement is ready, the existing test continues to exercise the old notebook.

## #publication-command

Expose conversion, documentation execution and packaged-model regeneration through the explicit authoring command once every registered source supports them.

Use the existing command shell and dispatch to the tested generation functions. Keep command availability together with the website switch, after all scenarios are migrated.

Changed: **Expose the authoring command after all registered sources are converted.** The approved plan grouped command dispatch with the percent-cell reader and selector. Build those functions first, and expose the command in the final publication lot. Before ML is converted, its source defines a constructor rather than binding the initial system in a marked cell, so the new construction-only regeneration command could not process it.

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

## Coverage during source migration

#baseline-generation starts its equality case with e-commerce, replacing the introductory constructor check. #ml-guide adds ML and removes its constructor check; #edge-tutorial and #streaming-guide add their registrations. Compare every input and relationship, normalizing only generated ids in full runs; also check retained originals.

Changed: **Update each example's test when its source is converted.** The approved plan grouped both constructor-test replacements together. Existing tests call build_system() and compare the resulting model with packaged JSON. Converting e-commerce removes that function, so replace its test at the same time by executing its construction cells and comparing the result with the JSON. Add ML to that same test when ML is converted, then add IoT and streaming as they arrive.

## Pilot artifacts and catalogue readings

#catalogue supplies every required field at every existing registry entry. #presentation-tools converts both existing sources into packaged readings; the unchanged ML constructor remains executable until #ml-guide replaces it. #generation-narrative generates the e-commerce pilot for review without switching website navigation.

Changed: **Provide a readable file for every catalogue entry during the web pilot.** The approved plan required packaged readings but did not explain how to supply ML's reading before its later conversion. Generate a reading from its existing constructor source when adding catalogue paths; reading conversion only processes text. Regenerate that file when ML becomes sequential. This keeps every advertised reading path usable throughout delivery without running ML during catalogue discovery.

## Delivery

- **generation-tools** #source-format #presentation-tools #baseline-tools — Build and test selection, conversion and isolated execution using small source fixtures. Existing scenarios, constructor tests and the website stay green; no registry-backed authoring command is exposed yet.
- **web-pilot** #catalogue #ecommerce-tutorial #baseline-generation #focused-guides #interface-exports #generation-narrative — Catalogue construction changes together. E-commerce conversion and its equality-test replacement share one commit naming both pieces. User review of the generated notebook, readings and executed pilot blocks later scenario migration.
- **remaining-scenarios** #ml-guide #edge-tutorial #edge-exports #streaming-guide — After pilot approval, convert ML with how-to writer cleanup, then add IoT and streaming with regenerated baselines and readings. Extend the shared equality case per scenario. The interface companion plan gates the shared-starter handoff, not independent library delivery.
- **reference-pages** #reference-examples #reference-context — Consolidate class examples after all packaged scenarios exist, then add their context links. Preserve existing class coverage and keep supplementary objects without an origin; each commit maintains the reference generator's callers.
- **publish-documentation** #publication-command #presentations #shared-guidance — Switch the documentation build and navigation after every source is ready. Retire the old notebook with its execution-test replacement in one commit. Run the complete sequence matrix, conversion freshness check and strict documentation build before delivery closes.
