# Web vs edge modeling

e-footprint has two paradigms for sizing environmental impact, and they
differ in what drives the model. In the **web** paradigm, a centralized
infrastructure adapts to external usage: you describe demand (page views,
requests per hour, usage journeys started per hour), and the model sizes
the servers, storage, and network that must serve it. Causality runs
**usage → infrastructure**. In the **edge** paradigm, impact comes from a
fleet of deployed units — sensors, industrial PCs, smartphones from a
manufacturer's perspective, any decentralized hardware — each with its
own recurrent behaviour over its lifetime. Causality runs
**number of units × per-unit behaviour → impact**.

In a nutshell: in the web case, infrastructure depends on usage; in the
edge case, usage depends on the number of units deployed.

## When to use which

- **Web** for centralized services consumed by humans — SaaS, e-commerce,
  content streaming. The model question is "how much infrastructure does
  this demand require?"
- **Edge** for decentralized hardware fleets — IoT, industrial
  deployments, smartphones from a manufacturer's perspective. The model
  question is "what is the cumulative impact of N units, each behaving
  like this?"
- **Mixed** when deployed devices also interact with centralized servers
  — telemetry uploads, remote configuration, firmware updates. Both
  paradigms coexist in one model.

## How the two paradigms map

Both paradigms organize the model the same way — a *pattern* drives a
*journey*, which is composed of *units of work* — but each layer means
something different:

| Layer        | Web                                              | Edge                                                                 |
|--------------|--------------------------------------------------|----------------------------------------------------------------------|
| Pattern      | {class:UsagePattern} — hourly rate of **user journey starts** in a country. | {class:EdgeUsagePattern} — hourly rate of **device deployments** in a country. |
| Journey      | {class:UsageJourney} — *one visit*: a short, discrete sequence of steps. | {class:EdgeUsageJourney} — *the long-running activity of the deployed fleet*: a set of functions that run while devices are in service (over the {param:EdgeUsageJourney.usage_span}), and that can span several device types. |
| Unit of work | {class:UsageJourneyStep} — a discrete step with bounded {param:UsageJourneyStep.user_time_spent}, triggering {class:Job}s once per step. | {class:EdgeFunction} — a coherent feature, described by **recurring** device-side needs ({class:RecurrentEdgeDeviceNeed}) and **recurring** server-side jobs ({class:RecurrentServerNeed}) — unbounded in time. |

Reading the table top to bottom captures the difference in one line:

- **Web** is **unitary journeys × volume**: each visit is short and
  discrete; impact scales with how many *start* per hour.
- **Edge** is **recurrent functions × deployed units**: the journey
  runs for years and decomposes into functions described by *what runs
  recurrently*, not by per-call payloads. The count of deployed units
  actively in service comes from the deployment schedule and the
  {param:EdgeUsageJourney.usage_span} (calculated by
  {calc:EdgeUsageJourney.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern}).

## Where they meet

The bridge between paradigms is {class:RecurrentServerNeed}. It attaches
to an edge device and holds a per-unit weekly pattern (168 hours) of
recurrent server interaction, plus the list of {class:Job} objects the
device triggers on the web side. At calculation time, the per-unit
volume is multiplied by the deployed unit count to produce the hourly
demand those jobs impose on the web infrastructure.
