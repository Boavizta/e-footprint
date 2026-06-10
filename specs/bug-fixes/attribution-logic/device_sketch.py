"""Device — attribution shape (illustrative sketch for plan.html; not runnable, not imported).

The COUNTRY-DEPENDENT counterpart to server_base_sketch.py, and the simplest builder: no shares at
all. Device attaches to steps via user_time_spent, so its cells are (step, up) — each cell's value
is computed ground-up, with CI[up] inside for the usage phase and no CI for fabrication (one cell
path serves both phases). There is no Device -> Job edge, and no edge containers (on-edge hardware
is the separate EdgeDevice source).

Replaces the current fabrication/usage_impact_repartition_weights, which reused the per-pattern
footprint as a per-step weight — double-counting duration (already in nb_usage_journeys_in_parallel)
and smearing each step across the whole journey window instead of when it runs.

Bodies are analysis.md-style: a docstring carrying the formula, no real implementation.
"""


class Device(HardwareBase):  # noqa: F821 — sketch

    # === KEPT, eager calculated attributes — feed total_footprint, UNCHANGED =================
    #   energy_footprint, instances_fabrication_footprint
    #   energy_footprint_per_usage_pattern   (= Device -> UP usage; the fold recovers it)

    # === DELETED =============================================================================
    #   fabrication_impact_repartition_weights / usage_impact_repartition_weights

    # === NEW atom builder — the only Device-specific attribution code ========================
    def attribution_atoms(self, phase):  # -> Iterator[Atom]
        """One atom per (step, up) cell of the device's patterns.

        occupancy = step.hourly_avg_occurrences_per_usage_pattern[up]
            (the new Step primitive: the step's concurrent occupancy, averaged over its own
             user_time_spent and summed over the step's positions in up's journey — so summing it
             over a journey's steps tiles nb_usage_journeys_in_parallel_per_usage_pattern[up])

        USAGE        atom = (power × 1h) × occupancy × up.country.average_carbon_intensity
        FABRICATION  atom = device_fabrication_footprint_over_one_hour × occupancy

        Conservation (structural test): Σ over a pattern's steps recovers
        energy_footprint_per_usage_pattern[up] / the per-UP fabrication summand; Σ over all atoms
        recovers the eager phase totals."""

    # === NOT here — fold-generated (see attribution_sketch.py) ===============================
    #   Device -> step / UJ / UP / Country, and the Step <-> UP joints: group-bys of the atoms.
    #   Every atom carries CI[up] inside (usage), so every regroup is CI-correct by construction.
