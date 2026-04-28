# Usage and functionality at the center: the e-footprint method

> **Status:** skeleton draft. Full prose to be written after the tutorial-and-documentation specs ship; SSOT vocabulary and updated mkdocs structure will inform final wording.

## Meta

- **Channel:** Boavizta-blog (Vincent's LinkedIn relay)
- **Owner:** Vincent
- **Target:** 2026-07
- **Length target:** ~2000–2500 words
- **Voice:** substance-heavy, technical-but-accessible
- **Audience:** strategy circles 1–2; paradigm-symmetric (web + edge examples throughout)
- **Companion mkdocs page:** lands as enrichment of `methodology.md` and/or a new explanation page (`method_deep_dive.md`)

---

## Outline

### §1 — The shape that distinguishes e-footprint

Most carbon assessment frameworks start from inventory (component lists, host counts, traffic totals) or from lifecycle process stages. e-footprint starts from **how the service is used** — described as **usage journeys with steps** (web) or **functionalities** (edge).

Concrete shape:
- A usage journey is an ordered sequence of steps a "user" takes — where "user" covers humans and automated systems alike (an ML training run is a usage journey).
- Each step makes one or more **jobs** (requests).
- Jobs run on servers, use storage, traverse a network, are received by a device.
- Edge models work in parallel: **functionalities** are the unit of action for deployed devices.
- The bridge primitive (`RecurrentServerNeed`) lets edge fleets call into web-side jobs, so mixed systems are first-class.

Reference primitives: `UsageJourney`, `UsageJourneyStep`, `Job`, `UsagePattern`, plus edge counterparts. *(Verify exact names in latest object reference at draft time.)*

### §2 — Why a PM (or designer) can read it

The vocabulary aligns with how product teams already talk about the service. Examples:
- A web e-commerce model has journeys like *"browse → cart → checkout"* — the same flow a PM ships behind a feature flag.
- An edge IoT model has functionalities like *"send telemetry every 30 seconds"* or *"retrieve firmware update on boot"*.
- Less user-facing journeys (background syncs, ML training, admin tasks) sit alongside without changing the language.

The **non-code/code bridge** matters here: a designer can sketch a journey on paper and have an engineer run the model. The model becomes a shared artifact, not engineering-only.

(*"no one left behind, depth available on demand"* — echo to the interface's guiding principle.)

### §3 — Volumes and geographies as first-class inputs

Two structural inputs most measurement tools don't ask for:
- **Volumes** — how many users, how often, with what hourly distribution. *(`UsagePattern`)*
- **Geographies** — where users access from; where infrastructure is hosted. Drives electricity carbon intensity, network paths, device-fab origins.

Why first-class: the same usage journey at 100 daily users vs 100 million daily users has wildly different decision implications. Carbon-intensity geography multipliers can be order-of-magnitude (coal-grid vs hydro-grid). **The scope-neglect trap** — optimizing a unit by 90% on a low-traffic service produces tiny absolute gains — only becomes visible when volume and geography are explicit inputs, not buried assumptions.

### §4 — Simulation: the payoff (and why the constraint is acceptable)

Once the system is described in usage-journey/functionality terms with volumes and geographies, three things become available:
- **Current footprint**, computable without measurement.
- **Projected footprint**, at projected scale.
- **Hypothetical-change footprint**: *"what if we add an AI step to this journey?"*, *"what if we drop region X?"*, *"what if the journey runs 10× more often?"*

The **constraint** is real: you can't dump a raw request count and expect e-footprint to model it. Inputs must be structured. **The unlock**: that same structure makes everything above queryable. You don't get the simulation power without the structure; that's the trade.

This is the difference between **measurement** (a snapshot of what exists) and **simulation** (decision-grade comparison of what could exist).

### §5 — What this method gives you back: repartition and auditability

The structured input shape pays off twice on the output side.

#### Impact repartition to functional objects

Every gram of CO₂eq the model computes is **attributed back** to the functional objects that caused it:
- A specific journey step.
- A specific job's server-time.
- A specific device fleet's manufacturing.
- A specific region's electricity-mix multiplier.

**Sankey diagrams** are the natural visualization — flow from input objects to impact totals, with branch widths proportional to contribution. *(Reference the existing Sankey HTML examples — host them or screenshot them; deciding visual asset path is a TODO.)* Hugely useful for stakeholder communication: a PM sees *"my journey is responsible for X% of total impact"* and can act on it without translating from a number-only output.

#### Exhaustive auditability

Every calculated value carries:
- Its **formula** — the expression that produced it.
- Its **dependency graph** — the inputs that fed into the formula.
- A traceable path from end metric back to user-supplied inputs and external data sources.

This is built into the modeling layer (`ExplainableObject`). It matters for two reasons:
- **Internal trust** — a sustainability lead defending the numbers internally can show their full derivation.
- **Methodological transparency** — third parties can audit not just the result but the reasoning. A precondition for academic citation, regulatory acceptance, and methodology debate.

Together these two affordances turn the model from a black-box estimator into a **shared, defensible artifact**.

### §6 — Built on the open green-IT stack

e-footprint is not a from-scratch carbon database. It's a **modeling layer** on top of well-curated open-source data sources:

- **BoaviztAPI** — Boavizta's open API for impact factors of hardware (servers, devices, network equipment, etc.). e-footprint queries it for the underlying numerical data; the data work lives there, the system-level modeling lives in e-footprint.
- **EcoLogits** — open-source methodology and data for the environmental impact of generative-AI APIs. e-footprint composes EcoLogits' per-call methodology when modeling LLM-using journeys.

This composition is the point: e-footprint focuses on **system-level structure** (usage journeys, functionalities, propagation, simulation) and delegates **point-data sourcing** to specialized projects. Each does what it does best. The open green-IT stack benefits from the division of labor.

*(These are upstream collaborators, not adjacent competitors — different cooperative framing from the measurement-tools mention in the previous article.)*

### §7 — Conclusion

The shape — usage journeys, functionalities, volumes, geographies — is what makes the rest possible. Without it, you have measurement. With it, you have decisions, repartition you can communicate, and audit trails you can defend.

---

## Internal mkdocs links checklist

- `why_efootprint.md` — for the foundational user-journeys-must-be-input argument
- `methodology.md` — for the iterative process referenced in §4
- `UsageJourney`, `UsageJourneyStep`, `Job`, `UsagePattern` (auto-generated)
- `RecurrentServerNeed` (auto-generated) — bridge primitive
- Edge primitives (verify names in latest object reference)
- `ExplainableObject` reference — for §5 auditability deep-link

## Outbound references

- **BoaviztAPI** — https://github.com/Boavizta/boaviztapi
- **EcoLogits** — canonical URL TBD at draft time
- Sankey HTML examples — existing files in `e-footprint/` repo root (`Full impact repartition sankey.html`, etc.) — decide hosting/embedding for the published article

## LinkedIn derivative hooks

- *"Browse → cart → checkout. The same flow your PM ships is the input to your carbon model."* — derived from §2.
- *"Volume and geography aren't footnotes. They're the difference between 'should you act' and 'should you act here'."* — derived from §3.
- *"What if you added an AI step to your existing user journey? You can model it before building it."* — derived from §4.
- *"Sankey diagrams for carbon: see your service's environmental flow as clearly as a financial budget."* — derived from §5 (visual-friendly, image-attachment-ready).
- *"I can show my full carbon derivation: every formula, every dependency, every source. Why that matters."* — derived from §5 auditability.
- *"e-footprint stands on the shoulders of BoaviztAPI and EcoLogits. The open green-IT stack is real."* — derived from §6.

## Open items for full draft

- [ ] Confirm exact names of edge primitives (functionality, `EdgeDeviceGroup`, etc.) per current object reference at draft time.
- [ ] Sankey diagrams: decide hosting (embed in mkdocs companion page; PNG screenshot in the blog post; link to interactive HTML).
- [ ] EcoLogits canonical URL.
- [ ] §3 example: pick a clean volume-geography contrast (e.g., same service deployed in coal-grid vs hydro-grid region — order-of-magnitude difference).
- [ ] §5 audit example: pick one calculated value and trace its full derivation chain end-to-end (e.g., *"journey X emits Y kg CO₂eq"* → server-time formula → electricity-mix factor → BoaviztAPI hardware fab data).
- [ ] §6: confirm with Boavizta whether to mention any other ecosystem dependencies (carbon-intensity grids data, etc.).
- [ ] Decide whether to include a small inline usage-journey table or keep prose-only.
