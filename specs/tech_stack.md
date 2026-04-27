# Tech stack — e-footprint

## Language and runtime

- **Python ≥ 3.12** (declared in `pyproject.toml` as `^3.12`).
- **Poetry** for dependency management and builds. The Poetry environment is the canonical Python interpreter for development; do not prefix commands with `PYTHONPATH=...`.

## Core libraries

| Library | Why | Version |
|---|---|---|
| **Pint** | Unit handling. Custom units in `efootprint/constants/custom_units.txt`. | `^0.25` |
| **Pandas** | Tabular and time-indexed data manipulation. | `^2` |
| **NumPy** | Numerical arrays for hourly timeseries (transitive via Pandas/Pint). | (transitive) |
| **Matplotlib** | Plot generation; tests must use `MPLBACKEND=Agg`. | `^3.10` |
| **plotly** | Interactive charts for explainability graphs. | `5.19` |
| **pyvis** | Object-relationship graph rendering. | `0.3.2` |
| **orjson** | Fast JSON serialization for system snapshots. | `^3.11` |
| **zstandard** | Compression for large timeseries payloads. | `^0.23` |
| **pytz** | Timezone handling for `convert_to_utc` paths. | `2024.1` |

## Domain integrations

- **EcoLogits** (`^0.10`) — emission factors for LLM workloads (used by `EcoLogitsGenAIExternalAPI` builders).
- **Boavizta API** (`^2`) — server fabrication footprint (used by `BoaviztaCloudServer`); planned expansion to water and rare-earth metals.

## Tooling

- **pytest** + **pytest-cov** for tests (unit, integration, performance).
- **Black** with line length 120 (`target-version = ['py312']`).
- **mkdocs-material** + **pymdown-extensions** for the public documentation site.
- **Jupyter** + **ipykernel** for the tutorial notebook and doc generation.

## Distribution

- Published to PyPI as **`efootprint`**.
- Documentation site: https://boavizta.github.io/e-footprint/ (deployed via `mkdocs gh-deploy`).
- License: AGPL-3.0.

## Versioning policy

- Semantic versioning: `MAJOR.MINOR.PATCH`.
- A **JSON schema migration** (in `version_upgrade_handlers.py`) requires a `MAJOR` bump.
- New classes or backward-compatible additions are `MINOR`.
- Bug fixes without schema impact are `PATCH`.

## Out of scope

- Python < 3.12 (constitution §4).
- Replacing Pint, NumPy, or Pandas without a constitutional change.
- i18n.
