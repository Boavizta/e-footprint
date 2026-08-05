# Conventions — e-footprint

These are the strong preferences and patterns the project follows. They are softer than the constitution: deviations are possible with justification, but defaulting to these preserves consistency.

## Code style

- **Python ≥ 3.12** (constitution §4).
- **Black** formatter, line length **120**. Keep the number of lines low; in particular, avoid creating a new line solely to close a parenthesis.
- **Poetry** for dependency management.
- **Type hints** are encouraged but not strictly enforced. Don't use forward references in `ModelingObject.__init__` signatures.
- **Mutable defaults are forbidden** in function signatures (e.g. `SourceValue(...)`). Use `None` and create the mutable inside the body.
- **Comments only when the WHY is non-obvious.** If a reader can derive intent from well-named identifiers, the comment is noise. Never comment what the code does — only why it does it that way.
- **Fail loudly on impossible states.** When a value reaches code that assumes it is well-formed (e.g. a positive Pint quantity, a non-NaN magnitude, a populated dict), raise a `ValueError`/`AssertionError` with a message that points at the upstream root cause rather than silently coercing or filtering. Silent passes (returning `False` for NaN, defaulting to zero, swallowing a missing key) hide real bugs and make them hard to debug later. Filtering is only acceptable at intentional UX boundaries (e.g. dropping zero-magnitude flows from a chart) — and even there, NaN and negative values are bugs and should raise.

## Modeling refactor preferences

These are project-specific patterns worth keeping in mind when extending modeling objects.

- **Respect the object lifecycle boundary.** A modeling object's complete `__init__` and subclass `after_init()` hook are passive; `AfterInitMeta` makes it live after both finish. Builder hooks may create defaults or replace constructor inputs during that phase. JSON hydration uses the framework's private passive attachment APIs and makes the graph live only after relationships, cached values, ancestry, and dependency edges are restored. Once live, ordinary assignments and public mutations of attached input lists/dicts are always transactional—there is no caller-controlled update bypass. Framework apply/rollback, computed facades, hydration, and focused test pinning use explicit private passive primitives instead.
- Computed attributes are declared with **`@computed_attribute` / `@computed_dict` getters** (from the `efootprint.abstract_modeling_classes.reactive_core` package); `calculated_attributes` derives from the class registry, inheriting through the MRO. A subclass drops an inapplicable inherited attribute by declaring `attr = removed_computed_attribute()`. A getter must return a **fresh value** — deriving from another attribute directly requires `.copy()` (returning an attached value aliases the same object into two slots and the engine raises).
- **Slot flags:** `serialize=True` (on `@computed_attribute` / `@computed_dict` / `@computed_structure`) marks the slot's cached value for persistence under the minimal serialization contract — extend that set deliberately, it is the file-weight budget. `guard=True` marks a slot whose getter can intentionally reject an invalid state; a guard may also feed the footprint totals. Guard slots eagerly recompute whenever an update invalidates them, and every guard slot of an object newly linked into the model is computed at update time (a never-computed slot has no edges for the wave to reach), so bad edits and bad new links keep failing at update time. A computed getter containing an intentional direct `raise` or `assert` must therefore declare `guard=True`; the AST contract test enforces this syntactic boundary while ordinary transitive programming errors remain outside static detection. `purposes={ComputationPurpose.FOOTPRINT}` belongs only on meaningful footprint output roots (`total_footprint`, physical-object `energy_footprint` and `instances_fabrication_footprint`), never on every intermediate: runtime membership is derived by walking the materialized dependency graph upstream from those roots.
- **Choose computed decorators by caching shape, not domain:** use `@computed_attribute` for one fresh attached explainable, `@computed_dict(keys="…")` for one independently computable fresh explainable per member of a declared collection, and `@computed_structure` for one arbitrary raw/composite/nested result cached and invalidated as a unit. A dict result with coupled normalization, shared all-key setup, or dynamic composite keys is a computed structure, not a computed dict. Never use `functools.cached_property` on a `ModelingObject`. A structure getter that reduces explainables to plain scalars (e.g. matrix rows) must call `record_calculus_edges_from_ancestry` on each explainable before reducing, or the input dependencies carried only by arithmetic ancestry are lost.
- **When a total and a per-source breakdown depend on the same formula, compute the per-source dict first and make the total a simple sum.**
- Computed dicts declare their key set by attribute name — `@computed_dict(keys="usage_patterns")` — and the getter takes exactly one member of that collection as input. Each returned value must be labeled.
- A computed-dict key may instead be a frozen derived coordinate value when one cached calculation is naturally keyed by several modeled objects. Its equality, hash, and `id` must derive only from stable `ModelingObject` identities; recreate coordinates deterministically from structural relationships, and never make them serialized relationships. Keep dimensions out of the coordinate when they are applied after a reusable base calculation—for example, `JobOccurrenceCoordinate` excludes `EdgeFunction`, so all edge functions reaching one `(EdgeUsagePattern, RecurrentServerNeed)` reuse one slot before applying their multiplicity.
- Prefer **phase-specific logic that makes the allocated impact explicit** over generic helpers with a `phase` switch when the underlying formula differs materially between fabrication and usage.
- If a structure or parent-level impact is evenly shared across children, **keep that logic at the parent object level** unless there is a strong ownership reason to move it. Do not pollute child attributes with parent-specific policy if a parent cached attribute can express it cleanly.
- **Attribution semantics belong on the attribution layer, not renderers.** Sources own their `attribution_atoms(phase)` builders; skipping a Sankey column = leaving its classes out of the fold's visible levels, excluding a source class = filtering its atoms out of the fold (never rescale). Renderers (e.g. `ImpactRepartitionSankey`) consume the kg-float `node_totals_and_links_in_kg` fold for layout and presentation only; they never re-implement attribution or wrap matrix scalars in Pint quantities. The general `node_totals_and_links` surface remains quantity-valued for programmatic callers.

## Class-level metadata inheritance

- **Declare helper-text metadata at the class that introduces the param or concept.** `param_descriptions` entries belong on the class whose `__init__` introduces the param (e.g. `data_transferred` on `JobBase`, `server_type` on `ServerBase`). Subclasses spread the parent dict and override only the keys whose wording diverges: `param_descriptions = {**Parent.param_descriptions, "key_to_override": "..."}` — later keys win, so the spread comes first. Every concrete class must still declare its own `param_descriptions` block (this is enforced by `tests/test_descriptions.py`); when a child adds nothing, write `param_descriptions = {**Parent.param_descriptions}` rather than relying on MRO. **Structural outliers** (subclasses whose `__init__` exposes a strict subset of the parent's params, e.g. `GPUServer`, `BoaviztaCloudServer`, `VideoStreaming`, `EdgeAppliance`) cannot spread the parent dict cleanly because the test rejects "extra" keys not in `__init__`; for these, either spread + filter (`{**{k: v for k, v in Parent.param_descriptions.items() if k != "unwanted"}, ...}`) or cherry-pick individual keys (`"key": Parent.param_descriptions["key"]`). Pick whichever form is shorter for the case at hand. String fields like `pitfalls`, `interactions`, `disambiguation` inherit naturally; don't redeclare at a child unless the child genuinely adds content. `default_values` stays per concrete class.

## Context gathering

- **Don't overread the optimization layer.** Most modeling work doesn't require deep knowledge of `efootprint/abstract_modeling_classes/`. Avoid gathering context from there unless absolutely necessary — prefer asking questions directly.
- **Focus on the immediate context.** You don't necessarily need to understand all upstream and downstream dependencies of a given object to work on it. Focus on the object you are working on unless a broader focus is asked.
- **Ask before guessing.** When in doubt about how to implement a new feature, ask for guidance before starting implementation.

## Editing patterns

- **Use programmatic tools for systematic textual work across many files.** For renames, global substitutions, or dropping a pattern everywhere, batch the change with `sed -i ''` or `grep -l … | xargs sed -i ''` rather than a serial Read+Edit loop per file. Per-file Edit is for heterogeneous changes (each file needs a different edit) or when you need to inspect surrounding context before replacing. Verify with `grep` after the bulk replacement that no stale references remain.

## Documentation upkeep

- If you notice that the AGENTS.md or specs/ files are missing important information that would allow for less context gathering in developments, propose improvements so that fewer tokens are used in the future with same or better performance.
- Whenever you implement or change a non-trivial pattern (new relationship type, new infrastructure convention, new calculated-attribute pattern, serialization change), proactively check whether the owning page under `architecture/`, `conventions.md`, or `testing.md` should be updated and propose the changes. The goal is to keep specs accurate so that future agents don't have to rediscover patterns from code.

## Test conventions

See `testing.md` for the full testing guide. Highlights:

- Use `create_mod_obj_mock` from `tests/utils.py` instead of raw `MagicMock(spec=...)`.
- Keep modeling tests focused on the exact code path under test. Avoid populating calculated attributes or fixture state that is no longer consumed.
- Prefer `MPLBACKEND=Agg poetry run pytest ...` when running tests that exercise plotting code.
