"""ServerBase — attribution shape (illustrative sketch for plan.html; not runnable, not imported).

Impact source, neutral CI (the server's own country CI, constant across patterns).

PHASE vs STREAM — two orthogonal dimensions, both preserved at every level:
  - phase  = life-cycle phase (FABRICATION | USAGE). It is the parameter of attribution_atoms();
    every fold and every Sankey link is per-phase, so the fabrication/energy split survives at
    every node of every column, exactly as today.
  - stream = the within-phase attribution driver:
        provisioned (∝ nb_of_instances — who forces instances to exist): carries ALL of the
                    fabrication phase AND the idle part of the usage phase, same weights;
        dynamic     (∝ raw_nb_of_instances — hourly use): carries the load part of usage.

Cells: every (job, step, up) a job runs in web-side, every (job, rsn, ef, up) edge-side.
All per-level / per-link flows are folds of these atoms (see attribution_sketch.py) — none of the
~9 Server -> X relations of analysis.md is a method here.

Bodies are analysis.md-style: a docstring carrying the formula, no real implementation.
"""

from functools import cached_property


class ServerBase(InfraHardware):  # noqa: F821 — sketch

    # === DELETED =============================================================================
    #   job_repartition_weights (+ update_ / update_dict_element_)      -> replaced by the weights below
    #   fabrication_impact_repartition_weights / usage_impact_repartition_weights   (properties)
    #   generic *_impact_repartition* calculated attributes             (inherited from ModelingObject)

    # === KEPT, eager calculated attributes — feed total_footprint, UNCHANGED =================
    #   nb_of_instances, raw_nb_of_instances
    #   instances_energy = idle (∝ nb_of_instances) + load (∝ raw_nb_of_instances)
    #   instances_fabrication_footprint, energy_footprint
    #   idle_energy_footprint, load_energy_footprint   (the two usage components, exposed separately)

    # === NEW physics — the binding-resource weights (attribution-only, lazy cached) ==========
    @cached_property
    def binding_demand_per_job(self) -> dict:  # {job: hourly}
        """d_j(h) = binding-resource need × hourly_avg_occurrences_across_usage_patterns, the
        binding resource picked by raw[h] = max(compute_need[h]/available_compute_per_instance,
        ram_need[h]/available_ram_per_instance) — the same denominators as update_raw_nb_of_instances,
        so attribution charges the resource that actually drives the instance count.
        A ServiceJob additionally carries its volume share of its service's base consumption
        (service base need × job occurrences / Σ occurrences over the service's jobs — a service's
        standing reservation is paid by that service's own jobs)."""

    @cached_property
    def dynamic_share_per_job(self) -> dict:  # {job: hourly}
        """s_j(h) = divide_or_fallback(d_j(h), Σ_jobs d(h), fallback=0) — exact for the demand
        stream: zero demand at h means zero dynamic footprint at h."""

    @cached_property
    def provisioned_share_per_job(self) -> dict:  # on-premise: {job: flat scalar}; else: = dynamic
        """On-premise: per instance tier k, the demand share restricted to the hours that need the
        tier ({h: raw[h] > k-1}), summed over tiers -> a FLAT per-job weight w_j (a job present
        only off-peak still pays the lower tiers it requires). Autoscaling/serverless re-provision
        hourly -> collapses to dynamic_share_per_job. The subtlest helper; unit-tested in isolation."""

    # === NEW atom builder — the ONLY attribution output =====================================
    # Output: a FLAT generator of Atom rows (long-format table), never a nested dict. Each atom
    # holds one hourly kg series plus flat coordinates. Worked micro-example in plan.html §1.2.
    def attribution_atoms(self, phase):  # -> Iterator[Atom]
        if phase == LifeCyclePhases.MANUFACTURING:                       # noqa: F821
            streams = [("provisioned", self.instances_fabrication_footprint)]
        else:  # USAGE — the idle/load split that already exists in update_instances_energy
            streams = [("provisioned", self.idle_energy_footprint),
                       ("dynamic", self.load_energy_footprint)]

        for stream, stream_footprint in streams:
            for job in self.jobs:
                job_weight = (self.provisioned_share_per_job if stream == "provisioned"
                              else self.dynamic_share_per_job)[job]
                for cell in job.attribution_cells():
                    # JobBase topology enumeration: every (step, up) the job runs in web-side,
                    # every (rsn, ef, up) edge-side — the o(rsn, ef, up)/o(rsn, up) count ratio
                    # and within-step multiplicities live inside the cell's shares.
                    share = (cell.flat_share        # scalar: Σ_h occ_cell / Σ_h occ_job
                             if stream == "provisioned" and self.is_on_premise
                             else cell.hourly_share)  # occ_cell(h)/occ_job(h), fallback=0 (exact:
                                                      # zero occurrences => zero demand footprint)
                    yield Atom(source=self, stream=stream, job=job, up=cell.up,   # noqa: F821
                               step=cell.step, rsn=cell.rsn, ef=cell.ef,
                               value=stream_footprint * job_weight * share)

        # Conservation (structural, tested generically): Σ atoms of each (phase, stream) == that
        # stream's footprint total — any missed cell or share fails this loudly.

    # === NOT here — fold-generated (see attribution_sketch.py) ===============================
    #   Server -> Job / step / UJ / UP / Country / RSN / EF / EdgeUsageJourney / EdgeUsagePattern
    #   and every Job <-> Step / Step <-> UP joint flow: group-bys of the atoms above.
