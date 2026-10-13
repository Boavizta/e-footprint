# Task 2 — Reject incompatible library changes atomically

Repository and implementation range: `e-footprint` `190f9341b7e6e584fdd26db22fc7dd988894976c..625fd79b3e2a6e02fea15001abb0f257355ca4d2`.

## Review pointers

- `ModelingUpdate` captures addresses after normalization and validates the union of changed and declared dependent inputs against the fully applied graph, inside the existing rollback boundary and before eager pulls. Task 1 query APIs are unchanged.
- `ModelingObject.check_belonging_to_authorized_values(name, proposed_changes=None)` validates one input. Passive assignments stage their value and check assigned dependents before attachment; hydration retains its explicit bypass. The old local reverse-map helper is removed.
- Three existing `System.__new__` fixtures in `tests/test_system.py` omitted base initialization. They now call `ModelingObject.__init__` to establish the identity required by input-address maps; no production fallback was added.
