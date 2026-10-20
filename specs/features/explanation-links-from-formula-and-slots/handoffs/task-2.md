# Task 2 — Derive explanation links from formula and slot graph
Repositories and implementation ranges: e-footprint `57d10ac5..f01893df` (single commit `f01893df`; `57d10ac5`
is an unrelated tooling commit from another session on top of `9ea0617e`).

## Review pointers
- `explainable_object_base_class.py`: `get_attribute_from_flat_obj_dict` (resolver, facade for computed-dict
  elements), `_attached_formula_leaves`, the `None` sentinel set in `initialize_calculus_graph_data_from_json`,
  and the `direct_children_with_id` property.
- New integration helpers in `integration_test_base_class.py` run on every fixture, in both the code and from-json
  variants: `run_test_explanation_links_survive_round_trip` and
  `run_test_displaying_one_stored_formula_computes_only_its_operands`. The second covers "load computes nothing",
  "save of a partially computed model computes nothing", "display computes only what it shows" and "stored values
  re-serialize unchanged after a display". The from-json simple test also asserts that loading computes nothing.
- The re-serialization assertion compares everything except `calculation_graph`. On the shared, mutated complex
  fixture, a slot recomputed for display gets reads that its saved edges lacked: an earlier test leaves
  `Usage-pattern-2` on a second `France` object with the same id, and the save drops the edge to that object's
  timezone as foreign. The stored values and objects are identical. Top-level class key order can also change
  after pulls, so the comparison is by dict equality, not by JSON string.
- Outside the brief's file list: a stale docstring clause in `peek_attribute_value`
  (`object_linked_to_modeling_obj.py`) that named the removed rehydration.

## Open concerns
- After a reload, children are incomplete for computed-dict elements keyed by derived attribution coordinates
  (for example `hourly_data_transferred_per_coordinate[...]`, a child of `Job.data_transferred` once attribution
  or Sankey ran). `calculation_graph_section` (`system_to_json.py`) skips sub-slots whose key is not a serialized
  modeling object, so their edges are not saved and those children are listed only after they are recomputed.
  This predates the feature: the old inversion pass listed even fewer children. It does break the plan's "children
  complete after round trip" row for these keys. The round-trip test leaves such children out of the expected
  list, with a comment. A fix would mean persisting coordinate-keyed sub-slot addresses and rebuilding their keys
  at load, which is outside this task.
