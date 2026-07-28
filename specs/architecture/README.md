# `specs/architecture/`

The architecture hub: e-footprint's load-bearing engineering patterns, split into one self-contained HTML page per concern. [`index.html`](index.html) is the entry point, with a system map, a curated route for first-time contributors, and task-oriented links.

This folder replaces the former single-file `specs/architecture.md`. Its complete canonical content is preserved across the pages below. Human readers get diagrams and short visible summaries first; implementation detail lives in meaningful `<details class="fold">` sections rather than being removed. The same plain-text HTML remains fully legible to agents, so this folder is still the architecture SSOT.

## Conventions

- Pages need no build step or external/CDN assets. The local `source-links.js` helper is shared by every page: it defaults repository links to GitHub's `main` branch, persists a folder-wide branch selection, and propagates it through page navigation.
- Diagrams use HTML/CSS boxes whose text carries the meaning; color is only a secondary cue.
- Keep load-bearing detail. Fold it under a precise summary instead of deleting it.
- Reusable technical building blocks live below their owning subsystem (for example `recomputation/blocks/`). Links with class `zoom` dock the block on the right on wide screens and fall back to normal full-page navigation on narrow screens.
- Advanced terms have one canonical entry in `glossary.html`. Link the first relevant use with `class="term"`; the shared helper opens that entry in a bottom drawer. Term links inside a right-side technical zoom message the parent page, so the definition drawer and zoom remain visible together. Give enough local context to read the sentence without opening the drawer.
- When a summary or diagram first introduces a difficult concept that is explained elsewhere, link the concept at that first use to its detailed section, technical zoom, or glossary entry. Readers should never have to guess whether an explanation appears later.
- Deep-link pages by anchor. Link other specs relatively.
- Link repository files relatively; `source-links.js` converts them to syntax-highlighted GitHub links for the selected branch. Do not hard-code GitHub blob URLs in individual pages.
- Update the page whose footer claims ownership when a cross-cutting pattern changes.
- The constitution remains authoritative; these pages explain it and never override it.

## Pages

| Page | Canonical for |
|---|---|
| [`index.html`](index.html) | Architecture map, curated getting-started route, task routing |
| [`layers-and-modeling.html`](layers-and-modeling.html) | Layer boundaries, core/framework responsibilities, modeling-object shape, registration, units, doc-as-code |
| [`recomputation.html`](recomputation.html) | Pull-based engine, reactive slots, dependency recording, invalidation, eager outputs, guards, rollback. Technical zooms: [`recomputation/blocks/computed-attribute.html`](recomputation/blocks/computed-attribute.html) for decorator → descriptor → per-instance dispatch, and [`recomputation/blocks/reactive-slot.html`](recomputation/blocks/reactive-slot.html) for slot identity, cache state, dependency edges, pull, and invalidation. |
| [`relationships.html`](relationships.html) | Direct/list/dict links, traversal SSOT, reverse links, `ExplainableObjectDict` input semantics |
| [`persistence.html`](persistence.html) | Minimal JSON contract, cached slots and graph topology, version-aware loading, sources |
| [`attribution.html`](attribution.html) | Atom model, folds, conservation, relay weights, reactive projection caches, edge fabrication |
| [`comparison-and-display.html`](comparison-and-display.html) | System comparison, duplication, Pint/display boundary, doc-as-code metadata |
| [`glossary.html`](glossary.html) | Canonical definitions for advanced Python and recomputation vocabulary; source for bottom-drawer term definitions |
