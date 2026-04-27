# Constitution — e-footprint

These are the project's immutable rules. They must be respected by every code change, by every author (human or agent), and they are amended only deliberately, not by drift. If a proposed change requires breaking a rule here, raise it explicitly and update the constitution before the change ships.

---

## 1. Engineering principles

1. **Three-layer separation.** `efootprint/abstract_modeling_classes/` is the framework layer (ModelingObject, ExplainableObject, dependency graph). `efootprint/core/` builds on it with the modeling primitives. `efootprint/api_utils/` builds on both for serialization. The dependency direction is strictly upward: `core/` must not import from `api_utils/`, and `abstract_modeling_classes/` must not import from `core/` or `api_utils/` (one pre-existing back-edge from `abstract_modeling_classes/modeling_object.py` to `core/` is documented in `architecture.md` and must not be extended).
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

Other coding-style and testing rules live in `conventions.md` and `testing.md`.

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
