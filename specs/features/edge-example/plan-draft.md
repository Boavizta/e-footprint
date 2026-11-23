# Edge example — technical decisions held before the plan

Decisions as they stand. The plan stage turns them into pieces and deletes this file.

- The example lives today in the interface: its script is
  `scripts/intro_example_scenarios/iot_industrial.py` (165 lines, no `EdgeDeviceGroup`), its file
  `model_builder/domain/reference_data/modeling_examples/introductory/iot_industrial.json`, and its
  picker entry is in the `registry.py` next to that file. `scripts/build_intro_examples.py`
  regenerates the file.
- It moves to `efootprint/modeling_examples/introductory/`, next to `ecommerce`: the script under
  `_authoring/`, the file beside it, an entry in `registry.py`. The JSON is covered by the
  `[tool.poetry] include` pattern already there.
- The interface reads it through `get_introductory_example`, as it does for `ecommerce`, and keeps
  the picker entry (name, description, icon, concepts) on its side.
- The interface's plan is written in `../e-footprint-interface-worktree`, under the same feature
  name, and points at the library piece under `## Planned elsewhere`. It needs the editable path
  dependency on the library checkout that holds the piece.
- The script reaches `api.boavizta.org` through `BoaviztaCloudServer` when it is run; the shipped
  file is what an agent reads.
- Once `agent-guidance` has landed, `python -m efootprint.agent_guide examples` lists it with no
  further change.
