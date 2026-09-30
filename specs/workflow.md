# Spec-driven development workflow

Canonical in e-footprint, synchronized unchanged into e-footprint-interface. Repository-specific
architecture, gates and review-risk surfaces live in `.agents/repository.md`; runtime roles,
synchronization and local usage collection are described in `specs/agent-tooling.md`.

## Scope and ownership

Features follow specify → plan → tasks → implement, with human approval between design stages,
then explicit archive after shipping. A user's clear request to implement an already agreed
change is authorization; do not manufacture another approval gate.

Small fixes, local refactors and investigations may go directly to work. A conversational bug
batch uses `bug-fixes`: evidence-backed diagnostics plus one task list replace spec/plan. The
normal implement/review/archive steps still apply. This workflow does not authorize deployments,
publication, destructive operations or paid external actions beyond the user's actual grants.

Library-only and library-driven changes live under the library's `specs/features/<feature>/`.
Interface-driven and other interface/cross-repo changes live in the interface. Cross-repo work
has ONE task list in the driving repo, with explicit repository ownership and dependencies.

## 1. Specify

`spec-specify` writes self-contained `spec.html`: problem, audience, scope, success criteria and
open product decisions. It is not an implementation design. After approval, start planning in a
fresh session from the approved document; preserve a design-rich kickoff's draft plan for refinement.

## 2. Plan

`spec-plan` writes/refines `plan.html` as an anticipated code review. Ground it in current code,
follow user interactions or library caller operations, show changed structures/contracts, and
provide linked changed-file navigation. Separate reading order from delivery dependencies and
map important behavior to verification. Keep the existing level of architectural explanation;
link owning pages where helpful, without adding a teaching section.

Review and approve the plan, then start tasks in a fresh session. Missing decisions in the
persisted documents must be resolved instead of inferred from another session's memory.

## 3. Tasks and briefs

`spec-tasks` produces a concise `tasks.md` overview and `briefs/task-N.md` for implementers.
Tasks are review-sized behavioral increments with acceptance, ownership, dependencies and risk.
Briefs verify symbols, reusable mechanisms, earlier-task effects, invariants and exact checks.
The same agent writes every brief in dependency order, then checks that dependent tasks' assumptions
match their predecessors' planned outputs. It completes the full preparation pass autonomously,
collecting proposals for one combined review. Only a major blocker that prevents a coherent working
set even with explicit provisional assumptions warrants interruption; finish unaffected work first.

Gaps found during grounding become visible `[PLAN-UPDATE-01] — PROPOSED` callouts beside affected
passages in `plan.html`, with stable IDs and a small linked index near the top. Search `PLAN-UPDATE`
to find them. `tasks.md` links to the proposals; affected tasks and briefs remain provisional while
decisions are pending. The approved design stays intact until acceptance, then the plan/tasks/briefs
are synchronized and the callout is marked ACCEPTED. Amendments, task ordering and completeness
can be approved in the same review before implementation. Named runs keep large features manageable.
No plan amendments is also a valid result: leave the plan unchanged, omit amendment sections and
report “No plan changes proposed” with the completed task breakdown and briefs.

## 4. Implement and review

An approved `feature-implement` run proceeds end-to-end through implementation, independent review,
corrections and global review. The supervisor resolves technical choices within the agreed outcomes;
user intervention is reserved for major blockers, necessary changes to agreed product scope or
constitutional rules, and operations outside existing authority. Continue independent work when
a task must be parked, preserving pre-existing changes and other sessions' ownership.

`task-implement` runs required gates and writes a minimal committed handoff with implementation
ranges, useful review pointers and material unresolved concerns. `task-review` reads the actual
diff first and chooses LIGHT/STANDARD/FULL internally. Feature-review assignments authorize evident
scoped fixes in the same pass; standalone review remains read-only unless fixes are requested.
Review depth does not waive quality gates. The implementer and reviewer execute checks; the
supervisor tracks completion and routes missing checks or failures back to the responsible agent.

Consequential decisions update the relevant plan text with visible `[IMPL-DECISION-01] — APPLIED`
callouts and a linked index; use PROPOSED only for exceptional decisions requiring the user's
authority. A bug batch without a plan uses the same tags beside the affected tasks. Routine fixes,
ordinary choices and successful test results do not need annotations or reports. No judgement
files or gate journals: `tasks.md` holds status and outstanding blockers/prerequisites only,
distinguishing code blockers, deployment-only conditions and later human checks.

Finish with global review and the consolidated changelog for delivered behavior. The global
reviewer owns final checks, including cross-repository integration, reusing completed checks that
still cover the final changes. Unresolved failures and unavailable required checks remain explicit; never treat
them as success. The user receives the delivered outcome, any consequential decisions in the plan,
outstanding exceptions and a compact usage summary. A five-run shadow-review comparison is opt-in
and ends in a decision; it is not a permanent second reviewer.

## 5. Archive

Invoke `feature-archive` explicitly after shipping and resolving gates. Promote durable insight
into owning architecture pages, conventions, testing, design/published docs as appropriate.
Park actionable unfinished work with enough context to survive deletion. Update roadmap/changelog,
then delete the committed feature working set, including briefs and minimal handoffs.
Git history is the archive; do not create a redundant per-feature summary. Never automatically
retire migration or serialization-upgrade tests as a side effect of archiving.

## Maintenance

Skills are committed under `.agents/skills/`; `.claude/skills` is a compatibility symlink.
Shared files are explicitly synchronized; local references stay local. Every repository remains
independently usable. Update affected documentation with the pattern it describes. Constitutional
changes use `update-constitution` and remain separate from ordinary feature changes.
