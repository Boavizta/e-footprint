# Conventions — e-footprint

These are the strong preferences and patterns the project follows. They are softer than the constitution: deviations are possible with justification, but defaulting to these preserves consistency.

## Code style

- **Python ≥ 3.12** (constitution §4).
- **Black** formatter, line length **120**. Keep the number of lines low; in particular, avoid creating a new line solely to close a parenthesis.
- **Poetry** for dependency management.
- **Type hints** are encouraged but not strictly enforced. Don't use forward references in `ModelingObject.__init__` signatures.
- **Mutable defaults are forbidden** in function signatures (e.g. `SourceValue(...)`). Use `None` and create the mutable inside the body.
- **Comments only when the WHY is non-obvious.** If a reader can derive intent from well-named identifiers, the comment is noise. Never comment what the code does — only why it does it that way.

## Modeling refactor preferences

These have accumulated as we refactored the impact-repartition logic. They are project-specific and worth keeping in mind when extending modeling objects.

- When a modeling object needs different attribution rules for fabrication and usage, prefer **explicit phase-specific calculated attributes and update methods** over compatibility bridges or legacy fallback machinery.
- In `ModelingObject` subclasses that override `calculated_attributes`, prefer `super().calculated_attributes` and append local attributes rather than duplicating base-class-managed names.
- If a subclass needs to drop inherited calculated attributes because it exposes them as properties instead, prefer **filtering them out of `super().calculated_attributes`** rather than rewriting the whole list manually.
- Prefer computing reusable per-pattern quantities once as calculated attributes, then aggregating from them. For example, if usage attribution depends on per-usage-pattern energy footprint, compute `*_per_usage_pattern` first and let totals sum that dict rather than recomputing the same formula in repartition methods.
- More generally: **when a total and a repartition both depend on the same per-source formula, compute the per-source dict first, reuse it for repartition, and make the total a simple sum.**
- For calculated attributes backed by an `ExplainableObjectDict`, follow the **`update_dict_element_in_<attribute>` plus `update_<attribute>` pattern** used elsewhere. The bulk updater should reset the dict then delegate element population, and each stored explainable value must be labeled before insertion. `update_dict_element_in_<attribute>` methods always take exactly one `ModelingObject` as input — don't try to pass other parameters.
- For fabrication repartition, **do not introduce per-pattern calculated attributes when a simple proportional activity weight is sufficient.** Fabrication and usage repartition weights do not need to be coherent with one another; they only need internal coherence within the same phase on the same object.
- **Repartition weights do not need local normalization.** Use direct proportional weights when possible and let final repartition normalization happen downstream.
- **Units of repartition weights do not need to match across phases.** They only need to remain Pint-coherent within a given phase/object weight set.
- When a costly aggregate is reused across several repartition calculations, **prefer introducing a dedicated calculated attribute on the natural owning object** rather than ad hoc helper caching. Example: component-level totals belong on `EdgeComponent`, not in a transient cache inside `EdgeDevice`.
- Prefer **phase-specific logic that makes the allocated impact explicit** over generic helpers with a `phase` switch when the underlying formula differs materially between fabrication and usage.
- If a structure or parent-level impact is evenly shared across children, **keep that logic at the parent object level** unless there is a strong ownership reason to move it. Do not pollute child attributes with parent-specific policy if a parent cached attribute can express it cleanly.
- If the exact same `ExplainableObjectDict` should serve both as a reusable computed quantity and as repartition weights, prefer **exposing the repartition weights as a property returning that dict** instead of copying the same explainable objects into another calculated attribute. This avoids explainability-graph conflicts from attributing one explainable object to multiple attributes on the same modeling object.
- If a lifecycle phase is intentionally unsupported for an object, prefer **making that explicit**. For example: return an empty repartition-weight dict while the corresponding footprint is empty, and raise `NotImplementedError` if a non-empty footprint is later introduced without implementing the matching repartition logic.

## Context gathering

- **Don't overread the optimization layer.** Most modeling work doesn't require deep knowledge of `efootprint/abstract_modeling_classes/`. Avoid gathering context from there unless absolutely necessary — prefer asking questions directly.
- **Focus on the immediate context.** You don't necessarily need to understand all upstream and downstream dependencies of a given object to work on it. Focus on the object you are working on unless a broader focus is asked.
- **Ask before guessing.** When in doubt about how to implement a new feature, ask for guidance before starting implementation.

## Documentation upkeep

- If you notice that the AGENTS.md or specs/ files are missing important information that would allow for less context gathering in developments, propose improvements so that fewer tokens are used in the future with same or better performance.
- Whenever you implement or change a non-trivial pattern (new relationship type, new infrastructure convention, new calculated-attribute pattern, serialization change), proactively check whether `architecture.md`, `conventions.md`, or `testing.md` should be updated and propose the changes. The goal is to keep specs accurate so that future agents don't have to rediscover patterns from code.

## Test conventions

See `testing.md` for the full testing guide. Highlights:

- Use `create_mod_obj_mock` from `tests/utils.py` instead of raw `MagicMock(spec=...)`.
- Keep modeling tests focused on the exact code path under test. Avoid populating calculated attributes or fixture state that is no longer consumed.
- Prefer `MPLBACKEND=Agg poetry run pytest ...` when running tests that exercise plotting code.
