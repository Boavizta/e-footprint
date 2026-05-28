---
name: spec-specify
description: Use when the user wants to start a new feature in this repo. Walks the agent through writing specs/features/<feature-name>/spec.html — the first stage of the four-stage spec-driven workflow (specify → plan → tasks → implement). Read-only on code. May also draft plan.html in the same pass when the kickoff is design-rich.
---

# spec-specify

You are about to start a new feature spec. Do NOT write any code or modify any source files. The primary output is `specs/features/<feature-name>/spec.html`. When the kickoff is design-rich (see Process step 3), you also draft `plan.html` in the same pass so design detail is not lost.

## What goes where

- **`spec.html` = WHAT and WHY.** Capability, audience, why-now, success criteria phrased as user-observable outcomes, in/out scope at the capability level, constraints (mission / constitution / external dependencies).
- **`plan.html` = HOW.** Module layout, class/method/parameter names, defaults, internal hypotheses, refactor steps, code-level patterns to mirror, file paths, unit/mapping tables.

If you can't write a sentence without naming a file, class, or method, it's plan content.

## Process

1. **Confirm the feature name** with the user (kebab-case, descriptive). If the slot already exists at `specs/features/<feature-name>/`, stop and ask whether to overwrite or pick a different name.

2. **Read `specs/mission.md` and `specs/constitution.md`** before drafting. The spec must be in scope per `mission.md` and respect `constitution.md`. If it isn't, surface the conflict before writing.

3. **Classify accumulated context.** Audit the prior conversation for design-level signals: file paths, class/method names, parameter defaults, refactor instructions, citations of existing-code patterns to copy, decisions made about provider/model splits, where-things-live, internal vs external parameters, etc. If load-bearing design content is already in the conversation, drafting only `spec.html` will either (a) discard that content or (b) leak it into the spec. In that case, produce **both** `spec.html` and a draft `plan.html` in this same pass. Tell the user explicitly that you're producing two files and why. If the conversation is purely capability-framed, draft only `spec.html`.

4. **Draft the spec** following the template below. Use AskUserQuestion for any unclear *capability-level* question (audience, user outcome, in/out scope). Do not invent answers. Do **not** ask design-level questions here — those go to `spec-plan`. If the user volunteers a design decision, capture it for `plan.html` instead of folding it into the spec.

   For any user-facing surface, **embed a clickable HTML mockup or an inline SVG of the interaction / data flow** in §4 rather than describing it in prose. Showing the experience is the main reason the spec is HTML — prefer a concrete artifact the user can look at and react to over a paragraph that approximates it.

5. **Draft the plan (if step 3 triggered it).** Follow the `spec-plan` template. The plan is explicitly marked as a draft and the user is invited to refine it during the `spec-plan` stage (which is now a refinement pass — see that skill).

6. **Self-check.** Re-read the spec. For each bullet in §3, ask: *is this a capability the user experiences, or a how-we-build-it decision?* If the latter, move it to `plan.html`.

7. **Save the file(s).**

8. **Tell the user** the spec (and plan, if drafted) is ready and wait for their review. Do not proceed to tasks.

## Authoring conventions (HTML)

The spec is a **single self-contained `.html` file** — openable offline, shareable as one file, committed to git and deleted at archive time. Keep it lean so it reads cleanly both in a browser and as agent context in later stages:

- **Classless / semantic markup.** Use semantic tags (`<h2>`, `<table>`, `<details>`, `<code>`) and the `<style>` block from the template. Do **not** add per-element `class=` attributes, and do **not** pull in Tailwind, Bootstrap, React, or any CDN — class-soup and frameworks bloat the diff and the tokens every later stage pays to read this file.
- **Inline everything.** One `<style>` block, no external stylesheets, no `<script src=…>`. The file must render with no network.
- **Collapsible sections use native `<details>/<summary>`** — no JavaScript.
- **JavaScript only for an interactive mockup in §4** (e.g. a slider that tunes a parameter), scoped to that mockup, vanilla JS, no framework. Everywhere else, no JS.

## Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><Feature title> — Spec</title>
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
  .mockup { border: 1px dashed #999; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
  blockquote { border-left: 3px solid #ccc; margin: 1rem 0; padding: .2rem 1rem; color: #555; }
</style>
</head>
<body>

<h1><Feature title></h1>
<p class="status">Status: Spec — under review · <YYYY-MM-DD></p>

<section>
  <h2>1. Problem and audience</h2>
  <ul>
    <li>What user problem does this solve?</li>
    <li>Who experiences it (user persona, frequency, severity)?</li>
    <li>Why is it worth solving now?</li>
  </ul>
</section>

<section>
  <h2>2. Success criteria</h2>
  <p>How do we know this feature is done? Each criterion must be testable.</p>
  <ul>
    <li>...</li>
  </ul>
</section>

<section>
  <h2>3. Scope</h2>
  <blockquote>Capability-level only. File paths, class/method/parameter names, refactor
  instructions, internal hypotheses, and "mirror pattern X" code-level decisions belong in
  <code>plan.html</code>, not here. If you can't say it without naming a file, class, or method,
  it's plan content.</blockquote>
  <details open><summary>In scope</summary>
    <ul><li>...</li></ul>
  </details>
  <details><summary>Out of scope (this iteration)</summary>
    <ul><li>...</li></ul>
  </details>
</section>

<section>
  <h2>4. UX / interface (if applicable)</h2>
  <p>If the feature has a user-facing surface, show it here at the conceptual level. Prefer a
  concrete artifact over prose:</p>
  <div class="mockup">
    <!-- Clickable HTML mockup, or an inline <svg> of the interaction / data flow.
         Vanilla JS allowed here only, scoped to this mockup. -->
  </div>
</section>

<section>
  <h2>5. Constraints</h2>
  <ul>
    <li>Performance, compatibility, dependencies, regulatory, etc.</li>
    <li>References to <code>constitution.md</code> or <code>architecture.md</code> if applicable.</li>
  </ul>
</section>

<section>
  <h2>6. Open questions</h2>
  <ul><li>...</li></ul>
</section>

<section>
  <h2>7. Resuming from cold context</h2>
  <ol>
    <li>Read this file end to end.</li>
    <li>Read <code>plan.html</code> (when written) for ordered steps and test gates.</li>
    <li>Re-read the relevant spec files (<code>specs/architecture.md</code>,
    <code>specs/conventions.md</code>) for code-style and architectural constraints.</li>
  </ol>
</section>

</body>
</html>
```

## After writing

Tell the user clearly:

- Path(s) of the new file(s) — `spec.html`, and `plan.html` if you drafted one.
- A one-paragraph summary of the spec.
- If a plan was drafted: a one-sentence note that it captured design content from the kickoff conversation and will be refined in the `spec-plan` stage.
- Any open questions surfaced during drafting.
- The next step: human review, then `spec-plan`.
