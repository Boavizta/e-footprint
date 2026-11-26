# Agent guidance

On hold until [Executable modeling documentation](../executable-modeling-documentation/spec.md)
is delivered and reviewed. This spec must then be revised using the
[resumption instructions](resume.md) before planning or implementation continues.

The library ships a guide for coding agents and a command that prints it, so that an agent
models with the installed version from one instruction of its user.

## Problem

A coding agent asked to model a system with the library gets there, but by reading the package.
Three agents were each given a brief, the published package and nothing else. All three produced a
model that ran, after reading 12 to 23 source files, around 2,000 lines, before writing a line of
their own. The worked example that unlocked every run sits in a folder they found only by listing
every file, and the descriptions, pitfalls and default values each class carries were found only by
opening its source.

Reading did not give them everything. Some choices gave a wrong number with no error: a cloud
server that draws no power when idle, a carbon intensity that does not follow the country, a year
that is not twelve months, a device whose manufacturing is only partly counted. None of the three
could tell what the interface opens: with or without saved values, one file or two for a
comparison. And the fleet agent had no edge example to start from.

The guidance that exists is a prompt for web chats and a kit for trying the library with one. Both
live in the repository, not in the package, and point at the documentation and the code of the
latest version, which may be ahead of the one installed.

## The change

**A guide in the package.** `python -m efootprint.agent_guide` prints it. It is intended to be
read whole at the start of a task, written as documentation of the library, and it matches the
installed version because it is installed with it. It holds what belongs to no single class:

- why the library exists, what it models, and the methodology of coarse modeling, refinement and
  comparison;
- a workflow with the user: establish boundaries and scale, ask about consequential assumptions
  and the model used for AI workloads, and agree on an overview before writing code;
- the core distinction between web and edge modeling and how their objects fit together;
- what builders provide beyond the underlying objects, and which assumptions remain to check;
- the conventions every class shares: values with a unit and a source, defaults, countries and
  usage volumes; prefer timeseries builders that retain form inputs so the interface can edit
  them, and explain the viewable-but-not-editable tradeoff before using custom arrays;
- one full runnable system script demonstrating broad web and edge object usage, maintained with
  the documentation and showing the recommended practices;
- how-to guides by title and the commands that print them, plus commands to inspect a class's
  inputs, defaults, allowed values, pitfalls, interactions and computed attributes; further
  examples are discoverable when needed;
- enough context on lazy calculation, dependency tracking and recomputation to model through the
  public API without reading the reactive engine, unless investigating a suspected bug;
- how to prepare a bug report for the library's repository: a minimal reproducing script, the
  installed version, expected and actual behavior, and an explanation supported by the evidence;
  suggest submitting the report, leaving submission to the user;
- how to read the results: where the totals are, the scale and uncertainty of the emissions,
  dominant contributors and possible oversized servers;
- the output for the interface: one JSON file containing a single system, or one comparison JSON
  file containing the reference system first and the compared system second, preserving the
  identities of corresponding objects; how to save calculated values when needed.

All substantive guidance has its source of truth in the documentation. The guide assembles
canonical pages or sections and executable examples used by the documentation; object semantics
remain in the class metadata from which the reference is generated. A documentation page on
modeling with an AI agent owns the user workflow, timeseries editability tradeoff and output
conventions. Missing explanations are added to their owning documentation rather than written
only for the guide. There are no independently maintained agent summaries or agent-only advice.
Only selection, reading order, minimal transitions and presentation of lookup links are specific
to the assembly. Exhaustive class references and specialized recipes remain available through
lookups.

Around 10,000 tokens is a starting allowance, not a hard ceiling. More is appropriate when it
helps prevent modeling mistakes or further exploration. Coverage and a useful reading order take
priority over compression; repeated explanations and unrelated detail do not belong in the guide.

**The same command looks things up.** Each lookup prints text, and says how to reach what it
refers to:

- `python -m efootprint.agent_guide Server` prints the reference of a class: what it is, each
  input with its description, its default and its allowed values, its pitfalls, how it interacts
  with other classes, and what it computes. It is what the documentation site shows for that class.
- `python -m efootprint.agent_guide web_vs_edge` prints a topic: one of the how-to guides of the
  documentation site, or its pages on edge modeling. These pages ship in the package.
- `python -m efootprint.agent_guide examples` lists the example models that ship in the package,
  each with what it shows and where its script and its file are on the user's machine.

**The user's side shrinks to two lines.** The README, which is also the package's page on PyPI,
gives them to paste into the instruction file of an agent: install the library, run the command and
follow what it prints before writing a model. It also tells an agent reading it to run the command.

**The guide is a page of the documentation site**, with the text the command prints.

**The earlier prompt and kit leave the repository.** What they taught is in the owning
documentation or class reference, reused by the guide.

**What the trial runs tripped on is fixed or said.**

- The choices that gave a wrong number silently are pitfalls in the reference of their class.
- Building a model no longer logs a line about a class the model does not use.
- A plain number given where a value with a unit is expected is refused with a message that says
  what to pass.
- Building a second system on the objects of a first is refused with a message that says to
  duplicate the system.
- The usage volume's documentation no longer lists an input that nothing reads.
- The links of the README work from the package's page.

## Rules no screen shows

- **one-text-per-explanation** Every substantive explanation in the guide is drawn from its
  canonical documentation source, including generated class references and executable examples,
  with the same wording apart from presentation and lookup links.
- **examples-run** Every code example of the guide runs as written on the installed library.
- **core-install-is-enough** Every form of the command works on the core install, without the
  optional groups.
- **every-class-answers** The command prints a reference for every modeling class of the library.
- **unknown-name-helps** An unknown name is answered with the names that exist, close ones first,
  not with a traceback.
- **references-resolve** Where the output refers to a class or a topic, it prints the command that
  looks it up, and that command answers.
- **one-text-per-class** The reference the command prints for a class and the page the
  documentation site shows for it carry the same descriptions, defaults, allowed values and
  pitfalls.
- **one-text-per-topic** A topic the command prints is the page the documentation site shows.
- **one-guide** The guide on the documentation site is the text the command prints.
- **every-example-listed** `examples` lists every example model of the package, with paths that
  exist on the machine it runs on.
- **quiet-build** Building and exporting a model that uses no cloud server from Boavizta logs
  nothing about that class.
- **number-needs-a-unit** Giving a plain number where a value with a unit is expected fails with a
  message naming the input and what to pass.
- **second-system-says-duplicate** Building a second system on the objects of a first fails with a
  message that says to duplicate the system.
- **readme-links-resolve** Every link of the README resolves from the package's page on PyPI.

## Not doing

- An interface walkthrough. The guide covers timeseries editability and the files the interface
  opens, where these affect modeling and delivery.
- New default values for the cloud server from Boavizta. Its idle power and its carbon intensity
  are said as pitfalls; changing them is a modeling decision of its own.
- A change of what the export writes. The guide says when and how to save calculated values
  before exporting.
- Authoring the shared tutorials and examples, including the Industrial IoT starter's move into
  the package: [Executable modeling documentation](../executable-modeling-documentation/spec.md).
- The interface's entry for starting from a conversation with an AI agent: `start-from-ai-agent`,
  in the interface.
- A text file at the root of the documentation site for AI assistants to fetch. Chat assistants
  mostly do not fetch one by themselves, and the guide's page is already the address to give them.
- A skill file for agents that load skills. It would save the two lines of the README and no more.
- A server exposing the library as tools. An agent that writes Python does not need a second way
  in.
- Team-organization pages and the tutorial as topics. The library's reason for being belongs in
  the guide.
- A guide for a web chat that cannot run Python.
