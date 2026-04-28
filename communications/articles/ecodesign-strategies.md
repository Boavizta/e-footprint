# Best practices, measurement, simulation: three strategies for ecodesign and where each one stops

> **Status:** skeleton draft. Full prose to be written after the tutorial-and-documentation specs ship; the SSOT vocabulary and updated mkdocs structure will inform the final wording. `measurement_tools.md` to be written separately by Vincent first; this article links into it.

## Meta

- **Channel:** Boavizta-blog (Vincent's LinkedIn relay)
- **Owner:** Vincent
- **Target:** 2026-06
- **Length target:** ~1800–2200 words
- **Voice:** substance-heavy, cooperative; no PS mention
- **Audience:** strategy circles 1–2; paradigm-agnostic
- **Companion mkdocs page:** ships into `docs_sources/mkdocs_sourcefiles/ecodesign_strategies.md` when article publishes

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
- **Variability defeats them.** Best practices shine when systems have low variability; digital services are highly variable, so best-practice lists risk pointing you at low-leverage actions on your specific service. *(cite `best_practices.md`)*
- **They induce guilt without leverage.** A long list of "things you should do" with no information about which matter for your service lands as "you're not doing enough" — without telling you where to start.

→ Differentiator: **"Prioritize, don't guilt-trip."**

### §3 — Measurement: the snapshot, not the projection

What measurement does well: calibrating models against reality where measurable; finding low-hanging optimizations on existing systems.

Cooperative tool mention (per strategy §5 stance): EcoIndex (page-load assessments), Green Metrics Tool (energy in CI), Carbonalyser (browser-side network traffic), CarbonAPI. Each is useful for what it measures.

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

None of the three strategies replaces the others.

| Strategy | Gives you | Limit when used alone |
|---|---|---|
| Best practices | A catalogue of possible moves | No leverage info per move |
| Measurement | A diagnostic of the current system | No projection; misses what isn't there yet |
| Simulation | Decision-grade priorities | Requires structured input (constraint as unlock) |

The argument is for the right *relationship* between them, not a winner. Restate the cooperative tool naming: EcoIndex / GMT / Carbonalyser are **complementary** to e-footprint — they address different questions.

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

- `best_practices.md` (existing) — cited in §2
- `methodology.md` (existing) — cited in §6
- `why_efootprint.md` (existing) — cited in §4 for the user-journey argument
- `measurement_tools.md` (Vincent to write first) — linked from §3
- `UsageJourney`, `UsagePattern` object reference (auto-generated) — referenced in §4
- `ecodesign_strategies.md` (this article's mkdocs home, created when article publishes)

## Adjacent-tool references (cooperative, by name)

- **EcoIndex** — page-load environmental assessment.
- **Green Metrics Tool** — energy-and-resource measurement of running software.
- **Carbonalyser** — browser-side network traffic measurement.
- **CarbonAPI** — methodology and infrastructure footprint API.
- *(others to add per Boavizta volunteer feedback on tone)*

## LinkedIn derivative hooks

- **Headline hook (Title D):** *"Best practices tell you what's possible. Measurement tells you what is. Only simulation tells you what to prioritize."* — high-impact opener, derives directly from §5 table. Use as a standalone LinkedIn post around article launch.
- *"The intuition trap: you can feel latency, you can't feel carbon."* — derived from §1, links to `why_efootprint.md`.
- *"When the model says 'you're fine': the most useful answer it can give."* — derived from §6.
- *"Compression, lazy-loading, efficient regions — useful, but which one matters for **your** service?"* — derived from §2.
- *"EcoIndex measures, e-footprint models. We need both."* — derived from §3 / restates strategy §5 cooperative stance.
- *"Why a PM can read an e-footprint model: usage journeys, not raw request counts."* — derived from §4; doubles as cross-promotion for Article #3.

## Open items for full draft

- [ ] Resolve the §6 "your service is too small" example: anonymized historical case (the Paylib insight, if reusable in anonymized form) or a clean hypothetical.
- [ ] §2 — pick 3–4 best-practice examples concrete enough to land but not platform-specific.
- [ ] §3 — confirm with Michalina that Boavizta-blog tone supports naming adjacent tools by name, or whether to genericise.
- [ ] §4 — decide whether to include a small inline example (sample usage journey table) or keep prose-only.
- [ ] Full prose pass once tutorial-and-documentation SSOT vocabulary is settled.
