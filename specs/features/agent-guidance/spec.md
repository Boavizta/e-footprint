# Agent guidance

The library ships a short guide for coding agents and a command that prints it, so that an agent
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

**A guide in the package.** `python -m efootprint.agent_guide` prints it. It is short enough to be
read whole at the start of a task, written as documentation of the library, and it matches the
installed version because it is installed with it. It holds what belongs to no single class:

- what the library models;
- the objects and how they are built on one another, for a web service and for a fleet of devices;
- the conventions every class shares: values with a unit and a source, defaults, countries, usage
  volumes given as a start date, a duration, a volume and a growth rate;
- a way of working: a coarse model first, an overview before any code, the questions to ask the
  user about scale and, for AI, about the model;
- one small model, from the first object to the export, that runs as written;
- how to read the results: where the totals are, what the size of the emissions calls for, how to
  spot an oversized server;
- how to export one system or several, with one line saying that the interface opens either file
  as it is;
- how to look up everything else.

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

**The earlier prompt and kit leave the repository.** What they taught is in the guide, or in the
reference of the class it concerns.

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

- **guide-stays-short** The guide is at most 1,500 words.
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

- A section of the guide on the interface. One line says what it opens; how to model is the same
  whoever reads the file.
- New default values for the cloud server from Boavizta. Its idle power and its carbon intensity
  are said as pitfalls; changing them is a modeling decision of its own.
- A change of what the export writes. The guide says how to save every value before exporting.
- An edge example, and the Industrial IoT starter moving from the interface into the package: the
  `edge-example` feature.
- The interface's entry for starting from a conversation with an AI agent: `start-from-ai-agent`,
  in the interface.
- A text file at the root of the documentation site for AI assistants to fetch. Chat assistants
  mostly do not fetch one by themselves, and the guide's page is already the address to give them.
- A skill file for agents that load skills. It would save the two lines of the README and no more.
- A server exposing the library as tools. An agent that writes Python does not need a second way
  in.
- The pages of the documentation site written to convince or to organise a team, and the
  tutorial, as topics.
- A guide for a web chat that cannot run Python.
