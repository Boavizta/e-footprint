# Task handoff

Write `specs/features/<feature>/handoffs/task-<n>.md` in the driving repo for agent coordination.
Commit it with the working set. Use the implementation commit's SHA in a subsequent documentation
commit; never require a file to contain the SHA of its own commit. The implementation ranges are
required; include the following sections only when they carry material information.

```markdown
# Task N — title
Repositories and implementation ranges: ...

## Review pointers
- A non-obvious entry point or cross-task interaction worth inspecting.

## Design decisions
- Links to relevant IMPL-DECISION callouts in the plan; rationale lives there.

## Open concerns
- A material unresolved assumption, failed/unavailable required check, or cross-task concern.
  Give only the evidence and location needed to resolve it; link to its task blocker when present.
```

Do not record routine fixes, successful test results, command transcripts, or empty sections and
"nothing to report" explanations. Remove resolved routine concerns. Required checks still run;
unresolved failures and unavailable required checks must remain visible. In cross-repo work name
both baselines/ranges; review must not guess from `HEAD` after documentation commits.
