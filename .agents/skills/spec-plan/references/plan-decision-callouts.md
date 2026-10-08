# Plan decision callouts

Use this presentation for every `PLAN-UPDATE` and `IMPL-DECISION` in `plan.html`. The `spec-tasks` and `feature-implement` skills own when to record a decision, its status and its required explanation; this reference owns the shared HTML presentation.

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
