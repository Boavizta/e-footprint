---
name: feature-implement
description: Execute an approved feature or bug-batch task list with implementer/reviewer agents, bounded recovery, cross-task review, documented decisions and usage reporting.
---

# feature-implement

Supervise the approved tasks; delegate implementation and independent review. Read `.agents/repository.md`, `task-implement`, `task-review` and `specs/agent-tooling.md` once. Resolve the feature/run from the request; use the first unfinished run when unambiguous. Do not ask again for authority already supplied.

## Setup

- Read the approved spec/plan (or linked bug diagnostics), tasks, constitution and relevant architecture pages. Check that acceptance and dependencies are usable without inventing product decisions. Keep a single working set in the driving repo.
- Record starting commits and existing dirty files in every affected repo. Agree file ownership with parallel work; commit only exact owned paths. A shared checkout need not become globally clean.
- Start committed `run-<label>-judgements.md` and `run-<label>-gates.md` (or unprefixed names for a single run). Record consequential decisions as they happen, not from memory at close-out.
- Use configured roles: Sol/medium implementer; Astra/high hard implementer, reviewer and diagnostician. The supervisor is preferably Astra/high. Respect explicit user model choices; report actual configuration instead of claiming a role pin worked. See `specs/agent-tooling.md` for Claude equivalents and runtime dispatch.
- Collect local usage and register this session/each subagent with the feature, owner, stage, run, role and task where its runtime exposes an ID. Missing telemetry never blocks implementation and is reported as missing.

## Per-task loop

1. Spawn `implementer` for exactly one task, or `implementer-hard` for a concrete high-risk task. Supply task/brief paths, repository roots, dependency changes, owned file boundaries and role instructions. Defer only the consolidated changelog to the supervisor. Require implementation commits, gate results, durable handoff, scope deviations and doubts in the return.
2. Spawn an independent `reviewer` over the explicit implementation range(s), not whatever `HEAD` happens to be after handoff commits. Give the same intent and handoff path. It chooses its own tier; preserve the tier and reason in judgements.
3. Triage findings. Resolve evident supported fixes and reversible implementation choices within the approved design. Log consequential choices and alternatives. Do not silently change product scope, constitutional rules or an external contract. An unresolved choice needed for this task parks it; continue independent work. If the user requested live consultation, use it; silence is not approval for a decision requiring approval.
4. Resume the reviewer to apply the accepted fixes. Batch related edits and targeted checks; finish required constitution gates before marking the task complete. The Pretext optimization that leaves full validation to the next task is NOT a standing waiver here. Ask for short global-review leads in the handoff even when there are no fixes.
5. Update task status, judgements and gates; commit exact working-set files. Report a compact progress update, then continue to the next independent task.

## Recovery and decisions

Resume the same agent once for a diagnosed scoped failure. If implementation difficulty remains, escalate once to `implementer-hard` with the failed attempt's evidence. A missing dependency or wrong plan is not fixed by spending more reasoning.

If still blocked, park that task and its transitive dependents, record what is needed and continue independent tasks. Keep any green completed stage. Preserve unrelated dirty files; use a scoped revert of your own work only when its effect is understood and authorized. Never label a red or unverified change complete. Halt when no authorized useful work remains or the user asks to stop.

Judgements record: actual roles/models, review tiers, evidence for non-trivial decisions, deviations, rejected/deferred findings, parked tasks and final validation. Gates distinguish:

- evidence/prerequisites that block a later task or run;
- operations that block deployment only;
- end-of-run human validation, naming the build/environment and observable result.

Do not guess missing evidence. A human check is not automatically a blocker for independent code work. Destructive actions, external publication and paid operations require the authority that actually applies to them; Pretext's project-specific standing grants do not transfer.

## Close-out

- Run a fresh `reviewer` on both repositories' cumulative feature/run ranges. Start with each handoff's global-review leads and diff statistics; inspect interactions and remaining concerns. Triage and apply scoped fixes.
- Write a consolidated `CHANGELOG.md` entry in each affected repo. Run applicable full suites and conditional gates against the final implementation, including cross-repository integration. Report failed/unavailable gates and tested revisions accurately.
- Collect usage again; report by feature/run with initial work, follow-ups, supervisor/global-review/brief costs, attempts, active duration and unknown coverage. Separate API-equivalent estimates from Codex credits. Record model or effort deviations. Usage collected before closing is a snapshot, not an exact final invoice.
- Commit the final working-set records and report completed/parked tasks, decisions, gates and usage. Suggest explicit `feature-archive` after the work has shipped and outstanding gates are resolved. Do not merge, deploy, archive, or create a new user task merely because the loop ended.

## Optional bounded shadow-review experiment

Only run when the user explicitly requests the experiment or approves its feature-local protocol. Compare Astra/high with Sol/high on identical immutable task ranges, starting independently with the same brief and no access to the other's findings. Shadow only the initial task review, not fixes or global review. Limit to five named runs, then stop for a decision; never make the second review permanent by accident.

The shadow is read-only and may not run stateful suites or shared-cache writers. A failed shadow does not block normal review. Record reviewer IDs, tiers, matched findings, approved material misses, useful shadow-only findings, noise, durations and INITIAL-review cost (not the primary reviewer's later fix work). Act on a genuine shadow-only defect through normal triage. Book experiment cost separately. Use evidence about misses and completed-task cost to decide whether to keep, split or change the reviewer role.
