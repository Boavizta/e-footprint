I’ve rethought the attribution logic from the ground up and I think I’m much clearer on 2 original sins that lead to the repeated problems we’re facing when attributing footprint while skipping Sankey columns:
- Having failed to have explicit code paths for all object links (like explicit Server->step, Server->UJ, Server->UP impact attribution), to fix the skipped column impact repartition logics,
- Having tried too much to put factor impact repartition logic into ModelingObject. I now think it should be totally separate because impact repartition logic belongs to domain.

Having said that, here’s how I’m finding more clarity: explicitly mapping all impact repartition relationships.
Let’s start with impact sources attribution:

## Impact sources attribution logic

### Server

Fabrication and usage no longer share one weight (today's job_repartition_weights serves both); their drivers differ, so split the server footprint into two streams:
- **provisioned stream** = fabrication + idle energy (both ∝ nb_of_instances): driven by *sizing* — who forces instances to exist.
- **dynamic stream** = the load energy (∝ raw_nb_of_instances, the used capacity): driven by hourly use.

Both key on the **binding resource** raw[h] = max(compute_need[h]/compute, ram_need[h]/ram) — not the current additive (compute/compute + ram/ram) weight, which charges the non-binding resource (a RAM-heavy job on a compute-bound server). The idle/dynamic energy split already exists in update_instances_energy; only the attribution weights below are new.

#### Web
- Server -> Job, dynamic stream: per hour, split among the server's jobs by each job's share of the hour's binding-resource demand (job.compute_needed or ram_needed × hourly_avg_occurrences_across_usage_patterns, for whichever resource binds). Hourly, conserving.
- Server -> Job, provisioned stream: **per-instance-tier** — each instance is paid for by the jobs that need it, in the hours they need it. Tier k is needed in N_k = {h : raw[h] > k−1}; within each needed hour, share by binding-resource demand; sum over tiers. Conserves.
  - Autoscaling/serverless re-provision hourly, so this collapses to the dynamic per-hour split. On-premise provisions once for the peak, so a tier spreads over all its needed hours — a job present only off-peak still pays the lower tiers it requires (no off-peak-free corner case). On-premise → a per-job weight flat across hours; autoscaling/serverless → an hourly weight.
- Both streams then relay to step / UJ / UP / Country by the occurrence weights below (the job's server share, split across where the job runs):
- Server -> steps: needs identifying for each step the jobs pointing to server, and attributing share based on **new hourly_avg_occurrences_per_usage_journey_step** JobBase calculated attribute.
- Server -> UJ: same thing needs identifying for each UJ the jobs pointing to server, and attributing share based on **new hourly_avg_occurrences_per_usage_journey** JobBase calculated attribute.
- Server -> UP: same thing needs identifying for each UP the jobs pointing to server, and attributing share based on hourly_avg_occurrences_per_usage_pattern JobBase calculated attribute.
- Server -> Country: Sum Server -> UP impacts for all UP in country usage patterns.

New JobBase attributes introduced:
- hourly_avg_occurrences_per_usage_journey_step
- hourly_avg_occurrences_per_usage_journey

#### Edge (recurrent server needs)
A Job can also be triggered on the edge side — by RecurrentServerNeeds, not UsageJourneySteps (job.recurrent_server_needs) — so its server impact must partition across both sides. The edge containers mirror the web ones: RecurrentServerNeed ≈ step, EdgeUsageJourney ≈ UJ, EdgeUsagePattern ≈ UP. They share the same per-job denominator as the web bullets above — hourly_avg_occurrences_across_usage_patterns, which already sums occurrences over web and edge patterns — so for a job used on both sides Σ(web steps) + Σ(edge recurrent needs) = the job's total occurrences, and its server impact splits across both rather than landing 100% on the web side (the latent assumption that made weighting on hourly_avg_occurrences_per_usage_journey_step alone incomplete).

- Server -> Job: both streams span web + edge — each job's edge occurrences feed compute_need / ram_need and hence raw[h] alongside its web steps (hourly_avg_occurrences_across_usage_patterns sums both), so the binding-resource and per-tier weights partition a dual-side job's server impact across both sides rather than landing it 100% web-side.
- Server -> RecurrentServerNeed: for each recurrent server need, identify the jobs pointing to the server and attribute share based on the new hourly_avg_occurrences_per_recurrent_server_need (edge analogue of hourly_avg_occurrences_per_usage_journey_step), each job's share normalized over hourly_avg_occurrences_across_usage_patterns.
- Server -> EdgeUsageJourney: same, share based on the new hourly_avg_occurrences_per_edge_usage_journey (edge analogue of hourly_avg_occurrences_per_usage_journey).
- Server -> EdgeUsagePattern: no new attribute — hourly_avg_occurrences_per_usage_pattern already keys edge usage patterns, so this is exactly Server -> UP applied to an edge UP.
- Server -> Country: already covered by Server -> Country above — EdgeUsagePattern carries a country (EdgeUsagePattern.country), and Country.usage_patterns returns its modeling_obj_containers, which include those edge UPs, so they fold into the same by-country sum with no separate edge handling.

New JobBase attributes introduced (edge):
- hourly_avg_occurrences_per_recurrent_server_need: keyed by the job's recurrent server needs; for rsn, the request_duration-averaged per-RSN occurrence = compute_nb_avg_hourly_occurrences over the raw per-RSN volume job.py builds on the edge branch — sum over rsn.edge_usage_patterns of rsn.unitary_hourly_volume_per_usage_pattern[edge_up] × edge_up.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[edge_up] × rsn.jobs.count(self). The edge analogue of hourly_avg_occurrences_per_usage_journey_step; Σ_rsn = the job's total edge occurrences (= Σ over edge patterns of hourly_avg_occurrences_per_usage_pattern).
- hourly_avg_occurrences_per_edge_usage_journey: keyed by the job's edge usage journeys; the by-edge-journey regroup of hourly_avg_occurrences_per_usage_pattern — sum over the job's edge patterns whose edge_usage_journey is euj (clean partition, one edge UJ per edge UP). The edge analogue of hourly_avg_occurrences_per_usage_journey.

### Network (only usage impact)

#### Web
Now onto Network:
- Network -> Job is covered by current logic
- Network -> step computes from the ground up: for each job and pattern, energy_footprint_for_data_volume_and_usage_pattern(job.compute_hourly_data_transferred_per_usage_pattern_per_step(up, step), up)
- Network -> UP is covered by current logic (energy_footprint_per_usage_pattern).
- Network -> UJ can be derived from Network -> UP by simple sum over the patterns sharing the journey (one UJ feeds many UPs, so the sum runs UJ-from-UP, not UP-from-UJ): sum(self.energy_footprint_per_usage_pattern[up] for up in self.usage_patterns if up.usage_journey == UJ)
- Network -> Country: sum Network -> UP over the country's usage patterns (country.usage_patterns).

New JobBase methods introduced:
- get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step): per step, sum the contributions from the positions where uj_steps[i] is step, each = utc_hourly_usage_journey_starts(up) shifted by the cumulative delay × jobs.count(self), then apply compute_nb_avg_hourly_occurrences(.., request_duration). The request_duration-averaged, count-weighted per-step occurrences feeding both the network data volume and the storage data-stored rate.
- compute_hourly_data_transferred_per_usage_pattern_per_step(up, step): get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) × data_exchange_per_hour — the per-(pattern, step) data volume the Network converts to impact.

New Network method introduced:
- energy_footprint_for_data_volume_and_usage_pattern(data_volume, up): bandwidth_energy_intensity × data_volume × carbon intensity of up. Generalizes _compute_energy_footprint_for_job_and_usage_pattern (now a thin caller passing the job's per-pattern data). Keeps the data-to-carbon physics in Network; called by Network -> step and Job -> Step (network).

#### Edge (recurrent server needs)
EdgeUsagePattern carries a network (EdgeUsagePattern.network), and edge-triggered jobs transfer data over it, so Network is country-dependent on the edge UP exactly as on web UPs (Network.usage_patterns and energy_footprint_per_usage_pattern already span edge UPs). Mirror the web logic per (rsn, edge_up), keeping CI[edge_up] inside the conversion — never a CI-blind split.

- Network -> Job: unchanged (current logic; the job's hourly_data_transferred_per_usage_pattern already spans web + edge patterns).
- Network -> RecurrentServerNeed: ground-up per (rsn, edge_up) — for edge pattern edge_up, energy_footprint_for_data_volume_and_usage_pattern(data, edge_up) with data = sum over the rsn's jobs of job.compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need(edge_up, rsn). The edge analogue of Network -> step. Σ_edge_up recovers the per-RSN total, Σ_rsn recovers Network -> EdgeUsagePattern.
- Network -> EdgeUsagePattern: covered by current logic (energy_footprint_per_usage_pattern keys edge UPs).
- Network -> EdgeUsageJourney: sum over the edge patterns sharing the journey — sum(energy_footprint_per_usage_pattern[edge_up] for edge_up in usage_patterns if edge_up.edge_usage_journey == EUJ).
- Network -> Country: already covered by Network -> Country above (edge UPs carry a country and fold into the same by-country sum).

New JobBase methods introduced (edge):
- get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(edge_up, rsn): the per-(edge_up, rsn) average occurrences = compute_nb_avg_hourly_occurrences(rsn.unitary_hourly_volume_per_usage_pattern[edge_up] × edge_up.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[edge_up] × rsn.jobs.count(self), request_duration). The edge analogue of get_hourly_avg_occurrences_per_usage_pattern_per_step; its sum over the rsn's edge patterns is hourly_avg_occurrences_per_recurrent_server_need (and over rsn + edge_up is hourly_avg_occurrences_per_usage_pattern on edge UPs).
- compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need(edge_up, rsn): get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(edge_up, rsn) × data_exchange_per_hour — the per-(edge_up, rsn) data volume the Network converts to impact, CI[edge_up] applied inside energy_footprint_for_data_volume_and_usage_pattern.

### Storage (only fabrication impact)

#### Web
Now onto Storage (neutral-CI, fabrication only — operating energy folded into the server). Two drivers, so split the fabrication footprint F into two streams, each attributed by its own weight at every level:
- retention stream storage_retention_fabrication_footprint = F × full_cumulative_storage_need / provisioned_capacity (= amortized × N/storage_capacity): the job-written data that persists over data_storage_duration. Attributed by full_cumulative_storage_need_per_container.
- baseline stream storage_baseline_fabrication_footprint = F × (unused_storage + base_storage_need) / provisioned_capacity (= amortized × (unused+base)/storage_capacity): the baseline + provisioning slack, which serves reads e-footprint does not model (only data_stored writes and data_transferred). Attributed by occurrence share like the Server (the honest read proxy; write-volume would let read-heavy/write-light jobs off free).

provisioned_capacity = nb_of_instances × storage_capacity = N + unused + base, so the two streams sum to F (nb_of_instances cancels in each). This drops the old combined full_cumulative_storage_need_per_container + shared_storage_per_container weight and the shared_storage_per_* attributes: the baseline is now its own footprint split by the Server's occurrence weights.

Per level, attribute each stream by its weight (retention | baseline):
- Storage -> Job: full_cumulative_storage_need_per_job[job] (already implemented) | hourly_avg_occurrences_across_usage_patterns[job].
- Storage -> step: full_cumulative_storage_need_per_step[step] | hourly_avg_occurrences_per_usage_journey_step[step] (summed over the storage's jobs), each normalized over the steps holding a job writing here.
  - full_cumulative_storage_need_per_step[step]: sum over the storage's jobs of job.hourly_data_stored_per_step[step] × data_replication_factor, then push it through the cumsum-with-dumps used for full_cumulative_storage_need_per_job.
- Storage -> UP: full_cumulative_storage_need_per_usage_pattern[UP] | hourly_avg_occurrences_per_usage_pattern[UP] (summed over the storage's jobs), each normalized over the storage's usage patterns.
  - full_cumulative_storage_need_per_usage_pattern[UP]: sum over the storage's jobs of job.hourly_data_stored_per_usage_pattern[UP] × data_replication_factor, then push it through the cumsum-with-dumps used for full_cumulative_storage_need_per_job.
- Storage -> UJ: sum each stream across the patterns sharing the journey.
- Storage -> Country: sum each stream of Storage -> UP across the country's usage patterns.

New Storage attributes introduced:
- storage_retention_fabrication_footprint, storage_baseline_fabrication_footprint: the two streams (F × N / provisioned_capacity and F × (unused + base) / provisioned_capacity).
- full_cumulative_storage_need_per_step, full_cumulative_storage_need_per_usage_pattern (retention weights), from the container's data-stored rate — per-pattern from the existing hourly_data_stored_per_usage_pattern, per-step from hourly_data_stored_per_step — each pushed through the same cumsum-with-dumps as full_cumulative_storage_need_per_job. _per_usage_journey sums _per_usage_pattern over the patterns sharing the journey (clean partition: each UP has exactly one journey; a per-step regroup would double-count steps shared across journeys).
- The baseline weights are the Server's hourly_avg_occurrences_* (each summed over the storage's jobs), reused, not new. The normalized baseline share is level-invariant — per-step / UP / job occurrence totals all equal the storage's total job occurrences, so a flow gets the same baseline share through any partition. Edge: at zero-occurrence hours the baseline stream has no occurrence basis — split it evenly across the containers present at that hour, so the footprint is conserved, not dropped (divide_or_fallback with fallback=1 already does this).

New JobBase calculated attribute introduced:
- hourly_data_stored_per_step: keyed by the job's steps, each = sum over the job's patterns of get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) × data_stored_per_hour. Built from the job's own request_duration-averaged, count-weighted per-step occurrences — not the step's user_time_spent-averaged hourly_avg_occurrences_per_usage_pattern (the Device primitive).

#### Edge (recurrent server needs)
The server's Storage receives writes from edge-triggered jobs too: a job fired by a RecurrentServerNeed still runs on the server and writes via data_stored, so it lands in hourly_data_stored_across_usage_patterns (which spans web + edge patterns) and hence in full_cumulative_storage_need_per_job. So both streams partition across web steps AND edge recurrent needs, sharing the same denominators as the web containers — retention over N (the full job-written cumulative need, = Σ over web steps + edge RSNs), baseline over hourly_avg_occurrences_across_usage_patterns. A storage shared by both sides splits across both, never 100% to the web side. (Distinct from edge-device storage, RecurrentEdgeStorageNeed, which is its own source — handled like the edge device/component needs, not here.)

Per level, retention | baseline:
- Storage -> Job: unchanged — full_cumulative_storage_need_per_job (from hourly_data_stored_across_usage_patterns) | hourly_avg_occurrences_across_usage_patterns, both already web + edge.
- Storage -> RecurrentServerNeed: full_cumulative_storage_need_per_recurrent_server_need | hourly_avg_occurrences_per_recurrent_server_need (from the Server edge section). Retention normalized over N, baseline over total occurrences — the same totals as the web steps, so web steps + edge RSNs partition each stream.
  - full_cumulative_storage_need_per_recurrent_server_need[rsn]: sum over the storage's jobs of job.hourly_data_stored_per_recurrent_server_need[rsn] × data_replication_factor, then push it through the same cumsum-with-dumps as full_cumulative_storage_need_per_job.
- Storage -> EdgeUsageJourney: sum each stream across the edge patterns sharing the journey (retention via full_cumulative_storage_need_per_usage_pattern on edge UPs; baseline via hourly_avg_occurrences_per_edge_usage_journey).
- Storage -> EdgeUsagePattern: no new attribute — full_cumulative_storage_need_per_usage_pattern | hourly_avg_occurrences_per_usage_pattern already key edge UPs (this is Storage -> UP on an edge UP).
- Storage -> Country: already covered — edge UPs carry a country and fold into the same by-country sum.

New JobBase calculated attribute introduced (edge):
- hourly_data_stored_per_recurrent_server_need: keyed by the job's recurrent server needs; = hourly_avg_occurrences_per_recurrent_server_need[rsn] × data_stored_per_hour (data_stored_per_hour = data_stored / request_duration, the same per-job rate used web-side). The edge analogue of hourly_data_stored_per_step; Σ_rsn = the job's total edge data-stored rate, so web per-step + edge per-RSN sum to hourly_data_stored_across_usage_patterns.

New Storage calculated attribute introduced (edge):
- full_cumulative_storage_need_per_recurrent_server_need: cumsum-with-dumps of the per-RSN replicated data-stored rate, mirroring full_cumulative_storage_need_per_step. The _per_edge_usage_journey level regroups _per_usage_pattern over the edge patterns sharing the journey. Σ over web steps + edge RSNs = N, so the retention stream conserves across both sides.

### Device (energy CI dependent, fabrication neutral)

Now onto Device — attached to steps via user_time_spent, not jobs, so there is no Device -> Job edge: only -> step / UP / UJ. Country-dependent energy like Network, neutral fabrication like Server; both scale with the device's per-step occupancy (UsageJourneyStep.hourly_avg_occurrences_per_usage_pattern above), since the device is on for the whole journey and each step occupies user_time_spent of it. Every level is computed ground-up as a direct footprint dict, replacing the current fabrication_impact_repartition_weights / usage_impact_repartition_weights — which reused the per-pattern footprint as a per-step weight, double-counting duration (already in nb_usage_journeys_in_parallel) and smearing each step across the whole journey window instead of when it runs.

#### Web
Energy (country-dependent):
- Device -> step: energy_footprint_per_usage_journey_step[step] = sum over the step's patterns of (power × 1h) × step.hourly_avg_occurrences_per_usage_pattern[up] × up.country.average_carbon_intensity.
- Device -> UP: already computed = energy_footprint_per_usage_pattern[up] (power × nb_usage_journeys_in_parallel[up] × CI[up]).
- Device -> UJ: sum over the patterns sharing the journey — sum(energy_footprint_per_usage_pattern[up] for up in usage_patterns if up.usage_journey == UJ). Clean partition (one UJ per UP), like Network -> UJ.

Fabrication (neutral):
- Device -> step: instances_fabrication_footprint_per_usage_journey_step[step] = sum over the step's patterns of device_fabrication_footprint_over_one_hour × step.hourly_avg_occurrences_per_usage_pattern[up]. Same occupancy as energy, no CI. (device_fabrication_footprint_over_one_hour = carbon_footprint_fabrication × 1h / (lifespan × fraction_of_usage_time), already in update_instances_fabrication_footprint.)
- Device -> UP: instances_fabrication_footprint_per_usage_pattern[up] = device_fabrication_footprint_over_one_hour × nb_usage_journeys_in_parallel[up] — the per-UP summand currently folded into the instances_fabrication_footprint total, now stored per UP. (Re-derive instances_fabrication_footprint from the per-UP dict)
- Device -> UJ: sum instances_fabrication_footprint_per_usage_pattern over the patterns sharing the journey.

Device -> Country: sum Device -> UP (energy and fabrication) across the country's usage patterns.

#### Edge
Web Device has no edge containers: it attaches to web UsageJourneySteps via user_time_spent, and EdgeUsagePatterns carry no Device (edge hardware is the separate EdgeDevice source). So the web Device's attribution is entirely web (step / UP / UJ / Country) — nothing relays to the edge side.

New Device attributes introduced: energy_footprint_per_usage_journey_step, instances_fabrication_footprint_per_usage_pattern, instances_fabrication_footprint_per_usage_journey_step (the per-UJ levels are regroups = sum of _per_usage_pattern over the journey's patterns).

New UsageJourneyStep calculated attribute introduced:
- hourly_avg_occurrences_per_usage_pattern[up]: the step's concurrent occupancy = compute_nb_avg_hourly_occurrences(up.utc_hourly_usage_journey_starts shifted by the cumulative delay to this step within up's journey, uj_step.user_time_spent). Averaged over user_time_spent — the step's own duration, not a job's request_duration — so summing it over a journey's steps recovers nb_usage_journeys_in_parallel_per_usage_pattern (the consecutive per-step windows tile the full journey duration). Keyed by up so the step's position (hence the delay) is taken within that pattern's journey. This is the Device occupancy primitive, distinct from the job-level get_hourly_avg_occurrences_per_usage_pattern_per_step (request_duration-averaged, count-weighted).

## Container attribution logic
### Job

#### Electricity
##### Web
- Job -> Step, server (neutral): share Job’s impact coming from Servers weighted on hourly_avg_occurrences_per_usage_journey_step — occurrence share, CI-independent.
- Job -> Step, network (country-dependent): sum over the job's patterns up.network.energy_footprint_for_data_volume_and_usage_pattern(self.compute_hourly_data_transferred_per_usage_pattern_per_step(up, step), up). The Job supplies only the data volume; the data-to-carbon physics stays in Network.
- Job -> UJ, server (neutral): share Job’s impact coming from Servers weighted on hourly_avg_occurrences_per_usage_journey — occurrence share per journey, CI-independent.
- Job -> UJ, network (country-dependent): the one-job analogue of Network -> UJ — sum over the patterns sharing the journey of the Job -> UP network footprint: sum(up.network.energy_footprint_for_data_volume_and_usage_pattern(self.hourly_data_transferred_per_usage_pattern[up], up) for up in self.usage_patterns if up.usage_journey == UJ).
- Job -> UP, server (neutral): share based on hourly_avg_occurrences_per_usage_pattern — occurrence share per pattern, CI-independent.
- Job -> UP, network (country-dependent): per pattern, up.network.energy_footprint_for_data_volume_and_usage_pattern(self.hourly_data_transferred_per_usage_pattern[up], up) — the existing per-(job, pattern) network footprint, no per-step quantity needed.

##### Edge
Same relay, to the job's edge containers (RecurrentServerNeed ≈ step, EdgeUsageJourney ≈ UJ, EdgeUsagePattern ≈ UP), with the server share normalized over hourly_avg_occurrences_across_usage_patterns (web + edge) so web steps + edge RSNs partition the job's impact.
- Job -> RecurrentServerNeed, server (neutral): share weighted on hourly_avg_occurrences_per_recurrent_server_need — occurrence share, CI-independent.
- Job -> RecurrentServerNeed, network (country-dependent): sum over the job's edge patterns of edge_up.network.energy_footprint_for_data_volume_and_usage_pattern(self.compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need(edge_up, rsn), edge_up). The Job supplies only the data volume; the data-to-carbon physics stays in Network.
- Job -> EdgeUsageJourney, server (neutral): weighted on hourly_avg_occurrences_per_edge_usage_journey — occurrence share per edge journey.
- Job -> EdgeUsageJourney, network (country-dependent): the one-job analogue of Network -> EdgeUsageJourney — sum(edge_up.network.energy_footprint_for_data_volume_and_usage_pattern(self.hourly_data_transferred_per_usage_pattern[edge_up], edge_up) for edge_up in self.edge_usage_patterns if edge_up.edge_usage_journey == EUJ).
- Job -> EdgeUsagePattern, server (neutral): share based on hourly_avg_occurrences_per_usage_pattern (already keys edge UPs).
- Job -> EdgeUsagePattern, network (country-dependent): per edge pattern, edge_up.network.energy_footprint_for_data_volume_and_usage_pattern(self.hourly_data_transferred_per_usage_pattern[edge_up], edge_up).

#### Fabrication
##### Web
- Job -> Step, server (neutral): share Job’s impact coming from Servers weighted on hourly_avg_occurrences_per_usage_journey_step — occurrence share, CI-independent.
- Job -> step, storage: the job carries two storage streams (Storage fabrication split into a cumulative-data-stored part and a baseline-by-occurrence part); relay each by its own weight:
  - retention (cumulative data stored): split by per-(job, step) cumulative need / the job's total — cumsum-with-dumps of hourly_data_stored_per_step[step] × data_replication_factor, over Σ_step of the same (= full_cumulative_storage_need_per_job). Trivial (=100%) for single-step jobs.
  - baseline (occurrence): split by hourly_avg_occurrences_per_usage_journey_step — the exact same occurrence weight as Job -> Step, server above.
- Job -> UJ, server (neutral): share Job’s impact coming from Servers weighted on hourly_avg_occurrences_per_usage_journey — occurrence share per journey, CI-independent.
- Job -> UJ, storage: relay the job's two storage streams:
  - retention: split by the job's per-UJ cumulative need / full_cumulative_storage_need_per_job[job] — sum over the job's patterns sharing the journey of cumsum-with-dumps(hourly_data_stored_per_usage_pattern[up] × data_replication_factor) (UP-sum, like Storage -> UJ; avoids double-counting steps shared across journeys). Trivial (=100%) for single-journey jobs.
  - baseline: split by hourly_avg_occurrences_per_usage_journey — the exact same occurrence weight as Job -> UJ, server above.
- Job -> UP, server (neutral): share based on hourly_avg_occurrences_per_usage_pattern — occurrence share per pattern, CI-independent.
- Job -> UP, storage: relay the job's two storage streams:
  - retention: split by per-(job, UP) cumulative need / full_cumulative_storage_need_per_job[job] — cumsum-with-dumps of hourly_data_stored_per_usage_pattern[up] × data_replication_factor.
  - baseline: split by hourly_avg_occurrences_per_usage_pattern — the exact same occurrence weight as Job -> UP, server above.

##### Edge
Same relay to the job's edge containers, sharing the web+edge denominators: full_cumulative_storage_need_per_job[job] for retention, hourly_avg_occurrences_across_usage_patterns for server / baseline.
- Job -> RecurrentServerNeed, server (neutral): share weighted on hourly_avg_occurrences_per_recurrent_server_need.
- Job -> RecurrentServerNeed, storage: relay the two storage streams:
  - retention: split by per-(job, rsn) cumulative need / full_cumulative_storage_need_per_job[job] — cumsum-with-dumps of hourly_data_stored_per_recurrent_server_need[rsn] × data_replication_factor.
  - baseline: split by hourly_avg_occurrences_per_recurrent_server_need — the same occurrence weight as Job -> RecurrentServerNeed, server above.
- Job -> EdgeUsageJourney, server (neutral): weighted on hourly_avg_occurrences_per_edge_usage_journey.
- Job -> EdgeUsageJourney, storage: relay the two storage streams:
  - retention: split by the job's per-EUJ cumulative need / full_cumulative_storage_need_per_job[job] — sum over the job's edge patterns sharing the journey of cumsum-with-dumps(hourly_data_stored_per_usage_pattern[edge_up] × data_replication_factor) (edge-UP-sum, like Storage -> EdgeUsageJourney).
  - baseline: split by hourly_avg_occurrences_per_edge_usage_journey.
- Job -> EdgeUsagePattern, server (neutral): share based on hourly_avg_occurrences_per_usage_pattern (keys edge UPs).
- Job -> EdgeUsagePattern, storage: relay the two storage streams:
  - retention: split by per-(job, edge_up) cumulative need / full_cumulative_storage_need_per_job[job] — cumsum-with-dumps of hourly_data_stored_per_usage_pattern[edge_up] × data_replication_factor.
  - baseline: split by hourly_avg_occurrences_per_usage_pattern.

### Step

#### Electricity
- Step -> UP, server (neutral): per server job j in the step, split j's attributed server energy (Server -> Job, the existing per-job share) by the fraction of j's occurrences landing in (step, up): (Server -> Job energy for j) × get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) / hourly_avg_occurrences_across_usage_patterns[j], summed over the step's server jobs (divide_or_fallback → 0 at j's zero-occurrence hours, where j's energy is 0 anyway).
- Step -> UP, network: country-dependent, so computed ground-up per (step, up) — never by splitting the step's total network energy by a CI-blind weight (that would blend patterns of different CI). For pattern up: up.network.energy_footprint_for_data_volume_and_usage_pattern(data, up) with data = sum over the step's jobs of job.compute_hourly_data_transferred_per_usage_pattern_per_step(up, step). Same building block as Network -> step, but resolved at the single pattern up (CI[up] kept inside the conversion) instead of summed over patterns.
- Step -> UP, device (country-dependent): ground-up per (step, up), like network — for the device and pattern up, (power × 1h) × step.hourly_avg_occurrences_per_usage_pattern[up] × up.country.average_carbon_intensity.

#### Fabrication
- Step -> UP, server (neutral): same occurrence weight as Step -> UP, server (electricity) above — get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) summed over the step's server jobs (Server uses one repartition for usage and fabrication).
- Step -> UP, storage: relay the two storage streams per (step, up); both neutral, so occurrence / need weights are exact (no CI to keep).
  - retention: split storage_retention_fabrication_footprint by the per-(step, up) cumulative need / N — cumsum-with-dumps of the (step, up) data-stored rate (sum over the storage's jobs of get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) × data_stored_per_hour × data_replication_factor).
  - baseline: split storage_baseline_fabrication_footprint by the per-(step, up) occurrence share — get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step) summed over the storage's jobs.
- Step -> UP, device (neutral): device_fabrication_footprint_over_one_hour × step.hourly_avg_occurrences_per_usage_pattern[up] — the single-pattern term of Device -> step fabrication, no CI. Σ_up recovers Device -> step, Σ_step recovers Device -> UP = instances_fabrication_footprint_per_usage_pattern[up].

#### Step -> UJ
- Uniform across every stream (server, network, storage, device; both phases): Step -> UJ[step][uj] = sum over the UPs whose journey is uj of Step -> UP[step][up] — the by-journey regroup of Step -> UP, no new per-stream computation. Pattern-aware by construction: each Step -> UP[step][up] already carries CI[up] for the country-dependent streams, so grouping by journey never blends different-CI patterns. Trivial (= the whole Step -> UP) when the step's patterns all share one journey; for a step shared across journeys it splits by routing each pattern's contribution to that pattern's journey (each UP has exactly one journey). Conserves: Σ_uj Step -> UJ = Σ_up Step -> UP = the step's total across patterns.

### Usage journey

#### Electricity
- UJ -> UP, server (neutral): Server -> UP[up] — the up's directly-computed server energy (occurrence-weighted per pattern by hourly_avg_occurrences_per_usage_pattern, per the per-job rule in Step -> UP, server). CI is the server's own country, constant across the journey's patterns.
- UJ -> UP, network (country-dependent): Network -> UP[up] = energy_footprint_per_usage_pattern[up] — CI[up] already inside; a high-CI pattern of the journey simply has a larger value, not a larger share of a blended total.
- UJ -> UP, device (country-dependent): Device -> UP[up] = the device's energy_footprint_per_usage_pattern[up] — CI[up] already inside.

#### Fabrication
- UJ -> UP, server (neutral): Server -> UP[up] fabrication — same per-pattern occurrence weight as the electricity server bullet (Server uses one repartition for usage and fabrication).
- UJ -> UP, storage: Storage -> UP[up], i.e. the two streams read off per pattern — storage_retention_fabrication_footprint split by full_cumulative_storage_need_per_usage_pattern[up], and storage_baseline_fabrication_footprint split by hourly_avg_occurrences_per_usage_pattern[up].
- UJ -> UP, device (neutral): Device -> UP[up] = instances_fabrication_footprint_per_usage_pattern[up] — no CI.

### Country

Country is not a container in the Job ⊂ Step ⊂ UJ ⊂ UP chain — it is a second grouping of usage patterns, orthogonal to UsageJourney (each UP has exactly one country = up.country, just as it has exactly one journey). So every "-> Country" edge is the by-country regroup of the matching "-> UP" edge, uniformly across every source and every container level:
- Source -> Country[c] = Σ_{up in c.usage_patterns} Source -> UP[up] (Server / Network / Storage / Device, all streams).
- Step -> Country[step][c] = Σ_{up in c.usage_patterns} Step -> UP[step][up]; Job -> Country and UJ -> Country likewise, and the joint cell (uj, country) = Σ_{up : up.usage_journey == uj and up.country == c} Source -> UP[up].

Conserves because countries partition the UPs (Σ_c Source -> Country = the source total), and it is correct by construction for the country-dependent streams since each Source -> UP[up] already carries CI[up] (all UPs in a country share that CI). No new computation and no CI-blind split — Country is the same per-UP-resolution payoff as UJ and column-hiding, projected onto another attribute of UP. Servers carry no country, only a carbon intensity, so there is no territorial-vs-demand ambiguity here: Country always means the usage pattern's country.
