# Comparison file — the library's plan

Two functions of `efootprint/api_utils/`: one writes an ordered list of systems to one file, the
other loads such a file back into its systems. No existing code changes, and nothing in the
library calls either: both are new entry points for the modeler.

## #export

`systems_to_json` writes the systems in order, the first the reference, as a dict whose `models`
key lists each one's `system_to_json` document. Systems sharing a System id are refused.

Each document is its own save, so the single-system format and its schema version stay as they
are, and the file needs no version of its own. Refused: renaming a colliding System, which would
hide which system is which.

## #load

`load_systems` returns a comparison file's systems in the file's order, each loaded from its
document by `load_system_document`.

Systems alone are returned: a modeler compares systems, and each one reaches its objects. Two
documents sharing a System id are not checked: only a file assembled by hand can, and their loads
give separate objects. A single-system file given to the load fails with a KeyError on `models`:
the mix-up gets no check of its own.

## Rules no test holds

- **any-count** Both functions walk the list and neither counts it, so no limit can be reached.
- **each-is-a-system-file** Each element of the list is what `system_to_json` returns for its
  system, unchanged.
- **old-files-upgrade** The load hands each document to `load_system_document`, whose earlier-version
  case of the save-and-load narrative holds the upgrade and the baseline.

## Delivery

- **comparison-file** (easy) #export #load — Two new functions of a few lines each, whose design the plan leaves nothing open in, and no existing code changes. #export is committed first: the round-trip case of #load writes its file with `systems_to_json`.
