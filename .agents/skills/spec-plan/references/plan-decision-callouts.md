# Plan decision callouts

Use this presentation for every `PLAN-UPDATE` and `IMPL-DECISION` in `plan.html`. It serves the plans that carry callouts: a bug batch's `plan.html`, and a feature planned before pieces. A feature planned in pieces records a decision as a `Changed:` paragraph of its `plan.md` instead (`specs/workflow-formats.md`). When an implementation decision is recorded, its status and its required explanation are in [the last section](#when-an-implementation-decision-is-recorded).

Put a compact, linked index just after the plan header, only when that decision type exists. Give each decision its own row with the full searchable tag, a short specific title and current status. Use `id="plan-updates"` or `id="impl-decisions"`:

```html
<aside id="impl-decisions" data-note="review">
  <p><strong>Implementation decisions</strong></p>
  <p><a href="#impl-decision-01">[IMPL-DECISION-01] Specific title — APPLIED</a></p>
</aside>
```

Place each decision beside the plan passage it affects. Keep it always visible as an `aside`, with a strong, searchable status heading and the existing explanatory paragraphs, lists and file links. Do not use collapsible `details/summary` for these decisions. Preserve stable IDs and update the index status when a decision changes:

```html
<aside id="impl-decision-01" data-note="review">
  <p><strong>[IMPL-DECISION-01] — APPLIED</strong></p>
  <p>Concrete decision and rationale, with links to the affected code.</p>
</aside>
```

For plan amendments, replace `impl-decisions` / `impl-decision-01` / `IMPL-DECISION-01` with `plan-updates` / `plan-update-01` / `PLAN-UPDATE-01`. Use the same `data-note="review"` styling for proposed, accepted and rejected amendments; their heading and index row display the current status.

The plan's inline style block defines the amber callouts. The [plan starter](../assets/plan.html) carries these rules; merge the variables and rules into an older plan without replacing its reviewed layout:

```css
:root { --blue: #285e91; --blue-bg: #edf4fb; --amber: #835219; --amber-bg: #fff5e5; }
aside[data-note] { border-left: 3px solid var(--blue); background: var(--blue-bg);
  padding: .8rem 1rem; border-radius: 0 .5rem .5rem 0; margin: 1rem 0; font-size: .92rem; }
aside[data-note="review"] { border-color: var(--amber); background: var(--amber-bg); }
aside[data-note] p { margin: .3rem 0; }
```

Other disclosure sections may still use `details/summary`. Keep empty decision indexes and placeholder callouts out of the plan.

## Code evidence links

In every decision callout, give each existing code artifact its own deep VS Code link to the exact definition or relevant call site. Audit function and method names, classes, exception types, fields, variables, event names and protocol headers, whether they appear in `<code>` or ordinary prose. Include `:line:column` in the `vscode://file/` URL and the matching `#Lline:column` in `data-review-source-href`; follow the [source-link convention](plan-review-links.md). Do not put two named symbols under one link if they live at different lines. For a built-in type or a removed symbol with no current definition, link the concrete project call site or regression that supports the claim rather than inventing a location.

Before handoff, inspect every inline `<code>` element in `aside[id^="plan-update-"]` and `aside[id^="impl-decision-"]`: each code artifact must be inside its own file link with a verified line. Keep illustrative snippets and UI copy distinct from existing code references. Check existing links too; a nearby class or function is not a substitute for the named symbol's line.

## When an implementation decision is recorded

Compare the final reviewed implementation with the approved spec/plan, accepted amendments and
starting code, not only with intermediate task commits. Add a callout when the final behavior,
contract or architectural approach materially differs from what the approved plan led the user
to expect; when the run fixes a newly discovered pre-existing defect not already covered by the
plan; or when an internal fix leaves substantial ongoing complexity even though the approved
outcome is preserved. Such complexity includes a new cross-layer contract, state mechanism or
reconciliation path that future maintainers must understand. Explain its cost and why it was
accepted. Judge the intended outcome, not incidental implementation wording. A small fix that
restores approved behavior after an implementation or review regression remains routine; keep
ordinary plan prose accurate without promoting that fix to an `IMPL-DECISION`.

Once consequential choices have stabilized, update their relevant plan passages together to reflect the implemented design. Beside each, add a
visible **`[IMPL-DECISION-01] — APPLIED`** callout with anchor `impl-decision-01`, following the
index and callout format above.
Use stable, increasing IDs across the feature's runs, and a small linked index near the top with
anchor `impl-decisions`. Ctrl+F `IMPL-DECISION` must find the visible callouts.

Make each callout self-contained for plan review. State whether it records a material plan
difference, a newly discovered pre-existing defect or substantial lasting complexity; describe
the concrete failure or constraint and why the choice matters. For complexity, name the added
mechanism and maintenance trade-off even when behavior still matches the plan. Link the affected files
and name the key functions or methods. Explain what changed along the code path and its observable
effect, including relevant state or metadata that is preserved, remapped, or discarded. Give the
run/task and the decisive evidence or trade-off. Keep this focused on the consequential choice,
not a file inventory or a copy of task checks. Include a rejected review suggestion only when
retaining the existing design is itself consequential. Link to the decision from `tasks.md`
when needed; do not duplicate its explanation. The supervisor owns decision resolution and records
the rationale as choices stabilize; do not postpone it until close-out. Document editing and final
code-link consolidation may be delegated to the plan-review-guide agent.

When several functions or repositories participate, map each distinct change from its previous
behavior to its current behavior at the named call site; separate a shared helper from the callers
that use it. Say which path actually failed and which already handled the case, so one broad claim
does not imply every path had the same bug. Use short paragraphs or bullets when that makes the
mapping easier to review. For a superseded decision, name the specific mismatch that ended and
any generic mechanism that remains.

Check every APPLIED claim against the final code, especially whether a helper reads, copies, or
derives its inputs. Distinguish implemented behavior from a possible cleanup or remaining gap;
label the latter explicitly when material. Use specific titles in the index so a reviewer can
identify the issue without opening every callout. Audit each callout's code artifacts and exact
line links using the shared decision format before committing it.

For every `IMPL-DECISION` and changed plan passage, follow
[the shared plan-link convention](plan-review-links.md) for source links,
the right-click diff menu and link refresh. Refresh review links after the consolidated plan edit,
unless a link problem requires another pass. The supervisor checks changed claims and decision
consolidation, including edits delegated to the plan-review-guide agent.

Keep the plan's left reading-order and changed-file column collapsible during review. Use the
native `details/summary` pattern in [the starter](../assets/plan.html): collapsing it should leave a
narrow visible control and give the walkthrough more width beside an editor. Check that the
control stays reachable at narrow widths, works by keyboard, and does not hide the file tree in
print. When editing an older plan, preserve its existing navigation and decision anchors.

`APPLIED` is the normal state after implementation. Reserve **PROPOSED** for exceptional decisions
that actually require the user's authority; keep the current design intact while those are pending.
When accepted and implemented, integrate the change and mark it APPLIED. If rejected, remove the
proposal; keep a concise APPLIED callout only if the decision to retain the design merits review.

Do not annotate small routine fixes, including regressions introduced and repaired within this
run without substantial lasting complexity, passing checks or ordinary choices. If there are no consequential
decisions, add no callouts or index.
