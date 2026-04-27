# Constitution — e-footprint

These are the project's immutable rules. They must be respected by every code change, by every author (human or agent), and they are amended only deliberately, not by drift. If a proposed change requires breaking a rule here, raise it explicitly and update the constitution before the change ships.

---

## 1. Engineering principles

1. **Three-layer separation.** Modeling logic (`efootprint/core/`) is independent of the optimization layer (`efootprint/abstract_modeling_classes/`) which is independent of the API/serialization layer (`efootprint/api_utils/`). New code respects this direction.
2. **No backward compatibility burden.** There are no other external callers besides e-footprint-interface, which is co-developed. Don't carry shims, deprecation cycles, or compatibility branches.
3. **Leanness over cleverness.** Three similar lines beat a premature abstraction. Avoid speculative generality, defensive code for impossible states, and refactor-on-the-side during bug fixes.
4. **Doc-as-code is the SSOT for object semantics.** Class docstrings, `param_descriptions` dicts, and `update_<attr>` method docstrings are the authoritative description of what an object/param/calculated-attribute means. The mkdocs reference and the interface both read from them; do not duplicate descriptions elsewhere.

## 2. Quality gates (a change is not ready until)

1. Full pytest suite passes locally.
2. `mkdocs build --strict` is clean (once CI is wired).
3. JSON serialization round-trip is preserved for any modified `ModelingObject`.
4. If JSON schema changes, a migration handler is added in `efootprint/api_utils/version_upgrade_handlers.py` and the schema version bumps.
5. New `ModelingObject` classes are registered in `efootprint/all_classes_in_order.py` (both `ALL_EFOOTPRINT_CLASSES` and, for top-level core objects, `CANONICAL_COMPUTATION_ORDER`).
6. `CHANGELOG.md` entry added.

## 3. Agent-facing rules

1. **Never paper over a bug.** If you discover unrelated bad behaviour while working on a task, fix it on the spot or surface it explicitly. Never silently work around it in tests or production code.
2. **Never skip hooks (`--no-verify`)** unless explicitly authorized.
3. **Ask before destructive operations** (force pushes, branch deletions, hard resets that touch unsaved work).
4. **Don't mock the optimization layer in modeling tests.** Use `create_mod_obj_mock` from `tests/utils.py`. Use real `ExplainableObject` / `ExplainableQuantity` instances when possible.
5. **Never use mutable objects as default parameter values** (e.g. `SourceValue(...)`) in function/method signatures. Use `None` and create the mutable inside the body.
6. **Don't use forward references in `ModelingObject.__init__` signatures.**

## 4. Out of scope (rejected by default)

- Python < 3.12.
- Internationalization of error messages or descriptions.
- Alternative serialization formats beyond JSON.
- Replacing core dependencies (Pint, NumPy, Pandas) without an explicit principle change.
- Backward-compatibility shims for any consumer other than e-footprint-interface.

## 5. Amending the constitution

A change to this file requires:

1. A short justification ("why now") proposed alongside.
2. An explicit acknowledgment of which downstream artifacts (`architecture.md`, `conventions.md`, mkdocs pages, CI tests) need to follow.

Use the `update-constitution` skill, or just edit deliberately with a separate commit — never blend constitutional changes into a feature commit.
