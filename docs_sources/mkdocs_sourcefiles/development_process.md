# Modeling the development process of a digital service

Should the resources spent **building and operating** a service — CI pipelines, test runs, staging environments, ML experiments, coding agents — count toward its footprint?

## Rule of thumb: usually negligible

For most services, production load dwarfs development load. A handful of CI runs per merge and a few developers' machines running tests do not compete with thousands of users hitting the service every hour. In that regime, leave development out of the model.

## When development stops being negligible

A few patterns flip the balance:

- **Heavy ML experimentation.** Sweeps and ablations can burn more compute than the eventual inference traffic.
- **Heavy use of coding agents.** LLM-assisted development at team scale adds non-trivial inference cost upstream of any product traffic.
- **Small production surface.** Internal tools, prototypes, or low-traffic services where the build pipeline runs more often than users hit the product. In this case, also be wary of over-investing in modeling and optimization itself: if the production footprint is a small order of magnitude, the development footprint likely is too, and the iterative methodology says to stop modeling rather than chase precision (see {doc:methodology}).
- **Expensive CI.** Long end-to-end suites, frequent rebuilds of large container images, or full-stack runs on every push.

If any of these apply, model the development workload explicitly.

## How to model it

Development resources are modeled the same way as production. There is no separate "development" concept in e-footprint:

- A CI runner is a `{class:Server}`.
- A nightly training job is a `{class:GPUJob}`.
- Coding-agent usage maps to `{class:EcoLogitsGenAIExternalAPI}`.

In practice, add a `{class:UsageJourney}` describing the development workload (commits per day, experiment runs per week, agent calls per developer) and attach it to the relevant infrastructure. The production and development journeys then sit side by side in the same system.

## What's out of scope

e-footprint models digital resources. Office buildings, commuting, team travel, and other non-tech costs are real and may be non-neglectable, but they are out of e-footprint’s scope for now.

## Where to start

Follow the {doc:methodology}: start with a coarse modeling that will give you your first orders of magnitude to help prioritize actions and the rest of the modeling process. Include your development process when you reach the precision threshold at which you think it matters.
