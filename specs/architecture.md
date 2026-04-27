# Architecture — e-footprint

## Three-layer separation

The codebase is organised in three layers with a strict dependency direction:

```
efootprint/core/                       (modeling logic — what is computed)
        ↓ depends on
efootprint/abstract_modeling_classes/  (optimization layer — how to recompute incrementally)
        ↓ depends on
efootprint/api_utils/                  (serialization — how to persist/load)
```

This separation is constitutional (`specs/constitution.md` §1.1). Modeling code should not need to know how dependency graphs are tracked; serialization should not need to know how calculations work.

`efootprint/builders/` provides convenience subclasses of core objects with sensible defaults and external-data integrations (EcoLogits, Boavizta).

## Core (`efootprint/core/`)

- **Usage** — patterns, journeys, and jobs that define how systems are used.
- **Hardware** — physical infrastructure (servers, storage, networks, end-user devices).
- **Edge** — devices, components, processes, and groups for fleet modeling.
- **System** — top-level container; manages usage patterns and computes total footprint.

`System` is the only class explicitly listed in `CANONICAL_COMPUTATION_ORDER` for top-level recalculation ordering.

## Optimization layer (`efootprint/abstract_modeling_classes/`)

Avoid gathering context here unless absolutely necessary — most modeling work doesn't require it.

- **`ModelingObject`** — base class with dependency tracking and update logic. All e-footprint objects inherit from this.
- **`ExplainableObject`** — manages the calculation graph; allows automatic explanations and incremental recomputation.
- **`ExplainableQuantity`** — values with units; inherits from `ExplainableObject`.
- **`ExplainableHourlyQuantities`** — hourly time-series.
- **`ExplainableRecurrentQuantities`** — recurrent quantities defined over a typical week (168 hours).
- **`EmptyExplainableObject`** — neutral numerical object; acts like zero or zero-like time-series data.
- **`ModelingUpdate`** (in `modeling_update.py`) — handles all recomputation logic when inputs change.

## API utils (`efootprint/api_utils/`)

- **`json_to_system.py`** / **`system_to_json.py`** — serialization round-trip. Saves systems with or without calculated attributes.
- **`version_upgrade_handlers.py`** — migration logic for schema changes. Migrations apply to JSON files saved without calculated attributes.

## Modeling object structure

Every modeling object defines:

- **`default_values`** — dict specifying default values for numerical attributes. Units are used for unit consistency checks.
- **`calculated_attributes`** property — list of attribute names computed automatically.
- **`update_<attribute_name>`** methods — one per calculated attribute, implementing the calculation logic.
- **`after_init`** — called after initialization to toggle dynamic recomputation and trigger calculations.

The `__setattr__` override in `ModelingObject` ensures that when a numerical or object attribute is changed, all dependent calculated attributes are recomputed automatically.

## Adding a new modeling object

1. Inherit from the appropriate core or builder base class.
2. Define `default_values` and `calculated_attributes`.
3. Implement an `update_<attr>` method per calculated attribute.
4. Register the class in `efootprint/all_classes_in_order.py`:
   - Always add to `ALL_EFOOTPRINT_CLASSES` (used for serialization and deserialization).
   - For top-level core objects, also add to `CANONICAL_COMPUTATION_ORDER`.

This is a constitutional quality gate (`specs/constitution.md` §2.5).

## Object linking and dependencies

Object dependencies are managed through `modeling_objects_whose_attributes_depend_directly_on_me` on `ModelingObject`. When a numerical input changes, the calculation graph (managed by `ExplainableObject`) ensures only affected calculations are recomputed.

There are three relationship types between modeling objects:

- **Direct.** `self.child = some_modeling_object` — single reference.
- **List.** `self.children = ListLinkedToModelingObj([...])` — ordered collection.
- **Dict (input).** `self.children_by_key = ExplainableObjectDict({...})` passed as `__init__` param. Keys are `ModelingObject`s representing structural children.

All three populate `contextual_modeling_obj_containers` on the child objects so they can discover their parents. Dict-based relationships can also be discovered via `explainable_object_dicts_containers`.

## `ExplainableObjectDict` as input attribute

`ExplainableObjectDict` can be used both as a calculated attribute and as an `__init__` parameter (input attribute). Behaviour differs:

- **Calculated dicts.** `trigger_modeling_updates=False` (default). Mutations don't trigger recomputation — the owning `update_*` method manages them.
- **Input dicts.** `trigger_modeling_updates=True` (set automatically by `after_init()` for dicts that are `__init__` params). Mutations (`__setitem__`, `__delitem__`) trigger `ModelingUpdate` to recompute dependents.
- **Re-entry guard.** When `ModelingUpdate.apply_changes()` replaces a value inside a trigger-enabled dict, triggers are temporarily disabled to prevent infinite loops.
- **Deserialization order (critical).** Input dicts must be initialized empty before `after_init()` runs. Then a deferred loop populates them via `replace_in_mod_obj_container_without_recomputation`. Then triggers are enabled on the populated dicts. This prevents crashes from computing on incomplete state.

## Units and calculations

All quantities use Pint for unit handling. Custom units are defined in `efootprint/constants/custom_units.txt`. Calculations are explainable with full dependency graphs.

## Display layer

`efootprint/utils/display.py` provides `best_display_unit()` and `format_quantity_for_display()` for magnitude-aware unit scaling.

**Key invariant:** Pint quantities flow through calculations unchanged. Unit scaling to human-readable form happens only at render time. Explainable classes expose `display_quantity` and `display_unit` properties that use this layer.

## Doc-as-code metadata (in flight)

Per constitution §1.4, descriptive metadata about classes, params, and calculated attributes lives in the classes themselves, not in external documents. The migration is in flight; see `roadmap.md` and the cross-repo tutorial-and-documentation feature for status.

The shape (when complete):

- **Class docstring** — what the class is.
- **`param_descriptions` dict** — one entry per `__init__` param (minus `self` and `name`).
- **`update_<attr>` docstring** — what the calculated attribute means.
- Optional class attributes: `disambiguation`, `pitfalls`, `interactions`, `param_interactions`.

The mkdocs reference and the e-footprint-interface both consume this metadata; descriptions are not duplicated elsewhere.
