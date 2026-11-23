# Comparison file

The library writes several systems to one file and reads them back.

## Problem

A comparison is two systems side by side: a reference and a variant of it. The library computes
one, with its totals, its deltas and the diff of its inputs, and it duplicates a system so that the
variant's objects stay paired with the reference's. But it saves systems one at a time.

So a modeler working in Python, or a coding agent writing a model for them, cannot hand over a
comparison in one file. They export two files, and whoever receives them has to know which is the
reference and load each. The usual way to get the two files, export, change the model, export
again, also gives both systems the same identity.

## The change

The library exports an ordered list of systems to one file, and loads such a file back into its
systems, in the same order. The first system is the reference. Each system is stored exactly as its
own export would store it, saved values included, so a system taken out of the file is a valid
single-system file.

A comparison in Python becomes: build a system, duplicate it, change the copy, export both.

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

## Not doing

- One document mixing the objects of several systems. A variant keeps the ids of its reference's
  objects, so the two would collide.
- Storing the comparison's results in the file. The totals, the deltas and the diff are computed
  from the systems when they are loaded.
- Giving a fresh id to a system at export when two collide. The export refuses, so that the
  modeler knows which system is which.
- Any change to the single-system file.
- What the agent guide says of comparisons: its own feature, `agent-guidance`.
