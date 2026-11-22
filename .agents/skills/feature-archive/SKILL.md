---
name: feature-archive
description: Stage 5 of the spec-driven workflow — archive a shipped feature. Run this only once every lot of the feature's delivery is built and reviewed and the user is satisfied the work is final. It runs the archive gate, promotes any durable insight into the live reference docs, parks what is unfinished, takes the tags off the test titles, then deletes the feature folder. It never writes an archive summary file. Invoke explicitly; it is not chained from feature-implement.
---

# feature-archive

You are archiving a **shipped** feature. Every long-lived fact goes to the **reference docs**,
then the feature folder is **deleted**. Git history keeps the spec, the plan and the approval.

**There is no archive summary file. Never create one.** A per-feature summary duplicates the
code or the reference docs, and nobody reads it.

Read `.agents/repository.md` § "Archive": where this project promotes, parks and records, and
what it retires with a feature. `map …` is the map's command (`code-map` skill).

## Preconditions

1. **The archive gate passes** (`repository.md` § "Commands"): no `planned` call, `@planned`
   comment or planned test of the feature is left, no journey case is left to write, and every
   rule of its spec is owned by one written test or by a confirmed waiver. A failing gate is
   unfinished work: say what it lists and stop.
2. **Nothing waits for the reviewer.** `map check <feature>` shows no unit that differs from the
   approval and no `To confirm:`. The gates file's checklist is cleared, or each open item is
   parked in step 2 below. Deleting the folder would delete the question with it.
3. **The user wants to archive now.** Archiving deletes the folder; if that is unclear, ask.

A feature of the earlier form (`tasks.md`, a `plan.html`) is archived when every task is done and
no `IMPL-DECISION` or `PLAN-UPDATE` callout is still `TO CONFIRM` or `PROPOSED`. The gate of
precondition 1 does not apply to it.

## Process

1. **Promote durable insight, and check the reference docs say what is true.** Walk the spec,
   the plan (its reasons, its decisions across pieces, its notes and waivers), the gates file and
   the shipped diff. Any decision, convention, constraint or pattern a later contributor needs to
   make a sound call belongs in the reference docs, in the section that owns it. Most of it was
   written during implementation; this is the last check. A waiver that states a rule the code's
   shape holds is worth a line where that shape is described. If nothing is left to promote, say
   so.

2. **Park unfinished work where it will be picked up.** A deferred contraction, a gate still
   open, a second stage held for a reading, a follow-up refactor: each goes where the repository
   parks such things, carrying the analysis already done and its decision criteria, so it can be
   acted on without the folder you are deleting. Work that needs a run of its own gets a new
   feature folder. Name the archive commit so the original can be recovered, and check that the
   command resolves.

3. **Sync the roadmap and the design record** as `repository.md` § "Archive" says. A roadmap that
   still lists shipped work as next is the drift this stage exists to prevent.

4. **Retire what the project retires with a feature** (`repository.md` § "Archive"): promote
   first, then delete. Never retire a migration or an upgrade test merely because its feature is
   archived, when the repository does not say so.

5. **Take the tags off the test titles.** Each written test titled `<feature>#<slug>: <title>
   [<rule>]` becomes `<title>`. The tag tied the test to its piece while the feature was in
   flight; a title that keeps it would be read as another feature's. Run the tests of the files
   you retitled.

6. **Delete `specs/features/<feature>/`**: remove the tracked files with git, then whatever is
   left on disk, since ignored files (`plan-feedback.json`, generated pages) show in no status.

7. **Commit** with the repository's removal prefix, `<feature>: archive shipped feature spec`.
   The promotions, the parking, the retitling and the deletion go in this commit, or in a few
   related ones when the promotions are substantial.

For a feature that spans repositories, archive in the repository that held its folder.

## Constraints

- Never write a per-feature summary file.
- Do not delete the folder before the promotion, the parking and the retirements are done.
- If the reference docs turn out wrong or stale, fix them: keeping them accurate is the point of
  this stage.
