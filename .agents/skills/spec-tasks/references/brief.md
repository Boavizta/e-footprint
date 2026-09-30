# Implementer brief

Write `briefs/task-<n>.md` beside `tasks.md`, committed with it. Verify against current code; anchors use symbols because earlier tasks can move line numbers.

```markdown
# Task N — title
Written YYYY-MM-DD against repository/commit(s): ...
Plan: linked sections. Task: linked entry.
Status: under review / provisional — pending linked PLAN-UPDATE proposal(s).

## Start here
- symbol — repository/path — why.

## Change along the code path
Entry point, changed calls/data, and returned or visible result. Link plan snippets.

## Earlier tasks
What preceding tasks will introduce or move; what this task then reuses.

## Reuse
Existing helpers, fixtures, contracts; do not create parallel mechanisms.

## Invariants and traps
Authoritative owner, relevant standards, supported failure modes.

## Validation
Tests to extend, assertions that matter, exact commands and environment requirements.

## Out of scope
Related work that belongs elsewhere.

## Unverified
Hypotheses and how to settle them, or none.
```

Keep to about one or two screens. Write briefs in task dependency order and check assumptions
against preceding tasks' planned outputs. A brief is a map, not a second plan; record any proposed
design change once as a tagged callout in `plan.html`, then continue preparing the full working set.
Link any pending proposals the brief depends on and keep it provisional until they are resolved;
do not present a proposed design as approved implementation instructions.
