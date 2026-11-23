---
name: spec-plan
description: Use after the user approves a feature's spec to write or refine its plan — second stage of the spec-driven workflow. The plan is made of pieces written into the code (planned calls, shells, @planned comments, planned test titles) and a short plan.md; the reviewer reads the plan page generated from them. Planning only — nothing the product does changes, and no delivery is written.
---

# spec-plan

Help the reviewer picture the smallest justified change, with little interpretive effort. The
plan is not a document you draw: it is the feature's **pieces**, each tagged at the places it
changes, and the page is generated from them. You write:

- the **sites** in the code: `planned` calls where a change lands, shells for new functions,
  `@planned` comments where no line runs;
- the **planned tests** of the narrative and server tiers, as titles with no body;
- **`specs/features/<feature>/plan.md`**: a section a piece (its statement, its reason), the
  decisions across pieces, the waivers.

Nothing the product does changes: a `planned` call is inert and a shell fails loudly if reached.
You write no unit-tier title and no delivery; those are `spec-tasks`'.

**Run it in a fresh session**, from the approved spec. A spec that cannot stand alone fails here,
as a question to the user. Read `.agents/repository.md` (the stack's spellings, the commands, the
gates, § "Planning checks") and [`specs/workflow-formats.md`](../../../specs/workflow-formats.md)
§ "A site" and § "`plan.md`": the form is stated there and its budgets are checked. Do not read
the tools' source to learn it. `map …` below is the map's command (`code-map` skill).

The `references/` and `assets/` beside this file belong to the earlier `plan.html` form, which
`plan-review-guide` still reads.

## Before writing

- **Read the map first**: `map spec <feature>`, then the `narrative` and `around` answers it
  names, then `step` for the steps you will change. It gives a `file:line` for what matters, so
  you read ranges, not files. Then the spec, `plan-draft.md` if the spec stage left one, the
  project's rules and the architecture pages that own what the change touches.
- **List the narratives the change lands in, missing ones included.** From the spec's rules,
  name each action of the product the change enters and set it against the map: told, told
  wrongly, or missing. `map spec` names only the told ones, so a missing one is found from the
  rules. For each missing or wrong one, propose its narrative to the reviewer: its title, its
  reference case, the branch cases the rules need, and the functions its steps stand in.
- **The narratives the change lands in are reviewed before the plan is written.** A missing one,
  or one whose steps read wrong, is told or corrected first, in its own commit and preferably its
  own session; say so and stop. A plan written on a narrative nobody has read is
  rewritten when someone does.
- **Trace the real code and tests** along every path the feature touches: success, error,
  cancellation, retry, rendering, persistence. A document is no evidence of what a function does
  today.
- **Look for the existing mechanism** before proposing a new one. For each interaction, make the
  checks of `repository.md` § "Planning checks" and say which it touches.
- A feature that lands in no code that runs today has shells that never run, so its pieces have no
  run order on the page. Tell the reviewer; the order is then `plan.md`'s.

## Audit complexity before the review

The spec's scope was shaped at `spec-specify`. Planning is the first time it meets the code, where
a cost or a simpler alternative can show. For each added abstraction, store, queue,
synchronisation, validation or recovery, name the agreed behaviour it serves and compare it with
a smaller extension of what exists. Remove what has no demonstrated need.

- **A value that behaves like a figure of an existing whole joins it.** Challenge a parallel type:
  it costs a second type, another parameter and a rewritten filter wherever the whole is walked.
- A queue, a replacement rule or a pending flag is a smell: check first whether an existing lock
  already serialises the actions.
- No check for a hypothetical stale or hand-crafted request. "Defence in depth" is no
  justification; a new check has a concrete job in a supported path.
- Before planning a refresh, a preserved draft or a background sync, check which surfaces are
  visible. Showing an error is not keeping an edit.
- No framework inferred from one helper, no second model of data owned elsewhere.
- No recovery for a failure inside a failure handler by reflex: each adds branches of its own.
- A confirmed bug found on the way is reported with its evidence, and a deferred concern parked
  where the repository parks them. Nothing is fixed during planning.

**A change the feature needs in another repository is planned there**, in that repository's own
plan of the feature, by a session run there. Here it is a pointer, an item of
`## Planned elsewhere`, never a piece: say what this plan relies on and which pieces stand on it
(`workflow-formats.md` § "A feature that changes two repositories"). A guard here against what
the other repository should fix is put to the reviewer as a `To confirm:`.

**A requirement a small behaviour change would make much cheaper** is put to the reviewer as a
`To confirm:` in the piece it concerns: the smaller behaviour, which states, coordination or
recovery would disappear, and what the user would lose. Weigh frequency, benefit and failure
severity on evidence, never on invented figures. The spec changes only on the answer: then
`spec.md`, its cases and the plan are edited together, in place, with no note of the change. Correctness, security and the project's
invariants are never traded away. No proposal is a valid result.

This audits your reasoning. It is no section of `plan.md`.

## Writing the pieces

- **A piece is one statement the reviewer can approve alone.** Cut by what is decided, not by
  file or by layer. A change to stored data is a piece; so is each decision the reviewer could
  refuse without refusing the rest.
- **A clause states the change at its place**, not what the code does today: one clause, no
  reason, no list of cases. The reason is the piece's, in `plan.md`.
- **A new function is a shell, and the clause of the site that will call it names it in
  backticks.** Without that the piece is drawn in no narrative, and the check fails.
- **On code that runs, a site is a call.** A comment is for a type, a schema, a migration, a doc.
  No test crosses a comment, so no narrative shows it and no test reaches it.
- **A mechanical ripple is stated once, at its cause.** When one site makes twenty literals or
  assertions change the same way, its clause says so, and the twenty carry no tag. A place is
  tagged when its change is a decision.
- **Define a term where the plan first needs it**, and use only defined terms after.
- **For a mechanism in two steps, the piece's reason says why one is not enough.**
- **Each fact once.** What a site's clause says, the section does not repeat; what a test title
  says, neither does.

## Writing the tests

Titles only, of the narrative and server tiers. A behaviour is proven by a narrative case; a unit
title is `spec-tasks`' to plan.

- **Each rule of the spec has one owner**: the test whose title ends `[<rule-slug>]`.
- **No title repeats a case the feature's host already has.** When the new value only joins an
  existing whole, that whole's tests are extended, not copied with the value swapped in.
- **An existing case extended is the owner**: a planned test beside it, under a comment saying
  it is the case above, given what, and retitled, and that no case is added.
- **A rule true by the shape of the code is waived, not tested**: an item of `## Rules no test
  holds`, proposed with `To confirm:`. A test that restates the implementation is not written.
- **A planned case goes to the piece at whose commit it can be written.**
- **Re-read each journey case of the spec against the plan's decisions**, and reword one a
  decision made false.

## Guards and states

- **Before a guard on a value, list the paths that can produce it.** If none can, write no guard
  of its own: the existing loud check covers it.
- **Before making a validity check stricter, list the stored states an earlier client can
  leave.** A stricter check that throws on one of them breaks a screen for a user who did nothing.

## Points to confirm

- One per piece at most: the question in bold, then the alternative. Only what is the reviewer's
  to decide.
- **State the content, never a rule's name alone.** "Applied offline is owned by one case" reads
  as if offline saving were planned.
- An answer is written into the piece as a statement, and the paragraph goes.

## While editing, and before handing over

- **Batch the edits.** Each edit replays the session's whole context.
- `map check <feature>` says in a screen what fails; `map plan <feature>` shows the plan as it
  stands. Run the whole check once, before the commit, with the gate of a plan edit
  (`repository.md` § "Gates"). A plan needs no run of the whole test suite.
- **A mechanical change across many files goes to a cheaper agent with a precise brief**, then is
  checked: a rename, a retag.
- **Delete `plan-draft.md` once each of its lines is a piece**, a reason or a point to confirm.
  A line you do not follow is said to the reviewer, not dropped. Commit the plan's files by name.
- **Hand over only what the page does not hold**: where it is, what blocks the check or the commit,
  a line of the draft that no piece, reason or point to confirm carries, and **what you read that
  no verb of the map pointed at**: those are the map's gaps. The reviewer reads the pieces, their
  reasons and the points to confirm on the page; do not restate them.

## The review, and the approval

- The reviewer reads the page top down: the pieces no narrative shows, the narratives the change lands in,
  then a card a piece, those of the first block first. They ask in this session, and answer each
  point to confirm under it on the served page (`npm run comprehension`). Read those answers with
  `map feedback <feature>`; each answer is an edit in place and a commit.
- A simplification of the underlying code found on the way is made in another session, and the
  plan is then rewritten against it.
- **The plan is approved when no question is left and the reviewer says so.** Then, and only
  then, run the approval command and commit `plan.approved.json`. An agent never approves on its
  own judgement. The next stage is `spec-tasks`, in a fresh session.
