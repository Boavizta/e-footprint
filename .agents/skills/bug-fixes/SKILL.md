---
name: bug-fixes
description: Diagnose a batch of reported bugs before they are planned. Writes one evidence-backed diagnostic per report and the reproduction that fails today for the diagnosed reason, declared with the stack's reproduction form. Use for a conversational batch of bugs, not for a single quick fix. bug-fixes-plan then writes the plan.
---

# bug-fixes

Run a diagnosis-only session for a batch of bug reports. It leaves a working set under
`specs/features/`: a diagnostic a bug, and for each confirmed bug a test that fails today for the
diagnosed reason. `bug-fixes-plan` then writes the plan, in pieces, and `feature-implement`
delivers it a lot at a time. The diagnostics stand where a feature has a spec: they say what is
wrong, and they stay the record of each investigation.

Keep the roles separate:

- The main agent owns intake, the user's decisions and what is confirmed. Read the reference docs
  needed to assess findings, and keep your context by delegating the investigation of the code.
- The `diagnostician` role investigates one bug per sub-agent. It edits only its diagnostic and
  its reproductions; product code is read-only.

If the batch holds one or two small bugs, suggest diagnosing and fixing them directly, with the
discipline of `task-implement`, instead of opening a working set.

## Choose the driving repository

- Bugs of the library alone are driven from `e-footprint`.
- Interface bugs and bugs that cross the two are driven from `e-footprint-interface`.
- A batch has one working set, in the driving repository: every diagnostic is there, and names the
  repository that owns each change. The plan is then local to each repository
  (`specs/workflow-formats.md` § "A feature that changes two repositories"): a fix in the other
  one is planned there, by a session run there.

## Set up the working set

1. Create `specs/features/bug-fixes-<YYYY-MM>/`, with a numeric suffix if the name exists, and
   `diagnostics/` beneath it. The folder's name is the feature every tag of the batch carries.
2. Load the driving repository's `specs/constitution.md`, `specs/conventions.md`,
   `specs/testing.md` and `specs/architecture/index.html`, then the owning pages. Read
   `.agents/repository.md` in each affected repository: § "The stack" spells the reproduction.
3. For a report that crosses repositories, load the other one's constitution and the relevant
   architecture pages. The library is the truth of modeling.

## Diagnose each report

For every bug that can be observed on its own:

1. Capture the report faithfully: the symptoms, where it was met, what was expected, and the
   user's hypothesis. Ask only what is needed to find the surface.
2. Spawn one `diagnostician` per bug, in parallel where the reports are independent. Give it the
   report word for word, the path of its `diagnostics/<bug-slug>.md`, and the template below.
3. Require of it:
   - the behaviour traced through real code and tests, each material claim citing
     `repository/path:line`;
   - the user's hypothesis tested, and said plainly when it is disproven;
   - both repositories inspected when ownership is unclear;
   - the smallest correct fix named as **pieces**, each a statement a reviewer could approve
     alone, with no line of it written;
   - the [reproduction](#the-reproduction) written and run, its failure recorded;
   - what is flagged: an invariant of the constitution, a migration or a change of the saved
     shape, an order across repositories, a validation no local run gives;
   - a terse verdict, the fix direction and the forks that are the user's. The evidence stays in
     the diagnostic.
4. Check the verdict against the architecture and the constitution before relaying it. Challenge
   a finding that breaks a documented invariant or puts modeling logic in the interface.
5. Settle the real product forks with the user. The diagnostician records each under
   `## Decisions`, dated.
6. A report shown to be expected behaviour is dropped: tell the user why, and keep its diagnostic
   as `NOT A BUG`.

A `PLAUSIBLE` diagnosis is allowed when no local evidence can prove a cause that depends on a
device, a browser, data or an environment. Rank the hypotheses, and say which reading would tell
them apart, on which build: the plan makes it a gate, and nothing past it is built on a guess.

## The reproduction

A confirmed bug has a test that asserts what should be and fails today for the diagnosed reason.
It is the evidence run, the fix's acceptance, and the piece's whole test: the fix makes it pass
and edits none of its lines (`specs/workflow-formats.md` § "A bug").

- **Declared with the stack's reproduction form**, under the title
  `<feature>#<piece>: <the behaviour> [<rule>]`: `repository.md` § "The stack" spells it. A run
  expects its failure, strictly, so the suite stays green while the bug stands and the fix cannot
  land without turning it.
- **One a piece.** A title carries one piece. When the fix is two pieces, each has its
  reproduction, failing for its own reason: one failure across two pieces cannot be turned by the
  first one's commit.
- **It observes everything, then asserts once, at its end.** A story stops where its test fails,
  and what it crossed before that is the bug's chain on the plan page. Assert one value of named
  observations, so that the failure reads without the test: "a stale delete confirmation: a raw
  500".
- **At the supported boundary** (a view, a use case, a browser), by the cheapest tier of
  `specs/testing.md` that meets the real failure, with the repository's fixtures. Never inside a
  helper the fix may introduce. Size it to what the diagnostic names: every affected class,
  example or panel.
- **A test of its own**, beside the tests of the surface it crosses. An existing passing test is
  never turned into one: that would hide what it holds today.
- **Run it.** One that passes, or fails for another reason, is no reproduction. Where a scratch
  prototype of the fix exists, check that the test tells the two apart, and do not commit the
  prototype.
- **A fork still open**: assert only what nobody disputes (no raw 500, the object is gone), and
  say in the diagnostic how the assertion tightens once the fork is settled.
- **None** for a report that is expected behaviour, for a cleanup with nothing to observe, and for
  a `PLAUSIBLE` cause, whose reading plays that part. Say why in the diagnostic.
- **A bug whose chain crosses a process** has one reproduction per process, each watching the
  value at the seam. A reproduction a browser runs is served by the test's own process, so that
  its story holds the server's calls; the tools leave it out of their own runs.
- **Where the stack has no reproduction form for the language the bug shows in**
  (`repository.md` § "The stack" says what it reads), reproduce it through a tier that has one.
  When none can meet the failure, say so in the diagnostic: the plan then holds a place and no
  chain.

## Diagnostic template

```markdown
# <Symptom>: <root-cause characterization>

- **Status:** CONFIRMED | PLAUSIBLE | NOT A BUG
- **Confidence:** high | medium | low — <basis>
- **Reported:** <the report, faithfully, and whether its hypothesis held>

## Root cause
<The mechanism in one sentence, then the chain as numbered steps. Each step: `repository/path:line`,
what is seen there today (an expression and its value in the reproduction's run), and what should
be seen where the two differ.>

## Reproduction
- `<repository/path>::<test>` — `<feature>#<piece>`, <tier>; fails on `<branch>@<commit>`:
  <the assertion's message, trimmed> | none — <reason>

## Fix approach
<The pieces, a line each: `#<piece>` — what it changes. Then the alternatives refused, and why.>

## Places that change
- `<repository/path>` — <the change, with a line anchor where useful>, `#<piece>`

## Beyond the reproduction
- <A check the fix should also pass and the reproduction does not hold: a sweep of the shipped
  examples, a look on a device. The plan makes each a test or a gate for the user, or drops it.>

## Risks and side effects
- <Adjacent behaviour, and the trade-offs meant.>

## Flags
- <An invariant, an order across repositories, a migration or a saved shape, a validation no local
  run gives, or none.>

## Decisions
- <A decision and its date, when there is one.>
```

The chain is what `bug-fixes-plan` writes into the code: a step on a line the fix changes becomes
that place's `planned` call, a step on a line it does not an evidence call, each with the value
watched and the one expected. So a step names a line of code, never a range.

## Close the batch

1. Offer a read-only smell sweep over the surfaces several reports implicate. Its
   `smell-sweep.md` ranks findings by risk and effort, marks what overlaps a diagnosed bug, and
   records code that looks wrong and is sound. Only a refactor the user approves is planned: a
   piece under no bug, with no reproduction, held by the existing suite.
2. Verify that every confirmed report has a diagnostic, and that each has its reproductions or a
   stated reason for none. Run the reproductions' files once more: each fails as its diagnostic
   records.
3. Commit the working set when the user wants it final, as
   `[ADD] bug-fixes-<YYYY-MM>: diagnosed working set`, with the counts of diagnostics and of
   reproductions in the body.

Hand over to `bug-fixes-plan` in a fresh session. Use `feature-archive` once every lot has
shipped and what is durable has gone to the reference docs.

## Guardrails

- Fix nothing during this skill, an apparent one-liner included.
- Accept no root cause that cites no line, and do not keep a disproven hypothesis alive.
- Commit no reproduction that passes today, that fails for another reason than the diagnosed
  one, or that was made of an existing passing test.
- Prove nothing by a destructive operation: such a confirmation is a gate of the plan.
- One working set a batch, whatever the repositories it crosses.

Roles, telemetry and the sorting of gates: `specs/agent-tooling.md` and `feature-implement`. A
missing piece of evidence stays a gate; it is never guessed.
