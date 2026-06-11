# Architecture — e-footprint

## Three-layer separation

The codebase is organised in three layers with a strict dependency direction (foundation at the bottom, peripheral layers on top):

```
efootprint/api_utils/                  (serialization — how to persist/load)
        ↓ depends on
efootprint/core/                       (modeling logic — what is computed)
        ↓ depends on
efootprint/abstract_modeling_classes/  (framework — dependency tracking, ExplainableObject, incremental recompute)
```

This separation is constitutional (`specs/constitution.md` §1.1). `core/` is built on top of `abstract_modeling_classes/`, but it must not import from `api_utils/` — modeling code shouldn't know how it gets persisted. `api_utils/` is the only layer allowed to import from both.

**Known back-edge.** `abstract_modeling_classes/modeling_object.py` imports `LifeCyclePhases` from `efootprint/core/` (runtime), `System` (TYPE_CHECKING), and — function-locally — `core.attribution.footprint_per_node` for the two `attributed_*_footprint` convenience cached properties. This is a leak of the layering and should be paid down opportunistically; new code must not introduce additional upward imports from `abstract_modeling_classes/` into `core/`.

**No domain names in the framework layer.** The dependency rule applies to *names*, not just imports: `abstract_modeling_classes/` may not mention `core/` concepts (`UsagePattern`, `Job`, `Server`, …) by name — not in class attributes, not in strings, not in comments load-bearing for behaviour. When the framework needs to be polymorphic over a domain-specific extension (e.g., a cached property that only some subclasses define), it discovers the extension structurally rather than naming it. Example: `class_cached_property_names` auto-discovers every `functools.cached_property` through the class MRO; the flush machinery (`flush_cached_properties`, the system-wide sweep, `to_json` / `__setattr__` skip lists) consumes that discovery, so domain subclasses add cached properties without registering them anywhere. Corollary invariant: every `cached_property` on a `ModelingObject` is a flushable read-time projection (lazy attribution layer), never model state.

`efootprint/builders/` provides convenience subclasses of core objects with sensible defaults and external-data integrations (EcoLogits, Boavizta).

`efootprint/modeling_templates/` ships reference systems backing the mkdocs how-to pages: JSON files under `how_to/`, regenerable Python authoring scripts under `how_to/_authoring/`, and a typed registry (`HowToTemplate`, `HOW_TO_TEMPLATES`). Public helpers `list_how_to_templates`, `get_template`, `load_template_system` live on the package; imports are upward-only (`api_utils` for load/save). Template authoring uses `efootprint.builders.timeseries` builders for input hourly/recurrent timeseries so those inputs stay editable in the interface after JSON load.

## Core (`efootprint/core/`)

- **Usage** — patterns, journeys, and jobs that define how systems are used.
- **Hardware** — physical infrastructure (servers, storage, networks, end-user devices).
- **Edge** — devices, components, processes, and groups for fleet modeling.
- **System** — top-level container; manages usage patterns and computes total footprint.

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

- **Schema version policy.** The schema version bumps only when inputs-only JSONs change; adding or removing calculated attributes (and cached properties, which are never serialized) requires no bump. Cross-version loads of JSONs saved **with** calculated attributes are unsupported — no loader guard, no version handler (settled 2026-06-10).
- **`json_to_system.py`** / **`system_to_json.py`** — serialization round-trip. Saves systems with or without calculated attributes. **Reference resolution heuristic:** in `ModelingObject.from_json_dict`, a scalar string attribute is interpreted as an object reference when it equals an already-built object's `id`. `id` and `name` are exempt (names are plain labels, never references) — otherwise an object whose `name` equals another object's `id` (e.g. a second "France" country alongside the catalog one keyed `"France"`) would have its name silently resolved into that object.
- **`version_upgrade_handlers.py`** — migration logic for schema changes. Migrations apply to JSON files saved without calculated attributes.
- **`Source` is a top-level JSON entity (since v21).** Each `Source` carries a deterministic `id` (uuid in production, name-based in tests via `Source._use_name_as_id`). `ExplainableObject.source` serializes as `"source": "<source_id>"`; the system JSON has a top-level `"Sources": {id: {...}}` block with only the sources actually referenced. Sentinel ids `"user_data"` and `"hypothesis"` are pinned so `Sources.USER_DATA` / `Sources.HYPOTHESIS` re-identify with the live Python singletons across reloads. Source application during JSON load is centralized in `_apply_json_source` (in `explainable_object_base_class.py`); per-subclass `from_json_dict` no longer constructs `Source` instances.

## Modeling object structure

Every modeling object defines:

- **`default_values`** — dict specifying default values for numerical attributes. Units are used for unit consistency checks.
- **`calculated_attributes`** property — list of attribute names computed automatically.
- **`update_<attribute_name>`** methods — one per calculated attribute, implementing the calculation logic.
- **`after_init`** — called after initialization to toggle dynamic recomputation and trigger calculations.

The `__setattr__` override in `ModelingObject` ensures that when a numerical or object attribute is changed, all dependent calculated attributes are recomputed automatically.

## Class registration and ordering

`efootprint/all_classes_in_order.py` exposes two registries:

- **`ALL_EFOOTPRINT_CLASSES`** — every concrete `ModelingObject` subclass (core + builders + services). Used by JSON serialization/deserialization to resolve class names round-trip.
- **`CANONICAL_COMPUTATION_ORDER`** — top-level core classes ordered low → high level (`Country`, `UsagePattern`, …, `System` last). Used to walk objects deterministically when recomputing dependents (`ModelingUpdate`), to assign sankey columns, and to give tests a stable iteration order.

`SANKEY_COLUMNS`, `OBJECT_CATEGORIES`, and the various per-shape lists (`SERVER_CLASSES`, `EDGE_COMPONENT_CLASSES`, etc.) live alongside and are consumed by rendering and builder code.

## Adding a new modeling object

1. Inherit from the appropriate core or builder base class.
2. Define `default_values` and `calculated_attributes`.
3. Implement an `update_<attr>` method per calculated attribute.
4. Register the class in `efootprint/all_classes_in_order.py`:
   - Always add to `ALL_EFOOTPRINT_CLASSES`.
   - For top-level core classes, also add to `CANONICAL_COMPUTATION_ORDER` at the position that respects dependency order.

This is a constitutional quality gate (`specs/constitution.md` §2.5).

## Object linking and dependencies

Object dependencies are managed through `modeling_objects_whose_attributes_depend_directly_on_me` on `ModelingObject`. When a numerical input changes, the calculation graph (managed by `ExplainableObject`) ensures only affected calculations are recomputed.

There are three relationship types between modeling objects:

- **Direct.** `self.child = some_modeling_object` — single reference.
- **List.** `self.children = ListLinkedToModelingObj([...])` — ordered collection.
- **Dict (input).** `self.children_by_key = ExplainableObjectDict({...})` passed as `__init__` param. Keys are `ModelingObject`s representing structural children.

All three populate `contextual_modeling_obj_containers` on the child objects so they can discover their parents. Dict-based relationships can also be discovered via `explainable_object_dicts_containers`.

## Attribution layer (the atom model)

Attribution lives entirely in `efootprint/core/attribution/` and is lazy, read-time-only — calculated
attributes never read attribution results (the one-way rule that makes wholesale cached-property flushing
correct). Each impact source decomposes its footprint exactly once into **atoms** — the finest
`(source, stream, containment cell, usage pattern)` slices of hourly footprint, emitted by the source's
`attribution_atoms(phase)` generator. Every attribution number is the same operation, a fold: group atoms by
a key and sum.

- node total at any level = group by that level's key; link between columns = consecutive visible chain nodes
- **skip a column** = leave its classes out of the fold's `visible_levels` (adjacent visible nodes link
  directly)
- **exclude a source** = filter its atoms out — never rescale
- conservation is structural: Σ(atoms of a stream) == that stream's footprint == the eager totals
- renderers are presentation-only: `ImpactRepartitionSankey` makes one `node_totals_and_links` call per
  life-cycle phase and owns nothing but layout, colors and aggregation

Caching is two-tier in each owner's `render_cache` (itself a cached property): atom lists per
`(source, phase)`, fold results per query. Both are wiped by the system-wide cached-property flush after
every `ModelingUpdate` and after the initial build.

`ModelingObject` keeps two convenience cached properties — `attributed_fabrication_footprint` /
`attributed_energy_footprint` — that delegate to `attribution.footprint_per_node` at the object's own class
level. They are the only `attributed_*` surface; everything heavier (per-source dicts, resolve/rescale
machinery, eager repartition-weight calculated attributes) was deleted with the 2026-06 attribution revamp.

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
