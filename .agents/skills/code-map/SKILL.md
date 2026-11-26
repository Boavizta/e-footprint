---
name: code-map
description: Use BEFORE reading source to plan, task or change what the app does for an action — `npm run map` answers, in a screen of text, what a feature's spec changes, which steps a narrative is made of (each a `file:line`), what code sits around them, and which tests tell them. Triggers — writing or refining a plan or tasks for a feature that has a spec, "how does X work" about code that has `narrate` calls, "what touches this file", "what does this change ride on", about to edit a source file you have not read. Read-only; an answer costs 0.1 s.
---

# code-map

Some of what this app does is told as **narratives**: the code tells it itself, one `narrate('sentence')` call
per step, and a test crosses those steps in order. `npm run map` is that knowledge as text. Ask it
before opening files: it gives the `file:line` of what matters, so you read ranges, not files.

Narratives are a small, curated set of guides through meaningful flows. Each answers one coherent
question; ordinary tests can own other behaviour. Selection follows
[`workflow.md` § "Narratives and test ownership"](../../../specs/workflow.md#narratives-and-test-ownership).

Call it as `node comprehension_harness/map.mjs <verb> …` (or `npm run map -- <verb> …`).

| You need | Ask |
|---|---|
| What a feature changes: its spec, plus changed screens, cases and recorded crossings where screen journeys are configured | `spec <feature>` |
| The list of narratives; documentation flows only | *(no verb)*; `narrative --scope doc` |
| One narrative, step by step, under its causes; branches; mechanisms it rides on | `narrative <slug>` |
| One step: its function's source, who refers to it, what it calls, the tests reaching it, the debts and rules naming it | `step <slug>#<n>` |
| The functions next to a narrative that hold no `narrate` (handlers, helpers, the page that renders it) | `around <slug>` |
| Whether a file or a function is part of a narrative | `where <file \| function>` |
| A feature's plan: the pieces in run order, each with its statement, its reason, its places in the code and its planned tests; each rule's owner | `plan <feature>` |
| One piece of a plan with the code at each of its sites, who will call each new function, the decisions that bind it | `brief <feature>#<piece>` |
| A lot of the plan's delivery — what an implementer is handed: its pieces in commit order with their code, the decisions across pieces in full, the journey cases it writes last. A piece that is built reads as the approval holds it: each place that became code with its clause, each test written under its title, which is what a reviewer sets the code against | `brief <feature>/<lot>` |
| A plan's check in a screen: what fails, what is not as approved, what each lot owes — run this while editing a plan, not the whole `comprehension-render --check` | `check <feature>` |
| The reviewer's answers given from the plan's pages: what is not approved and why, each question's answer, what is not read yet | `feedback <feature>` |
| The tests that reach a piece's or a lot's sites today, by file, with their titles — read before a unit test is planned, kept or deleted | `reach <feature>#<piece>`, `reach <feature>/<lot>` |

A slug can be any part that names one narrative (`checkout`, `sign-in`).

## How to read with it

1. **Planning or tasking a feature: start at `spec <feature>`.** With screen journeys configured,
   its last lines name the narratives crossed. With `commands.journeys: []` in
   `comprehension.config.json`, it reads `spec.md` directly without captures or a test run;
   use the narrative list to select relevant planning context. Once the plan has sites
   (`planned` calls, `@planned` comments, tests to write under a tagged title),
   `plan <feature>` shows it as it stands, its delivery in lots, and what differs from the approved
   plan (`plan.approved.json`); an implementer starts at `brief <feature>/<lot>`.
2. **`narrative`, then `around`.** The narrative is what the code says it does; `around` is the code
   beside it that says nothing. A change usually lands in both.
3. **`step` only for the steps you will change.** It prints the function, so you rarely need to Read
   the file as well.
4. **`where` before reading a file nothing pointed you to.** "unmapped" is a normal answer: most of
   the app is outside narratives. Read the code directly. Propose a narrative only when a guide
   through that flow would materially help a developer; an unmapped file alone is no gap and
   does not block planning.

Every line carries a `file:line`. When you do open a file, Read that range.

## What the answers are, and are not

- **Steps, causes, branches, "rides on", tests reaching a step** come from test runs: they are what
  happened, in order.
- **`around` and the "referred to by / calls" lists** come from the stack's reader of the source, not from a
  run: candidates. A handler reached only through a context value is missed; a helper everything
  uses is left out on purpose.
- **`spec`'s "rides on"** lists steps the journey crossed on the way to a changed screen. A step
  crossed is not a step the feature changes, and a change with no screen (a migration, a type) is on
  no list.

## Freshness

With screen journeys disabled, `spec` reads the current `spec.md` directly. Other answers are
read from a snapshot. When a file it was read from has moved, the command rebuilds
it first and says so on stderr: 4 to 5 s. A step whose line moved is found again by its sentence; the
answer then ends with a note naming the test to run if you need the narrative observed again (after a
change of behaviour, not after adding a comment or a `planned` call). Two cases it will not fix by
itself, and says how to:

- a journey test newer than its captures: run the journeys (the answer names the command), then ask again;
- a narrative test that fails: fix it first — a failing narrative has no steps to report.

`--stale-ok` answers from what is there.

How it is built: `comprehension_harness/map-build.ts` and `comprehension_harness/map.mjs`.
