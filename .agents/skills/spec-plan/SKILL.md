---
name: spec-plan
description: Use after the user approves a feature's spec to write or refine its plan — second stage of the spec-driven workflow. The plan is made of pieces written into the code (planned calls, shells, @planned comments, planned test titles) and a short plan.md; the reviewer reads the plan page generated from them. Planning only — nothing the product does changes, and no delivery is written.
---

# spec-plan

Help the reviewer picture the smallest justified change, with little interpretive effort. The
plan is not a document you draw: it is the feature's **pieces**, each tagged at the places it
changes, and the page is generated from them. You write:

- the **sites** in the code: `planned` calls where a change lands, shells for new functions,
  `@planned` comments where no line runs. A place that becomes code names itself in its tag,
  `<feature>#<slug>:<place>`: a short name for what changes there, its own within the piece
  (`workflow-formats.md` § "A site"). The check asks for it;
- the **planned tests** that own the spec's rules, in any appropriate tier, and the narrative
  and server cases the change needs, as titles with no body;
- **`specs/features/<feature>/plan.md`**: a section a piece (its statement, its reason), the
  decisions across pieces, the waivers.

Nothing the product does changes: a `planned` call is inert and a shell fails loudly if reached.
Additional unit coverage and the delivery belong to `spec-tasks`; a rule owner can be an ordinary
test planned here.

**Run it in a fresh session**, from the approved spec. A spec that cannot stand alone fails here,
as a question to the user. Read `.agents/repository.md` (the stack's spellings, the commands, the
gates, § "Planning checks") and [`specs/workflow-formats.md`](../../../specs/workflow-formats.md)
§ "A site" and § "`plan.md`": the form is stated there and its budgets are checked. Do not read
the tools' source to learn it. `map …` below is the map's command (`code-map` skill).

The `references/` and `assets/` beside this file describe the earlier handwritten `plan.html`
format. Port an older plan to the current format before delivery resumes.

## Before writing

- **Read the map first**: `map spec <feature>`, then the `narrative` and `around` answers it
  names, then `step` for the steps you will change. It gives a `file:line` for what matters, so
  you read ranges, not files. Then the spec, `plan-draft.md` if the spec stage left one, the
  project's rules and the architecture pages that own what the change touches.
- **Read the narratives the change lands in and assess untold flows.** From the spec's rules,
  name the actions the change enters and set them against the map. Follow `workflow.md`
  § "Narratives and test ownership": untold code alone is no gap. Consider recurring kinds of
  change too: when another developer will need a pattern to follow, choose a representative
  example and assess whether a narrative would make that pattern clear. Give its question,
  reference case, useful variants and step functions. Use the doc scope for documentation flows.
- **Review the narratives used as planning context before relying on them.** Correct misleading
  steps first. When a new narrative of existing behaviour is chosen as planning context, tell it
  and have it read first, in its own commit and preferably its own session, taking out the prose
  it replaces. A new flow can be planned with intended narration when the stack supports it.
  Planning can proceed with direct code links and ordinary tests when a narrative adds little.
- **Keep documentation in its owning form.** Apply `workflow.md` § "Documentation ownership":
  patterns and execution belong in narratives, structuring decisions in architecture, local
  semantics beside code. State deliberate conventions and their reasons at the relevant steps.
  Link the representative example; remove prose the narrative replaces when it is delivered.
  Add only information needed to understand or evolve the change, once in its canonical home.
- **Trace the real code and tests** along every path the feature touches: success, error,
  cancellation, retry, rendering, persistence. A document is no evidence of what a function does
  today.
- **Look for the existing mechanism** before proposing a new one. For each interaction, make the
  checks of `repository.md` § "Planning checks" and say which it touches.
- A feature that lands in no code that runs today has shells that never run, so its pieces have no
  observed run order on the page. Tell the reviewer.

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
- Put adjacent cleanup in its own piece, marked `Kind: refactoring`. Its reason states why it
  belongs in this delivery and whether the feature depends on it. Separate behavior corrections
  from changes that only reorganize existing code or documentation.
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
  backticks.** This connects the new function to its caller; it does not require a narrative.
  An entry point nothing in the repository calls is named by the title of a planned test that
  calls it. A shell named by neither fails the check.
- **On code that runs, a site is a call.** A comment is for a type, a schema, a migration, a doc.
  No test crosses a comment, so no narrative shows it and no test reaches it.
- **A mechanical ripple is stated once, at its cause.** When one site makes twenty literals or
  assertions change the same way, its clause says so, and the twenty carry no tag. A place is
  tagged when its change is a decision.
- **Order the piece sections in `plan.md` for review**, introducing concepts before pieces rely
  on them; a brief overview can establish context first. The detailed cards preserve this order;
  narrative diagrams retain execution order. Implementation order belongs to `spec-tasks`.
- **Define a term where the plan first needs it**, and use only defined terms after.
- **For a mechanism in two steps, the piece's reason says why one is not enough.**
- **A useful new narrative can be planned before its reference run exists.** Use the stack's planned
  narration at the code for its step IDs, sentences and optional links to change places. Its planned
  reference test declares the IDs in intended order, without repeating the sentences. The page must label
  this as intent, never an observed run or landing. On implementation the named steps become recorded
  narration and the reference verifies their order. An existing-behaviour step needs no change link.
- **Cross-piece sections hold genuinely shared decisions, stated once.** Keep one only when it
  constrains several named pieces and has no clear owning piece or site. Put owned details with
  their pieces and sites, and test expectations in their cases. Remove repeated overviews,
  verification reports, unchanged guarantees and process commentary. Omit empty sections; never
  use them to bypass piece budgets.
- **Each fact once.** What a site's clause says, the section does not repeat; what a test title
  says, neither does.

## Writing the tests

Titles only. Rules are the spec's optional **Behavioral requirements**, not a checklist of its
architecture or prose. Keep design choices in their owning explanation or plan decision;
do not invent tests to restate them. A regression risk introduced by a plan choice is verified
with that choice, not promoted into a spec rule; unchanged guarantees stay with their existing
coverage. Each rule has an appropriate existing or new test owner,
or an explicit justified waiver. Use a narrative case when it helps explain
the flow; use an ordinary test for other behaviour, at the level the project's testing guidance
calls for. Plan rule owners in any appropriate tier here; additional unit coverage is
`spec-tasks`' to plan.

- **Each rule of the spec has one owner**: the test whose title ends `[<rule-slug>]`.
- **Narrative membership is an editorial choice.** Keep each narrative focused on one coherent
  question. A requirement, an additional code path or a branch crossed by an existing case does
  not oblige that narrative to own it. Put other behaviour in ordinary tests.
- **No title repeats a case the feature's host already has.** When the new value only joins an
  existing whole, that whole's tests are extended, not copied with the value swapped in.
- **An existing case extended is the owner**: a planned test beside it, under a comment saying
  it is the case above, given what, and retitled, and that no case is added.
- **A rule true by the shape of the code is waived, not tested**: an item of `## Rules no test
  holds`, proposed with `To confirm:`. A test that restates the implementation is not written.
- **A planned case goes to the piece at whose commit it can be written.**
- **Re-read each journey case of the spec against the plan's decisions**, and reword one a
  decision made false. Screen journeys apply only when `commands.journeys` is nonempty in
  `comprehension.config.json`; available tiers and commands come from repository settings.

## Guards and states

- **Before a guard on a value, list the paths that can produce it.** If none can, write no guard
  of its own: the existing loud check covers it.
- **Before making a validity check stricter, list the stored states an earlier client can
  leave.** A stricter check that throws on one of them breaks a screen for a user who did nothing.

## Points to confirm

- One per piece at most: the proposal in bold, stated as the plan would state it, then the
  alternative. Only what is the reviewer's to decide.
- **State the content, never a rule's name alone.** "Applied offline is owned by one case" reads
  as if offline saving were planned.
- An answer "Yes, as proposed" is written in by the approval command, word for word, into the
  piece's reason: the check counts the proposal in the reason's budget from the day you write it.
  Any other answer is yours to write into the piece as a statement, and the paragraph goes.

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
  then a card a piece in `plan.md` section order. They ask in this session, and answer each
  point to confirm under it on the served page (`npm run comprehension`). Read those answers with
  `map feedback <feature>`; each answer is an edit in place and a commit.
- A simplification of the underlying code found on the way is made in another session, and the
  plan is then rewritten against it.
- **The plan is approved when no question is left and the reviewer says so.** Then, and only
  then, run the approval command and commit `plan.approved.json`. An agent never approves on its
  own judgement. The next stage is `spec-tasks`, in a fresh session.
