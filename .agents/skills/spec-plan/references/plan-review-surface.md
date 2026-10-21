# Plan review surface

Shared rules for every `plan.html`, whether it plans a feature (`spec-plan`) or a diagnosed bug batch
(`bug-fixes-plan`). Those skills own the reading order and the content of their plans; this reference
owns how a code-grounded walkthrough is written, how the HTML surface is built, and what to audit
before handoff. Edit it here; do not restate these rules in a skill.

## Code-grounded walkthrough

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
  [the shared plan-link convention](plan-review-links.md), including its click/right-click
  behavior and refresh step. Include the line where a named function or class starts. When
  describing a specific branch, event handler, persistence check or other logic, link to the
  first line of that implementation, not merely to the file or a nearby caller. Keep proposed
  files linked to their file-tree entry until they exist. Distinguish illustrative pseudocode,
  UI copy and protocol values from existing code rather than presenting them as source links.
- Write the walkthrough as a narrated anticipated diff. At each affected call site, state what
  code is added, replaced, or removed and where its result goes next. Treat unmentioned behavior
  as preserved. State a preservation constraint only when the change could plausibly break a
  non-obvious contract; say it once beside that change. Keep rationale that explains a choice or
  rules out a plausible alternative, and replace confusing prose rather than accumulating it.
- Explain a refactor through: what happens today; what is extracted or changed and who uses it;
  what genuinely new behavior it enables. Preserve unrelated behavior.
- Examples illustrate generic mechanisms unless explicitly declared exceptions. Do not turn
  a product example or this review's particular implementation choices into universal rules.
- The reviewer knows the architecture: link the owning architecture page where a change relies
  on it, without adding an architecture-teaching block or repeating established patterns.

## HTML review surface

For a new plan or an authorized format refresh, read and adapt
[the HTML starter](../assets/plan.html). It contains the review layout, not a prescribed
structure. Replace its uppercase placeholders and authoring prompts; remove unused sample
sections and update navigation, file mappings and highlight selectors together.

- Use a linked reading-order navigation and collapsible filesystem-like changed-file tree,
  not an affected-files table. Mark new, modified, renamed or removed files; include a short
  purpose and links back to the relevant steps. Highlight files associated with the selected
  step through the starter's `data-steps` mapping. List changed files, not every referenced
  dependency. A file touched by several steps lists all of them: that is where ordering and
  merge conflicts show.
- Make the entire left navigation and changed-file column collapsible with a keyboard-accessible
  native `details/summary` control. When collapsed, shrink its layout column to a narrow visible
  reopen control so the plan gains width beside an editor. Keep the control reachable above the
  content at narrow viewport widths, and expand the changed-file tree for print.
- Put code relationships or sequence diagrams beside the step they explain. Link relevant nodes
  to files/steps and label what arrows mean. Never use an arrow merely to separate filenames.
  No mandatory overview diagram; non-code visuals are welcome when they clarify something prose
  or a small table cannot.
- Keep semantic HTML, one inline style block, native `details/summary`, and no frameworks.
  Include only the shared `specs/review-links.js` for the source-link menu; use inline SVG when
  useful. The starter's IDs/data attributes and CSS anchor highlighting work without JavaScript.
- Use the starter's `[data-chip]` badges for short status labels on a step (repository, verdict,
  difficulty); keep `[data-change]` for file-tree change kinds.
- For plan amendments and implementation decisions, use the shared
  [decision index and callout format](plan-decision-callouts.md). Keep decisions visible beside
  the passages they affect; other disclosures may still use `details/summary`.
- Preserve readable long paths, file-labelled code, keyboard focus, narrow-screen flow and print
  layout. Use tables for compact comparisons or verification, not as the default file overview.
  A small plan should not inherit the full visual density of a large cross-repository plan.

## Iteration

Refine existing plans in place. Preserve accepted decisions and the user's reviewed layout; do
not replace the document wholesale to impose the starter. Briefly state meaningful changes before
editing. Discussion-only requests are not permission to edit. When a decision changes, synchronize
the walkthrough, snippets, changed-file tree and verification together, and remove obsolete
machinery everywhere it was described.

## Handoff audit

Before handoff, check HTML IDs/anchors, local links, file labels and agreement between snippets,
prose and file-tree entries. Audit all code-styled mentions outside illustrative sketches: no
existing identifier or implementation detail should remain unlinked, and every source link should
resolve to the intended file and line. Apply the shared decision callout's code-artifact audit to
every plan amendment and implementation decision. Refresh plan links as described in
[the shared convention](plan-review-links.md). Inspect the rendered layout when an available,
permitted viewer supports it; otherwise disclose that visual verification was not performed. Do
not claim planned application tests have run.
