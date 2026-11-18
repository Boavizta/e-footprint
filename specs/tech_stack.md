# Tech stack — e-footprint

## Language and runtime

- **Python ≥ 3.12** (declared in `pyproject.toml`'s `[project]` table as `requires-python = ">=3.12,<4.0"`).
- **Poetry** (≥2.0, for the PEP 621 `[project]` layout) for dependency management and builds. The Poetry environment is the canonical Python interpreter for development; do not prefix commands with `PYTHONPATH=...`.
- **Support policy: rolling window, no cap on 3.x minors.** The floor is `>=3.12`; "supported" means the latest Python minors that every compiled dependency ships wheels for — today that's 3.12 and 3.13, reflected in `pyproject.toml`'s curated `classifiers`. The next minor is added (and its classifier appended) once its wheels land for all compiled deps. The `<4.0` bound in `requires-python` is a major-series guard, not a ceiling on the rolling window.

## Core libraries

| Library | Why | Version |
|---|---|---|
| **Pint** | Unit handling. Custom units in `efootprint/constants/custom_units.txt`. | `>=0.25,<0.26` |
| **NumPy** | Numerical arrays for hourly timeseries. | `>=2,<3` |
| **orjson** | Fast JSON serialization for system snapshots. | `>=3.11,<4.0` |
| **zstandard** | Compression for large timeseries payloads. Stays required: a benchmark (2026-06-30) showed it is fast and costs about 0 MB of RAM to import. | `>=0.23,<0.24` |
| **pytz** | Timezone handling for `convert_to_utc` paths. | `==2024.1` |

## Optional dependency groups

`pip install efootprint` installs the core only. The groups below are declared under `[project.optional-dependencies]` and installed with `pip install "efootprint[<group>]"`; `all` combines them. Their packages are imported inside the functions that need them, wrapped in `efootprint.utils.optional_dependencies.requires_extra`, which names the group to install when a package is missing.

| Group | Library | Why | Version |
|---|---|---|---|
| `viz` | **Matplotlib** | Plot generation; tests must use `MPLBACKEND=Agg`. | `>=3.10,<4.0` |
| `viz` | **plotly** | Interactive charts for explainability graphs and Sankey figures. | `>=6,<7` |
| `viz` | **pyvis** | Object-relationship and calculation graph rendering. | `==0.3.2` |
| `boaviztapi` | **boaviztapi** | Offline fallback for the Boavizta server builders when the web API is unreachable. | `>=2,<3` |

## Domain integrations

- **EcoLogits** (`>=0.11,<0.12`) — emission factors for LLM workloads (used by `EcoLogitsGenAIExternalAPI` builders).
- **Boavizta API** — server manufacturing footprint (used by `BoaviztaCloudServer`), called over the web at `https://api.boavizta.org`; the `boaviztapi` optional group provides the same computation offline. Planned expansion to water and rare-earth metals.

## Tooling

- **pytest** + **pytest-cov** for tests (unit, integration, performance).
- **Black** with line length 120 (`target-version = ['py312']`).
- **mkdocs-material** + **pymdown-extensions** for the public documentation site.
- **Jupyter** + **ipykernel** for the tutorial notebook and doc generation.

## Distribution

- Published to PyPI as **`efootprint`**.
- Documentation site: https://boavizta.github.io/e-footprint/ (deployed via `mkdocs gh-deploy`).
- License: AGPL-3.0.
- `.github/workflows/ci.yml` runs the full test suite on every push to `main` and every PR, across the
  supported Python matrix (3.12 + 3.13), with every optional group installed. A second `bare-core` job runs
  the suite on the core install alone.
- A `Dockerfile` gives a toolchain-independent way to run a model (`docker build` + `docker run`, see
  README's "Run with Docker"). Not published to a registry — publishing it was judged premature and
  parked (see `AGENTS.md`).

## Versioning policy

- Semantic versioning: `MAJOR.MINOR.PATCH`.
- A **JSON schema migration** (in `version_upgrade_handlers.py`) requires a `MAJOR` bump.
- New classes or backward-compatible additions are `MINOR`.
- Bug fixes without schema impact are `PATCH`.

## Out of scope

- Python < 3.12 (constitution §4).
- Replacing Pint or NumPy without a constitutional change.
- i18n.
