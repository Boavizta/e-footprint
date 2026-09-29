# Task handoff

Write `specs/features/<feature>/handoffs/task-<n>.md` in the driving repo. Commit it with the working set so it survives changing machines. Use the implementation commit's SHA in a subsequent documentation commit; never require a file to contain the SHA of its own commit.

```markdown
# Task N — title
Repositories and implementation commits: ...
Validation: command, outcome, tested revision; unavailable checks and why.

## Change map
- repository/path · symbol — what changed and which callers matter.

## Decisions and invariants
- Why the diff has this shape; authoritative owner; approved scope deviations.

## Tests
- Behavior proved, meaningful exclusions, remaining validation.

## Doubts
- Unverified assumptions, shortcuts, suspect adjacent behavior, or what was checked to conclude none.

## Documentation
- Owning pages updated, or why none needed.

## For the global review
- Filled by the reviewer: new helpers/contracts, deferred findings, possible duplication or cross-task overlap.
```

Pointers and facts suffice. Avoid advocacy, command transcripts, and repeating the plan. In cross-repo work name both baselines/ranges; review must not guess from `HEAD` after documentation commits.
