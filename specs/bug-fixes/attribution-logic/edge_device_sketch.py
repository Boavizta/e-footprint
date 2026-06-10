"""EdgeDevice — attribution shape (illustrative sketch for plan.html; not runnable, not imported).

The hardest builder, and the reason plan v1's engine fell short: needs reused within one journey
split across bundles (REDN) and functions (EF) by occurrence RATIOS, which no ancestor-lookup can
express. Here the ratios become slot ENUMERATION: one atom per (recn, redn, ef, up) slot, the
ratio folded into the value as a scalar multiplicity. All 21 pairs of edge-analysis.md are then
plain folds of these atoms.

Bodies are edge-analysis.md-style: a docstring carrying the formula, no real implementation.
"""


class EdgeDevice(ModelingObject):  # noqa: F821 — sketch

    # === DELETED =============================================================================
    #   _compute_component_need_weight
    #   fabrication_impact_repartition_weights / usage_impact_repartition_weights
    #   (and the generic _impact_repartition chaining on RECN / REDN / EdgeFunction / EdgeUsagePattern)

    # === KEPT ================================================================================
    #   all eager per-pattern totals (structure/instances fabrication & energy, per up and summed)
    #   fabrication/energy_footprint_breakdown_by_source — the EdgeDevice -> EdgeComponent
    #   hardware axis stays a renderer decoration, chassis split equally across components;
    #   the atom folds the chassis the same way, keeping the two axes mutually consistent.

    # === NEW physics — the per-(need, pattern) atom of edge-analysis.md ======================
    def atom_value(self, n, up, phase):
        """Need n's footprint at pattern up, on its component C (T = total_nb_of_units,
        N = nb_edge_usage_journeys_in_parallel; both already inside the comp_* per-pattern attrs).

        FABRICATION (neutral):  (comp_fab[C, up] + chassis_fab[up] / nb_components) × s_dem(n, up)
        USAGE (CI[up] inside):  idle/base floor × equal_share(n, up)  +  n's own dynamic marginal
            along the affine power curve unitary_power = idle + (power − idle) × workload
            (workload = (Σ_need + base)/capacity; EdgeStorage draws no power; chassis no energy).

        s_dem(n, up): n's share of capacity-occupying demand on C — CPU/RAM/workload by
          unitary_hourly_need_per_usage_pattern; EdgeStorage by the need's own cumulative HELD
          VOLUME (RecurrentEdgeStorageNeed.cumulative_unitary_storage_need_per_usage_pattern, not
          the component aggregate of the same name, which adds base_storage_need). Zero-demand
          hours fall back to the equal share.
        equal_share(n, up) = 1 / (number of C's needs present in up) — an explicit 1/n, NOT
          divide_or_fallback(fallback=1), which would book the floor once per need."""

    # === NEW atom builder ====================================================================
    def attribution_atoms(self, phase):  # -> Iterator[Atom]
        """Slot enumeration: for each up, walk J(up).edge_functions (with multiplicity), each
        function's recurrent_edge_device_needs, each bundle's recurrent_edge_component_needs —
        one atom per (n, redn, ef) slot:

            value = atom_value(n, up, phase) × slot_multiplicity / o(n, up)

        with o(n, up) = the total slot count of n in up's journey (the
        nb_of_occurrences_of_self_within_usage_pattern count RECN already builds), so the slots of
        a need partition atom_value exactly — within-journey reuse splits across its bundles and
        functions; the common case is one slot with ratio 1.

        Conservation (structural test): Σ over up's atoms == dev(up) == the eager per-pattern
        totals; Σ over all atoms == the eager phase totals."""

    # === NOT here — fold-generated (see attribution_sketch.py) ===============================
    #   All 21 pairs of edge-analysis.md (EdgeDevice/RECN/REDN/EF/EUJ/EUP -> any ancestor):
    #   group-bys of the atoms above. Replaces EdgeUsageJourney._edge_usage_pattern_base_weight
    #   and the neutral/country renormalization in attributed_energy_footprint_per_usage_pattern.
