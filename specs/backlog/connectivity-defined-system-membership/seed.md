# Connectivity-defined system membership — backlog seed

Status: parked backlog · 2026-10-20 · library-owned, interface adapts.
Origin: review of [IMPL-DECISION-02](../../features/explanation-links-from-formula-and-slots/plan.html#impl-decision-02)
and the parked item it left in the explanation-links `tasks.md`. This file carries the discussion until a
`spec-specify` session turns it into a feature.

## The problem

The library has two definitions of what belongs to a `System`, and they only coincide in the state the
constructor leaves behind.

- **Scope is defined forward.** `System.all_linked_objects` is the closure from the two input lists
  `usage_patterns` and `edge_usage_patterns`: patterns, journeys, steps, jobs, then servers, storages, devices.
  The save (`system_to_json`) and every per-category accessor (`servers`, `jobs`, `devices`, ...) use it.
- **Footprints are computed backward.** A server's `nb_of_instances` and use footprints iterate `self.jobs`,
  a reverse collection from `Job.server`; `Job.occurrence_coordinates` iterates its reverse links to steps,
  journeys and patterns and to recurrent server needs and edge patterns. Nothing in that walk asks which
  system a pattern belongs to.

So a server's footprint is a property of the server object across every pattern that reaches it, in any
system or in none, and the system merely sums what the forward walk finds.

The existing guard `check_no_object_to_link_is_already_linked_to_another_system` (re-run at
`total_footprint`) enforces half of the implicit invariant: an object may not be reached from two systems.
The other half, that an object inside the system may not be driven by a pattern listed in no system, is not
enforced anywhere.

## Evidence

Unlinking an `EdgeUsagePattern` from its system without deleting it (`system.edge_usage_patterns = []` on
the complex integration fixture after computing `impact_repartition_matrix`), then saving inputs-only and
reloading:

| | before `3dc4c55f` (IMPL-DECISION-02) | after |
|---|---|---|
| unlinked pattern written to the file | yes | no |
| total in memory after the unlink, kg | 36,859,408,384 | 36,859,408,384 |
| total after an inputs-only reload, kg | 36,859,408,384 | 10,156 |

Before the decision the old traversal reached the pattern by accident through a computed dict keyed by it.
The inputs-only traversal is the forward definition applied honestly; memory keeps the backward one.
The in-memory half is pre-existing; the file-side divergence was introduced by IMPL-DECISION-02.

The state is unreachable from the interface, which removes objects only through `self_delete` (refuses while
a container still holds the object, severs its slots). A library user who reassigns a system's pattern list
and saves loses silently everything the pattern drove.

Related code that exists only because of this state: the foreign-coordinate skip in
`calculation_graph_section` (`system_to_json.py`) and its producer test
`test_coordinate_with_an_unsaved_component_is_skipped_at_save` (`tests/api_utils_tests/test_minimal_serialization_contract.py`).

## Why the declared member list is a legacy

In the push-based engine the pattern lists defined the launch set: computation started from the patterns and
flowed down, so the system had to know where to start. The reactive engine removed that role; a server
computes from its reverse links with no root in sight. What remains of the lists is a membership declaration
that no computation consults, which is why it can disagree with what the computation does.

What a `System` still has to be: a named identity (interface, `compare_to`, version baseline), an aggregation
point (`total_footprint`, `impact_repartition_matrix`, category breakdowns), and the root a save starts from.
None of these needs a declared member list; they need a way to find the component.

## Proposed direction

Define membership as the connected component of the `System` over all relationships, forward and reverse.

- Scope and aggregation share one definition: an unlinked-but-connected pattern is simply still in the system,
  in memory and in the file. The parked product decision dissolves instead of needing a side picked.
- The save walks the component, ending the inputs-only versus reverse-links question behind
  IMPL-DECISION-02. Determinism then comes from a canonical order (class, then id) rather than traversal order.
- The two-systems guard becomes "at most one `System` per component", which is also necessary: shared leaf
  objects (a country, a default device) would otherwise glue two systems together. The constraint already
  exists today in another form.
- A user-authored journey whose pattern was removed stays connected through its jobs and is kept in the file;
  today the save silently drops it.
- `System.fork()` and the timeline item in `specs/roadmap.md` get a well-defined primitive: copy a component.

Open: keep the pattern lists as the system's own edges into the graph (minimal change, interface unchanged) or
drop them and derive the interface's pattern list from the component (honest version; changes the
constructor, the schema and every example).

## Options considered and set aside

1. Enforce the missing half as an invariant: extend the system guard so every pattern reachable backward from
   the system's objects is listed, raise at the edit pointing to `self_delete`. Smallest change; keeps the
   two-definition design and the state representable-but-rejected.
2. Make the save follow the backward definition by also writing objects reachable through reverse links only.
   Memory and file agree, but files then hold patterns no system lists, the state the interface treats as
   impossible.
3. Make computation follow the forward definition by passing the system into job and server aggregation.
   Contradicts the rule that objects compute independently of the `System`; ripples through attribution.

## Consumers to redirect

- `System.all_linked_objects` and the category accessors (`efootprint/core/system.py`).
- `ModelingObject.systems` (`modeling_object.py`), currently forward-only through containers; must become
  symmetric. Readers: `InfraHardware.systems`, `efootprint/core/attribution/__init__.py` (`for system in
  obj.systems`), `builders/services/service_base_class.py`.
- `system_to_json` object discovery; `pull_slots_system_wide` / `invalidate_slots_system_wide`
  (`modeling_object.py`).
- Interface: `views_edition.py` uses `len(obj_to_edit.systems) > 0` as "object is in the model".
- Docs: `specs/architecture/relationships.html`, `persistence.html`, `layers-and-modeling.html`.

## Costs and traps

- The component walk replaces `all_linked_objects` and runs on each total read, comparable to today's
  category walk (about 3 ms on 200 objects). Keep it a plain property; a reactive structure would be
  invalidated by every relationship edit anyway.
- Traversal must handle cycles (edge device groups) with a visited set, and include dict keys of
  `ExplainableObjectDict` attributes (see `ModelingUpdate.collect_newly_linked_mod_objs` for an existing
  closure that does).
- One-time regeneration of the committed reference fixtures if the file order changes.
- Once membership is connectivity-based, turn the foreign-coordinate save skip into a `ValueError`, like the
  loader's absent-object check, and delete its producer test.
