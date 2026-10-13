# Task 2 — Reject incompatible library changes atomically

Repository and implementation range: `e-footprint` `190f9341b7e6e584fdd26db22fc7dd988894976c..ed0e099864841bc809f31161f4a5ecf6fe246e0e`.

## Review pointers

- `ModelingUpdate` captures addresses after normalization and validates the union of changed and declared dependent inputs against the fully applied graph, inside the existing rollback boundary and before eager pulls. Task 1 query APIs are unchanged.
- `ModelingObject.check_belonging_to_authorized_values(name, proposed_changes=None)` validates one input. Passive assignments stage their value and check assigned dependents before attachment; hydration retains its explicit bypass. The old local reverse-map helper is removed.
- Three existing `System.__new__` fixtures in `tests/test_system.py` omitted base initialization. They now call `ModelingObject.__init__` to establish the identity required by input-address maps; no production fallback was added.
- Review found a pre-existing constructor leak: a rejected dependent retained its previously attached relationship, so subsequent controller edits discovered an incomplete owner and failed on its missing input. `AfterInitMeta` now retains the instance across `__init__`/`after_init`, detaches its owned inputs and caches, and removes computed dependency edges on failure before re-raising the original error. The supervisor approved this lifecycle correction; its rationale belongs in the plan's implementation decision callout.
