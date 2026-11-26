# Executable modeling documentation

Each packaged modeling scenario has one editable, executable explanation, reused for its
documentation, notebook, model file and the examples available to coding agents.

## Problem

Learning and reusing e-footprint currently means choosing between a notebook tutorial, packaged
example scripts, handwritten how-to sketches and interface starters. These sources overlap but
are maintained separately. A correction to one does not necessarily reach the others. The planned
agent guide would add another broad example to maintain.

The tutorial mixes a streaming model, several ways to visualize it, successive experiments and
an edge extension. An edge modeler must work through the web example first. The packaged examples
are easier to load but do not provide the same teaching explanations, and the Industrial IoT
starter is available only through the interface.

## The change

Authors maintain each scenario as Python text with prose, code cells and presentation tags.
The same source produces its runnable notebook, documentation presentation and packaged model.
Several focused guides can explain different parts of one scenario without maintaining copies
of its code. Existing overlapping sources are consolidated as their scenarios move over.

E-commerce becomes the main web tutorial: describe the service, construct its infrastructure and
usage, inspect results, explore a consequential change and deliver the model. Its database and
server-to-server guides reuse that scenario. Industrial IoT becomes the independent edge tutorial,
with sensors grouped by site, recurrent demand, cloud uploads and an analyst dashboard. It also
becomes the package's edge starter, shared with the interface. The machine-learning workflow stays
a focused example, and the streaming tutorial's useful service-builder material becomes a focused
how-to. Every packaged scenario has a tutorial or how-to presentation.

Tutorials teach editable usage inputs, meaningful assumptions and result inspection. They show
exporting a single model or a comparison for visualization in the interface, alongside optional
Python visualizations. Data-backed builders remain part of the teaching: making an external
request while modeling is an ordinary use of the library.

Readers can obtain a complete example without notebook setup, plotting instructions or saved
outputs. Its explanations and executable sequence come from the same source as the full tutorial.
Shared modeling principles retain one canonical explanation, and class semantics remain in the
generated reference. Tutorials teach coherent tasks; supplementary examples cover classes those
tasks do not need.

## Rules no screen shows

- **one-scenario-source** Changing a scenario's explanation or modeling code updates every published reuse without editing a second copy.
- **independent-tutorials** The web and edge tutorials each run from a fresh session without executing the other tutorial.
- **selected-example-runs** Each published example sequence runs in its documented order with its stated dependencies, including the selection without plotting.
- **example-in-package** Every packaged scenario includes its canonical Python source and a loadable model file matching its documented baseline.
- **baseline-is-explicit** A scenario's starter model is a designated baseline, unaffected by later tutorial experiments or visualization choices.
- **exports-open** Tutorial exports load in the interface; comparisons put the reference first and preserve the identities of corresponding objects.
- **editable-inputs** Starter models use interface-editable input timeseries; advanced custom-array examples explain their editability trade-off.
- **site-multiplicity** The IoT example counts the devices of a site together, and their contributions scale with the group's device counts.
- **starters-still-open** Existing e-commerce and Industrial IoT picker entries retain their names, descriptions, icons and concepts and open the shared packaged models.
- **generation-is-explicit** Reading or listing example content does not run its modeling code, make external requests or write model and visualization files.
- **assumptions-agree** A scenario's quantities, cadence, boundaries and comparisons agree with its explanation; corrections to existing assumptions are explicit.
- **class-coverage-remains** Generating class references retains examples for every registered concrete class, including classes outside the tutorials.

## Not doing

- Implementing or assembling the installed agent guide. That feature resumes against these delivered sources.
- Requiring every tutorial to demonstrate every object type, or adding a separate broad reference model for that purpose.
- A notebook editor, a general documentation framework, or automatic model regeneration when someone reads an example.
- Changing footprint formulas, library defaults or the model serialization format.
- Moving the interface-only AI chatbot and GenAI video starters into the package.
- Inventing a new IoT scenario or adding groups nested within groups to the introductory example.
