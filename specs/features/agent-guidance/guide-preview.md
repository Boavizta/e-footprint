# Agent guide — planning preview

On hold with the [plan](plan.md). Its example sources, ownership map and tutorial exclusion must
be revised after executable-modeling-documentation; see the [resumption instructions](resume.md).

This is the proposed reading order with the actual existing source text and explicitly marked gaps.
It is a review artifact, not another maintained guide. Implementation improves the owning canonical
sources and assembles them; this file does not ship. Preview-source notes and GAP blocks are not
command output. The script is deliberately the current source, pending the listed adaptation.

| Part | Canonical owner | Planned work |
|---|---|---|
| Purpose and scope | why_efootprint; efootprint_scope | Include the opening and scope page; render lookup links. |
| Modeling method | methodology | Include current sections, add a later results section. |
| Workflow and editability | modeling_with_ai | Author missing ordinary documentation. |
| Web and edge | web_vs_edge | Include the complete explanation. |
| Builders, conventions, reactive context | modeling_from_python | Author missing public Python guidance. |
| Full model, result inspection, exports | modeling_examples/reference_system.py | Adapt docs_case once; website and guide include named source regions. |
| How-to catalogue | Eight topic titles and topic registry | Generate names and commands. |
| Bug reporting | reporting_bugs | Author support guidance and link it from CONTRIBUTING. |
| Results and delivery | methodology; modeling_with_ai | Include their owning sections and executable recipes. |

All eight specialized how-to/edge pages are offered as lookups, including attribution and edge
hardware. Introduction, scope, methodology and the three new guidance pages are also lookups,
so their links resolve. The tutorial and get_started remain website-only, reached by explicit
website URLs rather than nonexistent command names.

Current review text below: 27,297 characters, about 6,824 tokens by the characters/4 heuristic, including gaps and the unadapted script. Missing prose and final example changes will change this count. Re-measure the implemented guide; 10,000 tokens is an allowance, not a ceiling.

## Purpose

> Preview source: why_efootprint.md — opening

> **GAP — website framing.** The page-forward paragraph below describes the whole website article, not this selected excerpt. #guide-assembly selects a named introduction region after the canonical page separates that framing; it does not rewrite the paragraph for agents.

# Why e-footprint ?

**We define ecodesign as the process of building or maintaining a digital service while minimizing its environmental impact.** Doing it well is less a question of *what could I do?* than of *what should I do first, and what impact would that have?*: out of all the actions a team could take to reduce a service's footprint, only some move the needle — and on every service it is a *different* some. Answering *which, in what order, and with what impact* is the problem e-footprint exists to solve.

This page lays out the three strategies teams use to answer that question, why modeling is the one e-footprint focuses on, why an explicit model is necessary at all, how precise it needs to be, and what a model of a digital service must therefore contain.



## Scope

> Preview source: efootprint_scope.md — complete page

# e-footprint scope

e-footprint aims at being a digital service carbon footprint modeling tool (more on what is means later). First of all, what is a digital service ? **We call digital service any set of information technology tools that allow users to accomplish something, including all hardware, software, and peripheral equipment**. In other words, the sum of all digital services makes up the entirety of the digital world. This scope is very large and that’s why e-footprint has taken a detailed low-level approach. This fine granularity is complemented by a library of higher-level builders like the Boavizta cloud server builder (`python -m efootprint.agent_guide BoaviztaCloudServer`) that allow for the creation of objects with fewer parameters for better usability. **Of course some digital services will be harder to model with e-footprint than others, but all can be approximated**. Refer to the how-to section for more information on how to model different types of services.

Read the Why e-footprint ? (`python -m efootprint.agent_guide why_efootprint`) article to understand the need for such a tool when ecodesigning a digital service.

## Methodology

> Preview source: methodology.md — current page, before the planned results section

# The e-footprint methodology

## High-level modeling then refinement
**Ecodesigning with e-footprint is an iterative process.** Since e-footprint is a modeling tool, it is possible (and advised) to **start with a very high level modeling of the studied system**. This first modeling will be very inaccurate but give useful orders of magnitude: I know that the impact potential of my ecodesign initiative will be much greater if my first modeling shows me 1000 tons of CO2 / year than if it shows only 100 kg / year, and I will size my efforts accordingly. An advantage of this approach is that it doesn’t require the installation of any tool. Then, depending on the results of this first analysis, I have 3 choices:

- **Stop modeling** because my system is too small to justify investing in ecodesigning it.
- **Invest effort to increase the granularity of my modeling** because it is not enough to guide decision.
- **Decide that the model is detailed enough** to make decisions and got to the next step.

## Modeling analysis
If the system is big enough, and once the model has been refined enough, comes the analysis time. It consists in **diving into the results of the model to understand where emissions come from and what the emission reduction opportunities are**. For example, if the analysis shows that much of the impact comes from the network, I can look up the network ecodesign best practices for inspiration, or simply ask the tech team.

## Simulation and priorisation
When ecodesign opportunities or new features are considered, they are implemented as changes to the e-footprint model, e-footprint computes the new impact of the system, and the difference between the old and the new footprint is the **environmental return on investment of the action**. Since modeling often takes orders of magnitude less time than implementing, this approach allows for an efficient **prioritization of effort: you will finally be able to choose the most impactful best practice for your particular conditions** !

This simulation loop should be re-triggered at every **structuring decision** of the service lifecycle — scaling up, adding a feature (typically an AI capability), considering an ecodesign action, changing hosting — not only once after the model is first refined. Modeling before deciding puts the trade-off back on informed ground.

## Working with the user

> Preview source: modeling_with_ai.md — Workflow

> **GAP — canonical text to author.** #modeling-workflow adds boundaries, scale, consequential assumptions, AI model and hosting questions, and agreement on a model overview before coding.

## Web and edge

> Preview source: web_vs_edge.md — complete page

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

Both paradigms organize the model the same way — a *pattern* selects one
or more *journeys*, which are composed of *units of work* — but each layer means
something different:

| Layer        | Web                                              | Edge                                                                 |
|--------------|--------------------------------------------------|----------------------------------------------------------------------|
| Pattern      | UsagePattern (`python -m efootprint.agent_guide UsagePattern`) — hourly rate of **pattern occurrences** in a country, with a positive weight per journey. | EdgeUsagePattern (`python -m efootprint.agent_guide EdgeUsagePattern`) — hourly rate and EdgeUsagePattern.usage_span (`python -m efootprint.agent_guide EdgeUsagePattern`) of **device deployments** in a country. |
| Journey      | UsageJourney (`python -m efootprint.agent_guide UsageJourney`) — *one visit*: a short, discrete sequence of steps. | EdgeUsageJourney (`python -m efootprint.agent_guide EdgeUsageJourney`) — a reusable functionality bundle carried by each deployment: a set of functions that can span several device types. |
| Unit of work | UsageJourneyStep (`python -m efootprint.agent_guide UsageJourneyStep`) — a discrete step with bounded UsageJourneyStep.user_time_spent (`python -m efootprint.agent_guide UsageJourneyStep`), triggering Job (`python -m efootprint.agent_guide Job`)s once per step. | EdgeFunction (`python -m efootprint.agent_guide EdgeFunction`) — a coherent feature, described by **recurring** device-side needs (RecurrentEdgeDeviceNeed (`python -m efootprint.agent_guide RecurrentEdgeDeviceNeed`)) and **recurring** server-side jobs (RecurrentServerNeed (`python -m efootprint.agent_guide RecurrentServerNeed`)) — unbounded in time. |

Reading the table top to bottom captures the difference in one line:

- **Web** is **unitary journeys × volume**: each visit is short and
  discrete; impact scales with how many *start* per hour.
- **Edge** is **recurrent functions × deployed units**: each deployment
  runs for its pattern's usage span and its bundles decompose into functions described by *what runs
  recurrently*, not by per-call payloads. The count of deployed units
  actively in service comes from the deployment schedule and the
  EdgeUsagePattern.usage_span (`python -m efootprint.agent_guide EdgeUsagePattern`) (calculated by
  EdgeUsagePattern.nb_deployments_in_parallel (`python -m efootprint.agent_guide EdgeUsagePattern`)).

## Where they meet

The bridge between paradigms is RecurrentServerNeed (`python -m efootprint.agent_guide RecurrentServerNeed`). It attaches
to an edge device and holds a per-unit weekly pattern (168 hours) of
recurrent server interaction, plus the list of Job (`python -m efootprint.agent_guide Job`) objects the
device triggers on the web side. At calculation time, the per-unit
volume is multiplied by the device's total units per deployment (its EdgeDeviceGroup (`python -m efootprint.agent_guide EdgeDeviceGroup`)
hierarchy unrolled, one when ungrouped) and by the deployments in service
(EdgeUsagePattern.nb_deployments_in_parallel (`python -m efootprint.agent_guide EdgeUsagePattern`)) to produce the hourly demand those jobs
impose on the web infrastructure.

## Builders

> Preview source: modeling_from_python.md — Builders

> **GAP — canonical text to author.** #python-guidance explains defaults, external data and object wiring supplied by builders, with remaining assumptions to check. Class-specific semantics remain in class metadata.

## Shared conventions

> Preview source: modeling_from_python.md — Values and volumes

> **GAP — canonical text to author.** #python-guidance authors units, meaningful hypothesis and measured sources, defaults, country boundaries, hourly and recurrent volumes before the example.

## Editable timeseries

> Preview source: modeling_with_ai.md — Timeseries

> **GAP — canonical text to author.** #modeling-workflow recommends form-input hourly, constant and weekly-profile builders; custom arrays require an explicit discussion of being viewable but not editable in the interface. Exact builder inputs come from class lookups rendering param_descriptions, including structured form_inputs fields; they are not repeated here.

## Full mixed model — current source to adapt

> Preview source: docs_sources/doc_utils/docs_case.py → modeling_examples/reference_system.py

> **GAP — canonical source adaptation.** #canonical-example replaces random hourly inputs and raw recurrent arrays with form-input builders; removes redundant source=None while declaring meaningful sources; connects the group and workload component; uses plain Server instead of Boavizta hardware; retains core EcoLogits/video examples. The implementation supplies the runnable full replacement here. The current script below exposes the exact starting material, not the proposed final code.

```python
from time import perf_counter

import numpy as np
from pint import Quantity

from efootprint.builders.external_apis.ecologits.ecologits_external_api import EcoLogitsGenAIExternalAPI, \
    EcoLogitsGenAIExternalAPIJob
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed

start = perf_counter()

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job, GPUJob
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.system import System
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_random_source_hourly_values, create_hourly_usage_from_frequency
from efootprint.logger import logger
logger.info(f"Finished importing modules in {round((perf_counter() - start), 3)} seconds")


storage = Storage(
    "storage",
    carbon_footprint_manufacturing_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored, source=None),
    lifespan=SourceValue(6 * u.years, source=None),
    storage_capacity=SourceValue(1 * u.TB_stored, source=None),
    data_replication_factor=SourceValue(3 * u.dimensionless, source=None),
    data_storage_duration=SourceValue(2 * u.year, source=None),
    base_storage_need=SourceValue(0 * u.TB_stored, source=None)
)

autoscaling_server = Server(
    "server",
    server_type=ServerTypes.autoscaling(),
    carbon_footprint_manufacturing=SourceValue(600 * u.kg, source=None),
    power=SourceValue(300 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power=SourceValue(50 * u.W, source=None),
    ram=SourceValue(128 * u.GB_ram, source=None),
    compute=SourceValue(24 * u.cpu_core, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    base_ram_consumption=SourceValue(300 * u.MB_ram, source=None),
    base_compute_consumption=SourceValue(2 * u.cpu_core, source=None),
    storage=storage
)

serverless_server = BoaviztaCloudServer.from_defaults(
    "serverless cloud functions",
    server_type=ServerTypes.serverless(),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    storage=Storage.ssd()
)

on_premise_gpu_server = GPUServer.from_defaults(
    "on premise GPU server",
    server_type=ServerTypes.on_premise(),
    lifespan=SourceValue(6 * u.year, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    storage=Storage.ssd()
)

video_streaming = VideoStreaming.from_defaults("Video streaming service", server=autoscaling_server)
genai_model = EcoLogitsGenAIExternalAPI.from_defaults("Generative AI model")
genai_video_model = EcoLogitsVideoGenExternalAPI.from_defaults("Generative AI video model")

video_streaming_job = VideoStreamingJob.from_defaults(
    "Video streaming job", service=video_streaming, video_duration=SourceValue(20 * u.min))
genai_model_job = EcoLogitsGenAIExternalAPIJob.from_defaults("Generative AI model job", external_api=genai_model)
genai_video_model_job = EcoLogitsVideoGenExternalAPIJob.from_defaults(
    "Generative AI video model job", external_api=genai_video_model)
manually_written_job = Job.from_defaults("Manually defined job", server=autoscaling_server)
custom_gpu_job = GPUJob.from_defaults("Manually defined GPU job", server=on_premise_gpu_server)

streaming_step = UsageJourneyStep(
    "20 min streaming",
    user_time_spent=SourceValue(20 * u.min, source=None),
    jobs=[genai_model_job, genai_video_model_job, video_streaming_job, manually_written_job, custom_gpu_job,
          manually_written_job]
    )

usage_journey = UsageJourney("user journey", uj_steps=[streaming_step])

network = Network(
        "network",
        bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))
random_hourly_occurrences = create_random_source_hourly_values(timespan=3 * u.year)
random_hourly_occurrences.source = None
usage_pattern = UsagePattern(
    "usage pattern",
    usage_journeys=[usage_journey],
    devices=[
        Device(name="device on which the user journey is made",
                 carbon_footprint_manufacturing=SourceValue(156 * u.kg, source=None),
                 power=SourceValue(50 * u.W, source=None),
                 lifespan=SourceValue(6 * u.year, source=None),
                 fraction_of_usage_time=SourceValue(7 * u.hour / u.day, source=None))],
    network=network,
    country=country_generator(
            "devices country", "its 3 letter shortname, for example FRA", SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
    hourly_occurrences=random_hourly_occurrences)

edge_storage = EdgeStorage(
    "edge SSD storage",
    carbon_footprint_manufacturing_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored, source=None),
    lifespan=SourceValue(6 * u.years, source=None),
    storage_capacity_per_unit=SourceValue(256 * u.GB_stored, source=None),
    base_storage_need=SourceValue(10 * u.GB_stored, source=None),
)

edge_computer = EdgeComputer(
    "edge computer",
    carbon_footprint_manufacturing=SourceValue(60 * u.kg, source=None),
    power=SourceValue(30 * u.W, source=None),
    lifespan=SourceValue(8 * u.year, source=None),
    idle_power=SourceValue(5 * u.W, source=None),
    ram=SourceValue(16 * u.GB_ram, source=None),
    compute=SourceValue(8 * u.cpu_core, source=None),
    base_ram_consumption=SourceValue(1 * u.GB_ram, source=None),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core, source=None),
    storage=edge_storage
)

edge_process = RecurrentEdgeProcess(
    "edge process",
    edge_device=edge_computer,
    recurrent_compute_needed=SourceRecurrentValues(
        Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core), source=None),
    recurrent_ram_needed=SourceRecurrentValues(
        Quantity(np.array([2] * 168, dtype=np.float32), u.GB_ram), source=None),
    recurrent_storage_needed=SourceRecurrentValues(
        Quantity(np.array([200] * 168, dtype=np.float32), u.kB_stored), source=None)
)

edge_appliance = EdgeAppliance(
    "edge appliance",
    carbon_footprint_manufacturing=SourceValue(60 * u.kg, source=None),
    power=SourceValue(30 * u.W, source=None),
    lifespan=SourceValue(8 * u.year, source=None),
    idle_power=SourceValue(5 * u.W, source=None)
)

edge_workload = RecurrentEdgeWorkload(
    "edge workload",
    edge_device=edge_appliance,
    recurrent_workload=SourceRecurrentValues(
        Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent), source=None)
)

ram_component = EdgeRAMComponent(
    "edge RAM component",
    carbon_footprint_manufacturing_per_unit=SourceValue(20 * u.kg, source=None),
    power_per_unit=SourceValue(10 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power_per_unit=SourceValue(2 * u.W, source=None),
    ram_per_unit=SourceValue(8 * u.GB_ram, source=None),
    base_ram_consumption=SourceValue(1 * u.GB_ram, source=None)
)

cpu_component = EdgeCPUComponent(
    "edge CPU component",
    carbon_footprint_manufacturing_per_unit=SourceValue(20 * u.kg, source=None),
    power_per_unit=SourceValue(15 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power_per_unit=SourceValue(3 * u.W, source=None),
    compute_per_unit=SourceValue(4 * u.cpu_core, source=None),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core, source=None)
)

storage_component = EdgeStorage(
    "edge storage component",
    carbon_footprint_manufacturing_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored, source=None),
    lifespan=SourceValue(6 * u.years, source=None),
    storage_capacity_per_unit=SourceValue(512 * u.GB_stored, source=None),
    base_storage_need=SourceValue(20 * u.GB_stored, source=None),
)

edge_device = EdgeDevice(
    "custom edge device",
    structure_carbon_footprint_manufacturing=SourceValue(50 * u.kg, source=None),
    components=[ram_component, cpu_component, storage_component],
    lifespan=SourceValue(6 * u.year, source=None)
)

ram_need = RecurrentEdgeComponentNeed(
    "RAM need",
    edge_component=ram_component,
    recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB_ram), source=None)
)
cpu_need = RecurrentEdgeComponentNeed(
    "CPU need",
    edge_component=cpu_component,
    recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core), source=None)
)

storage_need = RecurrentEdgeStorageNeed(
    "Storage need",
    edge_component=storage_component,
    recurrent_need=SourceRecurrentValues(
        Quantity(np.array([50] * 84 + [-50] * 84, dtype=np.float32), u.MB_stored), source=None)
)

edge_device_need = RecurrentEdgeDeviceNeed(
    "custom edge device need",
    edge_device=edge_device,
    recurrent_edge_component_needs=[ram_need, cpu_need, storage_need]
)

recurrent_volume = SourceRecurrentValues(np.array([1.0] * 168, dtype=np.float32) * u.occurrence, source=None)
recurrent_server_need = RecurrentServerNeed(
            "Server need",
            edge_device=edge_computer,
            recurrent_volume_per_edge_device=recurrent_volume,
            jobs=[manually_written_job])

edge_function = EdgeFunction(
    "edge function",
    recurrent_edge_device_needs=[edge_process, edge_workload, edge_device_need],
    recurrent_server_needs=[recurrent_server_need]
)

edge_usage_journey = EdgeUsageJourney(
    "edge usage journey",
    edge_functions=[edge_function]
)

edge_usage_pattern = EdgeUsagePattern(
    "Default edge usage pattern",
    edge_usage_journeys=[edge_usage_journey],
    country=country_generator(
            "devices country", "its 3 letter shortname, for example FRA",
        SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
    network=network,
    hourly_deployment_starts=create_hourly_usage_from_frequency(
        timespan=6 * u.year, input_volume=1000, frequency='weekly',
        active_days=[0, 1, 2, 3, 4, 5], hours=[8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19]),
    usage_span=SourceValue(6 * u.year, source=None)
        )

workload_component = EdgeWorkloadComponent(
    "edge workload component",
    carbon_footprint_manufacturing_per_unit=SourceValue(80 * u.kg, source=None),
    power_per_unit=SourceValue(40 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power_per_unit=SourceValue(4 * u.W, source=None)
)

edge_device_group = EdgeDeviceGroup(
    "edge device group",
    edge_device_counts=ExplainableObjectDict(
        {edge_device: SourceValue(2 * u.dimensionless, source=None)})
)

system = System("system", usage_patterns=[usage_pattern], edge_usage_patterns=[edge_usage_pattern])

logger.info(f"computation took {round((perf_counter() - start), 3)} seconds")
```

## How-to and reference discovery

> Preview source: page titles and the planned shared registries

- Web vs edge modeling — `python -m efootprint.agent_guide web_vs_edge`
- How to model a database — `python -m efootprint.agent_guide database_modeling`
- How to model server-to-server interaction — `python -m efootprint.agent_guide server_to_server_interaction`
- How to model serverless / per-invocation workloads — `python -m efootprint.agent_guide serverless_modeling`
- How to model a machine-learning workflow — `python -m efootprint.agent_guide machine_learning_workflow`
- Edge usage — `python -m efootprint.agent_guide usage_edge_index`
- Edge hardware — `python -m efootprint.agent_guide hardware_edge_index`
- How to read a footprint per tenant or per provider — `python -m efootprint.agent_guide attributing_footprint`

Class lookup: `python -m efootprint.agent_guide Server`. Other examples: `python -m efootprint.agent_guide examples`.

## Public reactive model

> Preview source: modeling_from_python.md — Public reactive API

> **GAP — canonical text to author.** #python-guidance explains lazy public reads, tracked dependencies, invalidation and transactional updates; engine exploration is reserved for investigating a suspected bug.

## Reporting a suspected bug

> Preview source: reporting_bugs.md — complete page

> **GAP — canonical text to author.** #support-results provides installed version, minimal reproducing script, expected and actual behavior, and an explanation only when supported by evidence. Suggest the repository report; leave submission to the user.

## Reading the results

> Preview source: methodology.md — Reading results

> **GAP — canonical text to author.** #support-results uses totals, dominant contributors, uncertainty and potential absolute savings to guide effort; #trial-pitfalls owns the raw-versus-provisioned sizing diagnostic in server metadata. Executable result inspection comes from #canonical-example.

## Delivering the model

> Preview source: modeling_with_ai.md — Delivery, including reference_system.py export regions

> **GAP — canonical text to author.** #modeling-workflow documents system_to_json, systems_to_json, duplicate_system and materialize_serialized_state. #canonical-example supplies executable single-file and ordered comparison-file recipes, corresponding ids preserved; include explicit materialization when saved values are required. The interface computes missing values on import.
