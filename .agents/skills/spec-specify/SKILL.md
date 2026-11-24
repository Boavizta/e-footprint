---
name: spec-specify
description: Use when the user wants to start a new feature. First stage of the spec-driven workflow (specify → plan → tasks → implement → archive). Writes the feature's spec.md (the intent, and the rules no screen shows) and, where the repository draws journeys, declares what changes on screen in the journey tests — planned screens, cases to write, few mockups. Writes no product code.
---

# spec-specify

You are starting a feature's spec. It says **what** changes for the user and **why**; how the code
delivers it is the plan's. You write `specs/features/<feature>/spec.md` and, where the repository
draws journeys, the planned screens and the cases to write in its journey tests. You never write
product code.

Read `.agents/repository.md` first: where this project's rules and documents are, how its stack
spells a journey, a planned screen and a case, and its commands. The forms are in
[`specs/workflow-formats.md`](../../../specs/workflow-formats.md) § "`spec.md`"; this skill does
not restate them. `map …` below is the map's command (`code-map` skill).

## What the reviewer reads

**The reviewer reads everything that is generated for them, so what is not worth reading is not
written.** Three rules follow, and they hold at every later stage:

- **Each fact has one home.** A criterion is a rule of `spec.md`, or a case at a screen, never both.
- **A spec is short.** The problem and the change in a few paragraphs, a line a rule, a line for
  each thing left out.
- **Few mockups: one per decision.** Every other state of a screen is a case with a title.

If a sentence cannot be written without naming a file, a function or a table, it is plan content.

**The spec is edited in place.** It states the feature as it is agreed now. An answer, a change of
scope or a later stage's finding rewrites the lines it concerns; nothing records how a decision
was reached.

## Feature shaping

Before a rule or a mockup makes a convenience look mandatory, hold the scope against the project's
priorities (`repository.md` § "Documents"). For each interaction with a real complexity trade-off:

- **Frequency and value.** Who benefits, how often, by how much? Keep evidence apart from
  assumptions, and never invent a usage figure.
- **The simpler interaction.** Could an existing control, an explicit action or a manual retry
  deliver the outcome at a small extra effort? Compare with not adding the convenience at all.
- **The likely complexity.** Does it imply remembered intent, a queue, automatic continuation, a
  preserved draft, extra states, coordination between surfaces or devices? Can a second request
  start while one is in flight, and would the project's existing lock do? Flag the cost from what
  you know; the mechanism is the plan's.
- **A recommendation.** Include, simplify or omit, with the marginal benefit and cost in a
  sentence or two. No scoring, no separate document.

Keep correctness apart from convenience: a rare but consequential failure can justify substantial
work, and rarity alone never weakens correctness. Respect what the user already decided, and put
a material unresolved trade-off to them before a polished interaction becomes a requirement.

### Split when the scope has grown

Scope creeps during the discussion, and each addition looks small in conversation and large in a
plan. **Just before drafting, size the scope.** Propose a split when it holds more than five or
six distinct interactions, or more than one surface where the user acts on the same state. A core
feature keeps the primary surface and what it cannot ship without; a follow-up takes the
extensions, and then starts from a shipped core. Name which interactions stay and which move, say
why, and ask. If the user prefers one spec, write one.

## Process

1. **Confirm the feature's name** (kebab-case). If `specs/features/<feature>/` exists, ask before
   touching it. Create the folder as the repository's file conventions ask (`repository.md`).
2. **Read the project's mission and its rules** before drafting. A feature out of scope, or
   against a rule, is said before anything is written.
3. **Keep the technical decisions the conversation already holds.** A decision about files,
   names, defaults, a pattern to follow or where things live is not spec content, and must not be
   lost: the plan session starts fresh and will not have heard it. Write each as a line of
   `specs/features/<feature>/plan-draft.md`, a plain list of the decisions as they stand, edited
   in place like the spec. The plan stage turns them into pieces and deletes the file. Write none
   when the conversation held no such decision, and tell the user when you did.
4. **Shape the scope**, and settle a split, as above. A follow-up gets its own folder holding a
   `spec.md` with the problem and the moved interactions; the core lists them under "Not doing".
5. **Write `spec.md`.** Ask the user any open question about audience, outcome or scope; never
   invent the answer, and never ask a design question here.
   - **A rule is a behaviour a test can hold.** A line that constrains the implementation ("costs
     no more than today") is worded as what the user would observe, or the plan will waive it.
   - A rule's slug is how a test will claim it: short, and true whatever the plan decides.
6. **Declare what changes on screen**, where the repository draws journeys:
   - **The screens the feature changes are walked by a journey first.** A screen no journey
     reaches gets its journey before the spec, on today's behaviour, in a commit of its own.
   - Mark each changed screen as planned, with a mockup: a full edited copy of today's capture.
     It opens with a comment saying what was edited in. The lot's brief prints that comment, so
     whoever writes the screen's case reads it and not the mockup.
   - **A case to write is one criterion, as a title that says what the screen reads.** Its title
     must stay true through the plan's decisions; the plan stage re-reads each.
   - **A journey shows, a narrative proves.** Plan a case for a screen, or a state of one, worth
     seeing. A criterion that is logic (a range, a combination, what is saved) is a rule of
     `spec.md`, for a narrative case to own. Written as a case too, the reviewer reads the same
     behaviour twice.

   Where the repository draws none, say what each changed screen reads in a section of `spec.md`,
   and point at the design page that shows it today.
7. **Render and read what you wrote.** Run the journeys and draw the spec page
   (`repository.md` § "Commands"), then `map spec <feature>`. Its last part lists what the change
   rides on: the narratives a case crosses before a changed screen, and the code on that path
   that tells nothing. Report both: the first is the plan's input, the second is worth a narrative
   before the plan is written.
8. **Self-check.** Each rule: is it something the user experiences? Each case: is it a screen
   worth seeing, and not logic? Do the rules and the mockups reflect the trade-offs chosen, or
   bring back a convenience that shaping left out?
9. **Run the gate of a doc edit** (`repository.md` § "Gates") and commit the spec's files by name.

## After writing

Tell the user, in a few lines: the files written, where the spec page is, the open questions, the
narratives the change rides on and any missing narrative worth writing first. Then wait for the review. When
the spec is approved, the next stage is `spec-plan`, in a fresh session.
