---
name: bug-fixes
description: Diagnose a batch of reported bugs before they are planned. The user reports bugs conversationally; you stay at discussion altitude and spawn one diagnostician per bug (read-only on product code), each writing diagnostics/<bug-slug>.md with file:line evidence and the reproduction that fails today for the diagnosed reason, one a piece of the fix, declared with the stack's reproduction form. bug-fixes-plan then writes the plan in pieces. Use when the user arrives with a batch of bugs to triage, not for a single quick fix.
---

# bug-fixes

Run a diagnosis-only session for a batch of bug reports. It leaves a working set under
`specs/features/`: a diagnostic a bug, and for each confirmed bug a test a piece of its fix that
fails today for the diagnosed reason. `bug-fixes-plan` then writes the plan, in pieces, and
`feature-implement` delivers it a lot at a time. The diagnostics stand where a feature has a
spec: they say what is wrong, and they stay the record of each investigation. **Nothing is fixed
in this session.**

Keep the roles separate:

- **You (main agent)** own the conversation: intake, clarification, relaying findings, the user's
  decisions and what is confirmed. You do not read product code yourself: your context is
  reserved for the discussion across many bugs.
- **The `diagnostician` role** investigates one bug per sub-agent, and writes the diagnostic and
  its [reproductions](#the-reproduction). Product code is read-only for it.

What is this project's own is in `.agents/repository.md`: § "The stack" spells the reproduction
and the evidence calls, § "Diagnosis" says where reports come from, how evidence is read, which
test layers a reproduction may use and which repository drives a batch, and § "Sub-agents and
the ledger" how a spawn is labelled. Spawn each diagnostician unnamed, labelled
`<feature>--diag-<bug-slug>`, and resume one by the id its spawn returned.

If the batch holds one or two small bugs, say so and suggest diagnosing and fixing them directly,
with the discipline of `task-implement`, instead of opening a working set.

## Set up the working set

1. Create `specs/features/bug-fixes-<YYYY-MM>/`, with a numeric suffix if the name exists, or
   adopt a parked batch folder whose README asks for it, with `diagnostics/` beneath it. The
   folder's name is the feature every tag of the batch carries. Its `README.md` says the status
   and the batch's scope in a paragraph.
2. **Read the reference documents properly**: the constitution, the conventions, the testing page,
   the architecture hub and the owning pages, and `.agents/repository.md`. Not only to brief the
   diagnosticians: you must follow a diagnostic's reasoning, notice when a claimed cause
   contradicts an invariant or the documented architecture, and send the diagnostician back with
   the specific doubt instead of relaying a wrong diagnosis.
3. **A batch that crosses repositories has one working set**, in the repository that drives it
   (`repository.md` § "Diagnosis"): every diagnostic is there and names the repository that owns
   each change. Load the other one's constitution and the relevant architecture pages. The plan
   is then local to each repository (`specs/workflow-formats.md` § "A feature that changes two
   repositories"): a fix in the other one is planned there, by a session run there.

## Diagnose each report

For every bug that can be observed on its own:

1. **Capture the report faithfully**: the symptoms, where it was met (device, build, time), what
   was expected, and the user's hypothesis. Ask only when the report is unactionable as evidence
   (you cannot even name the surface); otherwise let the investigation answer it. Reports the
   product files itself enter here too, as `repository.md` § "Diagnosis" says.
2. **Spawn one diagnostician per bug**, in parallel where the reports are independent. Give it the
   report word for word, the path of its `diagnostics/<bug-slug>.md`, the feature its tags carry
   and the template below. Add only what is specific to the bug: a server you started for it, a
   rule the report's source puts on what it may read.
3. **Require of it**:
   - the behaviour traced through real code and tests, each material claim citing `path:line`;
   - the user's hypothesis tested, and said plainly when it is disproven;
   - every repository inspected when ownership is unclear;
   - the smallest correct fix named as **pieces**, each a statement a reviewer could approve
     alone, with no line of it written;
   - the [reproduction](#the-reproduction) written and run, its failure recorded;
   - what is flagged: an invariant of the constitution, a migration or a change of the saved
     shape, an order across repositories, a paid call, a validation no local run gives;
   - a terse return: the verdict (CONFIRMED / PLAUSIBLE / NOT A BUG, a confidence, the cause in a
     sentence), the pieces with their reproductions, and the forks that are the user's. The
     evidence stays in the diagnostic, never in your context.
4. **Check the verdict before relaying it**, against the architecture and the constitution.
   Challenge a finding that breaks a documented invariant, and let the diagnostician defend or
   revise it first. Then tell the user each verdict in a few sentences.
5. **Settle the forks with the user.** The diagnostician records each under `## Decisions`, dated;
   one you settled yourself is marked "taken at triage". A report shown to be expected behaviour
   is dropped: tell the user why, and keep its diagnostic as `NOT A BUG`, with no reproduction.

A feature-sized request in the batch takes the same flow: its diagnostic maps the current code and
what to reuse instead of a cause, and its forks are settled at triage, not left to the implementer.

## A cause that is only plausible

A `PLAUSIBLE` diagnosis is allowed when no local evidence can prove a cause that depends on a
device, a browser, data or an environment. Rank the hypotheses, and say which reading would tell
them apart, on which build: the plan makes it a gate, and nothing past it is built on a guess.

- **Instrument the sequence, not the discriminator.** The reading must let a reader reconstruct
  what happened: enough fields, in order, that arithmetic over them closes (a clock value on every
  event, not only on the one the leading hypothesis cares about). A reading built only to tell A
  from B is useless the moment the answer is C, and C is common: it is why the diagnosis was
  plausible.
- **What follows the reading has an exit.** Never write it as a closed choice over the ranked
  hypotheses: the reading may refute every one of them while looking clean, and then nothing ships
  and the diagnosis reopens.
- **A log is evidence only once its build is established**: the lines a known commit introduced,
  or their absence, and any build stamp. The obvious origin is often the wrong one.

## The reproduction

A confirmed bug has, for each piece of its fix, a test that asserts what should be and fails
today for the diagnosed reason. It is the evidence run, the fix's acceptance and the piece's whole
test: the fix makes it pass and edits none of its lines (`specs/workflow-formats.md` § "A bug").
It is shown to discriminate before the fix exists, which a test written after it never is.

- **Declared with the stack's reproduction form**, under the title
  `<feature>#<piece>: <the behaviour> [<rule>]` (`repository.md` § "The stack"). A run expects its
  failure, strictly, so the suite stays green while the bug stands and the fix cannot land without
  turning it.
- **One a piece.** A title carries one piece. When the fix is two pieces, each has its
  reproduction, failing for its own reason: one failure across two pieces cannot be turned by the
  first one's commit.
- **It observes everything, then asserts once, at its end.** A story stops where its test fails,
  and what it crossed before that is the bug's chain on the plan page. Assert one value of named
  observations, so that the failure reads without the test: "a stale delete confirmation: a raw
  500". Keep each observation short: a long one is cut in its middle.
- **It is one test, not one a case.** A bug that shows on several inputs is one test that reads
  them all: the page draws one run and one failure, and a parametrized reproduction is refused.
- **At the supported boundary** (a view, a use case, a hook, an endpoint, a browser), never inside
  a helper the fix may introduce, sized to what the diagnostic names: every affected class,
  example, panel or row.
- **By the cheapest layer of the testing page that meets the real failure**, through the
  supported entry point and with that layer's fixtures, and with fakes that fail the way the real
  dependency does: a test red only because a fake is harsher than production is no reproduction.
  `repository.md` § "Diagnosis" says which layers are open and with what rules, and which of them
  the tools run themselves; prefer one they run.
- **A test of its own**, beside the tests of the surface it crosses. An existing passing test is
  never turned into one: that would hide what it holds today.
- **Run it.** One that passes, or fails for another reason, is no reproduction. Observe from the
  test side: never edit product code, not even temporarily, and never prototype the fix in the
  working tree, where sibling diagnosticians run their tests.
- **A fork still open**: assert only what nobody disputes (no raw 500, no lost row), and say in the
  diagnostic how the assertion tightens once the fork is settled.
- **None** for a report that is expected behaviour, a cleanup with nothing to observe, a
  `PLAUSIBLE` cause, whose reading plays that part, or a failure only a device shows faithfully.
  Say why in the diagnostic.
- **A bug whose chain crosses a process** has one reproduction per process, each watching the
  value at the seam. A reproduction a browser runs is served by the test's own process, so that
  its story holds the server's calls; the tools leave it out of their own runs.
- **Where the stack has no reproduction form for the language the bug shows in**, reproduce it
  through a layer that has one. When none can meet the failure, say so in the diagnostic: the plan
  then holds a place and no chain.

## Diagnostic template

```markdown
# <Symptom>: <root-cause characterization>

- **Status:** CONFIRMED | PLAUSIBLE | NOT A BUG
- **Confidence:** high | medium | low — <basis>
- **Reported:** <the report, faithfully, and whether its hypothesis held; its source and id when the product filed it>

## Root cause
<The mechanism in one sentence, then the chain as numbered steps. Each step: `path:line` (with the
repository when the batch crosses one), what is seen there today (an expression and its value in
the reproduction's run), and what should be seen where the two differ.>

## Reproduction
- `<path>` › `<title>` — `<feature>#<piece>`, <layer>; fails on `<branch>@<commit>`:
  <the assertion's message, trimmed> | none — <reason>

## Fix approach
<The pieces, a line each: `#<piece>` — what it changes. Then the alternatives refused, and why.>

## Places that change
- `<path>` — <the change, with a line anchor where useful>, `#<piece>`

## Beyond the reproduction
- <A check the fix should also pass and the reproduction does not hold: a sweep of real data, a
  look on a device. The plan makes each a test or a gate for the user, or drops it.>

## Risks and side effects
- <Adjacent behaviour, and the trade-offs meant.>

## Flags
- <An invariant, an order across repositories, a migration or a saved shape, a paid call, a
  validation no local run gives, or none.>

## Decisions
- <A decision and its date, when there is one.>
```

The chain is what `bug-fixes-plan` writes into the code: a step on a line the fix changes becomes
that place's `planned` call, a step on a line it does not an evidence call, each with the value
watched and the one expected. So a step names a line of code, never a range.

## Close the batch

1. **Offer a smell sweep** over the surfaces several reports implicate: one read-only
   `diagnostician`, labelled `<feature>--smell-sweep`. Its `smell-sweep.md` ranks findings by risk
   and effort, marks what overlaps a diagnosed bug, and records code that looks wrong and is sound,
   so a later audit does not argue it again. Only a refactor the user approves is planned: a piece
   under no bug, with no reproduction, held by the existing suite.
2. **Tell the user now about any constraint on the order** the intake surfaced (a dependency, a
   shared file, a gate) and record it in the diagnostics concerned, so the plan inherits it.
3. **Verify** that every confirmed report has a diagnostic, and each its reproductions or a stated
   reason for none. Have a `light` sub-agent run the reproductions' files once more: each fails as
   its diagnostic records. One that passes goes back to its diagnostician.
4. **Commit the working set** when the user wants it final, as
   `[ADD] bug-fixes-<YYYY-MM>: diagnosed working set`, with the counts of diagnostics and of
   reproductions in the body.

Hand over to `bug-fixes-plan` in a fresh session. Use `feature-archive` once every lot has
shipped and what is durable has gone to the reference docs.

## Guardrails

- Fix nothing during this skill, an apparent one-liner included.
- Never let a diagnostic's body into your context: the file, and the terse return.
- Accept no root cause that cites no line, and do not keep a disproven hypothesis alive.
- Commit no reproduction that passes today, that fails for another reason than the diagnosed one,
  or that was made of an existing passing test.
- Prove nothing by a destructive operation: such a confirmation is a gate of the plan.
- One working set a batch, whatever the repositories it crosses.
