This doc extends `analysis.md` to the edge hardware source — **EdgeDevice** — and its **EdgeComponents** (CPU, RAM, workload, storage). `analysis.md` covers the server-side sources reached from the edge (Server / Network / Storage via RecurrentServerNeed); this covers the on-edge hardware.

**Topology is unchanged.** EdgeDevice is the impact source, with its two existing axes:
1. **Repartition — `EdgeDevice -> RecurrentEdgeComponentNeed`** (then -> RecurrentEdgeDeviceNeed -> EdgeFunction -> EdgeUsageJourney -> EdgeUsagePattern -> Country): a component-need is what loads a component.
2. **Breakdown by source — `EdgeDevice -> EdgeComponent`** (`fabrication_footprint_breakdown_by_source` / `energy_footprint_breakdown_by_source`): the hardware axis, and the only place the chassis is split (equally across components).

Unlike the server, edge `nb_of_units` is a **fixed input** (only validated against peak): there is no *derived* sizing to attribute, hence no per-tier logic. Attribution is by **usage**, the mirror image of the server's sizing-driven split. Two weights do the work: a **demand share** `s_dem` (fabrication and the load-driven part of energy) and an **equal share** among a component's needs (the device's idle floor, which no need's demand changes).

## The weights

`s_dem(need, up)` — each need's share of the **capacity-occupying demand** on its component C in that pattern:
- CPU / RAM / workload: the resource need `unitary_hourly_need_per_usage_pattern[up]` (≥ 0).
- EdgeStorage: the **held volume** — the need's own `RecurrentEdgeStorageNeed.cumulative_unitary_storage_need_per_usage_pattern[up]` (not the `EdgeStorage` component aggregate of the same name, which adds `base_storage_need`) — **not** the write rate `unitary_hourly_need`, which goes negative on delete hours.
- **Zero-demand fallback:** at hours where no need loads C, fall back to the equal share below.

**Equal share** — `1 / (number of C's needs present in the pattern)`. Used for the idle/base energy at every hour, and as the `s_dem` fallback. Implement it as an explicit `1/n`: `divide_or_fallback(..., fallback=1)` does NOT produce it — it fills each sibling's 0/0 hours with a full share of 1, counting the footprint once per need.

`s_dem` is today's `_compute_component_need_weight`, with two fixes: the storage metric (held volume, not rate) and the fallback (equal share, not `fallback=0`, which silently drops the footprint).

## EdgeDevice -> RecurrentEdgeComponentNeed (the atom)

Resolved per pattern. Write `T = total_nb_of_units`, `N[up] = nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[up]`, `comp_fab[C,up] = T × C.fabrication_footprint_per_edge_device_per_usage_pattern[up]`, `chassis_fab[up] = structure_fabrication_footprint_per_usage_pattern[up]` (already × T). A need loads one component `C = need.edge_component`.

- **Fabrication** (neutral): `(comp_fab[C,up] + chassis_fab[up] / nb_components) × s_dem(need, up)` — the chassis rides with each component as an equal `1/nb_components` share (matching the breakdown axis). Σ over all needs = `chassis_fab[up] + Σ_C comp_fab[C,up] = instances_fabrication_footprint_per_usage_pattern[up]`.
- **Energy** (country-dependent): split C's per-pattern energy along the affine power curve `unitary_power = idle_power + (power − idle_power)·workload`, `workload = (Σ_need need + base)/capacity`:
  - **idle/base** `T·N[up]·(idle_power + (power − idle_power)·base/capacity)·1h·CI[up]` — the floor the device draws just by being deployed, which no need's demand changes; split by the **equal share**, every hour.
  - **dynamic** `T·N[up]·(power − idle_power)·need[up]/capacity·1h·CI[up]` — each need's own marginal, attributed to that need directly.
  - (capacity = `compute` / `ram`; workload component: capacity = 1 `concurrent`, base = 0; EdgeStorage draws no power.) Σ over C's needs = `comp_energy[C,up] = T × C.energy_footprint_per_edge_device_per_usage_pattern[up]` (CI[up] inside). Chassis carries no energy.

## Container attribution logic — every pair

The chain is `RecurrentEdgeComponentNeed (RECN) ⊂ RecurrentEdgeDeviceNeed (REDN) ⊂ EdgeFunction (EF) ⊂ EdgeUsageJourney (EUJ) ⊂ EdgeUsagePattern (EUP)`, grouped by `Country`. Sankey flows only go up this chain, so the complete set is the 21 ordered pairs `A -> B` with B an ancestor of A (source `EdgeDevice` + 5 containers as A; 6 ancestors as B). Each is laid out below — no flow is left to a "compose it yourself" rule.

Building blocks (energy carries CI[up], so every sum is CI-correct):
- `atom(n, up)` — need n's footprint at pattern up (fabrication or energy, from the atom section); `= 0` if n does not run in up. Its demand factor already includes **all** of n's occurrences in up's journey, so `atom(n, up)` is n's footprint across every bundle and function it sits in at up.
- `o(n, up)` — n's total occurrences in up's journey = `Σ over ef ∈ J(up).edge_functions, Σ over b ∈ ef.recurrent_edge_device_needs, of b.recurrent_edge_component_needs.count(n)` (the `nb_of_occurrences_of_self_within_usage_pattern` built in `RecurrentEdgeComponentNeed`).
- `o(n, r, up)` (bundle r) = `r.recurrent_edge_component_needs.count(n) × (Σ over ef ∈ J(up).edge_functions of ef.recurrent_edge_device_needs.count(r))`; `o(n, e, up)` (function e) = `J(up).edge_functions.count(e) × (Σ over b ∈ e.recurrent_edge_device_needs of b.recurrent_edge_component_needs.count(n))`. Summing over the journey's bundles (resp. functions) gives `o(n, up)`, so they partition n's occurrences.
- `a(n, X, up) = atom(n, up) × o(n, X, up) / o(n, up)` — n's pattern-up footprint attributable to chain-container X (a REDN or EF). Equals `atom(n, up)` when n is reached through X only (no within-journey reuse — the usual case).
- `dev(up)` = `Σ over all needs n of atom(n, up)` = `instances_fabrication_footprint_per_usage_pattern[up]` / `energy_footprint_per_usage_pattern[up]` — the per-pattern device total.
- `needs(X)` — the component-needs inside X (REDN: its `recurrent_edge_component_needs`; EF: those of its REDNs; EUJ: those of its EFs). `J(up) = up.edge_usage_journey`, `Co(up) = up.country`, `P(n)` = n's patterns.

The occurrence share `o(n, X, up)/o(n, up)` is the **only** non-trivial factor; it appears in every aggregation over a REDN's or EF's needs (pairs 2–3, 7–8, 12–18) and is exactly 1 unless a need or bundle is reused within one journey. Need-level and geographic pairs (1, 4–6, 9–11, 19–21) carry no such factor — each pattern has one journey and one country, so `atom`/`dev` regroup without splitting.

**From `EdgeDevice` (source):**
1. `-> RECN n` = `Σ over up ∈ P(n) of atom(n, up)`.
2. `-> REDN r` = `Σ over all up, Σ over n ∈ needs(r), of a(n, r, up)`.
3. `-> EF e` = `Σ over all up, Σ over n ∈ needs(e), of a(n, e, up)`.
4. `-> EUJ j` = `Σ over up with J(up)=j of dev(up)` (at such up every active need is j's).
5. `-> EUP up` = `dev(up)`.
6. `-> Country c` = `Σ over up with Co(up)=c of dev(up)`.

**From `RECN n`:**
7. `-> REDN r` (a bundle whose `recurrent_edge_component_needs` lists n) = `Σ over up ∈ P(n) of a(n, r, up)` = `Σ over up ∈ P(n) of atom(n, up) × o(n, r, up)/o(n, up)`. The ratio is bundle r's share of n's occurrences at up: it is `1` when n lives in one bundle the journey uses once (the common case → the flow is n's whole footprint `Σ over up ∈ P(n) of atom(n, up)`), and since `Σ over the journey's bundles of o(n, r, up) = o(n, up)`, the bundles holding n split that footprint with shares summing to 1.
8. `-> EF e` (a function reaching n through its bundles) = `Σ over up ∈ P(n) of a(n, e, up)` = `Σ over up ∈ P(n) of atom(n, up) × o(n, e, up)/o(n, up)`.
9. `-> EUJ j` = `Σ over up ∈ P(n) with J(up)=j of atom(n, up)`.
10. `-> EUP up` = `atom(n, up)`.
11. `-> Country c` = `Σ over up ∈ P(n) with Co(up)=c of atom(n, up)`.

**From `REDN r`:**
12. `-> EF e` (a function whose `recurrent_edge_device_needs` lists r) = `Σ over all up, Σ over n ∈ needs(r), of a(n, r, up) × o(r, e, up)/o(r, up)`, where `o(r, e, up) = J(up).edge_functions.count(e) × e.recurrent_edge_device_needs.count(r)` and `o(r, up) = Σ over ef ∈ J(up).edge_functions of ef.recurrent_edge_device_needs.count(r)` — the extra ratio is 1 when r is in one function (then this is r's whole footprint).
13. `-> EUJ j` = `Σ over up with J(up)=j, Σ over n ∈ needs(r), of a(n, r, up)`.
14. `-> EUP up` = `Σ over n ∈ needs(r) of a(n, r, up)`.
15. `-> Country c` = `Σ over up with Co(up)=c, Σ over n ∈ needs(r), of a(n, r, up)`.

**From `EF e`** (every edge below also receives e's parallel `RecurrentServerNeed` footprint — the `Server/Network/Storage/Job -> EdgeFunction` flows in `analysis.md`, split across EFs by the same `o(rsn, e, up)/o(rsn, up)` ratio as pairs 8/12 here — added in):
16. `-> EUJ j` = `Σ over up with J(up)=j, Σ over n ∈ needs(e), of a(n, e, up)`.
17. `-> EUP up` = `Σ over n ∈ needs(e) of a(n, e, up)`.
18. `-> Country c` = `Σ over up with Co(up)=c, Σ over n ∈ needs(e), of a(n, e, up)`.

**From `EUJ j`:**
19. `-> EUP up` (J(up)=j) = `dev(up)` — the whole per-pattern device total (each pattern has exactly one journey). Replaces `EdgeUsageJourney.fabrication_impact_repartition_weights` / `_edge_usage_pattern_base_weight` and the neutral/country renormalization in `attributed_energy_footprint_per_usage_pattern`.
20. `-> Country c` = `Σ over up with J(up)=j and Co(up)=c of dev(up)`.

**From `EUP up`:**
21. `-> Country c = Co(up)` = `dev(up)` — the whole pattern total to its single country.

Conservation checks (each follows from `Σ over the journey's bundles/functions of o(n, ·, up) = o(n, up)`): summing pairs 7 over r holding n, or 8 over e reaching n, gives `atom(n)` (pair 1); summing 14 over a pattern's REDNs gives `dev(up)`; summing 12 over the functions holding r gives pair 2. With no within-journey reuse the factors are 1, so 7 = 8 = 1 and 12 = 2. The sum over any column = `Σ over up of dev(up)` = the device footprint.

## EdgeDevice -> EdgeComponent (breakdown by source — unchanged)

`fabrication_footprint_breakdown_by_source[C] = T × C.fabrication_footprint_per_edge_device + chassis_total / nb_components`; `energy_footprint_breakdown_by_source[C] = T × C.energy_footprint_per_edge_device`. The orthogonal hardware axis, the single place the chassis is split (equally). The atom folds the chassis the same way (`1/nb_components`, then by demand), so the two axes stay mutually consistent.

## A note on the choice

Demand drives what scales with it — fabrication (the user sizes `nb_of_units` for the peak) and the dynamic energy — so both go by `s_dem`. The **idle floor** does not scale with any need's demand (the device draws it just by running the journey), so it is shared **equally** by the component's needs at every hour, not only at the fully-idle hours the `s_dem` fallback would catch.

Consequence to accept: for the demand-driven part this is a *usage* allocation — a steady low-demand need can out-pay a spiky peak-driver over the period (it is present more hours) — deliberate, since with a fixed `nb_of_units` nothing in the model *drove* the sizing.

## What changes vs keeps

- **Keeps**: the topology (`EdgeDevice -> RecurrentEdgeComponentNeed` + the `EdgeComponent` breakdown), the chassis-equal-across-components split, and the demand-proportional fabrication weight.
- **Fixes**: (1) zero-demand fallback → equal share (was `fallback=0`, dropping footprint at idle hours); (2) EdgeStorage demand → cumulative held volume (was the net write rate, negative on deletes); (3) idle/base energy split off and shared equally (the single demand weight mis-split it across needs at partial-demand hours — worst on mostly-idle devices, where idle dominates the energy).
- **Removes**: the generic `_impact_repartition_weights` chaining on RecurrentEdgeComponentNeed / RecurrentEdgeDeviceNeed / EdgeFunction / EdgeUsagePattern, replaced by the explicit per-container sums/regroups above — the column-skip fix.
