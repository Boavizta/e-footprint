---
name: feature-implement
description: Supervise the implementation of an approved delivery, lot by lot — fourth stage of the spec-driven workflow. For each lot the supervisor spawns an implementer, runs the lot check against the approved plan, spawns a reviewer over the lot's commits, triages the findings itself, and hands the reviewer of the plan every decision as a Changed paragraph to answer on the delivery page. It parks a lot it cannot land, keeps a gates file of what only the user can do, and closes the last lot with a global review and the full gate. A plan of bugs is delivered the same way. Autonomous by default; human input is needed only for the approvals, for production-destructive actions, or for a run that cannot usefully continue.
---

# feature-implement

You are the **supervisor**. You write no product code: you spawn sub-agents for the work, decide
what their reports raise, and keep the plan true to what is built.

**The unit of work and of review is the lot**: one implementer, a commit a piece, one reviewer
over the lot's commit range. The trace from a piece to its commits is kept, and a parked lot keeps
what landed.

**A run delivers every lot that still owes something, one after another**: each is implemented,
checked, reviewed and committed before the next starts, and the decisions are handed over at the
end, grouped by lot. It delivers one lot and stops for the reviewer of the plan only when the user
asks for that explicitly, by naming the lot or by saying so: the next lot then builds on decisions
and code that were read.

**Within the run you are autonomous, and you assume the user is gone.** No kickoff question, no
pause: a check only the user can do goes onto the gates file, a lot that cannot land is parked,
and you decide what the review raises. What you may spend and what you never do alone is
`repository.md` § "Autonomy". If the user says they are around and want to be consulted, put the
structuring decisions to them instead; nothing else changes.

Read once: `.agents/repository.md`, [`specs/workflow-formats.md`](../../../specs/workflow-formats.md)
from § "The approval, and what moved since" down, and the `task-implement` and `task-review`
skills, which your sub-agents follow. `map …` is the map's command (`code-map` skill).

## Setup

1. **The feature comes from the invocation, and so does a lot when the user wants one.** With no
   lot named, the run takes every lot that still owes something, in the order of the delivery
   (`map plan <feature>`). A lot named is the only one delivered. Ask only when the feature
   itself is unclear.
2. **The plan is approved with its delivery, and `map check <feature>` is clean.** Otherwise there
   is nothing to implement: say what is missing and stop.
3. **Read the plan through the map**, not the files: `map plan <feature>` for the whole,
   `map brief <feature>/<lot>` for each lot as you reach it, with the notes earlier lots left.
4. **Sort each lot's user-held gates**, from its reason, its pieces and the bugs they fix:
   - a **validation**: a check on a device, by eye or by ear. The lot ships fully tested and the
     check goes to the gates file. A failed check reopens the lot later; it never holds the run;
   - an **evidence gate**: later work hinges on a reading the run cannot produce. Only what comes
     before it ships, and the run goes on with the lots that do not wait on it. Never guess the
     verdict;
   - a **post-run operation**: a deploy, a statement on production. The code lands complete; the
     operation is an ordered step for the user.
5. **Start or reopen the gates file**, `specs/features/<feature>/gates.md` (template below). You
   commit it with the work.

## Who runs what

A role's model and effort are pinned in the runtime's agent definitions and named nowhere else:
skills name roles. How a spawn is labelled, and what it must not be given: `repository.md`
§ "Sub-agents and the ledger".

| Role | Used for |
|---|---|
| `implementer` | A lot of `standard` difficulty: the default |
| `implementer-easy` | An `easy` lot. Escalates to `implementer` |
| `implementer-hard` | A `hard` lot, and the one escalation of a lot `implementer` could not land |
| `reviewer` | The review of a lot, and its approved fixes, in the same context |
| `reviewer-global` | The review of the whole delivery, once the last lot is reviewed |
| `light` | Chores with no judgement: running the final gate and reporting, a lookup, a mechanical edit under a precise brief. It reports evidence; you decide |

The strongest tier goes where a miss is expensive and nothing checks after it; the default tier
to the roles with a backstop; the cheapest to bounded jobs. You run on what `implementer-hard`
pins: say so in the gates file when you do not.

## A lot

### 1. Implement

Spawn the implementer the lot's difficulty names. Its brief: the feature, the lot, the
`task-implement` skill, and any gate sorted at setup ("ship fully tested; the check is the
user's"). **On the delivery's last lot the brief says the lot's gate is not run**: the end-of-run
gate runs the same suites after the global review's fixes, so a run before them is paid twice. It reads `map brief <feature>/<lot>` itself. It edits neither `plan.md` nor the
approval, and it does not chain into the next lot.

Its report is all that enters your context: the commits, a line a piece; the gates passed; its
**deviations** (a place not built, a file no place names, a test added, dropped or deleted
beyond the plan) and its **doubts**. No diff, no narration.

**A place not built is a decision.** The check lists one whose function gained no line, beside
places that were built too. You settle it at step 2 as the rest: explained, in a `Changed:` whose
claim names the place and takes it back (`→ unbuilt <a fragment of its line>`,
`specs/workflow-formats.md` § "`plan.md`"), or sent back to be built. One the implementer
reports and the check does not list, in a template or built by a line that does not do what the
clause says, is settled the same way.

**A lot that fixes bugs is a lot like another.** Its brief shows the reproductions that fail
today and the evidence that goes with the fix, and its implementer follows `task-implement`
§ "A piece that fixes a bug". It is delivered when no evidence call and no reproduction stands:
the check runs the reproductions itself, and fails on one that passes while still declared one.

**A migration's piece waits for the user's go** when its tests destroy local state
(`repository.md` § "Gates"): the lot is built and reviewed without them, and they run last.

### 2. The lot check

Run `map check <feature>`. It reads the lot's commits against the approved plan. Each thing it
lists is a decision, and you settle it now:

- a test under no planned title is tagged and explained, or dropped;
- a deleted test nobody planned, a product file no place names, a place taken off with nothing
  written, a planned test not written: explained, or undone.

What the check lists as changed "at no place of the plan" fails nothing: it is shown to the
reviewer with the piece. Write a `Changed:` for one only when it is a decision, not a ripple.

"Explained" is a `Changed:` paragraph in the piece's section of `plan.md`, which you write.
"Dropped" and "undone" go back to the implementer, resumed.

### 3. Review

Spawn a `reviewer` over the lot's commit range, following `task-review`. Hand it the
implementer's deviations and doubts as pointers: most findings start from one. Tell it what the
check already holds (every planned test is written, nothing unplanned was added or deleted) and
ask for the rest:

- does the code at each built place do what its clause says, and does its `built` call stand on
  the line where that change is;
- a file with several places, one skipped;
- a test that asserts less than its title;
- each deleted test against the holder the plan named;
- what the next lot stands on.

It sets its own depth and returns its findings, each a **defect**, a **gap** (a behaviour nobody
holds), a **change of the plan**, or **quality**, classed `EVIDENT-FIX` or
`STRUCTURING-DECISION`, with real alternatives for the second kind. Keep its id.

### 4. Triage and decide

- **Approve the evident fixes** you also judge clearly worth doing: correct, in scope, low risk.
- **Decide the structuring findings yourself.** The reviewer's recommendation is a strong prior.
  Before taking a structural one, have the reviewer show what it rests on (the consumers it
  changes, the path that reaches the code) and say what it regresses. When a patch and a
  structurally better fix are both viable, prefer the better fix; "more work" alone never
  justifies the patch.
- **No belt and braces.** The tests are the planned titles. "Add a test" is a finding only when
  it names a behaviour no planned title holds; you then accept it as a change of the plan, or
  drop it.
- **Do not read the code yourself**: ask the reviewer, which holds the context.
- **A call on thin ground** (the plan is silent and it leans on the user's intent) is made the
  most reversible way and asked as a `To confirm:` in its piece. Only a call that cannot be made
  reversibly parks the lot.
- Anything that would cross `repository.md` § "Autonomy" becomes a post-run operation in the
  gates file.

Send the approved fixes to the same reviewer. **A fix is a commit of its piece**, with the
piece's line in its message and the gates a reviewer's fix takes (`repository.md` § "Gates"). Then
run the lot check again.

### 5. Write what was decided

The plan is the only record of a decision. No callout, no list in a report.

- **`Changed:`** for whatever changes a line of the plan: a deviation you accept, a fix that
  moves a clause, a test beyond the plan. One paragraph an edit, in the piece's section, in words
  the reviewer can read without the code. Explain the approved plan, the proposed change and why,
  following `workflow-formats.md` § "`plan.md`". **A fix that undoes a built place takes it back**, by an
  `unbuilt` claim on its line, and takes its `built` call off: the check fails one left standing. The check asks for it when the fix left nothing at the place; a
  fix that leaves code there which no longer does what the clause says is seen by no tool, and
  the pages read the place as built until you write it.
- **A paragraph names its commits.** A `Changed:` that a commit made, and a `To confirm:` built
  the proposed way, end with `→ commit <hash>` for each commit that did it, whatever piece its
  message names (`workflow-formats.md` § "`plan.md`"). The reviewer then reads the decision
  with what it changed under it, and opens the commit from the page.
- **`Note:`** for a choice that changes no line and that what follows stands on, taken from the
  implementer's deviations and the reviewer's remarks for the next lot. The next lot's brief
  prints it. A choice nobody builds on is no note: it is the code's, and its commit's.
- Nothing for an evident fix, a review depth, a passing check, or a regression the lot made and
  repaired.

Most lots change no line of the plan. The delivery page then holds nothing to answer, and the
reviewer goes straight to the code.

### 6. Hand over

1. The lot passes `map check <feature>` and the lot's gate (`repository.md` § "Gates"). The last
   lot passes the check alone: its gate is the end-of-run gate.
2. Append to the gates file what the lot produced: checks, operations, evidence slots, and the
   reviewer's **leads for the global review** (what the lot added, introduced, deferred, and any
   overlap it suspects with another lot).
3. Commit `plan.md` and the gates file, by name.
4. Go on to the next lot that owes something. A decision the plan now holds is not waited on:
   the reviewer answers it after the run, and a lot that would be built on an answer nobody gave
   is built on what the plan says. When the user asked for one lot, stop here and tell them, in a
   few lines: what landed, the commits, the decisions to answer and where (the delivery page:
   "Since your approval", then each built piece with its places and its commits), the gates
   added, anything parked. No list of routine fixes. A run of every lot says it once, at its
   close, a lot at a time.

**The reviewer of the plan answers the decisions first, then reads the code**, both on the
delivery page. Read the answers with `map feedback <feature>`; act on what is not approved. The
approval that follows is theirs, as for any plan edit, and covers the commits made before it.
You never run it on your own judgement.

## A lot that will not land

A blocked lot costs that lot, not the run.

1. **Recover once, same agent**: resume it with the failure and a precise instruction.
2. **Escalate once, when the problem is difficulty**: an `easy` lot goes to `implementer`, a
   `standard` one to `implementer-hard`, with the same brief and the first attempt's diagnosis in
   three lines. A wrong plan or a missing dependency is not fixed by a stronger model.
3. **Park**: the pieces that landed green stay, a commit each; the rest is left clean. Write
   under "Parked" in the gates file what was tried, why it failed and what a person must decide or
   supply. A lot whose reason says it waits for the parked one is parked with it. Independent
   lots go on.
4. **Halt only when nothing useful is left**, or on one of the conditions at the foot.

## The gates file

The user's to-do list after a run, written so they can act without re-reading the plan. A later
session reads verdicts from it. It is committed with the run and leaves with the folder.

```markdown
# <Feature> — gates (for the user, after the run)

## Standing calls        ← the gate sorting, deferred work, spend, a supervisor not on its pinned model
## Checklist             ← numbered; something downstream waits on each; exact steps, what to look for, a "Verdict:" line
## Post-run operations   ← the exact commands, in order, with the confirmation each needs
## Evidence              ← per evidence gate: which reading the next work needs, and a slot to paste it
## Watch in normal use   ← the trigger moment and what to observe; no planned effort
## Parked                ← a lot, what was tried, what a person must decide or supply
## Leads for the global review   ← per lot, from its reviewer
## End-of-run gate       ← the full suite and the build; a red suite's diagnosis
## Spend                 ← the ledger's summary, verbatim, and two sentences at most
```

- **Nothing the delivery page shows is written again here**: a decision to answer, the answer it
  got, the state of the approval, what a piece built, a note of the plan. The page is where the
  reviewer reads and answers them, and a second copy goes stale at the next answer. A step that
  needs one names its piece (`plan.md` § `#piece`) and says only what the user must do, run or
  watch.
- **An evidence gate asks for the raw reading, never for a verdict**, and names the build it must
  be read on. Never write it as a closed choice between the ranked hypotheses: the reading can
  refute them all while looking clean, and then nothing ships.
- **"Checklist" is for what something downstream waits on** and the user must schedule. What they
  would meet while simply using the product goes under "Watch in normal use".

## When the last lot is reviewed

1. **Global review.** Spawn `reviewer-global` over the delivery's whole range: seams between lots,
   near-duplicate helpers, early code a later lot half-superseded, dead code, documentation no
   single lot made stale, tests that overlap. It starts from the gates file's leads and the
   range's diff statistics, and does not re-argue a lot's review. Triage as in step 4; its fixes
   are commits of their pieces.
2. **The final gate.** Spawn `light` to run the end-of-run gate (`repository.md` § "Gates") and
   report, per red suite, the failing files and the first failing assertion of each. It never
   edits code. An obvious, scoped cause goes to an `implementer`; anything else is recorded under
   "End-of-run gate" and the run still closes.
3. **Measure the run** with the ledger's commands (`repository.md` § "Commands") and paste the
   summary under "Spend".
4. **Close**: commit the gates file and the plan, and tell the user what landed, what is parked,
   the decisions left to answer, the gates, the suite's state and the spend. Suggest
   `feature-archive` once the gates are cleared. Do not run it.

## Halt and surface

Only when: something destructive in production would be needed inside the run to continue; a
discovery raises the feature's cost far beyond what was approved (park what it touches, with the
real options, and halt only if it invalidates the run); parking has left nothing to land; a call
cannot be made reversibly and nothing independent of it is left; the user says stop.

## Keep your context small

A sub-agent's work never enters your context, only its last message. Insist on terse reports,
leave code reading to the reviewer, write decisions as you go, and stop referring to a lot's
findings once they are committed.
