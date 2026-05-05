# Adjacent Tools - e-footprint

This document is the source of truth for how e-footprint relates to adjacent and complementary tools. Communication assets may reference it, but should not maintain their own separate list.

## Positioning principle

e-footprint is part of a cooperative ecosystem. Its center of gravity is explicit modeling: describing a digital service, its usage journeys or edge functionalities, its infrastructure, and its geographies so that teams can compare scenarios and prioritize ecodesign decisions.

Measurement, inventory, analytics, and observability tools can make e-footprint models more grounded. They help answer questions such as "what exists?", "what actually happened?", "how much did this journey consume?", or "how many times did users do this?". e-footprint then turns those inputs into a service-level model that can be inspected, explained, and changed before acting.

The long-term direction is not to freeze e-footprint as modeling-only. e-footprint may progressively industrialize measurement and data-ingestion capabilities where they strengthen modeling. The rule is that measurement remains in service of model calibration, scenario comparison, and decision-making.

## Current integrations / dependencies

### BoaviztAPI

**Status:** current integration and dependency.

**What it provides:** BoaviztAPI provides environmental impact methods and reference data for digital equipment and cloud resources. e-footprint currently uses it through builder classes such as `BoaviztaCloudServer` to retrieve cloud instance characteristics, embodied GWP, and average power from provider and instance-type inputs.

**What e-footprint adds:** BoaviztAPI returns equipment-level or resource-level impact data. e-footprint composes that data into a full service model: usage volumes, journeys, jobs, storage, network, device fleets, geographies, lifecycle phases, and explainable scenario comparisons.

**Integration direction:** keep BoaviztAPI as the reference source for infrastructure impact factors where available. Planned expansion to additional impact categories, such as water and rare-earth metals, should build on BoaviztAPI integration where the data and methodology support it.

**Reference:** https://doc.api.boavizta.org/

### EcoLogits

**Status:** current integration and dependency.

**What it provides:** EcoLogits estimates the energy consumption and environmental impacts of generative-AI API requests. It uses request and model features such as provider, model, generated tokens, latency, model parameters, datacenter assumptions, and electricity mix.

**What e-footprint adds:** e-footprint wraps EcoLogits inside `EcoLogitsGenAIExternalAPI` and `EcoLogitsGenAIExternalAPIJob`. EcoLogits supplies the per-call GenAI impact logic; e-footprint places those calls inside usage journeys, scales them by volume over time, and combines them with the rest of the modeled service.

**Integration direction:** keep EcoLogits as the GenAI API impact engine. e-footprint should avoid duplicating EcoLogits methodology and instead focus on connecting GenAI API calls to service-level usage, infrastructure, and scenario modeling.

**Reference:** https://ecologits.ai/

## Identified complementary tools

### CloudScanner

**Status:** identified complementary tool; possible future integration.

**What it provides:** CloudScanner is a Boavizta-family tool that analyzes environmental impact for AWS cloud resources. It combines live cloud inventory and usage data with BoaviztAPI, and can expose results as JSON or metrics.

**What e-footprint adds:** CloudScanner can help discover and quantify deployed cloud resources. e-footprint can use that information to initialize or calibrate a service model, then let teams ask forward-looking questions: what happens if traffic grows, workloads move, journeys change, or an architecture is redesigned?

**Integration direction:** use CloudScanner as a possible source of live cloud inventory and observed usage data for e-footprint models. The most useful bridge is likely a converter from CloudScanner outputs into e-footprint server, storage, and usage assumptions.

**Reference:** https://boavizta.github.io/cloud-scanner/

### Green Metrics Tool

**Status:** identified complementary tool; possible future integration.

**What it provides:** Green Metrics Tool measures energy and CO2 consumption of software. It supports reproducible measurements through configuration-as-code and metric providers for sensors and runtime environments such as RAPL, IPMI, PSU, Docker, temperature, and CPU.

**What e-footprint adds:** Green Metrics Tool can produce deep measurements for representative software executions or usage scenarios. e-footprint can use those measurements to calibrate job or journey-step resource consumption, then scale them by user volumes, recurrence patterns, countries, hardware, and lifecycle assumptions.

**Integration direction:** use Green Metrics Tool outputs as calibrated unit measurements for jobs or usage journey steps. This is especially relevant when default assumptions are too coarse and a team needs measured resource consumption before scaling it through an e-footprint model.

**Reference:** https://www.green-coding.io/products/green-metrics-tool/

## Long-term integration families

### Analytics providers

**Status:** long-term integration family. Google Analytics is the first named example.

**What they provide:** Analytics tools expose observed product usage: events, sessions, page or screen views, geographies, acquisition dimensions, and user volumes over time.

**What e-footprint adds:** e-footprint needs usage journeys, recurrence patterns, and volumes. Analytics data could help semi-automatically create or calibrate those journeys from observed behavior, while e-footprint keeps the modeling structure explicit enough for humans to inspect and change.

**Integration direction:** ingest aggregated analytics data to propose usage journeys, journey volumes, countries, and temporal patterns. The integration should stay explainable: imported data should become model assumptions with clear source attribution, not opaque automatic truth.

**Example reference:** https://developers.google.com/analytics/devguides/reporting/data/v1

### Observability and application performance monitoring providers

**Status:** long-term integration family. Dynatrace is the first named example.

**What they provide:** Observability and application performance monitoring providers collect operational data such as user sessions, user actions, service calls, traces, infrastructure metrics, request durations, errors, and server load.

**What e-footprint adds:** e-footprint can use this data to connect user behavior to backend work: infer which jobs are triggered by which journeys, calibrate job resource needs from observed server load, and validate whether a model resembles the production system it represents.

**Integration direction:** ingest aggregated observability data to calibrate job consumption, request duration, service dependencies, and journey-to-backend mappings. This should support model creation and calibration, not turn e-footprint into a general observability platform.

**Example reference:** https://docs.dynatrace.com/docs/observe/digital-experience/rum-concepts/user-session
