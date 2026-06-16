# e-footprint — messaging one-pager

> **What this is.** The shared narrative for e-footprint, in one page. It locks the words the three actors (Boavizta, Publicis Sapient, Vincent) use across every channel. All other communication pieces cite this document.
>
> **Source of truth.** This is the *what we say*. The *why* and the per-actor *rules* live in [`strategy.md`](./strategy.md) — narrative rationale in §3, coexistence rules in §4. If this one-pager and `strategy.md` ever disagree, `strategy.md` wins and this file is corrected.
>
> **Status:** draft, pending review by the three actors.

---

## The thesis (load-bearing across every channel)

> **Ecodesigning a digital service isn't "what could I do?" but "what should I do first, and what impact would that have?"**

Three complementary strategies answer parts of that question — **best practices** (*what's possible*), **measurement** (*what is*), and **modeling** (*what to prioritize*) — and they feed each other rather than compete. e-footprint occupies the third: it models the whole service from how it's used and lets you **simulate** a change before you make it. That's the leg that turns the other two into decisions.

> **One-liner:** *Best practices tell you what's possible. Measurement tells you what is. Only simulation tells you what to prioritize.*

The full argument — why an explicit model is necessary, and what a model must contain — is the canonical [*Why e-footprint?*](../docs_sources/mkdocs_sourcefiles/why_efootprint.md) explanation page (published on the docs site). This one-pager distills it for communication; cite that page for substance.

## The three differentiating messages

The reusable distillation of the thesis: use these three, in these words, across all channels.

1. **Beyond the best-practice checklist — prioritize what matters here.**
   A checklist ("what could I do?") is a catalogue of candidate moves, but what dominates one service's footprint is negligible in another's. e-footprint shows which moves actually move the needle on *your* service, and in what order. That guards against the scope-neglect trap, where a 90% cut on a minor contributor saves less than a modest cut on the dominant one.

2. **Beyond the measurement snapshot — simulate before you act.**
   Measurement is a snapshot of the running system; it can't see a feature you haven't built or a scale you haven't reached. e-footprint models the environmental ROI of a change *before* you make it, just like its business ROI. *"What if we add an AI step, drop region X, serve 10× the volume?"*

3. **Actionable modeling must put usage and functionality at the center.**
   e-footprint describes a service the way its team already sees it: the **usage journeys** people follow and the **functionalities** it performs, in real volumes and geographies. That keeps the model readable by the whole team, not just engineers. It also makes the what-ifs above possible, because many of the changes a team wants to weigh (adding a feature, simplifying a journey, dropping a step) alter a functionality, so functionality has to be represented in the model in the first place.

## Who it is for

Product teams and operational sustainability leads whose decisions shape a digital service's or device fleet's impact — engineers, designers, PMs, architects on the web side; hardware, embedded, and IoT teams on the industrial/edge side; and the green-IT / ecodesign practitioners who work alongside them. e-footprint is deliberately a *whole-team* tool: approachable for non-code roles, with depth available on demand — *no one left behind*.

## What e-footprint is — and is not

| e-footprint **is** | e-footprint is **not** |
|---|---|
| A modeling tool that produces **estimates and orders of magnitude** | A certification, a label, or a measurement instrument |
| A **decision-support** tool for prioritizing ecodesign effort | A compliance / CSRD reporting tool |
| **Auditable**: every figure carries its formula, dependency graph, and data sources | A black box or a sealed score |
| A **modeling layer** on the open green-IT stack (it composes BoaviztAPI, EcoLogits) | A from-scratch carbon database |
| A **complement to** measurement and best practices | A replacement for them, or a rival to be ranked against other tools |
| **Open source, hosted by Boavizta** | A proprietary or vendor product |

Two guardrails worth stating plainly, because most communication risk comes from blurring them:

- **Estimate, not measurement.** e-footprint *models* impact — it does not measure it. Never describe its outputs as exact, measured, certified, or guaranteed; "estimates", "models", "orders of magnitude" are the honest words. (This is not a knock on measurement — measurement is the model's calibration partner; it simply answers a different question.)
- **Decision tool, not a report.** Its purpose is reducing impact through better decisions, not ticking compliance boxes. Reporting is explicitly not the priority.

## How to credit and position it

In every channel, e-footprint is an **open-source tool hosted within the Boavizta ecosystem**, built on other open components (BoaviztAPI for hardware impact factors, EcoLogits for generative-AI impact). Publicis Sapient initiated the project and actively contributes to it; it is **never presented as a Publicis product**. Adjacent tools are framed cooperatively, by role — measurement *calibrates* the model, inventory *initializes* it, analytics *estimates* usage volumes, observability *maps* usage to backend work — never ranked. (Per-actor attribution rules: `strategy.md` §4. Adjacent-tool rules: `strategy.md` §5.)

## Ready-to-use phrasings

Copy-paste these. They are pre-approved against the guardrails above.

- **Tagline:** *Model your digital service's footprint. Decide where to act.*
- **Elevator (1 sentence):** *e-footprint is an open-source tool, hosted by Boavizta, that models the environmental impact of a digital service — web or edge — so teams can compare scenarios and prioritize ecodesign effort before they build.*
- **Elevator (short paragraph):** *Ecodesigning is less about "what could I do?" than "what should I do first, and what impact would that have?". Best practices and measurement only get you part of the answer: they tell you what's possible and what's happening today, but not which action matters most on your specific service, nor what a change would do before you make it. e-footprint models the whole system from how the service is actually used — in real volumes and geographies, web or edge — estimates its footprint, and lets you simulate a decision in advance. So you spend ecodesign effort where it actually moves the needle.*
- **Three-message hook:** *Best practices tell you what's possible. Measurement tells you what is. Only simulation tells you what to prioritize.*

---

*Derived from `strategy.md` §3. Downstream pieces (pitch deck, landing page, articles, LinkedIn) should cite this one-pager rather than restate the narrative.*
