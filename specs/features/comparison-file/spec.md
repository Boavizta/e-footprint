# Comparison file

The library writes several systems to one file and reads them back, in the format the interface
already saves a comparison in.

## Problem

A comparison is two systems side by side: a reference and a variant of it. The library computes
one, with its totals, its deltas and the diff of its inputs, and it duplicates a system so that the
variant's objects stay paired with the reference's. But it saves systems one at a time. The file
that holds both exists only in the interface, which builds and reads it by itself.

So a modeler working in Python, or a coding agent writing a model for them, cannot hand over a
comparison. They export two files, and whoever receives them opens one after the other. Writing a
single file means assembling by hand a format that is documented nowhere. The usual way to get the
two files, export, change the model, export again, also gives both systems the same identity, which
the interface has to repair when the second one is opened.

## The change

The library exports an ordered list of systems to one file, and loads such a file back into its
systems, in the same order. The first system is the reference. Each system is stored exactly as its
own export would store it, saved values included, so a system taken out of the file is a valid
single-system file.

A comparison in Python becomes: build a system, duplicate it, change the copy, export both.

The interface saves and opens its comparisons through the library. Nothing changes on its screens:
saving a comparison and opening a file behave as today, and a file saved before this feature still
opens. What is new is that a file written from Python opens in the interface as a comparison, its
systems in the order of the file.

## Rules no screen shows

- **round-trip** Systems exported together and loaded back come out in the same order, each as its
  own export and load would give it: same inputs, same ids, same saved values.
- **each-is-a-system-file** A system taken out of a comparison file loads as a single-system file.
- **any-count** A file holds one system or more, and the library sets no upper limit.
- **distinct-systems** Exporting two systems that share a system id is refused, with a message that
  names the id and says to duplicate the system instead.
- **old-files-upgrade** A comparison file saved by an earlier version of the library loads the way
  single-system files of that version do: each system is upgraded and recomputed, and keeps its
  saved values as the baseline to compare against.
- **library-reads-interface-files** A comparison file saved by the interface loads in the library;
  what the interface added to it is ignored.
- **library-files-open** A file exported by the library opens in the interface as a comparison, the
  first system as the first model.
- **saved-files-open** A comparison file the interface saved before this feature opens there as
  before: its models, the active one, and each model's interface settings.

## Not doing

- One document mixing the objects of several systems. A variant keeps the ids of its reference's
  objects, so the two would collide.
- Storing the comparison's results in the file. The totals, the deltas and the diff are computed
  from the systems when they are loaded.
- Giving a fresh id to a system at export when two collide. The export refuses, so that the
  modeler knows which system is which.
- Referring to a model by its system id in the interface. A model stays at its position.
- Raising the interface's limit of two models. A file of more systems is refused there as today.
- Any change to the single-system file.
- What the agent guide says of comparisons, and the interface's entry for starting from a
  conversation with an AI agent. Each is its own feature (`agent-guidance` here,
  `start-from-ai-agent` in the interface).
