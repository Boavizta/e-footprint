# e-footprint communication strategy — working plan

Working document to structure the communication effort around e-footprint. Drafted as input for a discussion between the main actors:

- **Vincent Villet** — main maintainer of e-footprint, employed by Publicis Sapient.
- **Michalina Chwastyk** — A Boavizta volunteer. Represents the non-profit that hosts e-footprint in its open-source ecosystem.
- **Clémence Knaebel** — Publicis Sapient's sustainability director. Develops a consulting offer around e-footprint with Vincent.

The document is intentionally opinionated so the meeting has concrete material to push back on, amend, or reprioritize. Nothing here is locked.

---

## 1. Framing: three actors, one tool, aligned but distinct objectives

Before talking channels, we need to name the three-tier dynamic explicitly:

1. **e-footprint (the tool)** — open source, hosted within the Boavizta ecosystem. The communication goal here is **awareness and adoption** within the responsible-digital community.
2. **Boavizta (the non-profit home)** — carries e-footprint as one brick in a larger ecosystem of open-source green IT tools. The goal is to **reinforce Boavizta's identity as an independent reference** in European green IT, with e-footprint as one of its flagship contributions.
3. **Publicis Sapient (the commercial actor)** — employs the main maintainer and is building a consulting offer. The goal is to **establish PS as an ecodesign expert** without appropriating the tool and without turning Boavizta into a commercial channel.

The key constraint to lock in up front: the three objectives are **aligned but cannot be told the same way**. The more e-footprint is known, the more PS benefits indirectly; the more PS produces high-quality content, the more credibility the tool gains. But Boavizta-branded channels **must never cite PS's commercial offer**, and PS-branded channels must position e-footprint as a tool of the Boavizta ecosystem to which PS actively contributes — not as a PS product.

---

## 2. Target audiences

Four concentric circles, from warmest to coldest. Priority to confirm in the meeting.

1. **Product teams and sustainability leads in companies** — the actual end users. They will adopt the tool. Companies with significant digital footprint: retail, services, industry, media, SaaS.
2. **Green IT / responsible-digital community** — Boavizta itself, INR, Green IT Club, ADEME, schools (CS, 42, ENSIMAG, CentraleSupélec…). Already sensitized, influential, but saturated with content. Demands substance.
3. **Wider tech community** — developers, architects, DevOps. Activated via mainstream tech conferences (Devoxx, BDX I/O, Codeurs en Seine, FOSDEM…) and tech LinkedIn.
4. **Academics and institutions** — LCA researchers, ADEME, EU regulators (CSRD, ecodesign directive). Slowest circle but delivers the highest long-term legitimacy.

Each audience requires a different register, covered in section 4.

---

## 3. Core narrative (the shared foundation for every channel)

e-footprint has a **strong thesis** that must leave the documentation and move to the foreground everywhere. The existing docs phrase it well: **"the environmental impact of digital services lies beyond the reach of intuition; only explicit modeling allows us to prioritize ecodesign efforts."**

From that thesis, three differentiating messages can be reused across all channels:

- **"Prioritize, don't guilt-trip."** e-footprint helps decide where to invest effort, not produce a guilt-inducing carbon report. Decision-focused, not reporting-focused.
- **"Simulate before you act."** The environmental ROI of a product decision can be modeled before implementation, just like business ROI. Very few other tools currently offer that.
- **"User journeys at the center."** Unlike top-down carbon assessments, e-footprint starts from what users actually do — which speaks to product teams, not just engineers.

**Recommendation:** co-write a **one-page messaging document** during the meeting, validated by all three actors, to serve as the reference for all subsequent content. Prevents drift after six months.

---

## 4. Rules of coexistence: Boavizta vs Publicis Sapient

Concrete proposals to debate:

- **Shared assets** — documentation, website, GitHub, interface landing page. Managed on the Boavizta side. No PS logo or commercial mention. The project already credits PS as the initiator in `index.md`; that is enough.
- **Boavizta-branded assets** (newsletter, webinars, conferences under Boavizta's banner) — speak about the tool, the method, anonymized or academic case studies. Vincent can speak **as the maintainer**.
- **Publicis Sapient-branded assets** (PS blog, PS LinkedIn, commercial decks, client case studies) — speak about consulting, real client cases (with consent), PS's methodology around the tool. Cite e-footprint as a Boavizta ecosystem tool PS contributes to. May cite Vincent as the maintainer.
- **Vincent's dual hat** — assumed openly. On his personal LinkedIn he can say anything, with an explicit mention of both roles. In conferences, the organizer picks the banner and downstream messaging follows suit.
- **Client case studies** — the most powerful asset. Owned exclusively by PS. A study can be reframed as an anonymized "methodological return on experience" for Boavizta reuse, but the client relationship stays on PS's side.

---

## 5. Channel plan and pacing (proposed 12-month roadmap)

### Phase 1 — Foundations (0-3 months)

The priority is to give the three actors the **raw material** they need to communicate coherently.

- **One-page messaging document** (see section 3).
- **Redesigned e-footprint landing page** with a real pitch (today `index.md` is very dry). One page that answers in 30 seconds: what is it, who is it for, why is it different.
- **Shared pitch deck** (10 slides) usable by any of the three parties for talks, meetings, interventions.
- **2-3 foundation articles:**
  - "Why we should model rather than estimate the impact of digital services" (substance-heavy, Boavizta-published, personal LinkedIn relay).
  - An **applied case study** (PS-owned, with client consent).
  - A technical article on the method (user journeys, simulation, prioritization).
- **LinkedIn rhythm** — Vincent publishes once a week (short posts demystifying a concept or commenting on current green IT news). Boavizta reshares. PS relays from corporate accounts when relevant.

### Phase 2 — Ramp-up (3-6 months)

- **Boavizta introductory webinar** on e-footprint. Short format (45 min), replay available. This is the modern replacement for the static videos that the documentation overhaul rightly avoids: a webinar is **dated**, so its obsolescence is acceptable and assumed.
- **Applications to 2-3 targeted conferences**: an Impact Summit / GreenTech Forum type event (business audience), a mainstream tech conference (Devoxx or equivalent), an academic or LCA conference.
- **Case study #2** on PS's side.
- **Presence in third-party resources** — guest article on GreenIT.fr / INR, mention in Boavizta training material, inclusion in community resource lists.

### Phase 3 — Embedding (6-12 months)

- **Partnerships** — schools (integrating e-footprint into a green IT course), sister organizations (INR, Green IT Club, Climate Action Tech internationally), Boavizta's international relays.
- **Building a user community** — Discord/Slack channel, first user meetup, a lightweight contributors' day.
- **Open-source community work** — issues tagged "good first issue", target of one external contributor per quarter.
- **Internationalization beyond default English** — e-footprint is already English-by-default, but actively reaching out to non-French communities (UK, Germany, Nordics, NA) is a separate effort worth scoping in phase 3. Not a translation question — a distribution and network question.

---

## 6. Success metrics

Three families, measured monthly:

- **Awareness** — GitHub stars, mkdocs traffic, unique users of the interface, LinkedIn/Twitter mentions, Vincent's follower growth.
- **Adoption** — number of teams/companies declaring they use e-footprint (informal survey? direct feedback?), external contributions, issues opened by non-maintainers.
- **Commercial conversion** (PS-private) — leads attributable to the e-footprint channel.

The commercial metric is tracked privately by PS and does not influence Boavizta-side decisions.

---

## 7. Open questions for the meeting

A short list to focus the discussion rather than arrive with everything locked.

1. **Resources and cadence** — who does what, at what frequency? Vincent alone cannot sustain a high publication rhythm.
2. **Shared governance** — who reviews what before publication? A light process is needed to avoid drift *and* avoid paralysis.
3. **English-first distribution strategy** — content is already in English. Do we actively push into non-French circles from day one, or consolidate the French community first?
4. **Stance towards adjacent tools** — how do we position against EcoIndex, Green Metrics Tool, Carbonalyser, CarbonAPI, ClimateChange.ai etc. without being combative?
5. **Client case studies** — which PS clients might accept being named, and in what form?
6. **Flagship event** — should we aim mid-term for an "e-footprint day" or a co-organized green IT summit with Boavizta?
7. **Academic legitimacy path** — do we invest in a peer-reviewed paper or methodology publication? Long lead time but high return on legitimacy.

---

## 8. Next steps after the meeting

Regardless of where the discussion lands, two near-term deliverables would unlock everything else:

- The **one-page messaging document** (section 3).
- The **shared pitch deck** (section 5, phase 1).

Everything else — articles, webinars, conference submissions — becomes much easier once those two artifacts exist.
