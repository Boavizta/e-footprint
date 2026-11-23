# Comparison file — technical decisions held before the interface's plan

The library's lines are pieces of `plan.md`. What remains is the interface's, for its plan of the
feature; the session that writes it turns these lines into pieces there and deletes this file.

## The interface

- Its plan is written in `../e-footprint-interface-worktree` (branch
  `e-footprint-interface-worktree`), not in `../e-footprint-interface`, where another development
  is in progress on `dev`. It carries the same feature name and points at the library pieces
  (`#export`, `#load`) under `## Planned elsewhere`.
- That worktree pins the published `efootprint`. It needs the editable path dependency on the
  library checkout that holds the pieces before its plan can be tested. Its
  `comprehension.config.json` names the library as `../e-footprint`.
- `download_workspace` (`model_builder/adapters/views/views.py`) and `_restore_workspace`
  (`model_builder/adapters/views/views_workspace.py`) take the format from the library: its key,
  or the functions, as the library plan's point to confirm on `#export` settles.
- The interface's keys stay the interface's. On the envelope: `efootprint_workspace_version` and
  `active_slot`, which stays a position in the list. On each document: `interface_config` and
  `efootprint_interface_version`. The interface adds them to the library's output, as
  `_single_model_document` does for a single model.
- `MAX_SLOTS = 2` (`model_builder/adapters/repositories/workspace_base.py`) stays the interface's
  limit.
- Whether `_restore_workspace` keeps minting a fresh System id when two documents of a file
  collide (`with_fresh_system_id`). A file the library exported cannot collide; a file assembled
  by hand can. The library's load does not check it.
