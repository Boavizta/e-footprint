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

Walkthrough writing, the HTML surface and the handoff audit follow
[the shared plan review surface](references/plan-review-surface.md), which `bug-fixes-plan` also uses.
This skill owns what a feature plan contains and in which order.

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
- Look for existing mechanisms before proposing abstractions. Explain a refactor as the shared
  surface rules describe: today, what changes and who uses it, what new behavior it enables.
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
existing code. Remove mechanisms with no demonstrated need. A sync, queue, replacement or pending-flag
rule is a smell: before proposing one, check whether the existing lock already serialises the actions,
and list the descendants that would inherit the attribute. Apply the project's feature and resource
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

Within the walkthrough, apply the
[code-grounded walkthrough rules](references/plan-review-surface.md#code-grounded-walkthrough):
file-titled snippets, existing versus proposed code, helpers introduced at their first call site,
linked identifiers, and the narrated anticipated diff.

## HTML review surface

Build the page as described in
[the shared review surface](references/plan-review-surface.md#html-review-surface), starting from
[the HTML starter](assets/plan.html) for a new plan. Steps are the interactions of the reading
order above; the changed-file tree highlights the files of the selected interaction.

## Iteration and handoff

- Refine existing plans in place, following the
  [shared iteration rules](references/plan-review-surface.md#iteration).
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
- Run the [shared handoff audit](references/plan-review-surface.md#handoff-audit): anchors,
  links, file labels, snippet/prose/tree agreement, linked identifiers, link refresh and
  rendered-layout inspection.
- Report the plan path, substantive changes and remaining decisions concisely. Wait for review;
  do not advance to `spec-tasks` or implementation without authorization. After approval, hand off
  to `spec-tasks` in a fresh session.

## Maintaining this skill

The library repository's `.agents/skills/spec-plan/` is canonical; the interface copy is a mirror.
When editing the skill itself, synchronize both instructions and assets. Keep feature-plan
content rules here, rules shared with `bug-fixes-plan` in `references/plan-review-surface.md`, and
layout boilerplate in the starter, rather than copying a feature's entire review history into
the skill.
