---
name: feature-archive
description: Stage 5 of the spec-driven workflow — archive a shipped feature. Run this only once every task in the feature's tasks.md has shipped AND you are satisfied the work is done (typically after merge). It promotes any durable insight into the live reference specs, then deletes the spec folder. It never writes an archive summary file. Invoke explicitly; it is not auto-chained from feature-implement.
---

# feature-archive

You are archiving a **shipped** feature — the final stage of the spec-driven workflow (`specs/workflow.md` §5). The goal is simple: make sure every long-lived fact lives in the **reference docs**, then **delete the spec folder**. Git history preserves the original spec / plan / tasks.

**There is no archive summary file. Never create one.** A per-feature summary only duplicates the code or the live reference specs and nobody reads it. If you find yourself wanting to write `archives/features/<name>.md`, stop — that is exactly the mistake this skill exists to prevent.

## Preconditions

1. **Confirm the feature and that it has shipped.** Read `specs/features/<feature-name>/tasks.md`; every task must be marked done. If any task is unshipped, stop and surface it — do not archive a half-done feature.
2. **Confirm the user wants to archive now.** Archiving deletes the spec folder, so it is normally done once the work has merged / you are satisfied it is final. If that is unclear, ask before deleting.

## Process

1. **Promote durable insight into the live reference docs — and verify they reflect reality.** Walk the feature's spec / plan / tasks and the shipped diff, and ask: is there any decision, convention, constraint, or pattern that a future contributor or agent would need to make a sound call? If so, it belongs in the live reference specs (`architecture.md` / `conventions.md` / `testing.md`), **not** in an archive. Most of this should already have happened during implementation — this is the final check. Add the missing one-line mentions in the right sections. If nothing durable is left to promote (common for docs-only features, where the published docs are themselves the reference), say so explicitly.

2. **Delete `specs/features/<feature-name>/`.** Use `git rm -r` for tracked files, **and** remove any untracked `spec.html` / `plan.html` left behind (a tracked-files-only delete leaves those on disk — check with `git status` and `rm` them). Git history preserves everything.

3. **Update `CHANGELOG.md`** if the feature is not already recorded there.

4. **Commit** with a `[REMOVE]` prefix, body `<feature-name>: archive shipped feature spec`. Bundle the promotion edits, the deletion, and any CHANGELOG change into this commit (or a small number of related commits if the promotion edits are substantial).

For cross-repo features, archive in the **driving repo** (same rule as the feature folder).

## Constraints

- **Never** write `archives/features/*.md` or any per-feature summary file.
- Do not delete the spec folder until step 1's promotion check is done — otherwise durable insight is lost to a buried git history.
- If the promotion check reveals the reference docs are now wrong or stale, fix them; keeping the reference specs accurate is the whole point of this stage.
