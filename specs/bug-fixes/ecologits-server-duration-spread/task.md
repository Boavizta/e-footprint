# Fix: spread EcoLogits external-API server impact over request duration

**Status:** Done

## Problem

The EcoLogits external-API server aggregator books a job's **entire** per-request
energy / usage-GWP / embodied-GWP in the single hour the request *starts*, instead of
spreading it over the hours the request actually runs.

It does this because it multiplies the per-request figures by the job's **raw** hourly
occurrence series (`hourly_occurrences_across_usage_patterns`, request *start* counts),
e.g. in `update_energy_footprint`:

```python
energy_footprint += job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns
```

Every other footprint source that scales with how long work runs is already
duration-aware:

- a normal `ServerBase` derives load from `hourly_avg_occurrences_across_usage_patterns × *_needed`;
- `Network` / `Storage` spread their per-request volume via
  `compute_hourly_data_exchange_for_usage_pattern`:
  `data_transferred × (1h / request_duration) × hourly_avg_occurrences_per_usage_pattern`.

These external-API jobs carry `compute_needed = ram_needed = 0`, so the normal
resource-need path produces nothing and this aggregator is the *only* thing booking their
impact — and it's the one source that ignores `request_duration`.

**Symptom:** a video-generation job whose `request_duration` exceeds one hour (e.g. the
~62 min "49 x Video generation on Kling" job in the repro model) has all its server energy
and embodied GWP charged to its start hour, appearing as an hour-1 spike rather than a
profile spread across the hours it runs.

## Fix

In `efootprint/builders/external_apis/ecologits/ecologits_external_api.py`,
make the five aggregation methods spread per-request totals over `request_duration`,
mirroring the network/storage pattern:

```
per_hour_value = job.request_<X> * (1 hour / job.request_duration)
hourly_value   = per_hour_value * job.hourly_avg_occurrences_across_usage_patterns
```

Methods to update:

| Method | `request_<X>` |
|---|---|
| `update_energy_footprint` | `request_usage_gwp` |
| `update_instances_energy` | `request_energy` |
| `update_instances_fabrication_footprint` | `request_embodied_gwp` |
| `update_dict_element_in_usage_impact_repartition_weights` | `request_usage_gwp` |
| `update_dict_element_in_fabrication_impact_repartition_weights` | `request_embodied_gwp` |

> **Not a raw→avg swap.** `request_*` are per-request *totals*, so simply substituting the
> averaged occurrence series would change magnitudes. The `× (1h / request_duration)`
> factor is required. Totals are preserved because, over the request window,
> `∫ avg_occurrences dt = occurrence_count × request_duration`, so
> `Σ_hours (request_X / duration × avg_occurrences) = request_X × occurrence_count` — the
> same total as today, just redistributed in time.

## Scope / relationship to the other fix

- This fix is **independently correct** and stands alone: it makes the dominant cost
  (server energy/embodied) land in the hours the request runs.
- It does **not**, on its own, fix the Results-panel crash
  (`neutral remainder is negative`). That crash is caused by the attribution-share chain
  truncating any footprint that extends past the journey's start hour — see the sibling
  fix [`../duration-aware-impact-attribution/spec.html`](../duration-aware-impact-attribution/spec.html).
  (Verified: spreading the server here alone still crashes, because the tail is dropped one
  hop higher in the chain.)
- Do this fix first — it is small, low-risk, and the spread footprints it produces are
  exactly what the attribution fix then needs to carry through.

## Validation

- For the repro model (`bug/bug when clicking results.json`), the EcoLogits server
  `energy_footprint` / `instances_fabrication_footprint` of the long Kling job span its full
  run window (≈ hours 11:00 and 12:00) instead of length-1 at 11:00.
- `system.total_footprint.sum()` is **unchanged** (≈ `4.2747 kg`) — redistribution in time,
  not a magnitude change. Assert this explicitly.
- Existing models whose jobs are all shorter than an hour are byte-identical (no
  regression): the spread collapses back to a single hour when `request_duration ≤ 1h` and
  occurrences start mid-hour without crossing the boundary.
- Full `pytest` green; JSON round-trip preserved (no schema change expected); `CHANGELOG.md`
  entry.

## Constitution check

- §3.1 "never paper over a bug": this addresses a real temporal-allocation inaccuracy at its
  source rather than masking it.
- §1.3 "leanness": reuse the existing per-hour-spread idiom; do not introduce a new helper
  unless the same three-line shape repeats unmanageably.
