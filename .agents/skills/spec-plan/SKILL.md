---
name: spec-plan
description: Write or refine plan.html after a feature spec is approved. Build an interaction-led, code-grounded implementation plan with linked file navigation. Planning only; no application implementation or task generation.
---

# spec-plan

Help the reviewer picture the smallest justified code change, with little interpretive effort.
The reviewer already knows the spec: the plan is a high-level code review of proposed changes,
not another product explanation.

Output: `specs/features/<feature-name>/plan.html` in the driving repository. Keep the plan
self-contained and editable throughout review. Planning may include read-only code inspection
and scoped local diagnostics; do not implement application changes or generate tasks.

Start this stage in a fresh session from the approved spec and any existing plan. A decision
missing from those documents is a gap to resolve, not a reason to infer it from an earlier chat.
Refine an existing draft in place. Read `.agents/repository.md` for local adaptations.
Use the collection/binding commands in `specs/agent-tooling.md` at stage start and close-out;
attribute this session to the driving repo, feature and `plan` stage. Missing telemetry is reported,
not a reason to stop planning.

Vincent knows the architecture: link the owning page where a change relies on it, without adding
an architecture-teaching block or repeating established patterns.

## Ground the plan before writing

- Resolve the feature and driving repository from the conversation and workspace workflow.
  Read the approved `spec.html`, any existing plan and relevant review decisions. Ask only if
  the feature or approval is genuinely unclear; do not restart an established review.
- Read the repository's `AGENTS.md`, constitution and architecture entry point, then the owning
  documentation for affected paths. Both repositories use `specs/architecture/index.html`;
  consult `.agents/repository.md` if a documentation transition is still in progress.
  Flag architectural deviations; constitutional changes require explicit approval through the
  constitutional workflow, not an incidental plan paragraph.
- Trace the relevant existing code and tests, including success, error, cancellation, rendering
  and persistence behavior where the proposed change touches them. Documentation alone is not
  evidence of what an endpoint, hook or browser handler currently does.
- Look for existing mechanisms before proposing abstractions. Explain a refactor through:
  what happens today; what is extracted or changed and who uses it; what genuinely new behavior
  it enables. Preserve unrelated behavior.
- Ask about material unresolved decisions with a concrete scenario grounded in the current
  code or approved scope. Separate observations, proposals and uncertainties. Do not manufacture
  edge cases to force a product decision.

## Audit complexity before human review

For each added abstraction, state store, queue, synchronization step, validation or recovery
mechanism, identify the agreed behavior it serves and compare it with a smaller extension of
existing code. Remove mechanisms with no demonstrated need.

In particular:

- Do not duplicate existing validation or introduce protections solely for hypothetical stale
  or hand-crafted requests. A “defense in depth” label is not a justification. Preserve existing
  security protections and domain invariants; explain any necessary new check through its
  concrete role in the supported workflow.
- Check which UI surfaces actually exist or remain visible before proposing refresh, draft
  preservation or background synchronization. Distinguish error presentation from edit retention.
- Do not infer a generic framework from one shared helper, or a second data model from information
  already owned elsewhere. Share the smallest useful mechanism.
- Keep required feature work separate from unrelated reliability improvements. Surface confirmed
  bugs with evidence and ownership; park deferred concerns using the user's backlog convention,
  rather than making them feature prerequisites. Do not implement fixes during planning.

This is a check on the agent's reasoning, not a mandatory audit section in the rendered plan.
It does not universally forbid queues, drafts or defensive checks: their cost must earn its place
in the actual feature.

## Reading order and content

Use the following shape, scaled to the feature rather than a fixed number of sections:

1. **Shared data, if it changes.** Show significant new or extended structures before the
   interactions that need them. Include concrete fields, central return types, identity and
   ownership where relevant. Do not invent a structure just to fill this section.
2. **Follow interactions through the code.** Organize by user action or functional flow, not
   technical layer. For a library-only feature, follow the caller's operation. Name the entry
   point, changed calls/data and visible or returned result. Introduce shared helpers with their
   first consumer, then link back.
3. **Implementation sequence and verification.** Keep dependency order distinct from reading
   order. Name independently useful steps and any approved ride-along refactor. Map important
   behavior and regression risks to existing test layers; do not enumerate helper-internal
   assertions or duplicate library tests without a concrete reason.
4. **Material decisions only.** Keep risks, alternatives, migrations, documentation changes and
   unresolved questions where they help review. Omit empty sections, generic reassurance and
   unchanged rules. Keep actual review decisions visible, not hidden as agent-only detail.

Within the walkthrough:

- Title each code block with its owning file. Split multi-file snippets; label payload examples
  as payloads and name their producer/consumer. Mark existing versus proposed code.
- Show important structure changes and their callers, not opaque type names or callbacks without
  a home. Keep sketches short enough to reveal the contract rather than simulate implementation.
- Distinguish browser feedback, server processing and persistence; name the particular operation
  instead of “the save use case”. Describe rendering at the interaction that causes it.
- State a consistent path base and identify paths outside it and cross-repository ownership.
  Link to existing code when useful; link proposed files to their file-tree entry instead.
- Every sentence should convey a change, constraint, necessary rationale or decision. Omit
  ordinary behavior and spec repetition. Prefer concrete vocabulary over terms that suggest
  machinery that does not exist. Clarification should replace confusing prose, not accumulate it.
- Examples illustrate generic mechanisms unless explicitly declared exceptions. Do not turn
  a product example or this review's particular implementation choices into universal rules.

## HTML review surface

For a new plan or an authorized format refresh, read and adapt
[the HTML starter](assets/plan.html). It contains the review layout, not a prescribed architecture.
Replace its uppercase placeholders and authoring prompts; remove unused sample sections and
update navigation, file mappings and highlight selectors together.

- Use a linked reading-order navigation and collapsible filesystem-like changed-file tree,
  not an affected-files table. Mark new, modified, renamed or removed files; include a short
  purpose and links back to the relevant interactions. Highlight files associated with the
  selected step. List changed files, not every referenced dependency.
- Make the entire left navigation and changed-file column collapsible with a keyboard-accessible
  native `details/summary` control. When collapsed, shrink its layout column to a narrow visible
  reopen control so the plan gains width beside an editor. Keep the control reachable above the
  content at narrow viewport widths, and expand the changed-file tree for print.
- Put code relationships or sequence diagrams beside the interaction they explain. Link
  relevant nodes to files/steps and label what arrows mean. Never use an arrow merely to separate
  filenames. No mandatory overview diagram; non-code visuals are welcome when they clarify
  something prose or a small table cannot.
- Keep semantic HTML, one inline style block, native `details/summary`, and no frameworks,
  external assets or scripts. Use inline SVG when useful. The starter's IDs/data attributes and
  CSS anchor highlighting support navigation without JavaScript.
- Preserve readable long paths, file-labelled code, keyboard focus, narrow-screen flow and print
  layout. Use tables for compact comparisons or verification, not as the default file overview.
  A small feature should not inherit the full visual density of a large cross-repository plan.

## Iteration and handoff

- Refine existing plans in place. Preserve accepted decisions and the user's reviewed layout;
  do not replace the document wholesale to impose the starter. Briefly state meaningful changes
  before editing. Discussion-only requests are not permission to edit.
- When a decision changes, synchronize the walkthrough, snippets, changed-file tree, verification
  and affected spec statements. Update the spec only for agreed capability changes, not to smuggle
  implementation details into it. Remove obsolete machinery everywhere it was described.
- Task decomposition records proposed amendments beside affected passages in `plan.html`, using
  the `spec-tasks` review format: visible `[PLAN-UPDATE-01] — PROPOSED` callouts and a linked index.
  Preserve their stable IDs and the approved design while decisions are pending. Apply accepted
  changes to the plan, synchronize affected tasks/briefs, and mark the callouts ACCEPTED.
  Amendment decisions and task approval can happen in the same review.
- During an authorized implementation run, consequential technical decisions use the
  `feature-implement` format: update the owning plan passage and add an `IMPL-DECISION` callout.
  Keep ordinary fixes and successful test results out of the plan.
- Record recurring review feedback when requested, but do not automatically rewrite the skill
  during feature review. Generalize lessons only when the user authorizes that update.
- Before handoff, check HTML IDs/anchors, local links, file labels and agreement between snippets,
  prose and file-tree entries. Inspect the rendered layout when an available, permitted viewer
  supports it; otherwise disclose that visual verification was not performed. Do not claim
  planned application tests have run.
- Report the plan path, substantive changes and remaining decisions concisely. Wait for review;
  do not advance to `spec-tasks` or implementation without authorization. After approval, hand off
  to `spec-tasks` in a fresh session.

## Maintaining this skill

The library repository's `.agents/skills/spec-plan/` is canonical; the interface copy is a mirror.
When editing the skill itself, synchronize both instructions and assets. Keep reusable instructions
here and layout boilerplate in the starter, rather than copying a feature's entire review history
into the skill.
