"""ServerBase — attribution shape (illustrative sketch for plan.html; not runnable, not imported).

Impact source · leaf container = Job · neutral CI (the server's own country CI, constant across
usage patterns). Its entire attribution surface is therefore a FLAT {job: hourly} leaf-split; every
coarser / edge level is engine-generated (see engine_sketch.py). The two streams (provisioned vs
dynamic) and the idle/load energy split already exist today — only the per-job binding-resource
weights and the two leaf-split atoms are new.

Bodies are given analysis.md-style: a docstring carrying the formula, no real implementation.
"""

from functools import cached_property


class ServerBase(InfraHardware):  # noqa: F821 — sketch

    # --- attribution contract (read by core/attribution/engine.py) ---------------------------
    attribution_leaf = JobBase            # noqa: F821
    attribution_neutral_ci = True

    # === DELETED =============================================================================
    #   job_repartition_weights (+ update_ / update_dict_element_)      -> replaced by the weights below
    #   fabrication_impact_repartition_weights / usage_impact_repartition_weights   (properties)
    #   generic *_impact_repartition* calculated attributes             (inherited from ModelingObject)

    # === KEPT, eager calculated attributes — feed total_footprint, UNCHANGED =================
    #   nb_of_instances, raw_nb_of_instances
    #   instances_energy = idle (∝ nb_of_instances) + load (∝ raw_nb_of_instances)
    #   instances_fabrication_footprint, energy_footprint
    #   idle_energy_footprint, load_energy_footprint   (the two components, exposed separately)

    # === NEW physics — the binding-resource per-job weights (attribution-only, lazy cached) ==
    @cached_property
    def binding_raw(self):
        """Binding-resource series raw[h] = max(compute_need[h]/compute, ram_need[h]/ram).

        The common driver of both streams — charges only the binding resource, not the slack one."""

    @cached_property
    def dynamic_share_per_job(self) -> dict:  # {job: hourly}
        """Load (dynamic) split: each job's share of the hour's binding-resource demand.

        {job: divide_or_fallback(job_binding_demand[h], Σ_jobs binding_demand[h], fallback=0)}"""

    @cached_property
    def provisioned_share_per_job(self) -> dict:  # {job: hourly} (flat per-job if on-premise)
        """Sizing (provisioned) split: per instance tier k, the demand-share restricted to the
        hours that need the tier ({h: raw[h] > k-1}), summed over tiers.

        On-premise provisions once for the peak -> a flat per-job weight; autoscaling / serverless
        re-provision hourly -> this collapses to dynamic_share_per_job."""

    # === NEW atom — the flat leaf-split (the ONLY Server-specific footprint code) ============
    @cached_property
    def attributed_fabrication_footprint_per_job(self) -> dict:  # {job: hourly}
        """Fabrication rides provisioning (∝ nb_of_instances).

        {job: instances_fabrication_footprint × provisioned_share_per_job[job]}"""

    @cached_property
    def attributed_energy_footprint_per_job(self) -> dict:  # {job: hourly}
        """Idle energy rides provisioning; load energy rides demand.

        {job: idle_energy_footprint × provisioned_share_per_job[job]
            + load_energy_footprint × dynamic_share_per_job[job]}"""

    # === NOT here — engine-generated (see engine_sketch.py) ==================================
    #   Server -> step / UJ / UP / Country / RecurrentServerNeed / EdgeUsageJourney / EdgeUsagePattern
    #
    #   per_level(self, level, phase)
    #     = Σ_j  attributed_<phase>_footprint_per_job[j]
    #              × job.weight_for(level) / job.hourly_avg_occurrences_across_usage_patterns
    #
    #   weight_for(level) is the Job's Tier-A occurrence dict for that level
    #   (hourly_avg_occurrences_per_usage_journey_step, _per_usage_pattern, _per_recurrent_server_need, ...).
    #   The web+edge denominator splits a dual-side job across web steps AND edge needs.
