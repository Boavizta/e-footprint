---
name: feature-archive
description: Stage 5 of the spec-driven workflow — archive a shipped feature. Run this only once every lot of the feature's delivery is built and reviewed and the user is satisfied the work is final. It runs the archive gate, promotes the few load-bearing decisions into the live reference docs, takes off the prose a narrative now tells, parks what is unfinished, strips the feature's marks off the code (its `built` calls, the tags of its test titles, its planned screens), then deletes the feature folder. It never writes an archive summary file. Invoke explicitly; it is not chained from feature-implement.
---

# feature-archive

You are archiving a **shipped** feature. Every long-lived fact goes to the **reference docs**,
then the feature folder is **deleted**. Git history keeps the spec, the plan and the approval.

**There is no archive summary file. Never create one.** A per-feature summary duplicates the
code or the reference docs, and nobody reads it.

Read `.agents/repository.md` § "Archive": where this project promotes, parks and records, and
what it retires with a feature. `map …` is the map's command (`code-map` skill).

## Preconditions

The gate, the check and the strip read the stories of the last test run: on a checkout that has
none, run the tests first (`repository.md` § "Commands"). The gate and the check also run every
plan's reproductions, those of another feature included, on whatever each needs: `repository.md`
§ "Archive" says where an archive may run.

1. **The archive gate passes** (`repository.md` § "Commands"): no `planned` call, `@planned`
   comment or planned test of the feature is left, no journey case is left to write, and every
   rule of its spec is owned by one written test or by a confirmed waiver. A failing gate is
   unfinished work: say what it lists and stop. What is built keeps its marks through the gate:
   the `built` calls, the tags of the written tests and the planned screens stand until step 6,
   since the plan page reads the delivery by them.
2. **Nothing waits for the reviewer.** `map check <feature>` shows no unit that differs from the
   approval and no `To confirm:`. Every item of the gates file that is the user's (a check on a
   device, an operation after the run) carries its verdict or is marked done, or is parked in
   step 3 below. An operation the file leaves open is open: ask the user, never infer that it
   was done. Deleting the folder would delete the question with it.
3. **The user wants to archive now.** Archiving deletes the folder; if that is unclear, ask.

A feature of the earlier form (`tasks.md`, a `plan.html`) is archived when every task is done and
no `IMPL-DECISION` or `PLAN-UPDATE` callout is still `TO CONFIRM` or `PROPOSED`. The gate of
precondition 1 does not apply to it.

## Process

1. **Promote what is load-bearing, and nothing else.** A fact of the plan goes with the folder
   unless it passes the test below: git history keeps it, and most decisions need no log. The
   candidates are few and they are listed: the sections of `plan.md` that are no piece (its
   decisions across pieces), its `Note:` paragraphs, its waivers, what the spec leaves out, what
   the gates file still says, and any other file of the folder that holds a decision or a lead.
   The reason of a piece is a candidate only where it says why an alternative was not taken. For
   each candidate, the first home that can hold it:

   1. **A test, or the code itself.** A rule a test owns, a shape a type refuses: nothing is
      written. A shape that a few lines in an existing test would hold, and that none holds, is
      a test to write here, or to park when it is more than that: prose is no substitute for it,
      and with the test in place at most one line stays at the place, saying why.
   2. **A narrative's sentence.** What happens, in order, is told by the steps: nothing is
      written, or the sentence is corrected.
   3. **The reason of one object**, where the repository keeps it (`repository.md` § "Archive"):
      beside the declaration, not in a page about the subsystem.
   4. **A reference doc**, in the section that owns it, only for what none of the three can
      hold: a decision that spans several flows, a constraint no step executes, an alternative
      that was rejected.

   Homes 1 and 2 need nothing written. What reaches 3 or 4 is written only when it is
   **load-bearing**, which takes both: someone reading
   the code cold would plausibly propose the opposite, because it looks simpler or more obvious;
   and nothing would stop them, no test going red and no type refusing. A change a test refuses
   is logged by that test. A choice nobody will be tempted to undo needs no log. A waiver is the
   usual case that passes: a rule only the code's shape holds is worth a line where that shape is
   described, and a comment that already says it there is that line. What is written says what
   holds now and why, in the present tense: never the story of the choice, a date or the
   feature's name. A comment written into the code is checked as an edit of a doc is.

   Give each candidate one line in your report: promoted, and where; held, and by which test or
   narrative; or dropped. That list is the review of this step, and it is written in no file.

2. **Take off the prose a narrative now tells.** For each narrative the feature landed in, a
   mechanism's included (the flows of its plan page, and the steps the check prints its built
   places inside), read the reference docs that describe that flow: no tool lists them, so
   search them for the narrative's functions and for links to its page. Prose that tells what
   the code does, step after step, goes, and a link to the narrative's page stands where it was
   (`repository.md` says where the pages are). So does a step named by its number: the numbers
   move. Prose about what no step tells stays: why the flow is shaped so, what it deliberately
   does not do, and what a screen shows the user, which is the design record's to say. A
   sentence the feature made false is corrected or goes. The commit that wrote or changed the
   narrative should have done this: here is the last check, and the reference docs are read
   against the narrative, never the other way.

3. **Park unfinished work where it will be picked up.** A deferred contraction, a gate still
   open, a second stage held for a reading, a follow-up refactor: each goes where the repository
   parks such things, carrying the analysis already done and its decision criteria, so it can be
   acted on without the folder you are deleting. The gates file is read line by line: each open
   operation, each thing to watch and each lead a review left is parked, or dropped with its
   reason in your report. Work that needs a run of its own gets a new feature folder. What is
   parked names the last commit that holds the folder, so the original can be read back
   (`git show <commit>:<path>`): that is the commit before the deletion, known once step 8's
   first commit is made. Check that the command resolves.

4. **Sync the roadmap and the design record** as `repository.md` § "Archive" says. A roadmap that
   still lists shipped work as next is the drift this stage exists to prevent.

5. **Retire what the project retires with a feature** (`repository.md` § "Archive"): promote
   first, then delete. Never retire a migration or an upgrade test merely because its feature is
   archived, when the repository does not say so.

6. **Strip the feature's marks off the code**, with the strip command (`repository.md`
   § "Commands"), once steps 1 to 5 are done: from here on the plan page no longer shows the
   delivery. Run it with `--dry-run` first and read what it lists. It takes off, and nothing else:
   - each `built` call of the feature, with the import a file no longer uses;
   - the tag and the rule of each written test: `<feature>#<slug>: <title> [<rule>]` becomes
     `<title>`. A title that kept its tag would be read as another feature's;
   - each planned screen of a journey that names the feature.

   It refuses while the gate fails, and refuses a `built` call it cannot take off without
   changing the code around it: take that one off by hand and run it again. It ends with the
   lines that still name the feature outside its folder. One in the code fails it and goes by
   hand; one elsewhere (a link into the folder, an ignore rule) is yours to read and settle
   before step 7: a link into the folder becomes the command that reads the file back, or goes.
   A stack with no strip lists everything there, to take off by hand.

   Then run the gate `repository.md` § "Gates" gives the strip: it changes no behaviour, and the
   run rewrites the stories of the retitled tests, which the pages and the check read.

7. **Delete `specs/features/<feature>/`**: remove the tracked files with git, then whatever is
   left on disk, since ignored files (`plan-feedback.json`, generated pages) show in no status.
   Run the check: it passes, with no plan of the feature left. Render the pages once: the
   feature's plan pages go with its plan.

8. **Commit twice.** First, before step 6, the promotions, the prose taken off, the parking and
   the roadmap, whatever their size: the folder is still there, and this commit is the one a
   parked item names to read it back. Then, with the repository's removal prefix,
   `<feature>: archive shipped feature spec`: the strip, the lines it left that you settled, and
   the deletion. It changes nothing the product does.

For a feature that spans repositories, archive in the repository that held its folder.

## Constraints

- Never write a per-feature summary file.
- Do not strip, and do not delete the folder, before the promotion, the parking and the
  retirements are done.
- Never take a mark off by a search and replace over the text: the strip reads the code, and a
  line it leaves is read before it goes.
- If the reference docs turn out wrong or stale, fix them: keeping them accurate is the point of
  this stage.
- Never restate in a reference doc what a narrative tells or a test holds: the copy is what
  drifts.
