# Comparison file — gates (for the user, after the run)

## Standing calls

- Gate sorting: the lot `comparison-file` holds no validation, no evidence gate and no post-run
  operation. Both functions are library entry points tested end to end by the suite. Publishing
  them (a version bump, a PyPI release) is the usual release, outside this run.
- The supervisor ran on Opus 5.5, not on the model `implementer-hard` pins.
- Deferred to the archive (`feature-archive`): one sentence in
  `specs/architecture/persistence.html`, after "json_to_system.py and system_to_json.py own the
  serialization round-trip", giving the comparison file's shape (`{"models": [<system_to_json
  document>, …]}`, the first the reference, written and read by the interface too). Today that
  shape is stated only in two docstrings and the CHANGELOG.
- Deferred to the interface: no library change is needed for the seam (both formats load each
  other's files, and the two collision policies do not conflict). The interface caps a file at
  `MAX_SLOTS = 2`, so it refuses a library file of three systems or more with its own message.
  Its `start-from-ai-agent` README already lists "A file written by the library opens here as a
  comparison". It could note the cap there, in the interface's own run.
- `specs/roadmap.md`: the entry said the interface's plan of this feature was being written in its
  worktree. No such plan exists, and the interface's `start-from-ai-agent` README calls the
  feature library-only, so the entry now says library-only.

## Checklist

None.

## Post-run operations

None.

## Evidence

None.

## Watch in normal use

None.

## Parked

None.

## Leads for the global review

Lot `comparison-file` (commits 5e437fd1..bb7aeb1c), from its reviewer:

- Added: `systems_to_json` (refuses a shared System id, with a `narrate` step) and
  `json_to_systems`; three tests, one CHANGELOG entry.
- `next(iter(class_obj_dict["System"].values()))` now stands at five production sites
  (core/system.py, modeling_examples/__init__.py ×2, comparison/duplication.py,
  api_utils/json_to_system.py) and in the test helper `loaded_system`: a candidate helper
  "load a document, return its System".
- A seam with the interface's plan: the interface caps a file at `MAX_SLOTS = 2` and gives a
  colliding System a fresh id on load, whereas the library takes any count and refuses a
  collision at export. The interface's plan should say which holds. Its import path works on
  dicts, so it will likely not call `json_to_systems`.
- Deferred: `systems_to_json([])` writes `{"models": []}`, left as is (the plan counts nothing).

## End-of-run gate

Green on cd4fe5e2: `MPLBACKEND=Agg poetry run pytest` 1784 passed, 1 skipped (not a test of this
feature); `npx tsx comprehension_harness/render.ts --check` passes; `npm run map -- check
comparison-file` passes. The published documentation is unchanged, so `mkdocs build --strict` was
not run.

## Spend

```
Usage snapshot: 109 requests · USD API-equivalent (tokens only) · rates 2026-09-30
Measured total: 10.2386; unpriced: 0; unattributed: 0
Known tokens: input 570; cached 10,735,944; write 565,796; output 110,498
Coverage: 0 source errors; 0 registered intervals missing measurements. Standard mode assumed for 0 requests.
  gate: 0.0076 (follow-up 0.0000); 3 requests; claude-haiku-5-5; effort medium
  global-review: 2.3717 (follow-up 0.4483); 13 requests; claude-fable-5-1; effort high
  implementer: 0.0480 (follow-up 0.0082); 31 requests; claude-haiku-5-5; effort high
  main: 6.4468 (follow-up 0.0000); 31 requests; claude-fable-5-2; effort high
  reviewer: 1.3645 (follow-up 0.4115); 31 requests; claude-opus-5-5; effort high
Unassigned-to-task overhead: 10.2386. No inference about completed-task quality or subscription limits.
```

The report covers the feature as a whole, so the "main" line takes in the earlier stages' sessions
too. Most of this run went to the two reviews; the implementation itself was cheap.
