# Implementer brief

Write `briefs/task-<n>.md` beside `tasks.md`, committed with it. Verify against current code; anchors use symbols because earlier tasks can move line numbers.

```markdown
# Task N — title
Written YYYY-MM-DD against repository/commit(s): ...
Plan: linked sections. Task: linked entry.

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

Keep to about one or two screens. A brief is a map, not a second plan; proposed design changes go back to the main agent for the plan-amendment list.
