---
name: bug-fixes-plan
description: Write or refine the plan of a diagnosed bug batch after bug-fixes closes. The plan is a section a bug and the pieces that fix it, written into the code as planned and evidence calls, with the delivery in lots; the reviewer reads the plan page generated from them, with what each reproduction saw. Planning only; no fixes.
---

# bug-fixes-plan

Help the reviewer see a bug batch: what is wrong, where it shows, what changes, and in what order
it is delivered. They read the plan to keep their grip on the application's code and to push back
on a fix before it is built. The diagnostics hold the investigation; the plan is not a copy of them. It
is the batch's **pieces**, each tagged at the places it changes, under the bug it fixes, and the
page is generated from them with what each reproduction saw.

This is `spec-plan` for bugs. Follow [`spec-plan`](../spec-plan/SKILL.md) for how a piece, a
clause, a point to confirm and `plan.md` are written, for the audit of complexity, and for the
review and the approval. This skill says what a plan of bugs adds and what it leaves out. The
form is [`specs/workflow-formats.md`](../../../specs/workflow-formats.md) § "A bug", § "A site"
and § "`plan.md`": its budgets are checked.

Input: the working set `bug-fixes` left under `specs/features/bug-fixes-<YYYY-MM>/`, its
`diagnostics/*.md` and its reproductions, failing, and `smell-sweep.md` when there is one.
Output: `plan.md` beside them, the sites in the code, and `## Delivery`. Nothing the product does
changes: a `planned` call and an evidence call are inert.

Run it in a fresh session once `bug-fixes` has closed the batch; refine a plan in place. Read
`.agents/repository.md` (the stack's spellings, the commands, § "Planning checks", § "Lots").
`map …` below is the map's command (`code-map` skill). Spawn any sub-agent unnamed and labelled
(§ "Sub-agents and the ledger"); a diagnostician closing a gap is `<feature>--diag-<bug-slug>`.

## What differs from a feature's plan

- **The diagnostics stand where the spec does.** There is no `spec.md`, no rule to own and no
  journey case. A product fork a diagnostic left open is a `To confirm:` of the piece it concerns;
  what its `## Decisions` settled stays settled.
- **A bug is in no narrative**, or it would not be one: the pieces are told a bug at a time, in
  the order of `plan.md`, not in run order. A narrative the fix lands in is still read first,
  when there is one.
- **The tests are written already.** A reproduction is the piece's test: you plan no other,
  unless a check the diagnostic lists beyond it is worth one.
- **There is no tasks stage.** The reproductions are the unit tests and the diagnosis is the
  grounding, so this skill writes the lots too, and one approval holds the plan and its
  delivery.

## Ground the plan

- Read every diagnostic and the smell sweep. Note the commit each was traced on: code may have
  moved. Verify each line you tag, and trace again only where a claim needs a line the diagnostic
  does not give or where two disagree. Do not diagnose a confirmed cause a second time.
- **Check the batch is closed**: each `CONFIRMED` diagnostic has its reproductions or a stated
  reason for none, and they fail today as recorded. The check runs those the configuration's test
  command reaches. Run the others (a browser's, a layer with its own runner) yourself when they
  are a file or two, as `repository.md` says each layer is run; hand a longer list to a `light`
  sub-agent, which reports each failure. One that is missing, or that now passes or fails differently, is delegated
  to a `diagnostician` under [the reproduction's rules](../bug-fixes/SKILL.md#the-reproduction).
  A diagnosed bug is never dropped silently.
- **Group what one mechanism explains.** Two reports with one cause are one bug, or two bugs
  whose pieces say which fixes which: say for each pair that could be the same cause whether it
  is.

## A bug

One `## Bug: <what is wrong>` section a confirmed bug, in the order they are read: what loses
data or is silently wrong first, then what is contained to a screen, then what is larger or waits
on a gate.

- **What whoever meets it sees**, in sixty words: where, what happens, what should. The cause is
  no part of it: it is the pieces', and their chains'. Link the diagnostic.
- **The pieces that fix it follow it**, a `## #slug` section each, up to the next bug. A piece
  under no bug stands above the first: an approved refactor of the smell sweep is one.
- A bug with no piece under it fails the check, and so does one that says too much.
- **A bug that joins an approved plan takes one `Changed:`**, in its own section, for itself and
  the pieces that come with it. A piece added under a bug the approval holds takes its own; the
  lot takes none.

## The pieces of a bug

A piece is what the diagnostic's fix approach names, under the tag its reproduction already
carries. Its section says what changes, then why and what was refused: the diagnostic's
alternatives, in a clause each.

- **Each place the fix changes is a `planned` call** with its clause, on the line the change
  lands at. In a template it is a tag; where no line runs, a comment. Its tag names the place,
  `<feature>#<slug>:<place>`, a short name of its own within the piece
  (`workflow-formats.md` § "A site"): the fix leaves a `built` call of that tag there. An
  evidence call names none.
- **Each line the bug shows at and the fix does not change is an evidence call**: what is seen
  there today, with its watch. It marks no change, so it
  stands where the cause is even when the fix is elsewhere, and it goes with the fix.
- **`expect` says what a place should see**, on evidence or on a `planned` call: once for the
  place, or computed at each crossing where the right value depends on it. **`distinct`** names
  the keys each crossing should see its own value for, for a bug no crossing shows alone. `repository.md` § "The stack"
  spells both.
- **Watch what is wrong, not what led to it.** "Should be" is read as a claim about the watched
  value: a value that is right and only reaches the wrong branch is context, with no `expect`.
- **Evidence is a piece's own.** A reproduction that also crosses another piece's places draws
  nothing under the first.
- **A place is written or it is not.** A plan leaves nothing "optional" to the implementer: what
  the diagnostic left open is decided here, or asked.
- **Read each place against the piece's own reason.** A clause repeated over many places hides
  the one it does not fit: a reason that says what stays as it is (a full page, a download) rules
  places out, and one of
  those is no place of the plan.
- **A ripple needs a place in each file it changes**: the lot check refuses a file of the
  product's code no place names.

Then make the reproductions tell it:

- **One reproduction a piece**, under the piece's tag. Split one that spans two pieces, each half
  failing for its own reason; rewrite one that stops at its first assertion, or that runs a case
  at a time, to observe, then assert once. The body you leave is the one the approval holds.
- **Run the check and read the chain** on the plan page: each reproduction, the places it crossed
  in run order with the values it saw, then how it failed. The check fails on a place whose
  reproductions saw only what it expects: the bug does not show there, and the diagnosis or the
  expectation is corrected. A reproduction the tools do not run (a browser's, one their test
  command does not reach) has no chain on the page: its piece's section links the diagnostic's
  recorded failure.
- **What a diagnostic lists beyond its reproduction** is one of three things, and the plan says
  which: a test, planned under the piece; a check only the user can make, named in its lot's
  reason; or dropped, in a clause of the piece's reason.

## A cause that is only plausible

A `PLAUSIBLE` diagnostic has no reproduction and no fix to plan yet. Its piece is what produces
the reading that tells the hypotheses apart, designed as [bug-fixes](../bug-fixes/SKILL.md#a-cause-that-is-only-plausible)
says: the sequence instrumented, an exit when the reading refutes them all, the build it is read
on. What follows the reading is another piece, in a later lot whose reason says what it waits
on. The plan ranks the hypotheses and commits to none.

## The delivery

Write `## Delivery` as `spec-tasks` cuts lots
([§ "Cutting the lots"](../spec-tasks/SKILL.md#cutting-the-lots), and its difficulty, set on
what is left once the cause is known: a diagnosed fix is often `easy`).

- **A lot is one subject for one reviewer**: the bugs of one surface, the pieces that share a
  file or a test file. A piece that another piece's fix makes show something goes after it, in
  the same lot or a later one; the reason says so.
- **The order of the lots is the order of the bugs**: what loses data first, refactors last
  (a behaviour-preserving extraction only after every lot editing those files).
- **A gate only the user can pass** is named in the reason of the lot it follows, with what
  waits on it: a reading on a device, a paid check, a reproduction the tools do not run. Each
  gate says which of three it is, since the next lot may start before anyone reads the last:
  it blocks the next lot (a later lot's work changes without it: rare), it blocks the next
  deploy only, or it waits for the end of the batch (the default). Say explicitly, with the
  reason, when nothing blocks the next lot.
- A change in another repository is no lot here: it is a pointer of `## Planned elsewhere`, and a
  lot that stands on it says so.

## Before handing over

- `map check <feature>` in a screen, then the whole check once before the commit: it runs the
  reproductions itself, and fails on one that passes.
- **Read each lot as its implementer will**: `map brief <feature>/<lot>`. A place that reads
  wrong there, or a test under the wrong piece, is corrected now.
- **Apply each proposed change of the database** with the repository's command (`repository.md`
  § "Commands") and read what differs: it is what the reviewer will read on the card, so it holds
  the change and nothing beside it. The check does not apply one, and the render only warns when
  its SQL fails.
- **Hand over only what the page does not hold**: where it is, what blocks the check or the
  commit, and any diagnosed bug the plan holds no piece for, with the reason. The reviewer reads
  the bugs, their pieces and the points to confirm on the page; do not restate them.
- **The plan is approved with its delivery**, on the reviewer's word and by the approval command
  alone. The approval keeps each reproduction as written and what it saw that day. The next
  stage is `feature-implement`, in a fresh session.

## Guardrails

- Fix nothing, an apparent one-liner included: a site is inert, and the product behaves as it did.
- Do not reopen a decision a diagnostic settled, nor treat a disproven hypothesis as open.
- Do not copy a diagnostic into `plan.md`: link it.
- Weaken no reproduction to make a chain read better.

## Maintaining this skill

What a plan of bugs shares with a feature's lives in
`spec-plan`, `spec-tasks` and `specs/workflow-formats.md`: change it there. Keep here only what a
batch of bugs adds.
