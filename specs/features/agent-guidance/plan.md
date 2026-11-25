# Agent guidance — plan

Ship installed-version guidance assembled from canonical documentation and executable sources. The
construction narrative is approved; this plan changes no modeling behavior yet. Read the
[guide preview](guide-preview.md) alongside the pieces. The new command has no existing run order:
its shells are reviewed in the order below.

## #canonical-topics

Move the documentation needed by the command into the package and give the website and command one topic reader.

Keep the existing website filenames. Include both candidate topics: hardware composition complements
edge usage, and attribution explains results. Use the existing topic registry rather than another
catalogue. Named Python snippets are expanded as text; documentation never executes during a lookup.

## #class-reference

Render class semantics once from metadata for both the command and website, without constructing example objects.

The current renderer mixes semantic text with model construction and optional graph generation.
Extract the common text; keep example calculations as website additions. Merge inherited metadata,
show constructor and class defaults distinctly, preserve conditional choices, and include computed
docstrings even when a sample result is empty. Use ordinary string rendering, without Jinja2 in core.

## #canonical-example

Share one deterministic, core-only mixed web/edge script between the guide and website, completing its results and export flow.

Port docs_case rather than maintain another model. Replace Boavizta-backed hardware with plain
server inputs in this script; optional Boavizta graph examples stay in website tooling. Retain
core EcoLogits and video examples. Link the group and workload component into the actual model.
The existing example registry adds the reference JSON and its standard authoring wrapper.

## #python-guidance

Make public Python-modeling documentation own builders, shared input conventions and the reactive context needed to model without reading the engine.

Values carry units and meaningful assumption sources; defaults are starting hypotheses. Country
selection controls user-side electricity and timezone, not server electricity. Explain hourly
volumes and weekly recurrent demand before showing the model. Builder-specific form schemas stay
in builder docstrings. Public reads compute lazily, edits invalidate dependencies, and ordinary
assignments validate transactionally; no engine implementation guide is added.

## #modeling-workflow

Document collaboration with an AI modeler, editable-timeseries choices and the files delivered for the interface as ordinary library documentation.

Agree on boundaries, scale, consequential assumptions and an overview before coding; ask which AI
model and hosting arrangement apply. Prefer form-input hourly, constant and weekly-profile builders.
Explain custom-array editability before choosing them. Deliver one System file or one comparison
file, reference first; duplication preserves corresponding ids. Materialize explicitly when saved
values are required, not merely for interface import.

## #support-results

Put bug reporting and result interpretation in their canonical documentation homes, with executable result-inspection snippets.

Report the installed version, minimal reproduction, expected and actual behavior, and only
explanations supported by evidence. The user submits any report. Extend methodology with totals,
dominant contributors, uncertainty and absolute savings; avoid presenting illustrative emissions
thresholds as universal cutoffs. Server sizing diagnostics remain in server metadata.

## #guide-assembly

Assemble the default guide and its website page from the same selected sections, example source and registry-generated lookup catalogues.

The preview fixes reading order and marks missing canonical text. Selection uses explicit page
headings, not line offsets or summaries. Reuse named snippet markers already supported by
pymdownx; expand the same Python regions for command output. Only transitions, selection and link
presentation belong to the assembly. Compare text after normalizing links, never separately
maintained snapshots.

## #example-discovery

List every packaged model using the two existing example registries, with descriptions and absolute paths to its JSON and source script.

Add the missing fields to those records rather than introduce another example type. Existing
how-to titles remain with their guide registry. The new reference example joins the introductory
registry. Authoring scripts are for reading: their regeneration entry points overwrite packaged
JSON; the reference demonstration writes its requested output to the working directory.

## #command

Provide the module command, installed resources and helpful lookup dispatch on the bare core installation.

No argument prints the guide; one argument is tried as examples, then an exact class, then an
exact topic. Unknown names return a nonzero status and all names, with close matches first.
Use argparse, difflib and package-resource access. Do not import documentation tooling, construct
examples, contact external services or require optional groups to print guidance.

## #entry-pointers

Point agents and users at the command from the package and README, and make README destinations work on PyPI.

The pasteable two lines install efootprint and instruct an agent to run the guide before modeling.
Convert every repository-relative link and image destination, including root-relative paths, to
its GitHub source or raw-image URL. Preserve external and mail links. Check resolution during
implementation; the plan itself does not need a network link check.

## #trial-pitfalls

Put the trial runs' silent modeling traps in their owning class references without changing defaults or calculations.

Cloud idle power defaults to zero and server electricity does not follow usage country. Hourly
form-input volumes are uniform within each day, with 30-day months and 365-day years. Longer edge
lifespans allocate only part of manufacturing over shorter usage. Compare raw and provisioned
server instances when investigating oversized hardware; a rounding gap alone proves no preferred
replacement size.

## #trial-errors

Replace the trial runs' obscure quantity and ownership errors, remove the unused volume key and silence the cloud-class import log.

Constructor labels run before attachment checks, so preflight is needed there as well as at the
existing live-input boundary. Reuse resolved annotations and reject only already-invalid numbers,
including quantity unions; neither coerce values nor catch unrelated failures. Hydration is
unchanged. Preserve ownership enforcement and failed-construction cleanup, extending the approved
cases. Remove only the ignored volume key and import log.

## #retire-chat-kit

Remove the earlier prompt and trial kit once their useful guidance has canonical homes reused by the installed guide.

Preserve the behavioral advice through #modeling-workflow, sizing advice through #trial-pitfalls,
result interpretation through #support-results and exports through #canonical-example. The old
comparison instructions become the current ordered-file recipe rather than being copied literally.
Delete all tracked kit assets, including the spreadsheet; Git history remains their record.

## The canonical sources and reading order

#canonical-topics, #python-guidance, #modeling-workflow, #support-results and #guide-assembly use the
source map in the preview. Its GAP blocks are implementation obligations in those owning pages,
not proposed agent-only prose. Use documentation voice rather than role instructions. Ship all eight specialized topics plus why_efootprint,
efootprint_scope, methodology, modeling_from_python, modeling_with_ai and reporting_bugs. Keep
get_started, the notebook tutorial and team pages outside the command's topic registry.

## One reference for every emitted name

#canonical-topics, #class-reference and #guide-assembly use the existing concrete-plus-canonical
class registry. Supplement it with Source, source-value wrappers and timeseries builders referenced
by the shipped documentation. These references describe their public constructors and docstrings;
not every value class has ModelingObject metadata. Class and member links become the class lookup
command, keeping the member label. Convert interface template links to absolute URLs.

## Executable sources and package boundaries

#canonical-example, #canonical-topics and #guide-assembly include source text without importing
it. The reference script has a pure builder and a demonstration entry point writing to a supplied
directory. Register its reproducible input JSON and standard authoring wrapper using existing
example conventions. Replace handwritten topic sketches with executable named regions, including
currently incomplete database and server-to-server sketches. Website-only plots remain outside
the shared semantic renderer.

## Reference-script coverage

#canonical-example relies on the existing serialization and comparison tests for JSON semantics,
system ordering and identity preservation. Its smoke test checks that the published example is
usable, without adding separate cases for each demonstrated API operation.

## Command and lookup coverage

#command has one installed-wheel smoke test for successful dispatch: no argument, examples,
one class and one topic, outside the checkout on a core install. It replaces a separate
successful-dispatch test. Unknown-name behavior is checked in-process.

#class-reference and #canonical-topics render every registered modeling class and topic
in-process, retaining class completeness and website–command text checks. #guide-assembly
checks emitted lookup targets against the registries across the guide, references and topics;
it does not recursively execute every emitted command.

## README link coverage

#entry-pointers checks absolute URLs and maps repository link and image destinations to tracked
files without network requests in the routine test. External destinations are verified once
during implementation; remote availability is not a recurring CI dependency. The requirement
that README links resolve from PyPI is unchanged.

## Project contracts

#trial-errors changes constructor diagnostics, without reactive-slot calls, unit policy or
lifecycle changes. #class-reference preserves doc-as-code and upward-only imports. #canonical-example
uses current save/load and duplication APIs; neither JSON shape nor cached-state policy changes.
No registry of modeling classes changes and no migration is needed. Interface behavior is
documented, not changed; edge-example and start-from-ai-agent remain independent features.

## Acceptance beyond deterministic checks

#guide-assembly is reviewed for missing context, repetition and website-only navigation using the
preview's approximate size. Re-run the three briefs below against the installed wheel and guide,
without repository access. Record concrete modeling mistakes and additional exploration; the
original one-run-per-brief results establish no statistical performance threshold. The user
confirms consequential assumptions; no agent submits a bug report automatically.

Web: a French sports-booking platform, 400,000 bookings yearly growing 15% yearly, smartphones on
mobile networks, an autoscaling Python API and dedicated Postgres server; three years, editable
volumes, interface output, dominant emissions and oversizing.

GenAI: 50,000 monthly support conversations on laptops over wifi in France and Germany, six calls
of 800 output tokens to a mid-size hosted model; compare without and with the assistant over two
years, ready for the interface.

Edge: 500 building kits deployed yearly for three years in France, each with a four-core/eight-GB
gateway and 40 wired sensors using a few watts, eight years in service and hourly cloud uploads;
compare the sensors, gateway and cloud contributions.


## Trial baseline and its limits

#guide-assembly compares against three isolated trials on published 27.1.0: all models ran after
12–23 source files and roughly 2,000 lines were read, about 20 tool calls and 127k–136k tokens
per run. Their five output files imported into the interface on 27.1.0. One unchanged model's
export grew from 162 kB to 294 kB after values were read; passive serialization explains this,
and #modeling-workflow documents explicit materialization instead of changing it.

Each trial used one strong agent allowed to inspect the installed package, closer to a ceiling
than an average agent. No web chat with a Python sandbox and no shell was evaluated; that use
case is outside this feature. Retain these limits when interpreting the repeat trials.
