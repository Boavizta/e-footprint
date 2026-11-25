---
name: task-implement
description: Implement one lot of an approved delivery, a commit a piece — the implementer's rules in the fourth stage of the spec-driven workflow, under feature-implement or alone. Reads the lot's brief from the map, turns each planned place into code and each planned test into a test under its title, and reports its deviations and doubts. A piece that fixes a bug is built the same way, from its reproduction.
---

# task-implement

You implement **one lot** of a feature's delivery, then stop. A lot is a few pieces of the plan;
each piece lands as one commit, in the delivery's order.

Read `.agents/repository.md` (the stack's spellings, the commands, § "Gates"), then
`map brief <feature>/<lot>` (the map's command: `code-map` skill). The brief is what you are
handed: each piece with its statement, the code at each of its places, who will call each new
function, the decisions across pieces, the notes earlier lots left, the tests to write, change
and delete, and the journey cases of the lot's screens. How a piece becomes code:
[`specs/workflow-formats.md`](../../../specs/workflow-formats.md) § "Implementing a piece" and
§ "A `narrate` sentence". Read the project's rules for its quality gates and the architecture
pages that own what the lot touches.

**Read as you build, not before.** What is read at the start is carried by every request after
it, and that is most of what a lot costs:

- The brief shows the code at each place, the lot's statements and decisions, and what the spec
  plans at its screens with each mockup's opening comment. Do not read `plan.md`, the spec or a
  mockup again for what the brief holds.
- Open a file when its piece starts. A long file, a test file above all, is read by the range
  around the line the brief gives; whole only when the piece rewrites it.
- Which tests cross a place: `map reach <feature>/<lot>`. A wording gone stale across the
  repository: search for the files that hold it first, then the lines in those that matter.
- The tools' source is not where the method is learnt. What a title, a tag, a journey case or a
  commit's line becomes is said here, in `specs/workflow-formats.md` and in `repository.md`
  § "The stack". A question the three leave open is the first of your doubts, so that it gets
  written down.

**You edit neither `plan.md` nor `plan.approved.json`.** The plan is the reviewer's; what you had
to do differently goes in your report.

## A piece

1. **Each place becomes code**: a `planned` call is replaced by what its clause says, a shell
   gets its body, a comment goes with the change it announced. The clause is what was approved:
   when the code cannot do what it says, stop at that piece and report it.
   **A `built` call stands where the `planned` one stood**, with its tag and nothing else
   (`repository.md` § "The stack" has the spelling; your brief gives each place's line). Put it
   on the line where the change is, where the code runs whenever the change does: the reviewer's
   page opens there, and the stories read off it which step the place lands in. A new function
   holds it as its first line. A function that goes and an evidence call leave none. The check
   fails a place whose `planned` call you took off with no `built` call of the same tag.
   **Read each place against what the piece's reason leaves as it is.** A reason that says what
   stays (a kind of view, a file, a case) rules places out, and a clause repeated over many
   places hides the one it does not fit. A place the reason rules out is not built: its call
   goes, nothing is written, no `built` call either, and it is the first of your deviations.
2. **Each planned test becomes a test under the same title**, tag and `[rule]` kept. An existing
   case extended takes the planned title. A test under an `@planned.remove` comment is deleted,
   one under an `@planned` comment changed as the comment says.
   **An existing test whose title the piece makes false**, and that no comment plans, is retitled
   to what it now holds, under the piece's tag, and listed in your deviations with both titles:
   the check reads a new title as a test added and the old one as a test deleted.
3. **No test beyond the planned titles.** A test nobody planned is a change of the plan: if a
   behaviour is truly held by no planned title, write the test under the piece's tag and say so
   in your deviations. The same holds for a planned test you could not write and for a deletion
   nobody planned.
4. **A `narrate` sentence the code makes false is corrected here.** New and removed steps wait
   for the lot's last commit.
5. **Docs the change makes stale are updated in the same commit.**
6. **Commit the piece**: its files staged by name, the repository's message convention, and a
   last line `Piece: <feature>#<slug>`. A fix of an earlier piece is a commit of that piece. A
   piece that cannot pass its gate alone lands with the piece it needs, in one commit naming both.
7. **The commit passes a piece's gate** (`repository.md` § "Gates"): the types, and the piece's
   own test files, which the brief names: those it writes, changes or deletes a test in, and
   those `map reach` lists at its places. Not every test the changed files' imports lead to, and
   not the whole suite: the wide net is the lot's gate.
   **While working, run the tests alone.** The types are checked once, before the commit, beside
   the last test run and not in front of each one.

## A piece that fixes a bug

Its brief shows it: a reproduction reads "FAILS TODAY", and evidence "goes with the fix"
(`specs/workflow-formats.md` § "A bug"). It is built as any piece, and:

1. **See each reproduction fail first**, the way the brief says it fails. One that passes, or
   fails for another reason, is a diagnosis that no longer holds: stop at the piece and report it.
2. **Each evidence call goes, with nothing written in its place**, and so do the `expect` and the
   `distinct` of the piece's other calls. An import or a load line that served only the calls that
   went goes with them.
3. **Each reproduction passes, and is then declared a written test under the same title**
   (`repository.md` § "The stack" says how). Its body is not touched: a reproduction is never
   weakened to pass, and one that should assert more is a doubt you report, not an edit you make.
   The approval holds its lines, and the check lists one that changed.

The reproductions are the piece's tests. Nothing else is written (rule 3 of "A piece").

## The lot's last commit

- **The steps**: write the `narrate` and `event` calls the lot's pieces add, remove those of what
  went, in one pass. A step is where a reader would stop, not every line that changed. Run the
  narrative tests that cross them. Read the affected narrative as a guide through the code. Keep
  it focused on one coherent question. Add a step where the reader needs an explanation; add a
  variant when it materially changes their understanding of that question. A feature requirement
  or an additional code path alone does not justify either. Keep other coverage in ordinary
  tests. Apply this to the narrative the lot touches; report any changes to planned tests as
  deviations under the rules above.
- **The journey cases** of the lot's screens, each under its planned title.
- **What the repository asks of production code that is delivered** (`repository.md` § "Gates":
  a changelog entry, where it asks one): the lot's part of it, said for whoever uses the product.
- Its message names every piece it tells of, a `Piece:` line each. A lot with no step, no case and
  no such entry has no last commit.
- **The lot's gate** runs before it (`repository.md` § "Gates"), unless your brief says the
  end-of-run gate stands for it: the last lot of a supervised delivery. The pieces' gates and
  the journey cases you wrote still run.

## What you do not do

- Touch a file no place of the lot names without saying so. No opportunistic refactor, no
  speculative abstraction, no test for a state nothing can produce.
- Hide a failure with a skip, a fabricated state, a fallback or an unexplained retry.
- Run what `repository.md` says is never run unprompted, or a gate that waits for the user's go.
- Reset, stash or discard work that was there before you.
- Chain into the next lot.

A failure in a file your lot did not touch may come from the previous lot's review fixes. Fix it
when it is trivial and say so; otherwise report it.

## Report

End your turn only when the work is durable: committed, nothing running. Then report tersely:

- **Commits**: a line a piece, with its sha.
- **Gates**: what ran and passed; anything red or not run, and why.
- **Deviations**: a place not built or built otherwise, a file no place names, a test added,
  not written or deleted beyond the plan. Each with its reason in a sentence.
- **Doubts**: what you did not verify, where you cut a corner, where you want a second pair of
  eyes. Never empty: if you have none, say what you checked to conclude that.
- **Docs** updated, one line each.

The reviewer starts from your deviations and doubts. They are a map, not a defence of the work.

## Alone, without a supervisor

Tell the user what was built, what passes and what is left in the delivery, and suggest
`task-review` on the lot's commits. Do not start the next lot without their word. A blocker (a
wrong clause, a missing dependency, a need outside the lot) is surfaced, not worked around.
