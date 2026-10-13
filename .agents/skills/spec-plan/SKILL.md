---
name: spec-plan
description: Write or refine plan.html after a feature spec is approved. Build an interaction-led, code-grounded implementation plan with linked file navigation. Planning only; no application implementation or task generation.
---

# spec-plan

Help the reviewer picture the smallest justified code change, with little interpretive effort.
The reviewer already knows the spec: the plan is a high-level code review of proposed changes,
not another product explanation.

Output: `specs/features/<feature-name>/plan.html` in the driving repository. Keep the plan
content self-contained and editable throughout review. Planning may include read-only code inspection
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
- Read the repository's `AGENTS.md`, mission, constitution and architecture entry point, then the owning
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
- Ground material unresolved decisions in a concrete scenario from the current code or approved
  scope. Separate observations, proposals and uncertainties; collect ordinary scope questions for
  plan review as described below. Do not manufacture edge cases to force a product decision.

## Audit complexity before human review

Treat the approved spec as scope already shaped by the mission's leanness preference during
`spec-specify`. Planning grounds those choices in actual code and supported interactions, where
new costs or simpler alternatives may become apparent. Look for newly discovered complexity traps
or opportunities where a small behavior change removes substantial implementation cost. Revisit
agreed tradeoffs when new evidence changes their balance; surface proposals for review rather
than silently changing the spec or routinely reopening settled product decisions.

For each added abstraction, state store, queue, synchronization step, validation or recovery
mechanism, identify the agreed behavior it serves and compare it with a smaller extension of
existing code. Remove mechanisms with no demonstrated need. Apply the project's feature and resource
priorities from its mission and `.agents/repository.md`.

Also look for requirements whose implementation cost could be substantially reduced by a small
behavior change. When traced code or necessary proposed mechanisms reveal such an opportunity,
actively recommend it for review: identify the affected spec clause, show the complexity it causes,
and compare the smallest behavior change with implementing the approved requirement. Explain which
states, coordination, persistence or recovery mechanisms would disappear; a difficult implementation
or a line-count estimate alone does not justify changing scope.

Assess the actual user cost, including expected frequency, benefit, failure severity and accessibility.
Distinguish evidence from assumptions and unknowns; do not invent usage figures or savings. A short
spec edit may have large behavioral consequences. Preserve correctness, security and domain invariants;
rare but consequential needs may justify substantial complexity. Separate maintenance benefits from
runtime/resource effects when relevant. Keep a consequential recommendation visible beside the
affected interaction using the proposal guidance below; no separate audit document or new stage is needed.

In particular:

- Do not duplicate existing validation or introduce protections solely for hypothetical stale
  or hand-crafted requests. A “defense in depth” label is not a justification. Preserve existing
  security protections and domain invariants; explain any necessary new check through its
  concrete role in the supported workflow.
- Check which UI surfaces actually exist or remain visible before proposing refresh, draft
  preservation or background synchronization. Distinguish error presentation from edit retention.
- Do not infer a generic framework from one shared helper, or a second data model from information
  already owned elsewhere. Share the smallest useful mechanism.
- Do not automatically add recovery for failures inside a failure handler. Such paths add more
  branches and failure states; require a concrete supported scenario and user benefit before
  planning them. Let ordinary error handling cover exceptional secondary failures.
- Keep required feature work separate from unrelated reliability improvements. Surface confirmed
  bugs with evidence and ownership; park deferred concerns using the user's backlog convention,
  rather than making them feature prerequisites. Do not implement fixes during planning.

This is a check on the agent's reasoning, not a mandatory audit section in the rendered plan.
It does not universally forbid queues, drafts or defensive checks: their cost must earn its place
in the actual feature.

## Reading order and content

Use the following shape, scaled to the feature rather than a fixed number of sections:

1. **Shared data, if it changes.** Start with materially new or changed data structures needed
   by the following interactions. Show their concrete shape, identity and ownership. Existing
   metadata can be read directly; explaining it does not require a wrapper or new data model.
   Omit this opening section when no shared data changes.
2. **Follow interactions through the code.** After the shared data, organize by user action or
   library caller operation. Follow its entry point, changed calls, validation, persistence and
   visible or returned result where relevant. Introduce a helper when its first caller invokes
   it, explaining its owning module and meaningful inputs/outputs in that flow; later flows
   link back. Avoid standalone inventories of implementation functions or query contracts.
   A dedicated contract section is appropriate when the contract itself is the feature's main
   review subject, such as a new public API or integration protocol; still connect it to callers.
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
  a home. At a helper's first call site, name the function, its definition module, caller and
  execution boundary (for example, class definition, instance creation or Save). Reuse function
  names in the explanation instead of ambiguous substitutes such as “the query” or “the resolver”.
  Show concrete inputs/outputs when they clarify the change; keep sketches short enough to reveal
  the contract rather than simulate implementation.
- Distinguish browser feedback, server processing and persistence; name the particular operation
  instead of “the save use case”. Describe rendering at the interaction that causes it.
- State a consistent path base and identify paths outside it and cross-repository ownership.
  Make every reference to existing code in the plan clickable through the reviewer's editor,
  including identifiers in prose, tables, callouts and file summaries. Follow
  [the shared plan-link convention](references/plan-review-links.md), including its click/right-click
  behavior and refresh step. Include the line where a named function or class starts. When
  describing a specific branch, event handler, persistence check or other logic, link to the
  first line of that implementation, not merely to the file or a nearby caller. Keep proposed
  files linked to their file-tree entry until they exist. Distinguish illustrative pseudocode,
  UI copy and protocol values from existing code rather than presenting them as source links.
- Write the implementation walkthrough as a narrated anticipated diff. At each affected call site,
  state what code is added, replaced, or removed and where its result goes next. Treat unmentioned
  behavior as preserved. State a preservation constraint only when the change could plausibly break
  a non-obvious contract; say it once beside that change. Keep rationale that explains a choice or
  rules out a plausible alternative, and replace confusing prose rather than accumulating it.
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
- Keep semantic HTML, one inline style block, native `details/summary`, and no frameworks.
  Include only the shared `specs/review-links.js` for the source-link menu; use inline SVG when useful.
  The starter's IDs/data attributes and CSS anchor highlighting work without JavaScript.
- For plan amendments and implementation decisions, use the shared
  [decision index and callout format](references/plan-decision-callouts.md). Keep decisions visible
  beside the passages they affect; other disclosures may still use `details/summary`.
- Preserve readable long paths, file-labelled code, keyboard focus, narrow-screen flow and print
  layout. Use tables for compact comparisons or verification, not as the default file overview.
  A small feature should not inherit the full visual density of a large cross-repository plan.

## Iteration and handoff

- Refine existing plans in place. Preserve accepted decisions and the user's reviewed layout;
  do not replace the document wholesale to impose the starter. Briefly state meaningful changes
  before editing. Discussion-only requests are not permission to edit.
- Record discovered spec simplifications as `[PLAN-UPDATE-01] — PROPOSED` callouts beside the
  affected plan passage, using the [shared index and callout format](references/plan-decision-callouts.md).
  Give each proposal a stable ID; continue the existing numbering if proposals already exist.
  Include the linked spec clause, precise current/proposed behavior, linked code evidence for the
  complexity removed, user tradeoffs, recommendation and material uncertainties. Label spec changes
  explicitly so the reviewer can distinguish them from implementation choices within approved scope.
  Keep the approved spec and accepted design intact while pending, and mark dependent plan passages
  provisional wherever they rely on the proposed behavior. Continue unaffected planning and present
  meaningful proposals together with the plan for review. Interrupt only when a fundamental scope
  contradiction prevents a coherent reviewable plan even with explicit provisional assumptions;
  complete unaffected work first. Do not manufacture proposals to fill the format.
- When a decision changes, synchronize the walkthrough, snippets, changed-file tree, verification
  and affected spec statements. Update the spec only for agreed capability changes, not to smuggle
  implementation details into it. For an accepted spec proposal, update the spec and plan together
  and mark its callout/index ACCEPTED. For a rejected proposal, mark it REJECTED with a brief reason
  and align the plan with the unchanged requirement. Remove obsolete machinery everywhere it was described.
- Task decomposition records proposed amendments beside affected passages in `plan.html`, using
  the `spec-tasks` content rules and [shared callout format](references/plan-decision-callouts.md).
  Preserve their stable IDs and the approved design while decisions are pending. Apply accepted
  changes to the plan, synchronize affected tasks/briefs, and mark the callouts ACCEPTED.
  Amendment decisions and task approval can happen in the same review.
- During an authorized implementation run, consequential technical decisions use the
  `feature-implement` content rules and shared callout format: update the owning plan passage
  and add an `IMPL-DECISION` callout.
  Keep ordinary fixes and successful test results out of the plan.
- Record recurring review feedback when requested, but do not automatically rewrite the skill
  during feature review. Generalize lessons only when the user authorizes that update.
- Before handoff, check HTML IDs/anchors, local links, file labels and agreement between snippets,
  prose and file-tree entries. Audit all code-styled mentions outside illustrative sketches:
  no existing identifier or implementation detail should remain unlinked, and every source
  link should resolve to the intended file and line. Apply the shared decision callout's
  code-artifact audit to every plan amendment and implementation decision. Refresh plan links as described in
  [the shared convention](references/plan-review-links.md). Inspect the rendered layout when an
  available, permitted viewer supports it; otherwise disclose that visual verification was
  not performed. Do not claim planned application tests have run.
- Report the plan path, substantive changes and remaining decisions concisely. Wait for review;
  do not advance to `spec-tasks` or implementation without authorization. After approval, hand off
  to `spec-tasks` in a fresh session.

## Maintaining this skill

The library repository's `.agents/skills/spec-plan/` is canonical; the interface copy is a mirror.
When editing the skill itself, synchronize both instructions and assets. Keep reusable instructions
here and layout boilerplate in the starter, rather than copying a feature's entire review history
into the skill.
