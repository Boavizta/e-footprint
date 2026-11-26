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

Each tutorial runs sequentially, with or without its plotting sections. Later comparisons start
by duplicating the original model and changing that duplicate; they leave the original available
for comparison and for the packaged example. The published documentation keeps executed charts
and numerical outputs.

E-commerce becomes the main web tutorial: describe the service, construct its infrastructure and
usage, inspect results, explore a consequential change and deliver the model. Its database and
server-to-server guides reuse that scenario. Industrial IoT becomes the independent edge tutorial,
with sensors grouped by site, recurrent demand, cloud uploads and an analyst dashboard. It also
becomes the package's edge starter, shared with the interface. The machine-learning workflow stays
a focused example, and the streaming tutorial's useful service-builder material becomes a focused
how-to. Every packaged scenario has a tutorial or how-to presentation.

Tutorials and packaged scenarios construct input timeseries using builders that preserve form
inputs for editing in the interface. Tutorials teach result inspection and make modeling
assumptions explicit, including the temporal assumptions of timeseries builders. Corrections to
existing scenario assumptions are explained.

A short note explains that custom timeseries at hourly resolution are also supported, but their
values cannot be edited manually in the interface; users update them in Python and re-export the
model. Tutorials also show exporting a single model or a comparison for visualization in the
interface, alongside optional Python visualizations. Data-backed builders remain part of the
teaching: making an external request while modeling is an ordinary use of the library.

Readers can obtain a complete example without notebook setup, plotting instructions or saved
outputs. Its explanations and executable sequence come from the same source as the full tutorial.
Shared modeling principles retain one canonical explanation, and class semantics remain in the
generated reference. Tutorials teach coherent tasks; supplementary examples cover classes those
tasks do not need.

## Behavioral requirements

- **selected-example-runs** Each published sequence, including either tutorial and selections without plotting, runs from a fresh session in its documented order with its stated dependencies.
- **starter-baseline** Each packaged model matches its tutorial or how-to's designated baseline, unaffected by later experiments or visualization choices.
- **generation-is-explicit** Reading or listing example content does not run its modeling code, make external requests or write model and visualization files.

## Not doing

- Implementing or assembling the installed agent guide. That feature resumes against these delivered sources.
- Requiring every tutorial to demonstrate every object type, or adding a separate broad reference model for that purpose.
- Teaching custom-array timeseries construction; retain only the short capability and interface-editability note.
- A notebook editor, a general documentation framework, or automatic model regeneration when someone reads an example.
- Changing footprint formulas, library defaults or the model serialization format.
- Moving the interface-only AI chatbot and GenAI video starters into the package.
- Inventing a new IoT scenario or adding groups nested within groups to the introductory example.
