# Best practices, measurement, modeling: three strategies for ecodesign

Ecodesigning a digital service is a decision problem: out of all the things a team could do to reduce a service's environmental impact, which ones move the needle? Answering that requires both *what's possible* — the catalogue of actions a team can take — and *what's likely to matter* — the relative impact of each action on the specific service at hand.

Most ecodesign content rests on one of three strategies: **best practices**, **measurement**, and **modeling**. Each is useful, each is necessary, and none of the three is sufficient on its own. e-footprint sits in the third — modeling — because that strategy has historically been the least developed for digital services. The point of this page is to lay out what each strategy gives you, where each one stops when used alone, and how the three feed each other.

## Best practices: the catalogue of possible moves

Best practices are accumulated recipes for what works: compress images, lazy-load modules, pick efficient cloud regions, avoid dark patterns etc. They answer *what could I do?*.

Their limit is variability. Digital services differ enormously in shape, scale, and usage, and what dominates one service's footprint is negligible in another's. Applied without knowing which apply to *your* service, a list of best practices points you at low-leverage actions as often as high-leverage ones, and reads as an undifferentiated checklist — many things you could be doing, no information about where to start.

Best practices remain indispensable as a **source of candidate actions**. The question they cannot answer alone is *which of these actions should I do first on this service?*.

## Measurement: the snapshot of what is

Measurement covers tools that observe an existing system and report its environmental footprint — energy consumption of a running service, carbon emissions of a training run, request-level resource usage from observability tooling. They answer *what is the footprint of this service, and how has it evolved?*.

Two limits keep measurement from being decision-grade on its own. First, **you cannot measure what isn't there yet**: a feature you haven't built, a scale you haven't reached, a region you haven't deployed to. Most ecodesign decisions are about candidate futures, and measurement can only see the present and the past. Second, **measurement often cannot reach every part of the footprint**: the impact of end-user devices, of the network or of external APIs notably. Faced with what it cannot reach, a measurement-only approach has two options — exclude the missing piece from scope, or leave it silently out — and both amount to the implicit hypothesis that it is worth zero. The alternative is an explicit, named hypothesis based on the best available proxy: less precise than a measurement but probably better than zero, and challengeable later.

Measurement is the **calibration partner** of modeling: where a number can be measured, it should be, and that measurement is the most trustworthy input a model can have. Two questions measurement cannot answer on its own: *what will the footprint look like under a change I haven't made yet?*, and *how should I account for the parts I cannot directly observe?*.

## Modeling: the projection that lets you decide

Modeling describes the system structurally — its usage journeys and functionalities, its volumes and geographies, the hardware those workloads run on — and computes a footprint from that description. From the same description, three things become available: the current footprint (overlapping with measurement on the parts that *are* measurable), the projected footprint at projected scale, and the footprint after a hypothetical change (*what if we add AI to this journey, drop region X, serve ten times the volume?*).

The structural property that makes this work is that usage is expressed in terms a product team can recognise — {class:UsageJourney} and {class:UsageJourneyStep} on the web side, {class:EdgeUsageJourney} and {class:EdgeFunction} on the edge side (see {doc:web_vs_edge}) — rather than as raw request counts. That structure is also the constraint: modeling demands a description of the service before it can give you a number. The unlock is that the same description supports what-if comparison, and protects against the scope-neglect trap where a 90% optimisation on a low-traffic flow produces tiny absolute savings.

This is the strategy e-footprint embodies. The conceptual case for it is made in {doc:why_efootprint}; the practical methodology for applying it is in {doc:methodology}.

## The three together

| Strategy | Gives you | What it cannot give alone                                                             |
|---|---|---------------------------------------------------------------------------------------|
| Best practices | A catalogue of possible moves | Which of these moves matters most for your service                                    |
| Measurement | A diagnostic of the current system | The footprint of changes not yet made, nor of parts that cannot be measured directly  |
| Modeling | Decision-grade priorities and scenarios | The measured inputs it depends on, nor the catalogue of actions it prioritises across |

The three feed each other. Measurement supplies the model with observed energy use, fleet-level data from device manufacturers, and request-level metrics from observability tooling, and best practices populate the action space the model helps prioritise across. Without the other two, modeling would have to guess at its inputs and produce abstract priorities; without modeling, best practices and measurement are catalogues and snapshots with no decision arrow connecting them.

e-footprint's contribution is to make the third strategy practical for digital services. The roles played by neighbouring tools, and the integration paths into and out of e-footprint, are picked up in the relevant how-to and reference pages.
