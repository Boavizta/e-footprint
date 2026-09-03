---
name: feature-implement
description: Orchestrate the full implementation of a feature's tasks.md end to end. A supervisor agent loops over every uncompleted task, spawning an implement sub-agent then a review sub-agent, triaging the review findings with its own judgement — auto-approving the evident fixes and escalating only genuinely structuring decisions to the user via AskUserQuestion — applying the fixes, and continuing to the next task. Use when you want to drive a whole feature with minimal human intervention, surfacing only the decisions that genuinely need you.
---

# feature-implement

You are the **supervisor** for implementing a feature's `tasks.md`. You do **not** write code yourself. You spawn sub-agents for the work, you own the conversation with the user, and you drive the loop from one task to the next. You **triage the review findings yourself**: you approve the evidently-good fixes on your own judgement and escalate to the user only when a finding is a genuinely structuring decision. Many tasks will need no human input at all; you handle everything else.

This skill orchestrates the per-task skills `task-implement` and `task-review`. Read both (`.claude/skills/task-implement/SKILL.md`, `.claude/skills/task-review/SKILL.md`) once at the start so you know the process each sub-agent must follow. Note that those skills' standalone constraints — "do not chain to the next task", "the reviewer never touches files" — are deliberately relaxed here: **you** own chaining, and the review agent **does** apply the approved fixes, **but without knowing it at first** (only after you have triaged the review — your own judgement, plus any user decisions). Their *processes* (gates and review checklist) still hold; this skill overrides their commit-message format for task-scoped commits.

## Setup

1. **Confirm the feature.** Ask the user which feature, or take the one they named. Read `specs/features/<feature-name>/tasks.md`. For cross-repo features, the single `tasks.md` lives in the driving repo. If its execution plan defines multiple runs, confirm which run this session executes.
2. **Read the loop's standing inputs once**, so you can brief sub-agents tersely: `specs/constitution.md` (gates), `specs/conventions.md`, and `specs/architecture/index.html` plus the owning architecture pages it routes to. For a normal feature, also skim `spec.html` and `plan.html` for intent. A bug-fix batch deliberately has neither; each task must link a diagnostic file, which replaces them for that task. If neither form of intent exists, stop.
3. **Check autonomy readiness once, before implementation.** Treat an approved spec, plan, and tasks list as the load-bearing contract for a smooth autonomous run. Confirm that acceptance criteria are testable, product and architectural decisions needed for implementation are resolved, task boundaries and ordering are coherent, and the selected model/reasoning effort are appropriate for the feature. Propagate the run's chosen model and effort to implement and review sub-agents rather than silently downshifting them. Stop here only when a real gap would force implementation to invent product behavior, architecture, scope, or a contract; ordinary implementation details are the agents' responsibility.
4. **Identify the uncompleted tasks** in the selected run's stated order, or document order when no runs are defined. These are the iterations of your loop.

## Per-task loop

For each uncompleted task, in order:

### 1. Implement (sub-agent)

Spawn a sub-agent (Agent tool, `general-purpose`) to implement **exactly one task**. Brief it: the feature name, the specific task, and the instruction to follow the process in `.claude/skills/task-implement/SKILL.md`. Tell it explicitly: **do not chain into the next task**, and **skip the CHANGELOG.md gate** — you (the supervisor) write one consolidated `## [Unreleased]` entry for the whole feature once every task is done, so a per-task entry would just fragment it.

Give it the task number and require the implementation commit subject to start `<repo tag> task N:`, for example `[ADD] task 4: replace catalog datalists with selects`. This task-numbered format overrides `task-implement`'s standalone `<feature-name>: <task title>` format and makes the feature history easy to scan.

Require a **compact structured handoff** — this is all that enters your context, so preserve decision-relevant information without step-by-step narration. For a substantive task, roughly 150–250 words is a useful target rather than a hard limit; simple tasks can be shorter, and material risks or decisions must not be omitted to meet it. Include:

- outcome and key implementation decisions or invariants;
- main files or areas changed;
- tests run and the behaviours they cover, plus any failing or unavailable gate;
- `Scope deviations / boy-scout fixes: none` or each deviation with its supported reproduction and owning layer;
- remaining risks, unresolved questions, follow-ups, and what remains in the task list.

Do not include diffs, command transcripts, or chronological implementation narration. A synthetic test that directly manufactures internal state is not a supported reproduction.

**A red gate is diagnostic evidence, not an automatic user interruption.** Have the implement agent diagnose the failure. When the cause and correction are evident, in scope, and low risk—such as an implementation defect, stale test expectation, malformed fixture, formatting issue, or another local inconsistency—tell the same agent to fix the demonstrated cause, rerun the affected gate, and continue without asking the user. Never convert an unexplained failure into speculative hardening or a downstream workaround. Briefly surface the recovery as a non-blocking progress update when useful; never hide a still-failing gate.

**Halt only for a load-bearing blocker:** the failure reveals a wrong or missing product assumption, requires a scope or contract change, presents reasonable architectural alternatives, needs an unavailable dependency or new authority, would require a destructive operation, affects broad unrelated behavior, or remains unexplained after reasonable in-scope diagnosis and correction attempts. Report the evidence and the decision or authority needed; do not move to the next task with a red gate.

### 2. Review (sub-agent)

Spawn a **second** sub-agent to review the commit, following `.claude/skills/task-review/SKILL.md` (it reviews `git show HEAD` against the checklist). Brief it with the feature name and task.

Require it to apply the checklist's provenance audit to every new defensive construct and every out-of-task hunk: name the supported state producer and owning layer, and reject synthetic internal-state setup as the sole justification for production integration code.

The review agent has the full review context — so **it does the deep work, not you.** Have it return, for **every** finding, a compact triage line, and a full question block **only** for the findings it judges to be structuring decisions:

```
#N [Category] file:line — one sentence problem.
   Class: EVIDENT-FIX | STRUCTURING-DECISION — one-line reason for the call.
   Recommended resolution: one sentence (what it would do if just fixing it).
   # The block below is included ONLY when Class is STRUCTURING-DECISION:
   Header: a chip label ≤12 chars.
   Question: the full question to put to the user.
   Options (2–4, recommended one first, marked "(Recommended)"):
     - <label> — <description, including the trade-off and, for the recommended one, why>
     ...
```

**EVIDENT-FIX** = a clear, low-risk improvement that any careful reviewer would just make (dead code, a missed invariant with one obvious fix, a local simplification, a test gap with a clear test to add). For behavioural or defensive changes, "evident" also requires a supported reproduction and a fix in the layer that owns the invariant. **STRUCTURING-DECISION** = a finding where reasonable choices genuinely diverge and the user would want a say — e.g. an unintended bug, a logical gap in the spec, a big refactoring opportunity, an architectural fork, or anything that changes scope or contracts.

For the structuring ones, brief the agent on the `AskUserQuestion` shape so its output drops in cleanly: each question has 2–4 options (use only as many as there are genuine alternatives — don't pad to a count); the recommended option comes first and is labelled "(Recommended)" with its rationale in the description; headers are ≤12 chars. **Options must be real alternatives**, not a fix/defer/reject template — genuinely different *ways to resolve* the finding (e.g. "extract a shared helper" vs "inline at both call sites" vs "restructure X to remove the need"), each with its trade-off. The default assumption is that a finding *will* be fixed on the spot, even when the fix implies substantial refactoring; offer defer/reject only when the agent genuinely thinks not-fixing is on the table.

This output is compact by construction, so the agent **always returns it inline** — there is no separate review file. Deeper detail (code excerpts, full reasoning) stays in the review agent's own context and is fetched on demand in step 3.

**Keep this agent's id** — you reuse it in step 3 (context Q&A) and step 4 (applying fixes) so both inherit its review context instead of re-reading the code.

### 3. Triage the findings (you, the supervisor)

Apply **your own judgement** to the review agent's classification. The agent proposes the split; you make the call.

**Auto-approve the evident fixes.** For findings classed EVIDENT-FIX that you also judge clearly worth doing, approve them yourself — no user input needed. The bar is "evidently good to do": correct, in-scope, low-risk, no contract or scope change; for behavioural or defensive changes, it must also have a supported reproduction and live in the owning layer. If you disagree with the agent's "evident" call (the fix looks riskier or more consequential than the agent thought), treat it as a structuring decision instead.

**Escalate only the structuring decisions.** Surface a finding to the user only when it is genuinely structuring — an **unintended bug**, a **logical gap in the spec**, a **big refactoring opportunity**, an architectural fork, or any change to scope/contracts where reasonable choices diverge. When in doubt about whether something rises to this bar, **lean on the review agent** (SendMessage to its id) for more context before deciding — don't read the code yourself.

**If nothing is structuring, skip to step 4** — no `AskUserQuestion` call, no blocking the user.

**When you do escalate, lead with full context — one briefing per point.** The user answers blind unless you set it up: a sub-agent's output is never shown to them, and `AskUserQuestion` renders only the bare questions and option labels. So **before** calling `AskUserQuestion`, post a normal markdown message that gives **detailed context for each and every finding you are about to ask about** — one clearly-headed section per point, matched one-to-one to the questions that follow (and covering every point in the batch). Each section covers: what the problem is, the relevant code/mechanism concretely (the `file:line`, with a short excerpt or paraphrase), what a fix would touch, and what is genuinely at stake in each direction — the trade-offs behind the options the user is about to choose between. Because the matters you surface are by definition the complex, structuring ones, **err toward more context, not less**: the aim is to give the user enough to decide in a single pass and avoid back-and-forth. The user can always ask follow-ups, but do not rely on that to fill gaps you could have closed upfront. The compact step-2 findings are usually too thin for this — when a point needs deeper grounding to brief it well, **fetch the detail from the review agent** (SendMessage to its id) rather than reading the code yourself, then write the briefing from what it returns.

**Then** call `AskUserQuestion` (you call it — never the sub-agent; sub-agents run non-interactively and their `AskUserQuestion` never reaches the user). You are a **relay, not an author** for the questions: hand the agent-prepared blocks from step 2 to `AskUserQuestion` largely verbatim, grouped into batches of up to 4. Light touch-ups for the tool's constraints (trimming a header to ≤12 chars, splitting a 5th option) are fine. If a prepared question looks too thin to decide on, **don't pad it yourself** — send it back to the review agent for a better-grounded version.

Let the conversation breathe — the user may push back or discuss before deciding. **When the user asks for more context** (how something works, what a fix would touch, whether an approach is feasible), **do not search the code yourself** — pass the question to the review sub-agent (SendMessage to its id), let it research, relay its answer, and have it revise the affected question if the discussion changed the options. Keep this Q&A loop going as long as the user is exploring; only the questions and answers pass through you, not the code-reading. Collect the full set of decisions across all batches before moving on.

### 4. Apply the fixes (reuse the review agent)

Send the consolidated decisions — the fixes you auto-approved **plus** any the user decided — back to the **review sub-agent** (via SendMessage to its id, so it keeps full review context). Instruct it to apply only the approved fixes, in a **reasonable number of commits — typically 2–3** — grouping related changes, and putting any **larger refactor identified during review in its own commit**. Every review-fix commit subject starts `<repo tag> task N review fix:`, for example `[FIX] task 4 review fix: preserve a saved zero threshold`. It must re-run the constitution §2 gates after the fixes and report pass/fail tersely.

Apply the same gate policy here: autonomously diagnose and correct evident in-scope failures, rerun the affected gates, and halt only for a load-bearing blocker. Never move to the next task while a gate remains red.

### 5. Continue

Briefly tell the user what this task produced — a **terse, non-blocking** note: what you auto-approved and applied, what you escalated (if anything), and the commit(s). This keeps autonomy from becoming silent change; it is a status line, not a question. Then mark the task done in your own tracking and proceed to the next uncompleted task — back to step 1 with a fresh implement sub-agent. Once a task's fixes are committed, **stop referencing its findings**: the commit is the durable record, so don't re-quote or re-summarise them as the loop continues. (You can't reclaim context already spent — this only keeps it from *growing* as tasks accumulate.)

## When the loop ends

**First, write the CHANGELOG entry.** Spawn one final sub-agent (Agent tool, `general-purpose`) briefed with: the feature name, and the list of completed tasks — title, one-line summary, and commit(s) for each, from what you've tracked across the loop. Instruct it to:

1. Read the top of `CHANGELOG.md` to match its current format and voice (grouped `### Added` / `### Changed` / `### Fixed` / etc. subsections; user-facing prose that names the mechanism and the *why*, not a mechanical task-title dump).
2. Find the `## [Unreleased]` section (create it, positioned directly above the first version-numbered section, if it doesn't exist yet).
3. Add a **consolidated** entry synthesizing what this feature shipped as a whole — grouped by category, written as coherent user-facing bullets. Multiple tasks that form one user-visible change become one bullet, not one line per task or per commit.
4. Commit with `[UPDATE]` prefix, body `<feature-name>: changelog entry`.

This is the **only** point in the loop that touches `CHANGELOG.md` — implement sub-agents were told to skip that gate per task (step 1) specifically so this one write stays coherent.

**Then** give the user a short summary: tasks completed, total commits, what was auto-approved versus escalated, anything deferred/rejected during reviews (so nothing is silently dropped), the CHANGELOG entry, and the suggested next step. **Do not archive the feature yourself** — stage 5 archiving (per `specs/workflow.md` §5) involves a promotion check that reads the reference specs, which belongs in a fresh context, not yours, and is normally deferred until the work has merged. Instead, suggest the user run the `feature-archive` skill when they are ready, alongside opening PRs.

## Context discipline (why this stays lean)

A sub-agent's internal work never enters your context — only its final message does. Your context therefore grows by roughly one findings list per task, not by implementation transcripts. Protect that: require compact, decision-relevant handoffs rather than lossy summaries, keep returned findings focused (deeper detail stays in the review agent, fetched on demand), delegate code-reading to the review agent during Q&A, and stop referencing a task's findings once its fixes are committed. None of this reclaims context already spent — it only bounds *growth*. If a feature is very large (>~8 tasks) and discussions run heavy, suggest the user split it across more than one `feature-implement` run rather than letting your context grow unbounded.

## Halt-and-surface conditions (never silently continue)

- A quality-gate failure exposes a wrong or missing product assumption, scope/contract change, architectural fork, broad unrelated regression, unavailable dependency or authority, or remains unexplained after reasonable in-scope correction attempts. An evident local implementation/test/fixture/formatting correction is handled autonomously and the gate is rerun.
- A sub-agent surfaces a missing dependency, wrong plan assumption, or scope creep that cannot be resolved without changing the approved task or obtaining new authority.
- A destructive operation would be needed (constitution §3.3) — ask first.
- A finding is a genuinely structuring decision (unintended bug, logical gap in the spec, big refactoring opportunity, architectural fork, scope/contract change) — escalate it per step 3 rather than auto-approving.
- The user, mid-discussion, signals they want to stop or take over.
