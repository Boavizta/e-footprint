# Native multi-journey model profile — 2026-09-02

## Setup

- Library checkout: Task 1 review head `f70e05af`, plus the native profiler and deterministic gates described here.
- Runtime: macOS, Python 3.12, one new process per result, automatic GC enabled, 5 ms RSS sampler.
- Base scenario: 168 modeled hours, two web patterns, two edge patterns, three distinct journeys per pattern, and
  shared lower-level web and edge children.
- Representative scaling scenario: 8,760 hours, four web patterns, four edge patterns, and shared or distinct children.
- PSS, USS, and cgroup metrics were unavailable in this macOS sandbox; RSS is the available process measure. Values are
  single-run evidence, not portable thresholds or small-difference claims.

Every synthetic run serialized inputs only, released the authoring graph, then hydrated with e-footprint's
`json_to_system`. No Django or `ModelWeb` code was imported.

## Fresh-process scenario coverage

| Scenario | Calculation | Callbacks | Peak / retained RSS | Observable result |
|---|---:|---:|---:|---|
| Hydration | 0.000 s | 0 | 142.3 / 142.3 MiB | zero materialized reactive slots |
| Total footprint | 0.011 s | 178 | 143.1 / 143.1 MiB | 21.2127 kg |
| Cold attribution matrix | 0.023 s | 167 | 143.5 / 143.5 MiB | 120 scalar rows |
| Warm attribution matrix | &lt;0.001 s | 0 | 143.9 / 143.9 MiB | same 120 cached rows |
| Result-primed attribution matrix | 0.016 s | 55 | 143.5 / 143.5 MiB | same 120 rows |
| Direct manufacturing attribution | 0.013 s | 107 | 143.1 / 143.1 MiB | 0.7957 kg |
| Direct usage attribution | 0.013 s | 117 | 143.2 / 143.2 MiB | 0.3346 kg |
| Five retained attributed results | 0.031 s | 137 | 143.6 / 143.6 MiB | five live hourly results, 2.3419 kg summed |

Post-GC and post-release RSS matched retained RSS in these short macOS processes, which is allocator retention rather
than evidence that the model remains reachable. The cache inspection is the lifetime gate: every attribution scenario
reported zero cached transient source structures after source reduction.

## Scaling evidence

Each row is a fresh 8,760-hour process. Coordinate and array figures are cached computed-dictionary sub-slots after a
cold attribution matrix.

| Topology | Web step paths | Job coordinates | Edge component arrays | Edge server arrays | Scalar rows | Callbacks | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4 patterns × 1 shared journey | 4 | 8 | 12 | 4 | 80 | 225 | 158.1 MiB |
| 4 patterns × 5 shared journeys | 20 | 24 | 12 | 4 | 400 | 273 | 161.7 MiB |
| 4 patterns × 5 distinct-child journeys | 20 | 40 | 60 | 20 | 400 | 1,009 | 184.8 MiB |

Increasing shared journeys from one to five multiplied actual web path caches and scalar attribution rows by five.
The shared edge topology held hourly component arrays at `4 patterns × 3 distinct needs = 12` and server arrays at
`4 patterns × 1 distinct need = 4`; its 60 component containment paths and 20 server paths remained scalar inventory
entries rather than new hourly arrays. Giving every journey distinct edge children increased arrays to 60 and 20,
exactly the corresponding distinct `(pattern, need)` pair counts.

An additional shared-child run retained eight 8,760-hour attributed usage results: calculation time was 0.121 s, peak
RSS was 160.9 MiB, and zero transient source structures remained cached. No evidence justified a production cache
change or a transient `computed_dict` mechanism.

The interface's historical production/container evidence was neither moved nor edited; it remains linked from the
library laboratory README and retains responsibility for Django, middleware, cgroup, and deployment calibration.
