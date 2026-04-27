# Mission — e-footprint

## What e-footprint is

A Python toolkit for modeling the environmental impact of digital services, with a strong focus on **carbon footprint** (CO₂-eq) across the full lifecycle of digital infrastructure.

It uses a **declarative modeling approach**: users describe the system (servers, storage, network, devices, usage patterns), and the library automatically computes — and incrementally recomputes — the impact whenever any input changes, with full explainability of the calculation graph.

## Audience

- **Sustainability-aware product teams** sizing the environmental impact of a digital service before, during, or after building it.
- **Industrial users** modeling fleets of deployed devices (IoT, edge) and the web services they depend on.
- **Researchers and consultants** producing eco-design assessments who need a reproducible, transparent calculation.
- **Indirect: e-footprint-interface users** — the Django UI co-developed with the library.

The library is open-source and hosted within the [Boavizta](https://boavizta.org/) ecosystem.

## In scope (today)

- **Lifecycle phases:** fabrication and usage of servers, storage, network (usage only), end-user devices, and edge devices.
- **Two paradigms:**
  - *Web (demand-driven):* hourly demand → infrastructure footprint.
  - *Edge (deployment-driven):* number of deployed units × per-unit behaviour → fleet footprint.
- **Hierarchical edge fleets** via `EdgeDeviceGroup` with sub-groups and per-component multiplicity.
- **Bridge between paradigms:** `RecurrentServerNeed` lets edge fleets call into web-side jobs.
- **Full explainability:** every calculated value carries its formula and dependency graph; any input change triggers minimal incremental recomputation.
- **JSON serialization:** systems persist to JSON with optional calculated-attribute snapshots; migration handlers cover schema evolution.
- **Auto-generated mkdocs reference** per class, augmented by class-level descriptive metadata.

## Out of scope (today, by deliberate choice)

- Other environmental impact categories (water, rare earth metals, etc.) — planned via Boavizta API integration; tracked in `roadmap.md`.
- Transportation and end-of-life lifecycle phases — currently considered negligible.
- i18n; English only.
- Alternative serialization formats (XML, YAML, protobuf).

## Main components

- `efootprint/core/` — modeling primitives (servers, storage, networks, jobs, usage journeys, edge devices).
- `efootprint/abstract_modeling_classes/` — optimization layer (dependency tracking, automatic recomputation, explainability graph).
- `efootprint/builders/` — convenience builders with sensible defaults and external-data integrations (e.g. EcoLogits for LLM workloads).
- `efootprint/api_utils/` — `system_to_json` / `json_to_system` round-trip and version migration.

## Distribution & ecosystem

- **PyPI:** [`efootprint`](https://pypi.org/project/efootprint/).
- **Documentation:** https://boavizta.github.io/e-footprint/
- **Interface:** https://e-footprint.boavizta.org (open-source, separate repo).
- **Use cases:** [e-footprint-modelings](https://github.com/publicissapient-france/e-footprint-modelings).
- **License:** AGPL-3.0.
- **Maintenance:** Vincent Villet (Publicis Sapient), hosted by Boavizta.
