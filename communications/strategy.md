# e-footprint communication strategy

This document captures the communication strategy agreed by the three actors involved in e-footprint at the April 2026 kickoff meeting:

- **Vincent Villet** — main maintainer of e-footprint, employed by Publicis Sapient.
- **Michalina Chwastyk** — Boavizta volunteer responsible for communication and member of the board of directors. Represents the non-profit that hosts e-footprint in its open-source ecosystem.
- **Clémence Knaébel** — Publicis Sapient sustainability director. Develops a consulting offer around e-footprint with Vincent.

It is the source of truth for all subsequent communication work. Editorial pacing lives in [`editorial-calendar.csv`](./editorial-calendar.csv); piece drafts live in `articles/` and `linkedin/posts/` here, or in the interface repo's `communications/` folder when the subject is an interface feature.

---

## 1. Framing: three actors, one tool, aligned but distinct objectives

The three actors with stakes in e-footprint:

1. **e-footprint (the tool)** — open source, hosted within the Boavizta ecosystem. Communication objective: **awareness and adoption** within the responsible-digital community.
2. **Boavizta (the non-profit home)** — carries e-footprint as one brick in its open-source green-IT ecosystem. Objective: **reinforce Boavizta's identity as an independent reference** in European green IT, with e-footprint as one of its flagship contributions.
3. **Publicis Sapient (the commercial actor)** — employs the main maintainer and is building a consulting offer. Objective: **establish PS as an ecodesign expert** without appropriating the tool and without turning Boavizta into a commercial channel.

The three objectives are **aligned but cannot be told the same way**. The more e-footprint is known, the more PS benefits indirectly; the more PS produces high-quality content, the more credibility the tool gains. **Hard constraints**: Boavizta-branded channels never cite PS's commercial offer; PS-branded channels position e-footprint as a tool of the Boavizta ecosystem to which PS actively contributes — not as a PS product.

---

## 2. Target audiences

Five concentric circles, ordered by long-term priority.

1. **Tech and industrial product teams + operational sustainability leads** — joint priority; the people whose decisions drive a digital service's or device fleet's environmental impact. **The end-user target.** This circle mirrors e-footprint's two paradigms (web and edge):
   - **1a. Web product teams** — engineers, designers, PMs, UX, architects building web/SaaS/services. The joint decision-makers for what gets built and how. Companies with significant digital footprint: retail, services, media, SaaS.
   - **1b. Industrial product teams** — hardware and embedded engineers, IoT product managers, fleet operators, industrial PMs building edge-device fleets and mixed web/edge systems. **Higher commercial conversion to date**: the only paying e-footprint engagement so far is industrial; higher willingness to pay; sector-specific channels.
   - **1c. Operational, hands-on sustainability leads** — especially those with an explicit Green IT or ecodesign mission. Often work transversely across product teams; closest ally to 1a/1b in companies where they exist.
   - *Internal heterogeneity (applies primarily to 1a).* e-footprint deliberately bridges the code and non-code sides of web product teams. In practice the **design/product side tends to be more aware and willing to act**; the engineering side is closer to implementation but less primed. Reaching both is essential — the team's *collective* decisions drive the impact. This is both a strength of e-footprint (whole-team tool) and a constraint (UX must be approachable for non-code folks while staying useful for code-savvy ones — *"no one left behind, depth available on demand"*, per the interface mission). 1b is more uniformly engineering-led; the same dual-audience constraint applies less.
   - *Year-1 paradigm balance.* Web (1a) has higher adoption volume potential — more product teams to reach. Industrial (1b) has higher commercial conversion to date. Both warrant deliberate content tracks; neither is the residual. Boavizta-channel content leans web (volume); PS-channel content includes a deliberate industrial track (the French industrial white paper, see §7).

2. **Green IT / responsible-digital community / consultants ** — Boavizta itself, INR, Green IT Club, ADEME, schools (CS, 42, ENSIMAG, CentraleSupélec…). Already sensitized, influential, demands substance. **Peer credibility multiplier**: warmest, fastest circle to validate; unlocks adoption in circle 1.

3. **Wider tech community beyond product roles** — developers, architects, ops not directly tied to product decisions (infra teams, internal tooling, generalist devs). Reached at scale via mainstream tech conferences (Devoxx, BDX I/O, Codeurs en Seine, FOSDEM…) and tech LinkedIn. **Awareness funnel for circle 1**, lower direct-adoption ROI per touch.

4. **Academics and institutions** — LCA researchers, ADEME, EU regulators (CSRD, ecodesign directive). Slowest circle, highest long-term legitimacy.

5. **Reporting-focused sustainability leads** — auditors, CSRD compliance officers. Explicitly **not** the priority. e-footprint may do some reporting eventually, but its purpose is **decision-making for impact reduction**, not compliance reporting. Calling this distinction out upfront protects the tool's positioning against drift.

**Year-1 sequencing.** Peer credibility first via circle 2 (the warmest, fastest to validate), moving quickly to circle 1 (tech + industrial product teams and sustainability leads) once foundation content is in place. Circles 3–4 are addressed opportunistically (conferences, papers); circle 5 is deliberately deprioritized.

**Cross-reference to library mission.** [`specs/mission.md`](../specs/mission.md) describes the narrower set of *actual library user types* (sustainability-aware product teams, industrial users, researchers/consultants). Mapping: web product teams ↔ circle 1a; industrial users ↔ circle 1b; researchers/consultants ↔ mostly circles 2 and 4. The communication-target audience is wider than the user audience because comms reaches future-users (the broader Green-IT community, academics, the wider tech population) before they convert.

---

## 3. Core narrative

The thesis stays load-bearing across every channel: **"the environmental impact of digital services lies beyond the reach of intuition; only explicit modeling allows us to prioritize ecodesign efforts."**

Three differentiating messages reused across all channels:

- **"Prioritize, don't guilt-trip."** e-footprint helps decide where to invest effort, not produce a guilt-inducing carbon report. Decision-focused, not reporting-focused.
- **"Simulate before you act."** The environmental ROI of a product decision can be modeled before implementation, just like business ROI. Few other tools currently offer that.
- **"Usage and functionality at the center."** Unlike top-down carbon assessments and unlike pure unit-optimization narratives, e-footprint starts from **how the service is actually used** — by humans and by automated processes alike — in what volumes and in what geographies. Usage is described as **usage journeys with steps** (web) or **functionalities** (edge), not as raw request counts. The same primitive covers user-facing flows (browse catalog → add to cart → checkout) and technical flows with no direct user interaction (an ML training run, a scheduled sync). A PM or designer recognizes the user-facing usage journeys; together with the technical ones, they form the full system story. This is the **structural differentiator**: the constraint (volumes must be phrased as usage journeys or functionalities, not dumped as raw counts) is also the unlock — the same description supports **what-if simulation** (*"what if I add AI to this journey, simplify that one"*) and guards against the **scope-neglect trap** (a 90% unit optimization on a low-traffic service produces tiny absolute gains).

A **one-page messaging document** derived from this section is the next foundation deliverable; all subsequent content cites it. Tracked in the editorial calendar.

---

## 4. Rules of coexistence: Boavizta vs Publicis Sapient

These rules are the agreed working contract between the three actors. They take effect immediately and apply to all communications.

- **Shared assets** (documentation, website, GitHub, interface landing page) — managed on the Boavizta side. No PS logo, no commercial mention. The project credits PS as the initiator in `index.md`; that is the extent of PS visibility on shared assets.
- **Boavizta-branded assets** (newsletter, webinars, conferences under Boavizta's banner) — speak about the tool, the method, anonymized or academic case studies. Vincent speaks **as the maintainer**.
- **Publicis Sapient-branded assets** (PS blog, PS LinkedIn, commercial decks, client case studies) — speak about consulting, real client cases (with consent), PS's methodology around the tool. Always cite e-footprint as a Boavizta-ecosystem tool that PS contributes to. May cite Vincent as the maintainer.
- **Vincent's dual hat** — assumed openly. On personal LinkedIn he can say anything, with explicit mention of both roles. In conferences, the organizer picks the banner and downstream messaging follows suit.
- **Client case studies** — owned exclusively by PS. A study can be reframed as an anonymized "methodological return on experience" for Boavizta reuse, but the client relationship stays on PS's side.

---

## 5. Channel plan and pacing

### Cadence and ownership

| Channel | Cadence | Owner |
|---|---|---|
| Vincent's LinkedIn | 1 post / week | Vincent |
| Boavizta's LinkedIn | 1 post / month (reshares + originals) | Boavizta volunteer |
| Articles | 2–4 / year (start with 2–3 short-term) | Vincent, for Boavizta and/or PS channels |
| Webinar | ~1 in months 3–6 | Vincent + Boavizta |
| Conference talks | 2–3 submissions in months 3–6 | Vincent |

LinkedIn posts are **mostly derivative**: each post hooks into an article, a feature release, a mkdocs page, or a third-party publication. This keeps the cadence sustainable and drives traffic to substance content.

### Governance

**Light — trust + flag.** Authors publish on their own channel without prior review. Cross-actor review is the exception, triggered only when a piece touches another actor's domain (a PS article that names Boavizta heavily, a Boavizta piece that references PS). Default to trust.

### Distribution language

**English-default, French only when context requires.** Articles and LinkedIn posts default to English. French is used when the context is intrinsically French (French conference, Boavizta-FR webinar, French-press relay). No active translation effort planned in year 1; international push happens at the channel level (network effects), not the content level.

### Stance toward adjacent tools

**Cooperative.** EcoIndex, Green Metrics Tool, Carbonalyser, CarbonAPI, ClimateChange.ai etc. are cited as **complementary**: e-footprint occupies a different niche (modeling vs measurement, prioritization vs reporting). No combative comparisons on any channel.

### Phase 1 — Foundations (months 0–3) — committed

The priority is to give the three actors the **raw material** they need to communicate coherently.

- **One-page messaging document** (see §3).
- **Redesigned e-footprint landing page** with a real pitch (today's `index.md` is dry). One page that answers in 30 seconds: what is it, who is it for, why is it different.
- **Shared pitch deck** (10 slides) usable by any of the three parties for talks, meetings, interventions.
- **2–3 foundation articles**:
  - "Best practices, measurement, simulation: three strategies for ecodesign" — substance-heavy, Boavizta-published, Vincent's LinkedIn relay. Paradigm-agnostic. Argues that none of the three strategies suffices alone; simulation is what enables prioritization.
  - An **applied case study** — PS-owned, with client consent (see §7). **Industrial-flavored**, derived from the French industrial-actor mission: edge fleet modeling, mixed web/edge concerns, decision-making for impact reduction in a non-web context. Establishes industrial as a first-class use case in published content from day one.
  - A technical article on the method (usage-and-functionality framing, volumes/geographies, simulation, prioritization). Paradigm-agnostic; uses both web and edge examples.
- **LinkedIn rhythm starts**: Vincent 1/week + Boavizta 1/month.

### Phase 2 — Ramp-up (months 3–6) — loose; revisit at month 3

- **Boavizta introductory webinar** on e-footprint. Short format (~45 min), replay available. Modern replacement for the static videos the docs overhaul rightly avoids — a webinar is **dated**, so its obsolescence is acceptable and assumed.
- **Conference submissions** — 2–3 in the phase-2 window, selected from candidates spanning audience reach:
  - green-IT or business event (Impact Summit, GreenTech Forum-type) — circles 1a/1c + 2.
  - mainstream tech conference reaching the engineering side of 1a (Devoxx, BDX I/O, Codeurs en Seine, FOSDEM…) — circle 1a (engineering) + circle 3.
  - industrial or sector-specific event reaching 1b (LCA conference, IoT industrial sustainability event, Boavizta-led industrial methodology workshop) — circle 1b + circle 4.
- **Reaching the design / non-engineering side of 1a** (the more environmentally-receptive half) is harder via conferences. Default channel: LinkedIn (Vincent's feed and Boavizta reshares) plus the interface itself as a low-barrier entry point. A guest article on a UX/product publication is a candidate when a fit emerges; a design-side conference submission is a phase-3 option.
- **Industrial reach via direct B2B.** Beyond conferences, circle 1b is best reached via white papers (the PS white paper from §7), direct sector outreach, and Boavizta industrial-methodology partnerships. Boavizta-channel reach to 1b stays content-led (white papers, methodology notes, industrial case studies) rather than mass-event-led.
- **Case study #2** — PS-owned.
- **Presence in third-party resources** — guest article on GreenIT.fr / INR, mention in Boavizta training material, inclusion in community resource lists.

### Phase 3 — Embedding (months 6–12) — loose; revisit at month 3

- **Partnerships** — schools (integrating e-footprint into a green IT course), sister organizations (INR, Green IT Club, Climate Action Tech internationally), Boavizta's international relays.
- **User community** — Discord/Slack channel, first user meetup, lightweight contributors' day.
- **Open-source community work** — issues tagged "good first issue", target of one external contributor per quarter.
- **International distribution beyond default English** — actively reach into non-French communities (UK, Germany, Nordics, NA). Not a translation question — a network and channel question.

**No flagship event** in year 1. Existing conferences (Devoxx-style, GreenTech Forum, Impact Summit) are higher-ROI than building a custom event before community traction warrants one. Revisit only if traction makes it obvious.

---

## 6. Success metrics

Five families, measured monthly with a baseline taken at month 3. Numerical targets are deliberately deferred until the baseline exists.

- **Awareness** — GitHub stars, mkdocs traffic, unique users of the interface, LinkedIn/Twitter mentions, Vincent's follower growth.
- **Adoption** — number of teams/companies declaring they use e-footprint (informal survey, direct feedback), external contributions, issues opened by non-maintainers.
- **Endorsement** — mentions in ADEME and third-party reports (Boavizta publications, INR resources, academic citations, partner methodologies). Captures legitimacy growth that pure web metrics miss.
- **Qualitative user satisfaction** — direct feedback from operational sustainability leads using the tool: are they making decisions with it, are they recommending it, where's the friction. Captured via informal interviews and feedback channels — not an NPS, just a regular pulse.
- **Commercial conversion** *(PS-private)* — leads attributable to the e-footprint channel. Tracked privately by PS; does not influence Boavizta-side decisions.

---

## 7. Open items to revisit

Most strategic decisions are now baked in. The following are deliberately deferred:

1. **Phase 2–3 specifics** — endorsed in spirit but not committed to dates or counts. Revisit at month 3 based on phase 1 traction.
2. **Academic legitimacy path** (peer-reviewed paper or methodology publication) — deferred to month 6+. The methodology needs more battle-testing by real users before formal publication is worth the lead time.
3. **Client case study #1 framing** — a French industrial actor has agreed to a public case study. PS is in discussion about co-writing a white paper based on the e-footprint mission already conducted with them. Framing in this strategy doc and across Boavizta-side channels to be confirmed once the white paper is drafted.
4. **Numerical targets for §6 metrics** — baseline at month 3, targets set after.

---

## 8. Near-term unblockers

Three deliverables unlock everything else:

- **One-page messaging document** (§3) — locks the shared narrative; cited by all subsequent content.
- **Shared pitch deck** (§5 phase 1) — usable by all three parties for talks and meetings.
- **First Boavizta-published article** (working title: "Best practices, measurement, simulation: three strategies for ecodesign") — establishes the substance baseline and gives LinkedIn a derivative source to point to.

Tracked in `editorial-calendar.csv`.
