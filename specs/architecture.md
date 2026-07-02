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

**No back-edge.** `abstract_modeling_classes/` no longer imports anything from `efootprint/core/`: the last framework→core leak (a function-local `System` import in the former computation-chain optimizer) was deleted with the eager push engine when computation became pull-based. Keep it that way.

**No domain names in the framework layer.** The dependency rule applies to *names*, not just imports: `abstract_modeling_classes/` may not mention `core/` concepts (`UsagePattern`, `Job`, `Server`, …) by name — not in class attributes, not in strings, not in comments load-bearing for behaviour. When the framework needs to be polymorphic over a domain-specific extension, it discovers the extension structurally rather than naming it. Example: `@lazy_attribute` (in `reactive_core.py`) is the framework-level notion of a read-time projection slot; the attribution layer declares its projections with it without the framework ever naming attribution. (`functools.cached_property` is no longer used on `ModelingObject`s — the former "every cached_property is a flushable projection" invariant died, together with the wholesale flush machinery, when attribution caching joined the reactive graph.)

`efootprint/builders/` provides convenience subclasses of core objects with sensible defaults and external-data integrations (EcoLogits, Boavizta).

`efootprint/modeling_templates/` ships reference systems backing the mkdocs how-to pages: JSON files under `how_to/`, regenerable Python authoring scripts under `how_to/_authoring/`, and a typed registry (`HowToTemplate`, `HOW_TO_TEMPLATES`). A separate `HowToGuide`/`HOW_TO_GUIDES` registry maps each how-to *page* (`doc_path`) to the `template_id` it walks through — decoupled from the loadable template, so several guides can share one scenario (the database and server-to-server guides both point at `ecommerce`), and `HowToTemplate` itself carries no `doc_path`. Public helpers `list_how_to_templates`, `list_how_to_guides`, `get_template`, `load_template_system` live on the package; imports are upward-only (`api_utils` for load/save). Template authoring uses `efootprint.builders.timeseries` builders for input hourly/recurrent timeseries so those inputs stay editable in the interface after JSON load.

## Core (`efootprint/core/`)

- **Usage** — patterns, journeys, and jobs that define how systems are used.
- **Hardware** — physical infrastructure (servers, storage, networks, end-user devices).
- **Edge** — devices, components, processes, and groups for fleet modeling.
- **System** — top-level container; manages usage patterns and computes total footprint.

## Optimization layer (`efootprint/abstract_modeling_classes/`)

Avoid gathering context here unless absolutely necessary — most modeling work doesn't require it.

- **`ModelingObject`** — base class with dependency tracking and update logic. All e-footprint objects inherit from this.
- **`reactive_core.py`** — the pull-based computation engine: `@computed_attribute` / `@computed_dict` descriptors (each computed attribute resolves to a per-instance `ReactiveSlot` that computes on read, caches, and is invalidated by deletion waves along recorded dependency edges), `@lazy_attribute` read-time projection slots (same graph and invalidation, but excluded from `calculated_attributes` — so never eagerly recomputed, serialized, or documented — and holding raw values such as plain dicts/tuples outside the container bookkeeping, with calculus edges recorded from every explainable found in the returned structure), `ReverseCollection`/`ReverseLink` declarative reverse relationships, and the relationship read/write hooks' primitives.
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
- **`@computed_attribute` / `@computed_dict` getters** — one per computed attribute; the getter body is the calculation and its docstring the doc-as-code description. `calculated_attributes` is derived from the class computed-slot registry (`computed_slots(cls)`); a subclass drops an inapplicable inherited attribute with `removed_computed_attribute()`.
- **`after_init`** — called after initialization to enable live updates (`trigger_modeling_updates`).

Computation is pull-based: reading a computed attribute computes and caches it on demand. The `__setattr__` override in `ModelingObject` routes live input writes through `ModelingUpdate`, which invalidates the changed slots' dependency cones and eagerly recomputes (currently every slot, so errors surface at update time).

## Class registration and ordering

`efootprint/all_classes_in_order.py` exposes two registries:

- **`ALL_EFOOTPRINT_CLASSES`** — every concrete `ModelingObject` subclass (core + builders + services). Used by JSON serialization/deserialization to resolve class names round-trip.
- **`CANONICAL_CLASSES`** — the top-level core families every object maps to (`canonical_class`), derived from the Sankey structure: flattened `SANKEY_COLUMNS` plus `SANKEY_BREAKDOWN_ONLY_CLASSES` and `NON_SANKEY_CANONICAL_CLASSES`. Membership only — pull-based computation needs no class ordering.

`SANKEY_COLUMNS`, `OBJECT_CATEGORIES`, and the various per-shape lists (`SERVER_CLASSES`, `EDGE_COMPONENT_CLASSES`, etc.) live alongside and are consumed by rendering and builder code.

## Adding a new modeling object

1. Inherit from the appropriate core or builder base class.
2. Define `default_values`.
3. Implement a `@computed_attribute` (or `@computed_dict`) getter per computed attribute.
4. Register the class in `efootprint/all_classes_in_order.py`:
   - Always add to `ALL_EFOOTPRINT_CLASSES`.
   - For new top-level core families, extend the canonical-class registry (`SANKEY_COLUMNS` / `SANKEY_BREAKDOWN_ONLY_CLASSES` / `NON_SANKEY_CANONICAL_CLASSES`).

This is a constitutional quality gate (`specs/constitution.md` §2.5).

## Object linking and dependencies

Object dependencies form one slot-addressed graph in `reactive_core`: calculus edges are recorded from each computed value's arithmetic ancestry (managed by `ExplainableObject`), and structural edges are recorded by relationship read hooks (list/dict/link wrappers, reverse relationships, `modeling_obj_containers`). Writes invalidate the changed node and the deletion wave voids its transitive dependents; membership writes additionally bump the affected reverse-relationship nodes at the container-field transition.

There are three relationship types between modeling objects:

- **Direct.** `self.child = some_modeling_object` — single reference.
- **List.** `self.children = ListLinkedToModelingObj([...])` — ordered collection.
- **Dict (input).** `self.children_by_key = ExplainableObjectDict({...})` passed as `__init__` param. Keys are `ModelingObject`s representing structural children.

All three populate `contextual_modeling_obj_containers` on the child objects so they can discover their parents. Dict-based relationships can also be discovered via `explainable_object_dicts_containers`.

Downwards, `mod_obj_attributes` is the SSOT: it returns every referenced object across all three relationship types, and is what consumers walking the object graph (the relationship graph builder, the interface's cascade deletion) must call. Direct and list references are wrapped in `ContextualModelingObjectAttribute`s while structural dict keys are the `ModelingObject`s themselves, so `contextual_mod_obj_attributes` exposes the wrapped subset for the one caller that needs it — `self_delete`, which severs those links one by one and leaves dict-held children to the dict, which unlinks its keys as a whole. Only **structural input** dicts count as references: calculated dicts keyed by modeling objects (`Job.hourly_occurrences_per_usage_pattern`, `Storage.full_cumulative_storage_need_per_job`, …) are results, and treating their keys as references would make every result-holder look like a container of its keys.

## Attribution layer (the atom model)

Attribution lives entirely in `efootprint/core/attribution/` and is lazy, read-time-only — calculated
attributes never read attribution results (the one-way rule that keeps the projection layer strictly
downstream of the footprint graph). Each impact source decomposes its footprint exactly once into
**atoms** — the finest `(source, stream, containment cell, usage pattern)` slices of hourly footprint,
emitted by the source's `attribution_atoms(phase)` generator. Every attribution number is the same
operation, a fold: group atoms by a key and sum.

- node total at any level = group by that level's key; link between columns = consecutive visible chain nodes
- **skip a column** = leave its classes out of the fold's `visible_levels` (adjacent visible nodes link
  directly)
- **exclude a source** = filter its atoms out — never rescale
- conservation is structural: Σ(atoms of a stream) == that stream's footprint == the eager totals
- **two relay-weight kinds** (carried per containment cell by `JobAttributionCell`): demand streams
  (dynamic energy, autoscaling/serverless provisioned, storage retention, external-API requests) relay by
  *hourly* occurrence shares with fallback 0 — zero demand at an hour means zero footprint; always-on
  streams (on-premise provisioned, storage baseline, edge idle floor) relay by *flat period-total* shares
  (a scalar), so footprint at idle hours is conserved instead of dropped or double-counted
- renderers are presentation-only: `ImpactRepartitionSankey` makes one `node_totals_and_links` call per
  life-cycle phase and owns nothing but layout, colors and aggregation. That fold runs over the stored
  matrix's *period-total scalars* (the Sankey renders sums only); `footprint_per_node[_per_source]` remain
  the hourly reads, folding live atoms on every call

Caching follows the one paradigm of the reactive graph, in two `@lazy_attribute` projection layers: each
source (the `AttributionSource` mixin: `ServerBase`, `Storage`, `Device`, `Network`, `EdgeDevice`,
`ExternalAPIServer`) exposes `impact_repartition_rows` — its atoms reduced to dict-encoded matrix rows
`(source, stream, cell coordinate ids, up, phase) → period sum in kg`, with calculus edges recorded from
each atom's hourly value before reduction — and `System.impact_repartition_matrix` concatenates them.
The heavier per-source share physics (`binding_demand_per_job`, `attribution_cells`,
`retention_cumulative_per_cell`, …) are lazy slots too. Everything computes on first read, caches, and is
invalidated *precisely* through recorded dependency edges — a one-input edit voids only the row slots in
its cone; there is no wholesale flush anywhere. Lazy slots are never eagerly recomputed by
`ModelingUpdate` (they stay void until the next render) and never serialized.

**EdgeDevice fabrication is deployment-booked; energy is need-booked.** A component with no needs at a
pattern the device serves still books its embodied carbon eagerly with the deployment, exactly like the
chassis (`EdgeDevice.unused_component_fabrication_per_edge_device`, computed from the component's *input*
attributes because need-less components never enter the calculated-attribute chain), so the eager
per-pattern fabrication totals always carry the whole device. At attribution, that unused-components pool
(own fabrication + equal chassis shares) splits equally across the pattern's deployment carriers —
component needs and `RecurrentServerNeed`s — so RSN-only patterns route the whole device fabrication
through the RSNs; a pattern with booked fabrication and no carriers raises. Energy has no such rule: the
device draws nothing for unused components, so unused components book none on either side.

The convenience read `attribution.attributed_footprint(obj, phase)` returns any object's total attributed
footprint for a life-cycle phase — its node entry in `footprint_per_node` at the object's own class level,
summed over its systems (Empty when system-less). It is the only `attributed_*` surface; everything heavier
(per-source dicts, resolve/rescale machinery, eager repartition-weight calculated attributes, the former
`ModelingObject.attributed_*_footprint` cached properties) was deleted with the 2026-06 attribution revamp.

## `ExplainableObjectDict` as input attribute

`ExplainableObjectDict` can be used both as a calculated attribute and as an `__init__` parameter (input attribute). Behaviour differs:

- **Calculated dicts.** `trigger_modeling_updates=False` (default). Mutations don't trigger recomputation — the computed-dict slot machinery manages them (the dict is a live facade over the key-set node and per-key sub-slots).
- **Input dicts.** `trigger_modeling_updates=True` (set automatically by `after_init()` for dicts that are `__init__` params). Mutations (`__setitem__`, `__delitem__`) trigger `ModelingUpdate` to recompute dependents.
- **Re-entry guard.** When `ModelingUpdate.apply_changes()` replaces a value inside a trigger-enabled dict, triggers are temporarily disabled to prevent infinite loops.
- **Deserialization order (critical).** Input dicts must be initialized empty before `after_init()` runs. Then a deferred loop populates them via `replace_in_mod_obj_container_without_recomputation`. Then triggers are enabled on the populated dicts. This prevents crashes from computing on incomplete state.
- **Weighted relationship dicts.** Relationship dicts whose values are weights (`UsageJourney.uj_steps`, `UsageJourneyStep.jobs`, `RecurrentServerNeed.jobs`, `EdgeDeviceGroup.sub_group_counts` / `edge_device_counts`) are built with `to_weighted_explainable_object_dict` (constructor sugar: list of keys with duplicates accumulating, or plain-number values wrapped as dimensionless `SourceValue`s), which returns a `WeightedExplainableObjectDict` enforcing dimensionless, non-negative weights on every `__setitem__`. JSON load rebuilds dict attributes with the class declared by their `__init__` annotation, so the subclass (and its invariant) survives round-trips; `ModelingUpdate` and structural dict replacements preserve the dict type too. Calculations read the weights via `.items()` (e.g. journey duration = Σ times-per-journey × step time); iterating the dict yields the related objects in insertion order, so step ordering survives.

## Comparison (`efootprint/comparison/`)

`SystemComparison` (entry point `System.compare_to(other)`) is the domain-truth comparison of two systems, usable directly from a notebook or coding agent. It is pure read-time computation — no new modeling logic, no attribution claims — every number is read from each system's already-computed totals:

- **Totals + delta** from `total_footprint.sum()`; the `Delta` value object exposes the absolute change and the relative fraction over the baseline (`None` when the baseline is zero).
- **Per-(category, phase) decomposition** from each system's `total_energy_/fabrication_footprint_sum_over_period` dicts (category SSOT = `OBJECT_CATEGORIES`, phases = energy/fabrication). Because those dicts already sum to the total, the decomposition rows sum to the headline delta by construction.
- **Aligned + cumulative time-series** from each system's `total_footprint`, sharing one calendar axis via `align_temporally_quantity_arrays` (non-overlapping hours zero-padded). The `TimeSeries` also carries the per-phase usage/fabrication split (`usage_*`/`fabrication_*`) on that same axis — summed across categories exactly as the `total_footprint` getter builds the total, so `usage + fabrication` reconstructs the total hour-by-hour. This lets a consumer bucket usage vs fabrication exactly per period (e.g. per year) instead of with a single full-period ratio.
- **Input diff**: walks `all_linked_objects`, pairs objects by id first then by (name, type), and emits changed input-attribute rows plus "only in A / only in B". Inputs are identified *positively* from the constructor signature (`get_init_signature_params(efootprint_class)` — same SSOT as `copy_with`), not by excluding `calculated_attributes`, then bucketed by type: scalar/array `ExplainableObject`s diff by value (+ unit/source/confidence) — except a *form-built* timeseries (one exposing `form_inputs_for_display`, i.e. `ExplainableHourlyQuantitiesFromFormInputs` / `ExplainableRecurrentQuantitiesFromConstant`) on both sides, which diffs by its form **parameters** (e.g. "net growth rate: 10 % per year → 20 %"), listing only the changed ones and skipping the opaque array comparison — while `ExplainableObjectDict` and `List[ModelingObject]` relationship inputs diff by membership (per-key counts / present-or-absent), their keys/elements paired id-first then (name, type). A membership add/remove row is only emitted when the member exists in *both* models (a genuine re-link); a member that lives in only one model is left to its "only in A / only in B" row, so it is never reported twice. Reading the signature off `efootprint_class` (not `type(obj)`) sees through the `ContextualModelingObjectAttribute` proxy.
- **Notebook plots** (`plot_emissions_over_time`, `plot_cumulative_emissions`, `plot_decomposition`) reuse the existing matplotlib dependency.

`efootprint/comparison/duplication.py` provides `duplicate_system(system)` (serialize→deserialize round-trip that mints a fresh System id while preserving every object id — so the diff can pair by identity) and `assign_fresh_system_id(system)` (re-id only the System object). The new id is always distinct from the old one, even under the name-as-id test convention.

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
- **computed-attribute getter docstring** — what the calculated attribute means.
- Optional class attributes: `disambiguation`, `pitfalls`, `interactions`, `param_interactions`.

The mkdocs reference and the e-footprint-interface both consume this metadata; descriptions are not duplicated elsewhere.
