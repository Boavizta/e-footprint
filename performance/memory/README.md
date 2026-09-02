# Model-engine memory laboratory

This is the canonical home for e-footprint model-engine memory and cache-scaling benchmarks. The profiler uses the
public library loader and calculation APIs directly: it imports neither Django nor `ModelWeb` and adds no
benchmark-only production hook.

The interface laboratory and its historical production/container evidence remain in place at
[`e-footprint-interface/performance/memory/`](../../../e-footprint-interface/performance/memory/README.md). Use that
laboratory for Django/session hydration, rendered Sankey payloads, middleware sampling, cgroup enforcement, and
production-container calibration. Use this one for calculation topology, reactive cache shape, attribution-source
lifetime, and retained model results.

## Reproduce a native profile

Run each scenario in its own process so allocator history from another scenario cannot affect the result:

```bash
poetry run python -m performance.memory.profile_model \
  --scenario cold-attribution-matrix \
  --modeled-hours 8760 \
  --pattern-count 4 \
  --journeys-per-pattern 5 \
  --shared-children shared
```

`--shared-children distinct` gives every journey its own step/job and edge function/device/needs. In shared mode,
journeys stay distinct and reusable while all web journeys share one step/job and all edge bundles share one function,
process, server need, and component-need set. This is the pressure case for proving that edge arrays follow distinct
`(pattern, need)` pairs instead of scalar bundle paths.

Pass `--model /absolute/path/to/system.json` to load an existing e-footprint JSON model. Synthetic runs first serialize
inputs only, release the authoring graph, and hydrate the payload with `json_to_system`; hydration therefore exercises
the same native library boundary without carrying warm calculated state.

The final `RESULT` line is JSON. It includes topology dimensions, successful reactive callback counts, materialized
coordinate/cache-slot counts, attribution row count, elapsed time, retained and post-GC memory, and per-stage peaks.
RSS is always reported. PSS/USS and cgroup current/peak are included when the operating system exposes them. Commit
interpreted, dated evidence under `results/`; keep heap dumps, Memray captures, and raw bulk output under `artifacts/`,
which Git ignores.

## Scenarios

| Scenario | Measured operation |
|---|---|
| `hydrate` | Native JSON hydration only |
| `total-footprint` | Cold `System.total_footprint` |
| `cold-attribution-matrix` | Cold condensed attribution matrix |
| `warm-attribution-matrix` | Matrix read after priming that same model |
| `result-primed-attribution-matrix` | Matrix after priming total footprint |
| `attributed-manufacturing` | Direct manufacturing attribution for one edge pattern |
| `attributed-usage` | Direct usage attribution for one edge pattern |
| `retained-attributed-results` | Repeated direct usage attribution with returned hourly results retained |

Use at least three fresh-process repetitions before interpreting small RSS or latency differences. Memory readings are
evidence, not cross-platform pass/fail thresholds. Deterministic correctness gates live in
`tests/performance_tests/test_multi_journey_scaling.py`; run them with:

```bash
poetry run pytest tests/performance_tests/test_multi_journey_scaling.py
```
