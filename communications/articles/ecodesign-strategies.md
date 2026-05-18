# Best practices, measurement, simulation: three strategies for ecodesign and where each one stops

> **Status:** skeleton draft. Full prose to be written after the tutorial-and-documentation specs ship; the SSOT vocabulary and updated mkdocs structure will inform the final wording. The umbrella mkdocs page `ecodesign_strategies.md` is already published and frames the three pillars at navigator depth; this article expands on it for the Boavizta channel and links into its anchors.

## Meta

- **Channel:** Boavizta-blog (Vincent's LinkedIn relay)
- **Owner:** Vincent
- **Target:** 2026-06
- **Length target:** ~1800–2200 words
- **Voice:** substance-heavy, cooperative; no PS mention
- **Audience:** strategy circles 1–2; paradigm-agnostic
- **Companion mkdocs page:** `docs_sources/mkdocs_sourcefiles/ecodesign_strategies.md` (already published — umbrella the article expands on)

---

## Outline

### §1 — The decision question at the heart of ecodesign

Setup: ecodesigning a digital service means deciding **where to invest effort**. Decisions need:
- leverage information ("if I do X, how much does it move the impact?")
- relative-impact estimates across candidate actions

Most ecodesign content covers one of three strategies. Each is useful; each stops short of decision-grade information when used alone. (Note: the article is *not* arguing model-vs-estimate — modeling is a kind of estimation. The contrast is between *strategies* with different decision-support shapes.)

### §2 — Best practices: the catalogue, not the priority

Recipes for what's possible (compress images, lazy-load modules, efficient cloud regions, AVIF over JPEG, etc.).

Two limits:
- **Variability defeats them.** Best practices shine when systems have low variability; digital services are highly variable, so best-practice lists risk pointing you at low-leverage actions on your specific service. *(cite `ecodesign_strategies.md#best-practices-the-catalogue-of-possible-moves`)*
- **They induce guilt without leverage.** A long list of "things you should do" with no information about which matter for your service lands as "you're not doing enough" — without telling you where to start.

→ Differentiator: **"Prioritize, don't guilt-trip."**

### §3 — Measurement: the snapshot, not the projection

What measurement does well: calibrating models against reality where measurable; finding low-hanging optimizations on existing systems. If a named complementary tool is needed in this section, use only the SSOT in `specs/adjacent_tools.md` and explain the integration path rather than building a general market list.

Two limits:
- **You can't measure what isn't there yet.** A feature you haven't built; a scale you haven't reached; a region you haven't deployed to. Decisions need projection — measurement of the present alone can't compare candidate futures.
- **Some footprint isn't visible from the outside.** Manufacturing impact of user devices; fleet-wide footprint of edge devices; embedded carbon in infrastructure. Browser- or runtime-side measurement can't see these.

→ Differentiator: **"Simulate before you act."**

### §4 — Simulation: the projection that lets you decide

What modeling adds: a system description in **usage journeys with steps** (web) or **functionalities** (edge), with volumes and geographies as first-class inputs.

From this description, three things become available:
- the current footprint (overlaps with measurement use cases on the parts that *are* measurable)
- the projected footprint at projected scale
- the footprint after a hypothetical change (*"what if we add AI to this journey?"*, *"what if we drop region X?"*, *"what if we serve 10× the volume?"*)

The structural property that enables this: usage is described in terms a PM/designer can recognize, alongside more technical usage journeys that complete the system story. *(cite `why_efootprint.md` § "user journeys must be part of the model inputs"; `UsageJourney` and `UsagePattern` references)*

→ Differentiator: **"Usage and functionality at the center."**

### §5 — The three legs together

None of the three strategies replaces the others. The recap table comparing what each gives you and what each cannot give alone lives in the umbrella mkdocs page at `ecodesign_strategies.md#the-three-together` — the article reuses it by reference rather than duplicating it, to avoid drift.

The argument is for the right *relationship* between the strategies, not a winner. Measurement, analytics, inventory, and observability can feed the model; simulation turns those inputs into decision-grade scenario comparison.

### §6 — What this looks like in practice

The iterative methodology e-footprint follows *(cite `methodology.md`)*:
1. High-level model first — orders of magnitude. Sometimes that's enough to decide.
2. Refine **if and only if** the rough model isn't decision-grade.
3. Simulate alternatives.
4. Pick the highest-leverage action.

Three concrete answers a simulation can give:
- *"Here's where to act first."* — the standard payoff.
- *"Your service is too small to justify ecodesign effort — focus elsewhere."* — sometimes the most useful answer.
- *"The action you were about to take has a tiny absolute impact at your scale — invest the effort somewhere else."* — the scope-neglect trap, called out before you waste effort.

### §7 — Conclusion

Ecodesign isn't *"what should I do?"* — it's *"what should I do first?"*

Only simulation answers the priority question. Best practices and measurement remain useful in their place. The trinity matters more than the rivalry.

---

## Internal mkdocs links checklist

- `ecodesign_strategies.md#best-practices-the-catalogue-of-possible-moves` — cited in §2 (replaces the former standalone `best_practices.md`)
- `ecodesign_strategies.md#measurement-the-snapshot-of-what-is` — linked from §3 (replaces the former planned standalone `measurement_tools.md`)
- `ecodesign_strategies.md#modeling-the-projection-that-lets-you-decide` — natural §4 anchor for the umbrella's framing of the simulation pillar
- `ecodesign_strategies.md#the-three-together` — natural §5 anchor for the recap table
- `methodology.md` (existing) — cited in §6
- `why_efootprint.md` (existing) — cited in §4 for the user-journey argument
- `UsageJourney`, `UsagePattern` object reference (auto-generated) — referenced in §4

## Adjacent-tool references

- Use `specs/adjacent_tools.md` as the only source for named adjacent tools.
- Do not introduce ad hoc lists in the article draft.
- If a named example is useful, tie it to an integration path: measurement calibrates the model, inventory initializes the model, analytics estimates usage volumes, observability maps usage to backend work.

## LinkedIn derivative hooks

- **Headline hook (Title D):** *"Best practices tell you what's possible. Measurement tells you what is. Only simulation tells you what to prioritize."* — high-impact opener, derives directly from the umbrella's recap table (`ecodesign_strategies.md#the-three-together`). Use as a standalone LinkedIn post around article launch.
- *"The intuition trap: you can feel latency, you can't feel carbon."* — links to `why_efootprint.md`, where the intuition argument lives in full.
- *"When the model says 'you're fine': the most useful answer it can give."* — derived from article §6 (article-specific payoff; not in the umbrella mkdocs page).
- *"Compression, lazy-loading, efficient regions — useful, but which one matters for **your** service?"* — derived from `ecodesign_strategies.md#best-practices-the-catalogue-of-possible-moves`.
- *"Measurement calibrates the model. Simulation turns it into a decision."* — restates the cooperative stance from `ecodesign_strategies.md#the-three-together`.
- *"Why a PM can read an e-footprint model: usage journeys, not raw request counts."* — derived from `ecodesign_strategies.md#modeling-the-projection-that-lets-you-decide`; doubles as cross-promotion for Article #3.
- *"Leaving the parts you can't measure out of scope is a hypothesis: that they're worth zero. Modeling makes the alternative explicit."* — derived from `ecodesign_strategies.md#measurement-the-snapshot-of-what-is`. Reframes the measurement-only stance as a choice, not a default.
- *"Best practices and measurement are catalogues and snapshots. Modeling is the decision arrow that connects them."* — derived from `ecodesign_strategies.md#the-three-together`. One-line landing of the cooperative frame.

## Prose hooks surfaced by the May 2026 Alliancy tribune

A PS-channel instantiation of this framing was published as the [May 2026 Alliancy tribune](2026-05-tribune-alliancy/). Two formulations from that draft are worth reusing in the full Boavizta-channel prose:

- **"Missing third pillar" articulation.** The dominant conceptual frame in the responsible-digital community today rests on two pillars — *measure* (reporting, GHG inventories) and *apply* (best practices). The article can lead with this framing and position simulation as the third, missing pillar — *model to decide*.
- **Finance analogy.** Reporting is to environmental impact what the quarterly close is to budget: indispensable for accountability, insufficient for decisions. Modeling is the **business plan** that informs decisions before they are made. Reusable as the §3 opener or as the LinkedIn hook at article launch.

## Open items for full draft

- [ ] Resolve the §6 "your service is too small" example: anonymized historical case (the Paylib insight, if reusable in anonymized form) or a clean hypothetical.
- [ ] §2 — pick 3–4 best-practice examples concrete enough to land but not platform-specific.
- [ ] §3 — decide whether to include one named complementary tool from `specs/adjacent_tools.md`, or keep the measurement discussion generic.
- [ ] §4 — decide whether to include a small inline example (sample usage journey table) or keep prose-only.
- [ ] Full prose pass once tutorial-and-documentation SSOT vocabulary is settled.
