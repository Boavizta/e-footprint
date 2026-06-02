---
name: spec-plan
description: Use after the user approves a spec.html to write or refine the corresponding plan.html. Second stage of the four-stage spec-driven workflow. Plan answers HOW the spec becomes code; respects architecture.md. Still no code execution.
---

# spec-plan

You are about to write or refine a plan for a feature whose spec is approved. Do NOT write any code yet. The output is `specs/features/<feature-name>/plan.html` — either created fresh, or refined in place if a draft already exists (e.g. when `spec-specify` produced one because the kickoff was design-rich).

## Process

1. **Confirm which feature** with the user. The corresponding `specs/features/<feature-name>/spec.html` must exist and be approved.

2. **Check whether `plan.html` already exists.**
   - **If yes:** treat it as a draft to refine, **not** replace. Read it alongside the spec. Identify (a) gaps the spec implies but the plan doesn't cover, (b) plan content that's stale relative to the spec (e.g. capabilities the spec dropped), (c) anything that violates `architecture.md` or `constitution.md`, (d) implementation-level content that drifted into the spec and should move down to the plan. Surface this delta as a punch list to the user *before* editing. Apply changes via `Edit`, preserving the existing structure. Use AskUserQuestion for any material decision the existing plan doesn't settle.
   - **If no:** draft fresh, following the template below. Use AskUserQuestion for material decisions (which approach, where to put a new module, etc.).

3. **Read `specs/architecture.md` and `specs/constitution.md`.** The plan must respect both. If the plan requires deviating from architecture, the deviation is called out explicitly with rationale.

4. **Save the file** at `specs/features/<feature-name>/plan.html`.

5. **Tell the user** the plan is ready and wait for their review. Do not proceed to tasks.

## Authoring conventions (HTML)

The plan is a **single self-contained `.html` file** — same rules as the spec (see `spec-specify`):

- **Classless / semantic markup** with the `<style>` block from the template. No per-element `class=`, no Tailwind / Bootstrap / React / CDN.
- **Inline everything:** one `<style>` block, no external stylesheet, no `<script src=…>`. Renders with no network.
- **Collapsible sections use native `<details>/<summary>`** — no JavaScript.
- Use an inline `<svg>` for a module / data-flow diagram instead of an ASCII sketch when a diagram helps.

When refining an existing draft (Process step 2), preserve this structure and edit in place.

## Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><Feature title> — Implementation plan</title>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6;
         max-width: 52rem; margin: 2rem auto; padding: 0 1.2rem; color: #1a1a1a; }
  h1 { border-bottom: 2px solid #e0e0e0; padding-bottom: .3rem; }
  h2 { margin-top: 2rem; }
  .status { color: #666; font-size: .9rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; vertical-align: top; }
  th { background: #f5f5f5; }
  code { background: #f4f4f4; padding: .1rem .35rem; border-radius: 3px; font-size: .9em; }
  details { margin: .6rem 0; border: 1px solid #e0e0e0; border-radius: 6px; padding: .4rem .8rem; }
  summary { cursor: pointer; font-weight: 600; }
</style>
</head>
<body>

<h1><Feature title> — Implementation plan</h1>
<p class="status">Status: Plan — under review · <YYYY-MM-DD> · Spec: <a href="spec.html">spec.html</a></p>

<section>
  <h2>1. Approach</h2>
  <p>One- or two-paragraph summary of how the spec becomes code. Name the key abstractions or files.
  An inline <code>&lt;svg&gt;</code> module / data-flow diagram goes here when it helps.</p>
</section>

<section>
  <h2>2. Affected modules</h2>
  <table>
    <thead><tr><th>Module / file</th><th>Change type</th><th>Note</th></tr></thead>
    <tbody>
      <tr><td><code>efootprint/...</code></td><td>new / modified</td><td>...</td></tr>
    </tbody>
  </table>
</section>

<section>
  <h2>3. Cross-cutting concerns</h2>
  <ul>
    <li><strong>Tests:</strong> what test layers (unit / integration / e2e) are affected, and what the new coverage looks like at a glance.</li>
    <li><strong>Migrations:</strong> if JSON schema or DB schema change, identify the migration path.</li>
    <li><strong>Docs:</strong> what spec files (<code>architecture.md</code>, <code>conventions.md</code>) need to follow.</li>
  </ul>
</section>

<section>
  <h2>4. Risks</h2>
  <ul>
    <li>Risk 1 — what could go wrong, mitigation.</li>
    <li>Risk 2 — ...</li>
  </ul>
</section>

<section>
  <h2>5. Alternatives considered</h2>
  <ul>
    <li>Alternative A — why rejected.</li>
    <li>Alternative B — why rejected.</li>
  </ul>
</section>

<section>
  <h2>6. Constitutional notes</h2>
  <p>If the plan touches anything mentioned in constitution §1–§4, note it here. If anything in §4
  is being relaxed, that's a constitutional amendment — stop and use <code>update-constitution</code> first.</p>
</section>

<section>
  <h2>7. Open questions</h2>
  <ul><li>Should be resolved before tasks are emitted.</li></ul>
</section>

</body>
</html>
```

## After writing

Tell the user:

- Path of the new plan file.
- A one-paragraph summary of the approach.
- Any constitutional / architectural notes worth flagging.
- The next step: human review, then `spec-tasks`.
