---
name: task-review
description: Review a task's explicit commit range for correctness, complexity, invariant ownership and test quality. Choose LIGHT, STANDARD or FULL from the diff; report before editing.
---

# task-review

Review first; edit only after an explicit follow-up fix brief. Read `.agents/repository.md` for local risk surfaces and standards.

1. Identify the task and exact implementation range from the supervisor or handoff metadata. For standalone last-commit review use `git show HEAD` only when it is the requested implementation commit. Handoff and bookkeeping commits may follow it. Cross-repo tasks have one range per repo.
2. Read the actual diffs before the implementer's narrative. Inspect source size separately from tests/docs, while still reviewing the tests and docs.
3. Choose the highest applicable tier:

| Tier | Trigger | Depth |
|---|---|---|
| FULL | Repository-specific high-risk surface; changed invariant enforcement; `Risk: high`; missing handoff; exceptionally broad change (roughly >1,000 source lines or >25 source files) | Trace affected invariants, callers, consumers and cross-repo contracts; load relevant spec/plan and standards fully. |
| LIGHT | All: at most about 120 source lines and 5 source files; contained copy/style/docs/test change; no new public contract, dependency, persistence or state transition | Diff, task and handoff; follow an evidence-backed concern farther when needed. |
| STANDARD | Other changes | Relevant plan/spec sections, standards and adjacent code mapped by the handoff. |

You may raise the tier with a reason, never lower it below a triggered rule. Tier controls exploration, not validation requirements. No fixed quota of findings.

4. Read the handoff as a map and verify claims you rely on. Investigate doubts. For normal features consult the approved spec/plan; for bug batches the linked diagnostic supplies intent.
5. Apply the checklist at the chosen depth:


   - **Complexity** — recursive traversal, multi-layer indirection, or private helpers that could be a flat loop or direct inline logic.
   - **Dead defensive code** — code guarding hypothetical cases not grounded in real data or an enforced invariant.
   - **Defensive-code provenance** — for every new guard, fallback, reconciliation hook, duplicated validation, or hardening, identify the concrete producer of the guarded state, a supported application path that reaches it, and the layer that owns the invariant. A test that directly assigns an impossible internal state is not production evidence. If no supported path exists, flag the code for removal; if another component creates the state, flag a downstream workaround in favour of fixing that component.
   - **Missed invariant** — a constraint that is assumed downstream but not asserted at the earliest possible layer.
   - **Test quality** — piecemeal property assertions instead of full expected-state assertions; tests covering scenarios that can't actually happen; tests that manufacture internal state to justify production integration code instead of exercising the real producer and supported entry point. Direct state manipulation may test a low-level helper, but cannot by itself justify a global hook or boundary defence.
   - **Scope delta** — inspect every hunk not required by the task. A boy-scout change needs a concrete defect or maintainability problem, an evidenced reproduction when behavioural, and a fix in the owning layer.
   - **Cross-path consistency** — when parsing, validation, rendering, or error-handling responsibility moves, inspect sibling creation, editing, preview, import/export, and relevant unit/integration/E2E paths for stale copies or expectations.
   - **Integration coverage of new public-API consumption** — if the diff calls a public method/property/dict-attr on a `ModelingObject` subclass that no existing test path was reaching, flag whether the relevant integration fixture has an assertion that touches the new call site. `run_test_materialize_all_cached_properties` already covers new `cached_property` definitions; this rule catches the rest (plain `@property`, methods, dict lookups, new behavioural shapes on existing APIs).
   - **Convention violation** — anything contradicting `constitution.md` or `conventions.md`.
   - **Code quality / boy scout** — concrete problems in touched or adjacent code worth improving regardless of the task: poor naming, un-Pythonic patterns, structural awkwardness, or circumvolutions forced by the existing code shape. Surface observed defects and smells even if the task itself is clean; do not propose protection against hypothetical callers or unreachable states.


6. Return `Tier: ... — triggering rule`, then numbered findings: category, repository/path:line, supported failure/consequence, recommended resolution, and `EVIDENT-FIX` or `STRUCTURING-DECISION` with a reason. Include real alternatives for material design choices. If clean, say so without inventing concerns.
7. Wait for decisions. If asked to apply fixes, use the same context, group related changes, run affected checks and the required gates, and write cross-task leads under the handoff's `For the global review`. Record the tested final revision. Never include another session's changes in a fix commit.

The global review is always FULL but focuses on cumulative seams, duplicated helpers, superseded early work, contract mismatches and documentation drift. Start with handoff leads and diff statistics; inspect the cumulative diff where warranted instead of repeating every task review.
