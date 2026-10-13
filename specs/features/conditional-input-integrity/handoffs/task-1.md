# Task 1 — Register and query conditional rules

Repository and implementation range: `e-footprint` `e16f575391afb79323f1cff8951ed7a9ffe378a2..c1e90d00e6ef3cee55a9abfaa003c415359da203`.
The interface was untouched, baseline `7352ac8af148097e5ef186f2396a823fa987b181`.

## Review pointers

- `conditional_inputs.py` registers routing metadata at subclass definition; choices are read from effective class metadata on each query. Reverse lookup overlays proposed direct links and requires the exact registered dependent class.
- `resolve_input_path()` reads attached or proposed input values without invoking getters, returns the unwrapped controller owner, and reports missing terminal inputs as well as missing relationships.
- Legacy membership validation and `attributes_with_depending_values()` remain for Task 2 to replace. The query contract is documented in `specs/architecture/relationships.html#conditional-inputs`.
