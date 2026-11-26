# Spec-driven development workflow

Five stages for a feature that ships: specify, plan, tasks, implement, archive. A person reviews
and approves between them. What is particular to this project (its rules, its commands, its
gates, how its stack spells the method's calls) is `.agents/repository.md`; the forms of every
file a stage writes are [`workflow-formats.md`](workflow-formats.md). This page says what each
stage is for, who approves what, and what never happens without a person.

## The idea

**The plan is not a page someone keeps: it is written into the code, and the pages are generated.**

- A selected flow through the product is a **narrative**: the code tells it, one `narrate` call
  per step, and a test crosses the steps in order. Its page is rendered from the run, so it cannot drift.
- A feature's plan is its **pieces**, each tagged at the places it changes: a `planned` call
  where a change lands, a test title with no body, a comment where no line runs. The plan page
  draws the narratives the change lands in, each change at the step it lands in, then a card a
  piece. A piece no narrative shows, in none yet or with no place in this repository, is put first.
  A place that is built stays on its flow: the clause approved, under what its step tells now.
- **A plan is local to the changes of its repository.** A feature that changes two has a plan
  in each, and the one that relies on a piece of the other points at it
  (`workflow-formats.md` § "A feature that changes two repositories").
- **The reviewer reads everything that is generated for them.** So each fact has one home, under
  a budget of words, and what is not worth reading is not written.
- **No edit of an approved plan is silent.** The approval is a committed file; whatever differs
  from it afterwards carries its reason, and the reviewer answers it.

## Narratives and test ownership

Narratives help developers navigate the code through a small, carefully curated set of meaningful
flows. Each answers one coherent question through a representative reference case. Keep only
variants that materially change the reader's understanding of that answer. Add a narrative only
when its value as a guide justifies another page to maintain and read. A feature requirement or
an additional code path alone does not justify a narrative, a step or a variant.

The spec's optional **Behavioral requirements** section records agreed feature outcomes that the
explanation leaves ambiguous and that hold independently of implementation choices. Possible
regression risks, unchanged existing guarantees and another component's responsibilities are not
new feature requirements; `workflow-formats.md` § "`spec.md`" gives the selection criteria. Each
rule has an appropriate existing or new test owner, or an explicit justified waiver; it does not
demand a new test by itself.
Use a narrative case when it helps explain the flow; otherwise use an ordinary test at the
appropriate level. Narrative tests remain real, asserted examples. A narrative crossing a branch
does not oblige it to own every assertion about that branch. Preserve necessary coverage when
moving a case out of a narrative.

Read the existing narratives a feature lands in before planning, and correct misleading steps
before relying on them. Assess whether an untold flow would benefit from a narrative; planning
can proceed with direct code links and ordinary tests when it would not. When a new narrative of
existing behaviour is chosen as planning context, tell it and have it read before relying on it.
A narrative takes the place of the prose that told its steps: that prose goes, and a link to the
narrative's page stands where it was. Prose about what no step tells stays.

A useful new flow can be declared as an intended narrative during planning, with its ordered steps
and change links visible before a reference run exists ([the declarations](workflow-formats.md#a-site)).

## Documentation ownership

Narratives explain execution flows and recurring implementation patterns through representative,
tested examples. Architecture pages explain system structure, responsibilities, ownership,
boundaries and consequential decisions across flows. Local semantics and rationale stay beside
the code they describe. Each fact has one authoritative home; other surfaces link to it.
Keep content lean: a feature does not automatically require another explanation or documentation
section. When a recurring kind of change needs a pattern to follow, consider a narrative and its
linked example. Make deliberate conventions and their reasons clear at the relevant steps.
Documentation generation and authoring flows can carry the doc scope label; this describes their
subject, without introducing another narrative kind or contributor category.

In a brownfield project, retain useful handwritten explanations until a narrative replaces them.
Then remove the overlapping prose and leave a link; retain structuring decisions the flow does not
express. Consolidate material as it is touched, without requiring a wholesale documentation rewrite.

## Scope

Features go through the five stages. A user's clear request to implement an already agreed change
is authorisation; no stage manufactures another approval.

These go directly to work: a bug fix that introduces no pattern and touches no security boundary,
a local refactor with no change to an external interface, an investigation. A **bug batch** uses
`bug-fixes`, then `bug-fixes-plan`: its diagnostics stand where the spec does, its plan is written
in pieces with a section a bug and its delivery, it has no tasks stage, and stages 4 and 5 apply.

Nothing here authorises a deployment, a publication, a destructive operation or a paid external
action beyond what the user granted.

## 1. Specify — `spec-specify`

Writes `spec.md`: the problem, the change, any additional behavioral requirements, what is left
out. Screen journeys are optional, enabled by the repository's `commands.journeys` configuration,
not by an assumption that every product has a UI. Where configured, criteria best demonstrated
visually are declared in journey tests: changed screens with a mockup, and cases to write. Those
criteria are not repeated in the spec. Without journeys, the spec stands alone, including any
visible changes in its prose; no browser run or captures are required. Local commands and
verification surfaces belong in repository settings. The scope is shaped against the project's
priorities first, and split when it has grown. No product code.

**Gate:** the user approves the spec. Planning starts in a fresh session, from the committed spec.

## 2. Plan — `spec-plan`

Reads the map, then writes the pieces: the sites in the code, the test titles that own the rules
in any appropriate tier, the narrative and server cases the change needs, and `plan.md` (a
statement and a reason a piece, the decisions across pieces, the rules no test holds). Nothing
the product does changes.

How a plan is reviewed:

- The reviewer reads the plan page top down: the overview of pieces outside narratives, the
  narratives, then the detailed cards in `plan.md` section order. That order introduces concepts
  before pieces rely on them; a brief overview can establish context first. They ask in the
  session that holds the plan; each answer is an edit in place and a commit.
- A simplification of the underlying code found on the way is made in another session, and the
  plan is then rewritten against it.
- **The plan is approved when no question is left and the reviewer says so.** The session then
  runs the approval command, and the file it writes is committed as the approval. An agent never
  runs it on its own judgement.

**Gate:** the approval.

## 3. Tasks — `spec-tasks`

Prepares the delivery, in a fresh session. It cuts the pieces into **lots** (what one implementer
delivers and one reviewer reads, a commit a piece), each of which compiles and stays green alone.
It chooses implementation order in the delivery's lots and pieces; the piece sections retain
their authored review order.
It plans the additional unit coverage of each lot: the titles to write, and the existing tests
that change or go, each removal naming what holds the behaviour instead. Rule owners are already
chosen during planning. Where grounding the plan shows a gap it edits the plan in place, each
edit under a `Changed:` paragraph.

There is no task list and no hand-written brief: the map prints a lot's brief from the plan.

**Gate:** the reviewer reads what moved on the delivery page, answers each edit there or in the
session, and approves again.

## 4. Implement and review — `feature-implement`

A supervisor delivers the lots one after another, in one run. It stops after one lot, for the
reviewer, only when the user asks for that. For each lot:

1. An implementer builds the lot (`task-implement`): each planned place becomes code, with a
   `built` call left where it stood, each planned test a test under its title, a commit a piece
   whose message names it.
2. The lot check reads the commits against the approved plan: a test nobody planned, a planned
   one not written, a deletion or a file the plan does not name. Each is settled.
3. A reviewer reads the lot's commits (`task-review`), setting its own depth from the diff, and
   is asked for what no tool holds: whether the code at each place does what its clause says.
   The supervisor triages its findings and the reviewer applies the approved fixes.
4. **A decision is written into the plan and nowhere else**: a `Changed:` for what changes a line
   of it, a `Note:` for a choice the next lot stands on. No callout, no judgement file, no list
   of routine fixes.
5. The reviewer of the plan answers the decisions first, then reads the code, both on the
   delivery page, which lists each built piece with its places and its commits; the commits of a
   piece open as the one diff they come to. The approval that follows is theirs.

A lot that cannot land is parked and the independent lots go on. What only the user can do (a
check on a device, a production operation, a reading that decides later work) goes to the
feature's **gates file**, never into a pause. Once the last lot is reviewed, a **global review**
reads the whole delivery for the seams between lots, the full gate runs, and the run's cost is
measured.

The quality gates (what a piece's commit, a lot and a run must pass) are the project's:
`.agents/repository.md` § "Gates". A review's depth never waives one. If an unrelated bug is
found, it is fixed in a commit of its own or reported; never papered over.

## 5. Archive — `feature-archive`

Invoked explicitly, once the feature is final. The archive gate holds while anything planned
remains or a rule has no owner.

**Most of a plan goes with its folder.** A fact is kept in the first home that can hold it: a
test or the code itself; a narrative's sentence, for what happens in order; the reason of one
object, beside its declaration; and a reference doc only for what none of those can hold: a
decision across several flows, a constraint no step executes, a rejected alternative. That last
kind is written only when it is load-bearing: someone reading the code would be tempted to undo
it, and nothing would stop them. Reference prose that tells the steps of a narrative the feature
landed in goes, a link to the narrative standing in its place.

Unfinished work is parked where it will be picked up. Last, one command strips the feature's
marks off the code (the `built` calls, the tags of the test titles, the planned screens) and the
feature folder is deleted: until then the plan page still shows the delivery. Git history is the
archive: no per-feature summary is ever written.

**Gate:** the user confirms the deletion.

## Sessions and roles

- **A fresh session for each of specify, plan, tasks, and for each implementation run.** A
  decision that exists only in a conversation is a gap to resolve, not something to infer.
- The roles are `implementer`, `implementer-easy`, `implementer-hard`, `reviewer`,
  `reviewer-global` and `light`, with `diagnostician` for a bug batch.
  A role's text is `.agents/roles/<role>.md`. Its model and effort are pinned in the runtime's
  agent definition and named nowhere else: skills and documents name roles.
- Stateful test suites and mutable application databases are never shared between parallel
  agents.

## Maintenance

The skills are under `.agents/skills/` and the roles under `.agents/roles/`; a runtime's own
folder holds adapters that point at them. They, this page and the format reference are written
for any project and name none: a project's specifics go to its `.agents/repository.md`. A change
to the constitution uses `update-constitution`, in a commit of its own.
