# Did AI make my software greener? A carbon break-even experiment

> **Status:** concept note. Originated for a proposed 25-minute talk at GreenIO Paris, December 2026. The carbon model and results do not exist yet; no outcome should be implied before the study is complete.

## Meta

- **Primary format:** conference talk
- **Potential derivative:** evidence-led article after the model and benchmarks are complete
- **Owner:** Vincent
- **Target event:** GreenIO Paris, 2–3 December 2026
- **Audience:** Green IT practitioners, developers, architects and product teams (strategy circles 1a, 1c, 2 and 3)
- **Language:** English by default; the event also offers a French track
- **Working title:** *Did AI make my software greener? A carbon break-even experiment*

## Core question

e-footprint was developed and heavily optimized with extensive use of generative-AI coding assistants. Those assistants had an environmental footprint, but they also helped make the application substantially faster and less memory-intensive.

**Did the operational savings repay the environmental cost of using AI during development—and under which traffic, deployment and lifetime assumptions?**

The intended answer is not a universal “AI is good” or “AI is bad.” It is a break-even analysis: how much use, over how much time, is required for the avoided operational impact to outweigh the additional development impact? A negative result or a result showing that break-even is implausible would be just as valuable as a positive one.

## Why this story is useful

The case combines three perspectives that are usually discussed separately:

1. **AI’s direct footprint:** the inference used during an AI-assisted development process.
2. **Software efficiency:** the compute, memory and infrastructure avoided through architectural and implementation improvements.
3. **Decision-grade modeling:** the future traffic and deployment assumptions that determine whether a technical gain produces a meaningful absolute environmental benefit.

It is also a deliberately reflexive case: use e-footprint to model the development and operation of e-footprint itself. The tool should appear as the method used to investigate an honest question, not as the subject of a product demonstration.

## Connection to the three ecodesign strategies

The story provides a concrete route into the existing communication narrative:

- **Best practices** identify possible improvements: avoid unnecessary recomputation, use appropriate data structures, compress values, right-size precision, cache carefully and profile before optimizing.
- **Measurement** establishes what happened on representative application paths: runtime, peak and retained memory, throughput, container sizing and—where possible—energy consumption.
- **Modeling** projects those observations across traffic, infrastructure, geography and lifetime, and compares them with the development footprint.

Best practices tell us what we could do. Measurement tells us what happened. Modeling tells us whether the decision is likely to pay off.

## Comparison design

The historically meaningful comparison is:

- **Scenario A — conventional development, limited optimization:** the earlier, heavier implementation with little or no AI assistance.
- **Scenario B — AI-assisted development, optimized application:** the observed development process and the current optimized implementation.

These two scenarios change both the development method and the software outcome, so they do not by themselves prove that AI caused the optimizations. To make the reasoning explicit, use a conceptual 2 × 2 frame:

| | Earlier application | Optimized application |
|---|---|---|
| **No or limited AI assistance** | Historical/counterfactual reference | Analytical counterfactual: could the same result have been reached without AI? |
| **Heavy AI assistance** | Isolates AI use without operational gains | Closest to the observed development process |

The two unobserved cells should be modeled as ranges or sensitivity cases, not presented as facts. The goal is an honest environmental account of the project, not a causal study of developer productivity.

## System boundary to investigate

### Development

- AI-assistant inference: models used, input/output tokens or the best available usage proxy, provider and region where known.
- Developer workstation use during the relevant optimization work.
- Additional or avoided test, CI and profiling runs when material and measurable.
- Conventional-development counterfactual expressed as a range of developer time and compute, with assumptions visible.
- Exclude human biological emissions; decide explicitly whether office infrastructure belongs in scope.

### Operation

- Idle production baseline and minimum provisioned infrastructure.
- Ordinary model editing and recalculation.
- Model hydration and serialization.
- Standard results generation.
- Sankey/attribution generation as a distinct, heavier workload.
- Storage, database, cache and network effects where material.
- Server manufacturing and electricity use across the modeled deployment lifetime.

### Functional unit and horizon

Candidate functional units:

- one representative user interaction;
- one active modeling session composed of a stated mix of operations; and
- the complete hosted service over one to three years.

The service-level result should be shown for several traffic trajectories. e-footprint has no representative usage
evidence yet, so a single forecast would create false precision.

## Usage story and benchmark portfolio

The study will separate **benchmark operations**, which can be measured reproducibly, from **usage sessions**, whose
mix and future volume remain assumptions. This lets the traffic projection change without changing the underlying
performance evidence.

The four initial session types are:

1. **Explore an example:** select a maintained template, open results, then inspect a cold and warm Sankey.
2. **Build and refine a model:** load a model, save several structural or assumption changes, revisit results, audit
   selected values and export the model.
3. **Compare an alternative:** duplicate or import a second model, edit it and open the comparison dashboard.
4. **Audit and reuse a model:** import a model, inspect sources and derivations, export its sources, then save the model
   or workspace.

The reusable benchmark atoms underneath those sessions are hydration, import/load, a saved mutation, standard results,
cold attribution/Sankey, warm attribution refinement, comparison, audit and export. Landing-only traffic and the idle
production baseline remain visible but separate. Prospective product journeys are excluded until they ship.

The canonical counts, provisional low/expected/high launch trajectories, fixture portfolio, deployment constraints and
measurement rules live in the companion interface reference:
[`specs/e-footprint-modeling/README.md`](../../../../e-footprint-interface/specs/e-footprint-modeling/README.md).

## Evidence and benchmark discipline

The January 2026 presentation and optimization workbook are historical inputs, not sufficient evidence for the final carbon comparison. Update the inventory with the optimizations shipped since then, including pull-based computation, attribution and Sankey improvements, vectorization, caching, serialization/request-path reductions, and memory-retention work.

Do not multiply isolated speed and memory ratios to derive an environmental gain. Many optimizations affect different paths or overlap. Benchmark complete, representative application operations before and after each relevant architectural baseline.

Distinguish among:

- improvements that reduce work or provisioned capacity;
- improvements that move work outside the response path;
- reliability and containment mechanisms such as memory guards or worker recycling; and
- optimizations for exceptional heavy operations that do not affect ordinary traffic.

Report latency, throughput, peak memory, post-request memory and infrastructure-sizing consequences separately. Energy should be measured where possible and otherwise modeled transparently from resource use.

## Intended narrative for a 25-minute slot

Allow approximately 20 minutes of presentation and five minutes for questions.

1. **The paradox (2 min):** “I used AI to make my software drastically leaner. Was that environmentally rational?”
2. **The experiment (4 min):** boundaries, counterfactuals, evidence quality and why the answer depends on future use.
3. **The optimization story (6 min):** a small number of representative architectural and implementation changes, updated beyond the January 2026 deck.
4. **The carbon break-even (5 min):** development impact, operational savings and curves across traffic/lifetime scenarios.
5. **The broader lesson (3 min):** best practices, measurement and modeling as complementary ecodesign strategies.
6. **Questions (5 min).**

## Editorial stance

- Lead with the question and the experiment, not e-footprint’s feature list.
- Reveal e-footprint as the modeling instrument and reflexive case study.
- Do not claim “1000× greener.” The earlier “1000×” figure concerned a simplified product of compute and memory gains, not a measured lifecycle-carbon reduction.
- Prefer ranges, break-even curves and threshold statements to one headline footprint.
- Make uncertainty part of the lesson: modeling is valuable because it makes consequential assumptions visible.
- Avoid generalized claims about AI-assisted development from this single case.
- Keep the conclusion useful even if the development footprint never breaks even at realistic traffic.

## Candidate titles

- *Did AI Make My Software Greener? A Carbon Break-Even Experiment*
- *I Used AI to Cut My App’s Server Footprint. Was It Worth the Carbon?*
- *Can AI-Assisted Coding Repay Its Carbon Debt?*
- *Using e-footprint on Itself: The Carbon Balance of AI-Assisted Ecodesign*

The first is preferred for now: it is specific, outcome-neutral and keeps the tool out of the headline.

## Possible audience takeaways

After the talk, participants should be able to:

- separate development footprint from operational consequences;
- recognize when a two-scenario comparison hides multiple changing variables;
- build a traffic- and lifetime-dependent break-even analysis instead of relying on an efficiency ratio;
- understand why measurement alone cannot evaluate an unobserved future deployment; and
- use the three ecodesign strategies together to prioritize work.

## Inputs to collect

- [ ] Reconstruct AI-assistant use from provider dashboards, local histories or defensible proxies.
- [ ] Define the development period and which optimization work belongs to the comparison.
- [ ] Establish earlier and current application baselines from tagged commits or reproducible checkouts.
- [ ] Select representative model fixtures and operation mixes.
- [ ] Rerun current end-to-end performance and memory benchmarks in deployment-shaped environments.
- [ ] Determine whether direct energy measurements are feasible for local and hosted benchmarks.
- [ ] Model low, expected and high traffic trajectories and at least two service lifetimes.
- [ ] Review the resulting model and uncertainty ranges with Boavizta/EcoLogits contributors where relevant.
- [ ] Draft the GreenIO abstract only after the comparison design is stable; results may remain pending if the abstract clearly promises an experiment rather than a predetermined conclusion.

## Related repository material

- [`../../strategy.md`](../../strategy.md) — audiences, channel boundaries and core narrative.
- [`../ecodesign-strategies-article.md`](../ecodesign-strategies-article.md) — best practices, measurement and modeling framing.
- [`../usage-and-functionality-method.md`](../usage-and-functionality-method.md) — usage-centered modeling method.
- [`../../../../e-footprint-interface/specs/e-footprint-modeling/README.md`](../../../../e-footprint-interface/specs/e-footprint-modeling/README.md) — canonical interface usage story, benchmark operations and launch traffic cases.
- [`../../../docs_sources/mkdocs_sourcefiles/why_efootprint.md`](../../../docs_sources/mkdocs_sourcefiles/why_efootprint.md) — canonical “why e-footprint?” explanation.
- Interface performance evidence and memory experiments live in the companion `e-footprint-interface` repository; link individual results when the study selects its canonical benchmarks.
