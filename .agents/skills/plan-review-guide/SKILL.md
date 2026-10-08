---
name: plan-review-guide
description: Turn an implemented feature's existing plan.html, or selected sections, into a review guide with verified code links and consolidated implementation decisions while preserving the reviewed plan's structure. Use after implementation review or independently on delivered work.
---

# Plan review guide

The user has already invested in understanding the approved plan. Preserve its backbone:
section order, anchors, terminology, examples, rationale, navigation and reading granularity.
Layer implementation evidence onto familiar passages. Rewrite only where the final implementation
differs or the original wording would mislead the reviewer; do not replace the plan with a new
architecture document, implementation report or chronological narrative.

## Scope and evidence

- Resolve the driving repository and requested plan/section scope. Read its `AGENTS.md`,
  `.agents/repository.md`, architecture entry point and owning pages before tracing code.
  Use the approved plan, accepted amendments, task status, supervisor-resolved decisions and
  final implementation ranges across affected repositories. Current files, including approved
  uncommitted corrections, determine link targets; commit ranges identify the delivered scope.
- Edit the existing plan in place. Application code, task status and product scope remain with
  the supervisor and implementation agents. For section-only requests, preserve everything
  outside the requested scope, apart from necessary matching navigation/file-tree links.
- Trace each claim to actual code. A handoff or passing test alone does not establish that a
  particular branch implements the claim. Follow relevant callers when the behavior spans files.
  Link tests when they provide useful review evidence, without copying test results into the plan.

## Convert the plan

- Keep matching prose verbatim, inserting links on existing words. Do not reword a matching
  claim merely to introduce a helper name or explain its implementation; use the link for that
  evidence. Keep examples and disclosure labels, and do not reinterpret a generic payload as a
  particular scenario's expected output unless the original plan establishes that meaning.
  Replace stale proposed-file references with actual source
  links. Link declarations for structures and named symbols; link the first relevant branch or
  call site for behavior. Preserve snippet shape when it matches; correct material differences
  and distinguish abridged implemented code from illustrative payloads or pseudocode.
- Use [the shared source-link convention](../spec-plan/references/plan-review-links.md), including
  verified line/column targets, portable `data-review-source-href` attributes and the existing
  click/right-click menu. Put links on the existing words or identifiers; avoid appending file
  inventories. Each distinct code artifact gets its own target when locations differ.
- Mark a passage or section **Implemented as planned** only when its claims match the final
  code. Mixed sections need passage-level distinctions: implemented with a linked decision,
  unfinished, or requiring supervisor resolution. Preserve existing decision statuses; code
  evidence alone does not turn APPLIED into user-validated. Avoid changing tense mechanically.
- Update affected file-tree entries and snippet labels in the same scope, preserving navigation
  IDs and highlighting. Keep removed/proposed artifacts distinguishable from current source.
  Link the replacement or concrete regression when an old symbol no longer exists.

## Decisions and discrepancies

The supervisor owns consequential choices and their rationale. Read the consequential-decision
criteria in [feature-implement](../feature-implement/SKILL.md#consequential-decisions-in-the-plan)
and use [the shared callout format](../spec-plan/references/plan-decision-callouts.md).

Consolidate supervisor-resolved decisions beside their owning passages, with accurate current
code links and a matching index. Preserve stable IDs, approved explanations and meaningful
superseded history. Do not invent a rationale, accept a pending proposal, create a new decision
on your own, or silently describe a discrepancy as equivalent to the approved plan.

For an apparent material mismatch or uncertain implementation claim, give the supervisor the
plan passage, concrete code evidence and unresolved question. Leave that passage's status
unconfirmed and continue independent sections. On a standalone invocation, surface it to the
user with the same evidence. Routine wording corrections need no decision callout.

## Verify and hand off

After consolidated edits, run the link converter from the driving repository as documented in
the source-link convention. Check new and existing links in scope against the final files and
intended lines, including decision callouts. Check unique HTML IDs, internal anchors, snippets,
file-tree mappings and consistency between status labels and the evidence.

Inspect the rendered page and normal-click/right-click behavior when a permitted viewer is
available; disclose unavailable visual or editor-launch verification. Review the diff to ensure
the approved backbone and any section boundary were preserved. Application tests are not rerun
for this documentation pass; report application concerns to the supervisor instead.

Return the edited plan path, substantive corrections and any unresolved discrepancies or
verification limitations. The supervisor checks changed claims and decision consolidation before
the final commit; it need not duplicate every verified link. Escalate substantial unresolved
cross-repository tracing or architectural ambiguity to the configured standard implementer,
using the existing edits and evidence. The supervisor resolves consequential choices.

## Shared maintenance

The library's `.agents/skills/plan-review-guide/` is canonical and the interface copy is mirrored
through `.agent-tooling-sync.json`. Runtime role and model defaults live in `specs/agent-tooling.md`.
