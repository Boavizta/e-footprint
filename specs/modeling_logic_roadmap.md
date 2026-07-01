# Modeling-logic roadmap — e-footprint

Open **modeling-method** questions: places where modeling something *well* needs scientific
grounding (benchmarks, papers, or measured data) that we don't yet have. This register exists so
the project can name such a question, ship an honest fallback meanwhile, and avoid shipping
**false precision** — a plausible-looking coefficient that is really a guess.

This is distinct from [`roadmap.md`](roadmap.md): that tracks *features and scheduling*; this
tracks *whether we know enough to model a thing correctly at all*. A question graduates out of
here into a feature once the evidence exists to model it defensibly.

## Entry format

Each entry states: **the question** · **why it's hard** · **what's solid today** (the fallback we
ship) · **candidate approaches** · **evidence we'd need / what we know** · **status**.

---

## Database query resource & energy cost

**The question.** Given a database query or an aggregate query workload, how much `compute_needed`
(CPU-seconds), `ram_needed`, and I/O does it consume — i.e. how do we turn a description of
database usage into the per-job resource inputs e-footprint needs?

**Why it's hard.** A database's *energy-given-resources* is already well-modeled (a server's idle +
load energy, plus storage). The unsolved part is mapping query semantics (rows scanned, joins,
selectivity, query plan, index/cache state) to actual CPU/RAM/I/O. A literature/benchmark scan
(2026-06-30) found **no validated, hardware-/engine-independent closed-form model**, and a strong
consensus that one cannot exist as a ship-once artifact:
- Concrete DB-energy models are sets of per-operator cost functions whose coefficients are
  **calibrated per machine against a power meter**; they validate well for a single static query
  (<10% error) but **degrade to 40–65% error under realistic concurrency** (USF TR11-055).
- Learned cost models "don't transfer across databases, workloads, or hardware without
  retraining" (SIGMOD 2023); per-query energy is host/DBMS-specific (~38% variance, DBJoules 2023).
- A baked-in `rows → CPU-seconds` factor would be false precision — the same reason we declined to
  derive a serverless function's CPU from its allocated memory (see feature
  `saas-serverless-modeling-ergonomics`).

**What's solid today (the fallback we ship).** Two things are well-established and reassuring:
1. **e-footprint's server model is already the right structural form.** DB energy is dominated by
   (a) the **always-on idle baseline** (≈15–50% of peak power, the non-optimizable term) and (b) a
   **dynamic term proportional to CPU-active time** — `P ≈ P_idle + (P_busy−P_idle)·u`, R²≈98%.
   That is exactly the `idle_power` + load model already in `ServerBase`.
2. So we model a database by **composing existing primitives**: a server
   (`server_type=serverless` for managed/pay-per-use, `autoscaling`/`on_premise` for
   reserved/self-hosted) + `Storage` (data volume × fabrication × replication) + jobs whose
   resources are supplied directly by the modeler or from measurement. The always-on engine
   capacity is explicit via `idle_power` and `base_ram_consumption`/`base_compute_consumption`.
   Shipped as a how-to; it claims no query-cost model — it just structures the model.

**Candidate approaches (for the eventual deep dive).**
1. **Measured billing/telemetry resource-time (preferred).** Map managed-DB consumption units the
   providers already expose to physical resource-time and feed the existing energy model. All four
   major cloud carbon tools allocate DB energy this way, never by query content.

   | Provider | Unit | Physical mapping | Telemetry |
   |---|---|---|---|
   | Aurora Serverless v2 | ACU-hours | 1 ACU ≈ 2 GiB RAM + "corresponding CPU" (vCPU/ACU not vendor-published) | CloudWatch `ServerlessDatabaseCapacity` |
   | Neon | CU-hours | 1 CU = 1 vCPU + 4 GB RAM | consumption API `compute_unit_seconds` |
   | Azure SQL serverless | vCore-seconds | 3 GB/vCore; billed = max(CPU, mem/3) | Azure Monitor `app_cpu_billed` |
   | GCP AlloyDB / Cloud SQL | vCPU-hr + GiB-hr | chosen directly | Cloud Monitoring `cpu/usage_time` |

   Convert via reusable coefficient sets: **CCF / Etsy "Cloud Jewels"** (compute Wh/vCPU-hr,
   memory kWh/GB-hr, storage Wh/TB-hr, networking, per-provider PUE), **Boavizta** for embodied,
   **GSF SCI** `(E·I + M)/R` as the wrapping formula. This connects to the "operational data
   importers" need in the interface `user_research/needs-backlog.md`.
2. **A-priori estimation from query/workload features** — only if research yields a model that
   generalizes with stated error bounds. Default skepticism applies; treat any such model as an
   optional, clearly-labelled, per-environment-calibrated *refinement*, never the primary estimator.
3. **Hybrid:** measured baseline + a coarse per-query adjustment with explicit uncertainty.

**Evidence we'd need / what we know.** We'd need a validated hardware-parameterized model with
error bounds, *or* (more realistically) a clean documented mapping from provider compute-units to
physical resource-time plus a defensible coefficient set. The 2026-06-30 scan established the
latter exists and is the industry direction; the former does not.

**Key sources (curated).**
- Tsirogiannis et al., "Analyzing the Energy Efficiency of a Database Server," SIGMOD 2010 — idle ≈ ½ peak; "most efficient = fastest." https://dl.acm.org/doi/10.1145/1807167.1807194
- Barroso & Hölzle, "The Case for Energy-Proportional Computing," IEEE Computer 2007. https://www.barroso.org/publications/ieee_computer07.pdf
- Xu, Tu & Wang, "Power Modeling in DBMS," USF TR11-055 — static model <10% error, 40–65% under concurrency. https://cse.usf.edu/~tuy/pub/tech11-055.pdf
- Yang et al., "Rethinking Learned Cost Models," SIGMOD 2023 — non-transferability. https://15799.courses.cs.cmu.edu/spring2025/papers/15-learned/yang-sigmod2023.pdf
- SPECpower_ssj2008 — server load→power curves (idle/peak ratio, slope). https://www.spec.org/power_ssj2008/
- TPC-Energy Spec — Watts-per-work overlay on TPC benchmarks. https://www.tpc.org/tpc_energy/
- Cloud Carbon Footprint methodology + Etsy Cloud Jewels — reusable compute/memory/storage/PUE coefficients. https://www.cloudcarbonfootprint.org/docs/methodology/ · https://github.com/etsy/cloud-jewels
- Neon computes / consumption metrics. https://neon.com/docs/manage/computes · https://neon.com/docs/guides/consumption-metrics
- Aurora Serverless v2 how-it-works (ACU). https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.how-it-works.html
- GSF SCI Specification (ISO/IEC 21031:2024). https://sci.greensoftware.foundation/

**Status.** Open. Fallback shipped via docs in feature `saas-serverless-modeling-ergonomics`.
Preferred path is the measured-resource-time importer; revisit when there's time for the deep dive.
