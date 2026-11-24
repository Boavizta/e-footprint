# The formats of a feature's working set

What is written where while a feature goes from a spec to shipped code, and what the tools hold
each form to. The stages are in [`workflow.md`](workflow.md); the skills say what to do at each
and point here for the form. How a stack spells a call or a test, and the commands, are the
repository's (`.agents/repository.md`).

## The words

- A **narrative** is what the code does for one action on the product, told by the code itself:
  one `narrate` call per **step**, and a test that crosses the steps in order. A narrative the
  code does not tell yet is **missing**. An `event` call is a **cause**: something done to the
  system.
- A **piece** is one statement about a feature, with its reason, its changes and its tests. It is
  atomic to read and to approve, not to ship. Its name is `<feature>#<slug>`, both kebab-case.
- A **site** is one place tagged with a piece. Several sites share a piece; nothing is numbered.
- A **rule** is a behaviour of the spec that no screen shows. One test owns it, or a **waiver**
  says why none does.
- A **lot** is what one implementer delivers and one reviewer reads: a few pieces, a commit each.
- A **bug** is what is wrong for whoever meets it, with the pieces that fix it: one, or several
  when the fix is several decisions.
- A **reproduction** is a written test that fails today, for the bug its piece fixes. **Evidence**
  is a place the bug shows, with the values a reproduction saw there.
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
| A proposed change of the database | plan | Where the stack has one: `.sql` files that state what the database becomes, a piece each, the piece's tag in a comment. They hold what changes the state and nothing else: no header, no change a reviewer has to see through. Read in name order, each is diffed against the state the earlier ones leave, and its card draws that diff, which is what the reviewer reads. They are no migrations: the implementer writes those around them. A file two pieces change carries a tag each, and both cards draw its whole diff |
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
  place: no reason, no list of cases. **A place that becomes code names itself**: its tag is
  `<feature>#<slug>:<place>`, the place a short kebab-case name of its own within the piece, for
  what changes there (`first-cut`, not `site-2`). A function that goes and a place a bug shows
  take none: nothing stands for them once the piece is built. The id is no line of the plan: the
  approval keeps it beside the place's line and never compares it, so naming a place asks no
  `Changed:`, but an id written or changed after an approval is approved again before its place
  is built.
- **A planned test**: a test declared with no body, titled `<feature>#<slug>: <title>`. The title
  ends with `[<rule-slug>]` when the test owns a rule. Its tier is where its file stands.
- **A comment opening `@planned <feature>#<slug>`**, where no line runs: a type, a schema, a
  migration, a doc made stale. `@planned.remove <feature>#<slug>` says that what stands under the
  comment goes, and names what holds it instead. The comment is in the file's own syntax. Its text
  runs over the comment lines directly under it, and all of it counts in the clause's budget: leave
  a blank line before any comment that was there already, the one the tag is about included.

On code that runs, a site is a call, never a comment: no test crosses a comment. A new function
is named, in backticks, by the clause of the site that will call it; a shell no clause names is
drawn in no narrative and fails the check. An entry point that nothing in the repository calls is
named by the title of a planned test that calls it, as the test stands for its caller.

An existing test that changes carries an `@planned` comment. One a planned case now holds carries
an `@planned.remove` comment naming the holder, and says "planned" when the holder is not written
yet. An existing case extended is a planned test beside it, under a comment saying which case it
is and that no case is added.

## A bug

A bug is a section of `plan.md`, `## Bug: <what is wrong>`: its title and its paragraphs say what
whoever meets it sees, and where it was diagnosed. The pieces whose sections stand under it, up to
the next bug, fix it. The page is then read a bug at a time: what is wrong, then its pieces, in
the order of the file. The cause is no part of the section: it is its pieces', and their chains'.

A plan of bugs has no tasks stage. Its reproductions are its unit tests, written and failing,
and its diagnosis is its grounding: what is left of that stage is the lots, which the plan stage
writes itself, as `## Delivery`. One approval holds the plan and its delivery.

A piece that fixes a bug says, beside what changes, what is wrong today. Two forms carry it, and
the plan page draws them as one chain under the piece: each reproduction, the places it crossed
in run order with the values it saw at each, then how it failed.

- **A reproduction** is declared in place of a planned test, under the same kind of title. It is
  written, it asserts what should be, and a run expects its failure, strictly. It observes
  everything it has to and asserts once, at its end: a story stops where its test fails. It is
  one test, which reads its cases itself: one run a case at a time is refused. A bug whose chain
  crosses a process has one reproduction per process, joined by the piece.
  **The approval holds it as written.** The fix makes it pass and changes its declaration, not
  its lines: one edited since, to pass or to assert more, is a line of the piece's difference
  and takes a `Changed:` (`→ test "<its title>"`).
- **Evidence** is a call on a line the bug shows at, with a watch: what is seen there today. It
  marks no change, so it stands where the cause is even when the fix is elsewhere.
- **`expect`**, on evidence or on a `planned` call, gives the value a key of the watch should
  have. The page sets it against what the reproduction saw, in red where it differs. It is said
  once for the place, or computed at each crossing where the right value depends on it: a line
  crossed for every row, each with its own.
- **`distinct`**, on the same calls, names keys of the watch that each crossing should see a value
  of its own for. It is for a bug no crossing shows alone: one value written at several, as an id
  three rows share. The page draws those crossings together, the shared value once and in red,
  then what else each saw; the others are counted, and folded.
- **Watch what is wrong, not what led to it.** "Should be" reads as a claim about the watched
  value: a value that is right and only reaches the wrong branch is context, with no `expect`.

The render and the check run the plans' reproductions first, whole files, so the page shows what
they see now and not what the last run happened to leave: the served pages rerun them at each
save, those the unit command runs. A reproduction a browser runs is left out, and so is one under
a folder the configuration gives no command (`commands.testsUnder`); its page says why it has no
run. A run under the debugger writes no story.

Under the chain, the piece lists what the chain does not show: the places no reproduction
crosses, and the tests that are no reproduction.

**The chain outlives the fix.** Built, a piece has no evidence left and its reproductions pass:
no run tells the bug again. So the approval freezes each reproduction's chain as it stands, and
the pages draw it under the built piece, beside the test that now passes: what was approved as
wrong, then the code that fixed it. A bug reads "fixed" once every piece under it is built.

The check fails on evidence in a piece with no reproduction, on a place whose reproductions saw
only what it expects, or a value of its own at each crossing where it names distinct keys (the
bug does not show there), and when the reproductions do not run as expected: one that passes
fails its run. The piece is built when its evidence is gone and its
reproductions are declared as written tests; until then its lot is not delivered and the archive
gate holds.

## `plan.md`

A title, a lead, then:

- **One `## #slug` section per piece**: its statement in the first paragraph, then its reason
  and what was refused.
- **A `## Bug: <what is wrong>` section**, in a plan that fixes bugs: the sections of the pieces
  that fix it follow it. A piece of no bug stands above the first. A bug with no piece under it
  fails the check. It is approved as a unit, as a decision is.
- **Any other title** is a decision across pieces, which names the pieces it concerns as `#slug`.
- **`## Rules no test holds`**: the waivers, `- **the-rule** why no test holds it`, for a rule
  that is true by the shape of the code.
- **`## Planned elsewhere`**: the pointers, `- **the-repository** #the-piece — what this plan
  relies on`, for a feature that changes two repositories. Below.
- **`## Delivery`**: the lots, below.

Three paragraphs have a prefix:

| Prefix | Is | Written when |
|---|---|---|
| `To confirm: **the proposal.** the alternative → its commits` | A point to decide, one per piece at most: the proposal stated as the plan would state it | Only the reviewer can decide. Answered as proposed on the page, the approval command writes the proposal in; another answer is the agent's to write in. Either way the paragraph goes |
| `Changed: **what moved.** why → its lines; its commits` | One edit of an approved plan | A unit no longer reads as approved |
| `Note: **the point.** what follows from it` | Something to know, asking no answer | A piece was built with a choice no line of the plan says and a later lot stands on |

After ` → `, a `Changed:` names the lines of the difference it comes to, parted by `;`: a kind
(`code`, `test`, `statement`, `reason`, `text`, `unbuilt`) and a fragment the line holds, in double quotes
when it has a space. `Changed: **Its narrative case leaves for #wrap-row.** It reads the row the
other piece adds → test "a wrapped order"`. A section with one such paragraph needs no claim.

**A paragraph names the commits that did what it says**: `commit` and seven digits of the hash
or more, after the same ` → `: `→ test "a wrapped order"; commit 1a2b3c4d`. A `To confirm:`
names commits the same way, and no line: what was built the proposed way. The pages list under the paragraph what each
commit changed; its hash opens the commit in the editor, every file in one diff
(`tools/vscode-plan-review-links`, the `commit` route). The commit is named whatever piece its
message names: a fix is often a commit of another piece. The check fails a hash that no commit
of the feature has, or that two open with.

**A claim takes back a built place.** Once a place is code, nothing in the source marks it: the
plan alone can say that the code does not do what its clause said, because a review undid it or
because it was never written beside places that were. An `unbuilt` claim names such a place by a
fragment of its line: `→ unbuilt get_calculus_graph`. The place is then a line the piece lost,
drawn "taken back" under its edit, and the next approval no longer holds it. A claim that names
no built place fails the check. The check asks for the paragraph where nothing was written at the
place (§ "Commits, and the lot check"); where something was, and does not do what the clause
says, only a reading of the code tells that one is owed.

Each fact has one home, and each home a budget in words, which the check enforces:

| Fact | Home | Words |
|---|---|---|
| What changes at a place | The site's clause | 25 |
| The behaviour, and its case | The test title | 20 |
| What a piece changes, as a whole | The first paragraph of its section | 30 |
| Why, and what was refused | The rest of the section | 60 |
| A point to confirm, a waiver | Its paragraph, its item | 60 |
| What is wrong, for whoever meets a bug | The bug's section | 60 |
| An edit, a note, a lot's reason | Its paragraph, its item | 40 |

A word is a run of characters between spaces. The tag, the `[rule]` suffix, the prefixes and a
paragraph's claims are not counted.

**A proposal still to confirm is counted in its piece's reason too**: a "Yes, as proposed" writes
it there as read, so whoever writes the point makes the reason fit with it, and no one rewords an
approved line afterwards.

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
is the approval. It holds the plan a unit at a time, with no line number, and for a piece that
fixes a bug what each reproduction told that day (§ "A bug"), which is kept and never compared.
It keeps the same way the step of each narrative a place lands in, by its sentence: once the place
is code no story crosses a `planned` call there, and the plan page goes on drawing the clause
approved on its flow, under what the step tells now. Building a piece often gives its function one
more step: the step kept is found again by its sentence, and where that was reworded among several
the page draws the closest and says so. A place the approval froze nowhere (a function the plan added, a
place built before the approval kept this) is drawn where its own function tells a step, or where
a step's sentence names that function; where a function tells several steps and nothing says
which, the page says so.
The command approves a plan that passes the check, read before it writes anything: refused, it
leaves `plan.md` as the reviewer read it. It refuses while a `To confirm:` stands that the page did
not answer "Yes, as proposed", saying what the page answered. It then writes each accepted
proposal in, word for word, and takes the `Changed:` paragraphs off `plan.md`.

From then on the check lists every unit that is not as approved, and fails:

- a piece that gained a line, or lost one of its statement, its reason or its tests, and a
  decision that is new or reads differently, while its section holds no `Changed:`;
- a reproduction whose lines are not those approved, the same way (§ "A bug");
- a `Changed:` that stands on no difference.

What asks nothing:

- **A new piece under a new bug.** The bug's `Changed:` says why both are there. A piece that
  joins a bug the approval holds takes its own.
- **A line that moved word for word** from one piece to another. A line reworded on the way is a
  loss and a gain, each with its reason: so a line that moves keeps its words.
- **The tasks stage's own output**, until a delivery is approved: the delivery, the unit-tier
  titles and the comments on unit tests.
- **A site that became code**, once the approval holds a delivery: the piece keeps its line, as
  approved, and reads as built, until a `Changed:` takes it back (§ "`plan.md`").

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
- a place the approval held, taken off with nothing written: its function holds no line it did
  not hold when the plan was approved, what stands directly on the function counted with it. A
  place in no function, as a template's, is read by its file. Skipped beside places that were
  built, or undone by a later commit, it is taken back with an `unbuilt` claim (§ "`plan.md`");
  built by taking lines off, which reads the same, its `Changed:` says so;
- a delivered lot one of whose pieces no commit names.

Each is a decision: a `Changed:` in the piece's section, in words the reviewer can read without
the code.

**What a lot changed at no place of the plan, in a file the plan names, is listed and asks
nothing.** A ripple and a small extraction are common and sound: the reviewer is shown them, with
the piece, and an edit names one (`→ code <fragment>`) only when it is a decision. In code it is a
function that changed and that no place names; a line in no function, as an import, and a new
function that a line written elsewhere names are left out. A file with no function, as a
template, lists only what is certain: a change above its first place, since a tag stands above
what it changes and nothing says how far down that goes.

## Implementing a piece

- Each `planned` call becomes code, and each comment goes. **Where a place became code, a `built`
  call stands for it**: `built('<feature>#<slug>:<place>')`, the tag of the `planned` call it
  replaces and nothing else, on the line where the change is, written by the commit that takes
  the `planned` call off. A new function holds it as its first line. It is inert, as the other
  calls are, and stays until the archive. A story that crosses it tells which step the built
  place lands in, and the plan page draws the clause approved there, linked to that line.
- **The check holds a built place to its call.** A place the approval holds with an id, whose
  `planned` call is gone and that no `built` call names, fails; so do a call that names no place
  of the approval, a second call of one place, and a call left at a place a `Changed:` took back:
  taking a place back is taking its call off.
- Each planned test becomes a test under the same title, tag and `[rule]` kept until the archive.
- Each evidence call goes, with nothing written in its place, and each reproduction passes and is
  declared as a written test, under the same title.
- **A `planned` call does not become a `narrate` by rule.** A sentence the code makes false is
  corrected in the piece's commit. New and removed steps are written in one pass, the lot's last
  commit.

The archive gate holds while a site, a planned test or a case to write remains, and while a rule
has neither one owner nor a confirmed waiver. It passes with what is built still marked. The
archive then strips those marks with one command: each `built` call of the feature, the tag and
the `[rule]` of each of its test titles, each planned screen of a journey that names it. The
command refuses while the gate fails, and ends with every line outside the feature's folder that
still names a tag of it or a path into the folder: one in the code fails it.

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

A step lives in a named function, one call a line. **It stands in the function it tells**, as its
first statement, unless that function runs more than once per action or the step is a decision
of its caller: then it stands in the caller. The function's docstring keeps its contract and does
not repeat the step. **A call stands above the code it tells, as a comment would**, and its watch
shows what that code starts from or decides. It stands after only when what the code produced is
the point of the step, and its watch then shows that result.

A user's action calls `event` at its handler; a cause a test simulates calls it in the test. No
prose names a step by its number: it moves.

## The earlier form

A feature planned before pieces keeps its `tasks.md` and its `plan.html`, with its callouts, until
it is ported or finished by hand. No skill writes that form any more: a bug batch is diagnosed
and planned in pieces (`bug-fixes`, `bug-fixes-plan`, § "A bug").
