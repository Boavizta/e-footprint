---
name: task-implement
description: Implement one approved task using its plan or bug diagnostic, verified brief, repository gates, and a durable review handoff.
---

# task-implement

Implement only the selected task. Read `.agents/repository.md`, the constitution, conventions, and relevant architecture pages from `specs/architecture/index.html`. For cross-repo work read both repositories' guidance.

1. Resolve the driving repo, task and run. Read `tasks.md`, its brief when present, and the relevant approved spec/plan or linked bug diagnostic. Verify pointers against the current code; earlier tasks may have changed them.
2. Record each affected repository's baseline and pre-existing changes. Respect parallel ownership. Implement the agreed behavior in its authoritative layer. Additional files necessary for the same behavior are a reported scope deviation, not permission for unrelated refactors. A product/contract change goes back to the reviewed plan.
3. Run applicable constitution gates. Use focused checks while iterating, then required full checks before calling the task done; review tiers never waive them. Diagnose clear in-scope failures and fix their supported cause. Do not hide failures with skips, fabricated state, fallbacks, or repeated unexplained retries.
4. Update owning documentation when this change makes it stale. Add the standalone changelog entry, unless a `feature-implement` supervisor owns the consolidated feature entry.
5. Mark done only when applicable gates pass; otherwise record implemented/pending-validation or blocked status accurately. Commit only named owned files, using `[ADD]`/`[FIX]`/`[REFACTO]`/`[UPDATE]`/... and `task N: <summary>` under a feature supervisor, or `<feature>: <task title>` standalone.
6. Write and commit the [handoff](references/handoff.md), including actual implementation commit(s), tested revisions, doubts and deviations. Keep feature/task references out of product and test comments: explain code in durable terms instead.
7. Return outcome, commits, validation, handoff path and outstanding work. Standalone execution does not chain to another task or archive the feature.

Under `feature-implement`, surface blockers to the supervisor. Standalone, surface load-bearing product/contract, missing-authority or unexplained validation blockers to the user. Never reset, stash, or discard pre-existing work to make a tree look clean.

Role setup and usage attribution: `specs/agent-tooling.md`.
