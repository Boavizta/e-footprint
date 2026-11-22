# The formats of a feature's working set

What is written where while a feature goes from a spec to shipped code, and what the tools hold
each form to. The stages are in [`workflow.md`](workflow.md); the skills say what to do at each
and point here for the form. How a stack spells a call or a test, and the commands, are the
repository's (`.agents/repository.md`).

## The words

- A **narrative** is a flow the code tells itself: one `narrate` call per **step**, and a test that
  crosses the steps in order. An `event` call is a **cause**: something done to the system.
- A **piece** is one statement about a feature, with its reason, its changes and its tests. It is
  atomic to read and to approve, not to ship. Its name is `<feature>#<slug>`, both kebab-case.
- A **site** is one place tagged with a piece. Several sites share a piece; nothing is numbered.
- A **rule** is a behaviour of the spec that no screen shows. One test owns it, or a **waiver**
  says why none does.
- A **lot** is what one implementer delivers and one reviewer reads: a few pieces, a commit each.
- A **unit** is one thing the reviewer approves: a piece, a decision across pieces, the waivers,
  the delivery, the journey cases, a narrative's steps.

"Step" is never a part of a plan, and "run" is a session of `feature-implement`.

## What the folder holds

`specs/features/<feature>/`, deleted at the archive:

| File | Written by | Holds |
|---|---|---|
| `spec.md` | specify | The intent, and the rules no screen shows |
| Mockup fragments | specify | One per decision on screen, where the repository draws journeys |
| `plan-draft.md` | specify, when the discussion held any | The technical decisions already made, a line each. The plan stage turns them into pieces and deletes the file |
| `plan.md` | plan, then every later stage, in place | A section a piece, the decisions across pieces, the waivers, the delivery |
| `plan.approved.json` | the approval command, on the reviewer's word | The plan as it was approved |
| A proposed migration | plan | Where the stack has one: the file carries the piece's tag in a comment |
| `plan-feedback.json` | the served pages | The reviewer's answers. Ignored by git |
| `gates.md`, or `run-<x>-gates.md` | implement | What only the user can do after a run |

The rest of a feature is in the code and the tests: the sites, the planned tests, the planned
screens and their cases. The pages (the spec, the plan, the delivery) are generated from all of
it and never committed.

## `spec.md`

A title, a lead, then sections of paragraphs and `- ` lists, nothing else. It states the feature
as it is agreed now and is edited in place: no dated note, no record of a decision.

- **Problem**, then **The change**, in the user's terms. No file, no function, no type.
- **Rules no screen shows**: one item a rule, opening with its bold slug.
  `- **free-by-default** An order is not wrapped unless the buyer asks.`
  A rule is a behaviour a test can hold. A constraint on the implementation is worded as what the
  user would observe, or the plan will waive it.
- **Not doing**: what was considered and left out.

Where the repository draws journeys, what changes on screen is not described here. It is declared
in the journey tests: a **planned screen** names the feature and a mockup fragment, and each
criterion on a screen is a **case to write**, a title tagged with the feature and the screen. A
case is a screen, or a state of one, worth seeing; a criterion that is logic is a rule.

## A site

One of three, each carrying `<feature>#<slug>`:

- **A `planned` call**, on code that runs: on existing code where a change lands, its removing
  form in a function that goes, or as the only body of a **shell**, a new function with its real
  signature that fails loudly if reached. Its sentence is one clause saying what changes at this
  place: no reason, no list of cases.
- **A planned test**: a test declared with no body, titled `<feature>#<slug>: <title>`. The title
  ends with `[<rule-slug>]` when the test owns a rule. Its tier is where its file stands.
- **A comment opening `@planned <feature>#<slug>`**, where no line runs: a type, a schema, a
  migration, a doc made stale. `@planned.remove <feature>#<slug>` says that what stands under the
  comment goes, and names what holds it instead. The comment is in the file's own syntax; leave a
  blank line before an unrelated comment.

On code that runs, a site is a call, never a comment: no test crosses a comment. A new function
is named, in backticks, by the clause of the site that will call it; a shell no clause names is
drawn on no flow and fails the check.

An existing test that changes carries an `@planned` comment. One a planned case now holds carries
an `@planned.remove` comment naming the holder, and says "planned" when the holder is not written
yet. An existing case extended is a planned test beside it, under a comment saying which case it
is and that no case is added.

## `plan.md`

A title, a lead, then:

- **One `## #slug` section per piece**: its statement in the first paragraph, then its reason
  and what was refused.
- **Any other title** is a decision across pieces, which names the pieces it concerns as `#slug`.
- **`## Rules no test holds`**: the waivers, `- **the-rule** why no test holds it`, for a rule
  that is true by the shape of the code.
- **`## Planned elsewhere`**: the pointers, `- **the-repository** #the-piece — what this plan
  relies on`, for a feature that changes two repositories. Below.
- **`## Delivery`**: the lots, below.

Three paragraphs have a prefix:

| Prefix | Is | Written when |
|---|---|---|
| `To confirm: **the question.** the alternative` | A question, one per piece at most | Only the reviewer can decide. Answered, it becomes a statement and the paragraph goes |
| `Changed: **what moved.** why → its lines` | One edit of an approved plan | A unit no longer reads as approved |
| `Note: **the point.** what follows from it` | Something to know, asking no answer | A piece was built with a choice no line of the plan says and a later lot stands on |

After ` → `, a `Changed:` names the lines of the difference it comes to, parted by `;`: a kind
(`code`, `test`, `statement`, `reason`, `text`) and a fragment the line holds, in double quotes
when it has a space. `Changed: **Its narrative case leaves for #wrap-row.** It reads the row the
other piece adds → test "a wrapped order"`. A section with one such paragraph needs no claim.

Each fact has one home, and each home a budget in words, which the check enforces:

| Fact | Home | Words |
|---|---|---|
| What changes at a place | The site's clause | 25 |
| The behaviour, and its case | The test title | 20 |
| What a piece changes, as a whole | The first paragraph of its section | 30 |
| Why, and what was refused | The rest of the section | 60 |
| A point to confirm, a waiver | Its paragraph, its item | 60 |
| An edit, a note, a lot's reason | Its paragraph, its item | 40 |

A word is a run of characters between spaces. The tag, the `[rule]` suffix, the prefixes and a
`Changed:` paragraph's claims are not counted.

## A feature that changes two repositories

**A plan is local to the changes of its repository.** Each repository holds a plan of the feature,
under the same feature name, for what changes there: its pieces have their places, their tests,
their commits and their approval where the code is. The spec is written once, in the repository
that drives the feature.

Where one plan relies on a piece of the other, it says so with a pointer, an item of
`## Planned elsewhere`: the repository in bold, the piece's tag, then what this plan relies on and
which of its pieces stand on it, in 40 words at most.

- A pointer is no piece: it has no place, no test and no commit here, and no lot delivers it. A
  section names it as `#slug`; a lot says in its reason what it waits for.
- The plan page puts the pointers first, each with the statement its own plan gives the piece
  and whether that plan is approved. They are read from the other checkout's files, where the
  configuration names it (`repositories`); nothing of the other repository is run.
- The check fails on a pointer whose repository holds no such piece, and on a tag that is both
  a pointer and a piece. Where no checkout is known it says so and checks nothing.
- The approval holds the pointers: one that moves since is listed, and carries its own reason.

A narrative never crosses a repository: each project's calls are its own, and a test run
collects its own alone (`comprehension_harness/README.md` § "The Python stack").

## The approval, and what moved since

`plan.approved.json` is written by the approval command and by nothing else. It is committed: it
is the approval. It holds the plan a unit at a time, with no line number. The command refuses
while a `To confirm:` stands, and takes the `Changed:` paragraphs off `plan.md`.

From then on the check lists every unit that is not as approved, and fails:

- a piece that gained a line, or lost one of its statement, its reason or its tests, and a
  decision that is new or reads differently, while its section holds no `Changed:`;
- a `Changed:` that stands on no difference.

What asks nothing:

- **A line that moved word for word** from one piece to another. A line reworded on the way is a
  loss and a gain, each with its reason: so a line that moves keeps its words.
- **The tasks stage's own output**, until a delivery is approved: the delivery, the unit-tier
  titles and the comments on unit tests.
- **A site that became code**, once the approval holds a delivery: the piece keeps its line, as
  approved, and reads as built.

The reviewer answers on the served pages: under each edit and each question, approve, or say what
should change. A question is answered where it is stated, on the plan page and the delivery page,
from the first draft on: it needs no approval to have moved from. A plan never approved is approved
from its page too. The answers are read with the map's `feedback` verb.

## The delivery

`## Delivery` is a list and nothing else. An item is a lot:

`- **the-lot** (hard) #piece #piece @screen — why these together, and why here`

The slug; the difficulty when it is not `standard`; the pieces in commit order; the screens whose
journey cases the lot writes last; the reason. Every piece, and every screen with a case to
write, is in one lot. A lot's state is not written: it is delivered when its pieces hold no site
and no planned test, and its screens no case.

There is no task list and no hand-written brief. The map's `brief <feature>/<lot>` prints what an
implementer is handed.

## Commits, and the lot check

A commit delivers a piece when its message holds the line `Piece: <feature>#<slug>`: a piece's
commit and a fix of it name one; a commit that needs two pieces to hold names both; a lot's
closing commit names every piece whose steps it tells. A commit of the branch that names none is
other work.

The check reads the commits made since the approval against the approved plan, and fails until
each of these is settled:

- a test added under no planned title. It takes the piece's tag and a `Changed:`, or it goes;
- a test deleted with no `@planned.remove` on it, and a file of the product's code no place of
  the plan names;
- a place the approval held, taken off with nothing written in its file;
- a delivered lot one of whose pieces no commit names.

Each is a decision: a `Changed:` in the piece's section, in words the reviewer can read without
the code.

## Implementing a piece

- Each `planned` call becomes code, and each comment goes.
- Each planned test becomes a test under the same title, tag and `[rule]` kept until the archive.
- **A `planned` call does not become a `narrate` by rule.** A sentence the code makes false is
  corrected in the piece's commit. New and removed steps are written in one pass, the lot's last
  commit.

The archive gate holds while a site, a planned test or a case to write remains, and while a rule
has neither one owner nor a confirmed waiver. The archive then takes the tags off the titles.

## A `narrate` sentence

1. **A step tells its own line**: what happens at the call, not what ran before it or what
   another step says.
2. **Say what the code cannot**: the rule, and in a clause the reason a reader needs so as not to
   simplify it back into a bug.
3. **Never quote an expression.** Backticks name a declared symbol, which the page links; values
   are the watch's.
4. **A branch belongs to the test that crosses it.** The sentence tells the path its site is on.
5. **Sixty words, one bold at most, an opening clause that stands alone.** The bold is the rule
   the step enacts. The opening clause is what the plan page prints for the step.

A step lives in a named function, one call a line. A user's action calls `event` at its handler;
a cause a test simulates calls it in the test. No prose names a step by its number: it moves.

## The earlier form

A bug batch still writes `tasks.md`, diagnostics and a `plan.html` with its callouts (the
`bug-fixes` and `bug-fixes-plan` skills). So does a feature planned before pieces, until it is
ported.
