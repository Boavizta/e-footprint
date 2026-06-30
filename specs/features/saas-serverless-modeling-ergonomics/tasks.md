# SaaS & serverless modeling ergonomics — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

This is a documentation-only feature. Two tasks, split by repo: the library docs land together
(one PR), and the light interface adaptation lands separately.

## Task 1 — Library how-to docs (serverless, database note, attribution) — repo: `e-footprint`

**Status:** Done.

**Goal:** Make serverless modeling, the managed-database option, and per-tenant / per-provider
attribution discoverable through three small docs, all reachable from the "How-to guides" nav. No
new modeling code.

**Files touched:**
- `docs_sources/mkdocs_sourcefiles/serverless_modeling.md` (new) — model a function/edge/per-invocation
  workload as a `server_type=serverless` server (fractional, pay-per-use; ref
  `serverless_update_nb_of_instances`) + a plain `Job`, keeping CPU explicit. Link the E-commerce
  web/database scenario (`{{ config.extra.interface_base_url }}/template/ecommerce/`) as the worked example.
- `docs_sources/mkdocs_sourcefiles/database_modeling.md` (edit) — in the Python sketch, show
  `server_type=ServerTypes.serverless()` with a one-line comment that this models a managed / serverless
  database (pay-per-use, fractional instances).
- `docs_sources/mkdocs_sourcefiles/attributing_footprint.md` (new) — two parts. **Per tenant (demand):**
  one `UsagePattern` per tenant; per-usage-pattern attribution is built in and covers all tiers
  (devices, network, server, storage) — just read it. **Per provider (supply):** group `Server` +
  `Storage` by `provider` and sum, in code; note network and device impacts are not attributed to a
  provider (only infrastructure carries one).
- `mkdocs.yml` — add the two new pages under "How-to guides".
- `efootprint/core/hardware/server_base.py` — only if the `server_type` `param_descriptions` lacks a
  clear explanation of the serverless/autoscaling/on-premise semantics; add/clarify it so the
  explanation is authored once at the SSOT (consumed by both the mkdocs reference and the interface,
  constitution §1.4). Skip if already adequate.
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- None expected (docs-only). If a doc-snippet/example runner exists, extend it to cover the new
  snippets rather than adding a new harness.

**Acceptance:**
- The two new pages render and appear under "How-to guides"; `mkdocs build --strict` is clean (it
  fails on pages missing from nav, so the nav edit is part of this task).
- Every code snippet in the new/edited pages runs against the current API.
- `database_modeling.md` shows the serverless managed-DB option with its comment.
- No new `ModelingObject`, no schema change, no JSON round-trip impact.

**Depends on:** none.

---

## Task 2 — Interface: serverless server type discoverable in the model builder — repo: `e-footprint-interface`

**Goal:** Ensure a user building a model in the interface can select `serverless` as a server type
and understands what it means, so the interface doesn't recreate the discoverability gap.

**Files touched:**
- Model-builder form/render layer for server objects (locate via `specs/architecture.md`). In practice
  `server_type` is a `list_values` field already rendered as a dropdown, and its help text is sourced
  from the library `param_descriptions` (SSOT) — so this is mostly verification plus wiring the
  explanation through if it isn't already shown. Adjust only what's actually missing.
- `CHANGELOG.md` (interface) — entry, if a code change is made.

**Tests added/changed:**
- If a change is made: an interface test asserting `serverless` is among the selectable server-type
  options and its explanation is surfaced (unit or integration layer per `specs/testing.md`).

**Acceptance:**
- In the model builder, a server's type can be set to `serverless`, and the UI explains the
  fractional / pay-per-use semantics (text coming from the library description, not duplicated).
- If the interface already does both, the task is a no-op verification — record that and close it.

**Depends on:** Task 1 (only if the serverless explanation text is authored/clarified in the library
`param_descriptions` there; otherwise independent).

---

## Ordering rationale

Two tasks, one per repo. **Task 1** is the whole library deliverable as a single docs PR: the new
pages, the DB-note edit, and the nav addition have no behavioural pause point between them — and
`mkdocs build --strict` only passes once the new pages are in nav, so splitting pages from nav would
leave a broken intermediate state. The optional `param_descriptions` clarification rides along because
it is the SSOT source for the interface's help text. **Task 2** is a separate repo and a separate PR;
it is kept apart for parallel/independent landability and depends on Task 1 only if the serverless
explanation text needs to originate in the library.
