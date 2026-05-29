# Why e-footprint ?

**We define ecodesign as the process of building or maintaining a digital service while minimizing its environmental impact.** Doing it well is less a question of *what could I do?* than of *what should I do first?*: out of all the actions a team could take to reduce a service's footprint, only some move the needle — and on every service it is a *different* some. Answering *which, and in what order* is the problem e-footprint exists to solve.

This page lays out the three strategies teams use to answer that question, why modeling is the one e-footprint focuses on, why an explicit model is necessary at all, how precise it needs to be, and what a model of a digital service must therefore contain.

## Three strategies for ecodesign: best practices, measurement, modeling

Most ecodesign content rests on one of three strategies: **best practices**, **measurement**, and **modeling**. Each is useful, each is necessary, and none of the three is sufficient on its own. e-footprint sits in the third — modeling — because that strategy has historically been the least developed for digital services. What follows is what each strategy gives you, where each one stops when used alone, and how the three feed each other.

### Best practices: the catalogue of possible moves

Best practices are accumulated recipes for what works: compress images, lazy-load modules, pick efficient cloud regions, avoid dark patterns etc. They answer *what could I do?*.

Their limit is variability. Digital services differ enormously in shape, scale, and usage, and what dominates one service's footprint is negligible in another's. Applied without knowing which apply to *your* service, a list of best practices points you at low-leverage actions as often as high-leverage ones, and reads as an undifferentiated checklist — many things you could be doing, no information about where to start.

Best practices remain indispensable as a **source of candidate actions**. The question they cannot answer alone is *which of these actions should I do first on this service?*.

### Measurement: the snapshot of what is

Measurement covers tools that observe an existing system and report its environmental footprint — energy consumption of a running service, carbon emissions of a training run, request-level resource usage from observability tooling. They answer *what is the footprint of this service, and how has it evolved?*.

Two limits keep measurement from being decision-grade on its own. First, **you cannot measure what isn't there yet**: a feature you haven't built, a scale you haven't reached, a region you haven't deployed to. Most ecodesign decisions are about candidate futures, and measurement can only see the present and the past. Second, **measurement often cannot reach every part of the footprint**: the impact of end-user devices, of the network or of external APIs notably. Faced with what it cannot reach, a measurement-only approach has two options — exclude the missing piece from scope, or leave it silently out — and both amount to the implicit hypothesis that it is worth zero. The alternative is an explicit, named hypothesis based on the best available proxy: less precise than a measurement but probably better than zero, and challengeable later.

Measurement is the **calibration partner** of modeling: where a number can be measured, it should be, and that measurement is the most trustworthy input a model can have. Two questions measurement cannot answer on its own: *what will the footprint look like under a change I haven't made yet?*, and *how should I account for the parts I cannot directly observe?*.

### Modeling: the projection that lets you decide

Modeling describes the system structurally — its usage journeys and functionalities, its volumes and geographies, the hardware those workloads run on — and computes a footprint from that description. From the same description, three things become available: the current footprint (overlapping with measurement on the parts that *are* measurable), the projected footprint at projected scale, and the footprint after a hypothetical change (*what if we add AI to this journey, drop region X, serve ten times the volume?*).

The structural property that makes this work is that usage is expressed in terms a product team can recognise — {class:UsageJourney} and {class:UsageJourneyStep} on the web side, {class:EdgeUsageJourney} and {class:EdgeFunction} on the edge side (see {doc:web_vs_edge}) — rather than as raw request counts. That structure is also the constraint: modeling demands a description of the service before it can give you a number. The unlock is that the same description supports what-if comparison, and protects against the scope-neglect trap where a 90% optimisation on a low-traffic flow produces tiny absolute savings.

This is the strategy e-footprint embodies. *Why* an explicit model is required — rather than expert intuition — and *what* such a model must contain are developed in the sections below; the practical methodology for applying it is in {doc:methodology}.

### The three together

| Strategy | Gives you | What it cannot give alone                                                             |
|---|---|---------------------------------------------------------------------------------------|
| Best practices | A catalogue of possible moves | Which of these moves matters most for your service                                    |
| Measurement | A diagnostic of the current system | The footprint of changes not yet made, nor of parts that cannot be measured directly  |
| Modeling | Decision-grade priorities and scenarios | The measured inputs it depends on, nor the catalogue of actions it prioritises across |

The three feed each other. Measurement supplies the model with observed energy use, fleet-level data from device manufacturers, and request-level metrics from observability tooling, and best practices populate the action space the model helps prioritise across. Without the other two, modeling would have to guess at its inputs and produce abstract priorities; without modeling, best practices and measurement are catalogues and snapshots with no decision arrow connecting them.

## Why an explicit model, and not intuition?

If modeling is the decisive strategy, why not lean on experienced people's intuition to apply the right best practices — the way good teams already do for web performance?

Because the two are not alike. A poor performance is perceptible (and even often frustrating !), so the combination of theory and practice lets experienced professionals build an intuitive understanding of their systems. Environmental impact is different: it lives entirely outside of the reach of our senses. This great distance in space and time between our actions and their impacts (described in more detail in this [excellent article from Jean-Marc Jancovici](https://jancovici.com/publications-et-co/contributions-a-ouvrage/une-preface-pour-le-livre-comment-marche-vraiment-le-monde-de-vaclav-smil/)) is a very new and difficult problem for humanity, touches every aspect of modern life, and is especially salient for digital services. **It calls for a fully explicit model, because building intuition is simply not possible.**

## How precise does the modeling need to be ?

Now that we know we need an explicit model, how precise does it need to be to support good decisions? Any understanding is a tradeoff between precision and usability. For example, having in mind a mental model that says "[for an average consumer car, driving at 110km/h on the highway instead of 130km/h reduces the speed by 15% but the oil consumption by 25%](https://scienceetonnante.com/2022/08/07/autoroute-110-au-lieu-de-130/)" is simplistic because many factors influence the result (the exact shape of the car, the wind, the profile of the road etc.). However, I consider it usable for the decision I have to make (which speed to drive at when taking the highway) because I know that the exact oil saving figure for the particular vehicle I'm driving won't be so far from this simplified average. This example introduces two important concepts that physicists often use:

- **reduced-order modeling**, where the mathematical complexity of a real world phenomenon is voluntarily simplified while preserving enough precision for the task at hand.
- **order of magnitude**, an approximate figure that is easier to obtain and use in reduced-order model computations, and enough to make informed decisions.

**The more complex and variable the studied system is, the more complex (=high order) the corresponding model needs to be before it delivers useful orders of magnitude.**

## What a model of a digital service must contain

How complex would a good enough model need to be to effectively guide ecodesign decisions ? It depends on the complexity and variability of digital services. Let's make some observations and simple thought experiments to find out the essential parameters.

First and foremost, digital services vary wildly in usage volumes. The biggest social networks have billions of daily visits while your company showcase website might have only a few hundreds. The same ecodesign action leading to a 10% energy consumption reduction will be vastly more impactful on the big system than on the small one, so **usage volume input is critical**.

Then let's look at the four key components of digital services: **user devices, network, servers and storage**. Different services make use of them in vastly different proportions, making each of them sometimes negligible, sometimes crucial. For example, streaming services make a heavy use of the network, gen AI services use a lot of computing power in servers, and social networks store huge amounts of data. All these different types of objects thus need to be represented in our model.

Lastly, many ecodesign actions involve changing the way users interact with the service, so there needs to be a way to tell the model that users have changed the actions that they typically do. Hence, **user journeys must be part of the model inputs**.

We now have a framework for thinking about the physicality of our digital service: **digital services must at least be described in terms of usage journeys ({class:UsageJourney}) with their usage information ({class:UsagePattern}). Each user journey is made of steps ({class:UsageJourneyStep}) that make requests ({class:Job}) through a network ({class:Network}), on a server ({class:Server}), possibly saving data to storage ({class:Storage}).** This usage-and-functionality language is also what lets the model speak to tech professionals with a less technical background, not only to architects and developers.

Moreover, it is necessary to take a life cycle analysis approach to understand all aspects of environmental impact from cradle to grave. Here the orders of magnitude show that focusing on the fabrication and run phases of the service is a good first approximation, neglecting transport and end of life.

## The difference between the model and the modeling

e-footprint is a modeling tool that embeds a model of the relationships between components of a digital service and the associated environmental footprint. When you describe your digital service with e-footprint, what you get is a modeling of this service.

## The genesis of e-footprint

e-footprint was born from the above analysis and the observation that no other tool had taken a modeling approach bringing together all these objects. It started as an Excel modeling and then evolved towards a Python package to allow for greater flexibility in the combination of objects.

For a more in-depth discussion of e-footprint's genesis by its designer, watch the <a href="https://www.youtube.com/watch?v=pc-H5yySPRo" target="_blank">e-footprint presentation made by Vincent Villet at the 2023 Paris Impact Summit</a> (9 minutes, in French).

## Get started

Now that you understand the concepts on which e-footprint is built, read the [How to get started](get_started.md) article to start your ecodesign journey !
