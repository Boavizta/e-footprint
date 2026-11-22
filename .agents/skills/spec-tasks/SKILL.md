---
name: spec-tasks
description: Use after the user approves a feature's plan to prepare its delivery — third stage of the spec-driven workflow. Cuts the plan's pieces into lots (plan.md § Delivery), plans the unit tests each lot writes, changes and deletes, and edits the plan in place where grounding it shows a gap, each edit under a Changed paragraph. Writes no task list, no brief and no product code. Run in a fresh session.
---

# spec-tasks

You prepare an approved plan for implementation. A **lot** is what one implementer delivers and
one reviewer reads: a few pieces, a commit each. You write:

- **`plan.md` § "Delivery"**: the lots in order, each with its pieces in commit order, the screens
  whose journey cases it writes last, its difficulty and its reason;
- **the unit tests of each lot**: titles to write, comments on the existing tests that change or
  go. No bodies;
- **edits of the plan, in place**, where reading it with the implementer's eyes shows a missing
  site, a wrong clause, a piece to split or a test under the wrong piece.

There is no task list, no hand-written brief and no callout: `map brief <feature>/<lot>` prints
what an implementer is handed, from the plan itself.

**Run it in a fresh session**, from the approved plan. Read `.agents/repository.md` (commands,
gates, § "Lots") and [`specs/workflow-formats.md`](../../../specs/workflow-formats.md) § "The
approval, and what moved since" and § "The delivery". `map …` is the map's command (`code-map`
skill). The stage's two commands are **`map brief <feature>/<lot>`** and **`map check
<feature>`**: the first prints each piece with the code at its sites, the second says in a screen
what fails, what is not as approved and what each lot owes. Run the whole check once, before the
commit.

## Cutting the lots

- **A lot leaves the product shippable and the tests green, is one subject for one reviewer, and
  fits one implementer's context.** Ten pieces made three lots on the method's first feature.
  More than about five lots is a feature to split: say so before writing a delivery.
- **A lot compiles and stays green alone: check it before ordering the lots.** Apply the lot's
  shape changes in a scratch copy and run the type check. For a type that gains a required
  field, every literal of it is a site of the same lot, and the tests asserting the whole value
  change with it.
- **Pieces in the order their commits can be made**: each commit passes the types and the tests
  related to what it changed. A piece that cannot hold alone is committed with the piece it
  needs; say so in the lot's reason.
- **A planned case goes to the piece at whose commit it can be written.** A case that needs a
  later piece's behaviour moves to that piece, word for word.
- **A lot with no screen can still turn a journey assertion red.** Its reason then says the
  journey is run.
- **A gate only the user can pass** (a check on a device, a production operation, a reading that
  decides later work) is named in the reason of the lot it follows, with what waits on it.
- What usually belongs in one lot in this project: `repository.md` § "Lots".

### Difficulty

A lot's difficulty picks its implementer and is written only when it is not `standard`:

| Tier | What is left to do |
|---|---|
| `easy` | A bounded transformation or a fix whose cause is known, with little design judgement left: a rename, a move, a mechanical change of call sites, even across many files |
| `standard` | The default: ordinary work inside the prepared design |
| `hard` | An intrinsically difficult mechanism, or a real uncertainty, is still to be worked out. The reason names it |

What does not set it: the consequences of a bug, a sensitive path, the number of files. Those
decide how deep the review goes, which the reviewer sets from the diff. "Not looked at yet" is not
difficulty: settle the plain questions now, then classify. When in doubt, `standard`.

## The unit tests of a lot

For each lot, read `map reach <feature>/<lot>`: the tests that cross the lot's sites today.

- **A unit test exists for two reasons**: the input combinations of a pure function, or a branch
  no narrative case takes. Plan titles for those only, each naming the clause it holds. A title
  whose reason is not plain from its words gets a comment above it.
- **The case that takes a branch asserts it.** A clause whose branch a narrative case runs
  through without asserting gets its assertion in that case, under an `@planned` comment. A unit
  title is for a branch no narrative case runs through at all.
- **An existing test that a narrative case holds, and that has neither reason, goes**: an
  `@planned.remove` comment naming the case that holds it. An existing test that changes gets an
  `@planned` comment. So the reviewer approves each deletion before one is made.
- **Two holders together remove a test.** A test that replays a pure function through a screen
  checks the combination, which the function's own table holds, and the wiring, which one
  narrative case holds. The comment names both. A journey case is never a holder.
- **The assertion that holds a wiring would fail if the wiring were wrong.** One that passes
  whichever source the value comes from crosses the wiring and does not hold it. Check each
  holder you name; plan the missing read into the narrative case.
- **A removal that rests on a planned assertion says "planned"** in its comment.
- **The prune is a piece of its own, heading the first lot that would break a test it deletes.**
  Its sites are the removal comments and the comments of the reads that hold the removed tests,
  when those reads are of today's behaviour; its one commit writes the reads, then deletes. A
  read of the feature's own behaviour stays with the feature's piece.
- **A reorganisation of tests is a piece of its own** (cases merged into a table, moved, rebuilt
  on one fixture), within the tests the lot's sites reach. A wider one is not written into the
  plan: report it at the end, for the user to make a lot of or to park.
- **Prune around the feature only.** Bringing the whole suite down is a pass of its own.
- **No mechanical duplicate finder.** Tests that cross the same sites are mostly distinct cases.
  The listing is the map's; the judgement is a reading of the bodies.
- **Check each journey case against the narrative cases** the same way: a case that restates one
  leaves, a state worth seeing stays as a screen, and what a leaving case alone held gets a
  narrative owner first. One decision of `plan.md` says which case holds what.

What `reach` cannot see: a comment on code that runs (make it a call), a test that throws before
any site, a helper called on the line before a site. Search for those.

## Editing the plan

No edit of an approved plan is silent: a unit that differs from the approval carries a `Changed:`
paragraph or the check fails.

- **A `Changed:` is one edit**: what moved, in bold, why, then the lines it comes to.
- **Written for a reader who has not read the code.** Use only words the plan has defined, or
  name the function. Say what happens to the user or to the code, in the order it happens, then
  what it costs. The method's own words (ripple, site, facet, claim) stay out of it.
- **A line that moves keeps its words.** Moved word for word between pieces or lots, it is
  detected and asks nothing. Reword only what changes in substance.
- **The stage's own output is no change**: the delivery, the unit titles and the comments on
  unit tests carry no `Changed:`. A narrative case added, a read added to one, a clause reworded
  and a new piece are changes.
- **A question is a `To confirm:`**, not a `Changed:`. Only what is the reviewer's to decide.

## Handing over

1. `map check <feature>` is clean but for what awaits the reviewer. Run the gate of a plan edit
   (`repository.md` § "Gates"), then commit the stage's files by name.
2. Tell the user: the lots and their order, the tests each lot writes, changes and deletes in
   numbers, the edits of the plan with where to read them (the delivery page), the questions, and
   any wider reorganisation worth a lot or a parking place.
3. The reviewer reads the delta on the delivery page and answers there or in the session. Read
   the answers with `map feedback <feature>`, act on what is not approved, and turn each answered
   question into a statement.
4. **The delivery is approved by the reviewer**, as the plan was: on their word, run the approval
   command and commit `plan.approved.json`. Implementation starts in a fresh session, with
   `feature-implement`.
