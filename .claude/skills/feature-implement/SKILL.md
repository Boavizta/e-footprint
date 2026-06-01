---
name: feature-implement
description: Orchestrate the full implementation of a feature's tasks.md end to end. A supervisor agent loops over every uncompleted task, spawning an implement sub-agent then a review sub-agent, batching review findings to the user via AskUserQuestion, applying the approved fixes, and continuing to the next task. Use when you want to drive a whole feature with a single human intervention per task.
---

# feature-implement

You are the **supervisor** for implementing a feature's `tasks.md`. You do **not** write code yourself. You spawn sub-agents for the work, you own the conversation with the user, and you drive the loop from one task to the next. The user intervenes **once per task** — to review findings and decide on fixes — and you handle everything else.

This skill orchestrates the per-task skills `task-implement` and `task-review`. Read both (`.claude/skills/task-implement/SKILL.md`, `.claude/skills/task-review/SKILL.md`) once at the start so you know the process each sub-agent must follow. Note that those skills' standalone constraints — "do not chain to the next task", "the reviewer never touches files" — are deliberately relaxed here: **you** own chaining, and the review agent **does** apply the approved fixes, **but without knowing it at first** (only after the user has reviewed the review). Their *processes* (gates, commit conventions, review checklist) still hold.

## Setup

1. **Confirm the feature.** Ask the user which feature, or take the one they named. Read `specs/features/<feature-name>/tasks.md`. For cross-repo features, the single `tasks.md` lives in the driving repo.
2. **Read the loop's standing inputs once**, so you can brief sub-agents tersely: `specs/features/<feature-name>/spec.html` and `plan.html` (skim for intent), `specs/constitution.md` (gates), `specs/conventions.md`, `specs/architecture.md`.
3. **Identify the uncompleted tasks**, in order. These are the iterations of your loop.

## Per-task loop

For each uncompleted task, in order:

### 1. Implement (sub-agent)

Spawn a sub-agent (Agent tool, `general-purpose`) to implement **exactly one task**. Brief it: the feature name, the specific task, and the instruction to follow the process in `.claude/skills/task-implement/SKILL.md`. Tell it explicitly: **do not chain into the next task.**

Require a **terse final message** — this is all that enters your context, so keep it lean: task title; files touched; gate status (tests pass/fail, plus any repo-specific gates that applied); one line on what remains. No diffs, no narration.

**On gate failure or a surfaced blocker** (tests red, plan assumption wrong, missing dependency, scope creep): **halt the loop.** Report the failure to the user with the agent's output and wait. Do not silently retry and do not move on.

### 2. Review (sub-agent)

Spawn a **second** sub-agent to review the commit, following `.claude/skills/task-review/SKILL.md` (it reviews `git show HEAD` against the checklist). Brief it with the feature name and task.

The review agent has the full review context — so **it authors the questions, not you.** If you tried to compose questions yourself from compact findings, they'd be shallow. Let the review agent come back with its findings, then instruct it to return, for each finding, a **question ready to hand straight to `AskUserQuestion`**:

```
#N [Category] file:line — one sentence problem.
   Header: a chip label ≤12 chars.
   Question: the full question to put to the user.
   Options (2–4, recommended one first, marked "(Recommended)"):
     - <label> — <description, including the trade-off and, for the recommended one, why>
     ...
```

Brief the agent on the `AskUserQuestion` shape so its output drops in cleanly: each question has 2–4 options (use only as many as there are genuine alternatives — don't pad to a count); the recommended option comes first and is labelled "(Recommended)" with its rationale in the description; headers are ≤12 chars. **Options must be real alternatives**, not a fix/defer/reject template — genuinely different *ways to resolve* the finding (e.g. "extract a shared helper" vs "inline at both call sites" vs "restructure X to remove the need"), each with its trade-off. The default assumption is that a finding *will* be fixed on the spot, even when the fix implies substantial refactoring; offer defer/reject only when the agent genuinely thinks not-fixing is on the table.

This output is compact by construction, so the agent **always returns it inline** — there is no separate review file. Deeper detail (code excerpts, full reasoning) stays in the review agent's own context and is fetched on demand in step 3.

**Keep this agent's id** — you reuse it in step 3 (context Q&A) and step 4 (applying fixes) so both inherit its review context instead of re-reading the code.

### 3. Relay the questions to the user (you, the supervisor)

This is the single human touchpoint for the task. **You** call `AskUserQuestion` — never the sub-agent (sub-agents run non-interactively; their AskUserQuestion never reaches the user).

**First, display the review findings to the user.** A sub-agent's output is *not* shown to the user, and `AskUserQuestion` renders only the questions and their options — so unless you post the findings yourself, the user answers blind. Before calling `AskUserQuestion`, relay the review agent's full findings (from the step-2 first pass) as a normal markdown message, so the user can refer to the analysis while answering. Keep it faithful to what the agent reported — this is a relay, not a rewrite.

Then call `AskUserQuestion`. You are a **relay, not an author**: hand the agent-prepared questions from step 2 to `AskUserQuestion` largely verbatim, grouped into batches of up to 4. Don't rewrite or simplify them — the agent wrote them with full context, and that's what keeps quality high. Light touch-ups for the tool's constraints (trimming a header to ≤12 chars, splitting a 5th option) are fine.

If a prepared question looks too thin to decide on, **don't pad it yourself** — send it back to the review agent for a better-grounded version (see below).

Let the conversation breathe — the user may push back or discuss before deciding. **When the user asks for more context** about a finding (how something works, what a fix would touch, whether an approach is feasible), **do not search the code yourself** — your context stays lean by delegating. Pass the question to the review sub-agent (SendMessage to its id), let it do the research, and relay its answer back — and have it revise the affected question if the discussion changed the options. Keep this Q&A loop going as long as the user is exploring; only the questions and answers pass through you, not the code-reading. Collect the full set of decisions across all batches before moving on.

### 4. Apply approved fixes (reuse the review agent)

Send the consolidated decisions back to the **review sub-agent** (via SendMessage to its id, so it keeps full review context). Instruct it to apply only the approved fixes, in a **reasonable number of commits — typically 2–3** — grouping related changes, and putting any **larger refactor identified during review in its own commit**. Each commit follows the repo message convention (`[ADD]`/`[FIX]`/`[REFACTO]`/…, body `<feature-name>: <summary>`). It must re-run the constitution §2 gates after the fixes and report pass/fail tersely.

**On gate failure here too: halt and surface.**

### 5. Continue

Mark the task done in your own tracking and proceed to the next uncompleted task — back to step 1 with a fresh implement sub-agent. Once a task's fixes are committed, **stop referencing its findings**: the commit is the durable record, so don't re-quote or re-summarise them as the loop continues. (You can't reclaim context already spent — this only keeps it from *growing* as tasks accumulate.)

## When the loop ends

When every task is done, give the user a short summary: tasks completed, total commits, anything deferred/rejected during reviews (so nothing is silently dropped), and the suggested next step (stage 5 archive per `specs/workflow.md`, or opening PRs).

## Context discipline (why this stays lean)

A sub-agent's internal work never enters your context — only its final message does. Your context therefore grows by roughly one findings list per task, not by implementation transcripts. Protect that: insist on terse sub-agent returns, keep returned findings compact (deeper detail stays in the review agent, fetched on demand), delegate code-reading to the review agent during Q&A, and stop referencing a task's findings once its fixes are committed. None of this reclaims context already spent — it only bounds *growth*. If a feature is very large (>~8 tasks) and discussions run heavy, suggest the user split it across more than one `feature-implement` run rather than letting your context grow unbounded.

## Halt-and-surface conditions (never silently continue)

- Any quality gate fails (implement step or fix step).
- A sub-agent surfaces a missing dependency, wrong plan assumption, or scope creep.
- A destructive operation would be needed (constitution §3.3) — ask first.
- The user, mid-discussion, signals they want to stop or take over.
