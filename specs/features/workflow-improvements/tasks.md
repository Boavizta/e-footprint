# Workflow improvements — shadow-review experiment

**Status: ACTIVE** · Authorized 2026-09-30.

Observe the next five distinct features to decide whether GPT-6.1 Sol/high can take over
ordinary per-task reviews from GPT-6 Astra/high. This is a bounded workflow investigation;
the observation itself needs no product implementation or additional SDD stages.

## Task 1 — Observe five features

**Status: In progress.** Enrollment, progress and evidence live in
[`shadow-review.md`](shadow-review.md). Its feature rows are the single source of the count.

### Enrollment and stopping

- Enroll the next five distinct features reaching their first eligible task review after
  activation, across either repository. Existing prepared or partly implemented features are
  eligible; observe future reviews only. Standalone tasks, bug batches and this tracking
  feature do not consume slots.
- Identify a feature by its driving repository and feature slug. A cross-repository feature
  has one slot. Every later run of that feature reuses its slot; retries never add a slot.
- Before the first paired review, the supervisor reads the current feature table and adds an
  `OBSERVING` row if there is a free slot and both requested models are available. Record its
  session ID as the row's current writer. Coordinate overlapping supervisors before changing
  the shared record; re-read it before each edit and preserve other features' rows.
- Five enrolled rows close enrollment, even while some features are still in progress.
  Continue observing those features across their runs. Close a row as `COMPLETE` when all
  its approved implementation runs finish, or `PARTIAL` when remaining work is explicitly
  parked or cancelled. A partial feature keeps its slot and records the coverage gap.
  Further work on a closed feature does not reopen its observation slot.
- When all five rows are closed, set this protocol to `DECISION_READY`, complete Task 1 and
  perform Task 2. Spawn no further shadows under this experiment. Do not replace a partial
  sample, enroll a sixth feature or extend the experiment without the user's instruction.

### Paired task reviews

1. Compare the primary `reviewer` on **gpt-6-astra / high** with `reviewer-shadow` on
   **gpt-6.1-sol / high** for every initial per-task review of an enrolled feature. Keep the
   global reviewer on Astra; do not shadow fixes, resumed reviews or global review.
2. Give both reviewers the same task intent, brief, handoff and immutable implementation
   ranges in each affected repository. Start independent contexts without the other's
   findings. In runtimes with explicit spawn settings, pass both model and effort and use
   a context mode that permits those overrides. Record the actual settings and session IDs.
3. Both initial passes are read-only: no fixes, commits, stateful suites or shared-cache
   writes. Keep the reviewed code unchanged until both passes return. They may run in
   parallel when available concurrency permits; otherwise run independently in sequence.
4. Capture both initial results before resuming Astra with the combined, evidence-backed
   corrections. The supervisor assesses findings on their merits; Astra's output is not
   ground truth. A real Sol-only defect is corrected through the ordinary reviewer too.
   The implementer/reviewer still own all required checks after corrections.
5. If a shadow fails or cannot use the requested settings, continue normal review and mark
   that pair incomplete. Do not substitute a different model, repeatedly retry for the
   experiment, or turn missing evidence into a clean result.

### Evidence and review load

- A consequential finding changes correctness, a supported contract or invariant, material
  maintainability, or an architectural decision. Count supported consequential findings
  caught by both, missed by Sol, and missed by Astra. Distinguish severity and task risk.
  Count each underlying issue once even when phrased or split differently. Cosmetic
  suggestions and routine fixes are not consequential misses.
- Keep noise as an aggregate count of unsupported, duplicate or non-actionable suggestions
  per reviewer. Explain only a pattern that affects the eventual recommendation. Do not
  preserve routine-fix inventories, successful test results, raw review transcripts or a
  second judgement log. Link consequential implementation choices to their existing
  `IMPL-DECISION` callouts rather than duplicating the rationale.
- Record each pair's run/task, commit ranges, reviewer IDs, actual model/effort and tier.
  Use the existing usage collector and session bindings for input/cache-read/cache-write/
  output tokens, active review time, API-equivalent cost and Codex credits. Compare only
  each fresh reviewer's initial turn (`turn = 0`), excluding Astra's subsequent fix work.
  Keep the price-card date and missing coverage explicit; unavailable values are `unknown`.
- Attribute shadows to the observed feature/run/task with role `reviewer-shadow`. Keep their
  cost visible as experiment overhead, separate from the normal workflow cost. Do not
  compare a whole-run `reviewer` total, which includes global review and fixes, to shadows.
- At each run's close-out, update that feature's row and compact supporting evidence. Add
  later consequential global-review findings or regressions affecting the comparison when
  observed. Routine progress needs no separate user report.

### Shared record

These two files live only in the main library checkout. Both repositories point here through
`.agents/repository.md`; they are deliberately outside the shared-tooling sync manifest.
From a worktree, use `git worktree list` in the library repository to locate its main checkout
and update that record, not a worktree copy. Commit only these owned experiment files there,
preserving other sessions' changes. If the shared record is unavailable, continue the feature
without shadowing and surface that coverage gap; do not start an independent counter.

## Task 2 — Recommend a review policy

**Status: Pending Task 1.** The supervisor closing the fifth feature writes the recommendation
in [`shadow-review.md`](shadow-review.md#recommendation) and presents it once to the user.

Compare findings by severity and risk surface, plus paired initial-review time, token and cost
ratios. Show per-feature results so a large feature does not silently outweigh the others.
Use the same price-card date and complete pairs for cost comparisons; disclose missing pairs
and unrepresented task types. Both reviewers can miss the same defect.

Recommend one of:

- **Sol for ordinary per-task reviews** when the observed quality is sufficient and the
  savings are substantial, without an unacceptable pattern of consequential misses or noise.
- **Split by task risk** when evidence supports Sol for ordinary work and Astra for specific
  surfaces. Define the routing rule from observed misses, not model reputation.
- **Retain Astra** when consequential misses, noise or insufficient coverage leave the switch
  unsupported. Sparse evidence is not a reason to extend the experiment automatically.

Global review remains on Astra in all three options. The user decides the lasting policy.
After that decision, apply the agreed role/routing changes, synchronize the shared tooling,
remove the active-experiment pointers, and mark this protocol `CLOSED`. Archive only when asked.
