# How to model a machine-learning workflow

## The two phases

An ML system in production has two phases that consume resources very
differently: **training** (one-shot or recurrent, dense bursts of
compute) and **inference** (per-call cost that scales with end-user
demand). Model each as its own {class:UsagePattern} + {class:UsageJourney}.

Training is worth modeling only when its expected impact is meaningful
at the order-of-magnitude level — a random forest trained on a laptop
in five minutes will not move the needle. Which phase dominates
depends on the system: for an integration of a public GenAI API the
modeler's footprint is essentially inference, since training happened
elsewhere; for an internal corporate ML model retrained weekly and
served to a small user base, training can easily dominate. Per the
iterative methodology ({doc:methodology}), sketch both phases
roughly, see which one carries the total, then refine the dominant
one.

## Modeling training

**Recurrent retraining maps naturally onto {class:UsagePattern}.** Its
hourly journey-starts timeseries can carry any cadence: weekly
retraining is one journey-start every 168 hours, nightly is one every
24 hours, one-shot training is a single spike at t=0. No special
primitive is needed.

**Per-run resource numbers are best obtained by measurement.**
[CodeCarbon](https://codecarbon.io/) tracks the energy use of a Python
training script and produces values (energy, duration, hardware
utilisation) that feed directly into a {class:Job} or {class:GPUJob}
parametrisation. If you publish such measurements, consider also
contributing them to [Boavizta's BoAmps project](https://github.com/Boavizta/BoAmps),
a community catalogue of ML-training footprints that benefits both
research and downstream tools.

## Modeling inference

The right primitive depends on **who hosts the model**:

- **The model runs on the modeler's own infrastructure** — on-premises,
  or on a cloud server the modeler pays for. Use a {class:Job} on a
  {class:Server} for CPU inference, or a {class:GPUJob} on a
  {class:GPUServer} for GPU inference. The {param:Server.server_type}
  parameter captures whether the server is owned outright,
  autoscaling, or serverless — none of those change the modeling
  primitive, only its sizing behaviour. {class:GPUServer} currently
  requires the modeler to supply most inputs (GPU type, per-GPU
  fabrication footprint, per-GPU power); [Boavizta's BoaviztAPI](https://api.boavizta.org/docs)
  exposes per-GPU data at its `/v1/component/gpu` endpoint, which can
  be fed into {class:GPUServer} by hand today and would be a natural
  source for future archetype helpers — contributions welcome.
- **The model runs on a third-party GenAI provider's infrastructure**
  — OpenAI, Anthropic, Mistral, and similar. Use
  {class:EcoLogitsGenAIExternalAPI} with its
  {class:EcoLogitsGenAIExternalAPIJob}. The EcoLogits integration
  looks up the model's parameter counts, throughput, datacenter
  location, and grid carbon intensity automatically; the modeler
  picks a provider, a model, and an average output token count. This
  is by far the cheapest and most accurate path when the model is not
  the modeler's to run.

Fine-tuning a model and serving it yourself puts you in the first
bullet (with a {class:GPUServer}). The EcoLogits path is specifically
for calls that hit an external provider's API.

## Python sketch

```python
# Two patterns, same country, different journeys
training_pattern = UsagePattern(
    "Weekly retraining",
    usage_journey=training_journey,
    devices=[],  # backend-only workload: no end-user device
    network=internal_network,
    country=country_fr,
    hourly_usage_journey_starts=weekly_pulse_of_one_start_per_week,
)

inference_pattern = UsagePattern(
    "Production inference",
    usage_journey=inference_journey,
    devices=[smartphone],
    network=mobile_network,
    country=country_fr,
    hourly_usage_journey_starts=hourly_traffic,
)
```

The underlying {class:Job}, {class:GPUJob}, or
{class:EcoLogitsGenAIExternalAPIJob} carries the per-call resource
numbers — ideally measured (via CodeCarbon, EcoLogits, or your own
profiling) rather than guessed.

> Load this scenario in the e-footprint interface:
> [Machine learning workflow]({{ config.extra.interface_base_url }}/machine_learning_workflow)
