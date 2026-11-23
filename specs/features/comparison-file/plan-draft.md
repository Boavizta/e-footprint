# Comparison file — technical decisions held before the plan

Decisions as they stand. The plan stage turns them into pieces and deletes this file.

## The file

- The file is a dict whose `models` key holds a list of documents. The key keeps the name the
  interface writes today, so files users already saved load unchanged.
- Each document is exactly what `system_to_json(system)` returns, with `save_computed_state` at
  its default: saved values and calculation graph included.
- The list is ordered and the first document is the reference.
- The envelope carries no library version of its own. Each document has its own
  `efootprint_version` and `Sources` block, and is loaded and upgraded independently through
  `json_to_system`.
- The single-system format is untouched: no schema version bump and no upgrade handler
  (constitution §2.4 does not apply).

## The library

- The export and the load live in `efootprint/api_utils/`, next to `system_to_json` and
  `json_to_system` (constitution §1.1, the serialization layer). Their names are the plan's.
- The export raises when two systems share a System id. The remedy its message names is
  `duplicate_system`, or `assign_fresh_system_id`, of `efootprint/comparison/duplication.py`.
- The library sets no cap on the number of systems.
- The load ignores the keys it does not own, at both levels. `validate_system_dict_structure`
  already skips an unknown top-level key of a document.

## The interface

- Its plan is written in `../e-footprint-interface-worktree` (branch
  `e-footprint-interface-worktree`), not in `../e-footprint-interface`, where another development
  is in progress on `dev`. It carries the same feature name and points at the library piece under
  `## Planned elsewhere`.
- That worktree pins the published `efootprint`. It needs the editable path dependency on the
  library checkout that holds the pieces before its plan can be tested. Its
  `comprehension.config.json` names the library as `../e-footprint`.
- `download_workspace` (`model_builder/adapters/views/views.py`) and `_restore_workspace`
  (`model_builder/adapters/views/views_workspace.py`) go through the library's export and load.
- The interface's keys stay the interface's. On the envelope: `efootprint_workspace_version` and
  `active_slot`, which stays a position in the list. On each document: `interface_config` and
  `efootprint_interface_version`. The interface adds them to the library's output, as
  `_single_model_document` does for a single model.
- `MAX_SLOTS = 2` (`model_builder/adapters/repositories/workspace_base.py`) stays the interface's
  limit.

## Left to the plan

- Whether `_restore_workspace` keeps minting a fresh System id when two documents of a file
  collide (`with_fresh_system_id`). A file the library exported cannot collide; a file assembled
  by hand can.
