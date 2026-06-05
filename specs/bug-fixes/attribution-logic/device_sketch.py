"""Device — attribution shape (illustrative sketch for plan.html; not runnable, not imported).

The COUNTRY-DEPENDENT counterpart to server_base_sketch.py. Impact source · leaf = UsageJourneyStep.
Device energy uses CI[up], which varies by usage pattern, so Device exposes NO flat leaf-split: it
implements footprint_at(step, up) with CI[up] kept inside, and the engine climbs by pure summation
(group_cells_by_ancestor) — never a CI-blind split. Device attaches to steps via user_time_spent, so
there is no Device -> Job edge: only step / UJ / UP / Country, and no edge containers (on-edge
hardware is the separate EdgeDevice source).

Bodies are analysis.md-style: a docstring carrying the formula, no real implementation.
"""


class Device(HardwareBase):  # noqa: F821 — sketch

    # --- attribution contract (read by core/attribution/engine.py) ---------------------------
    attribution_leaf = UsageJourneyStep   # noqa: F821
    attribution_neutral_ci = False        # energy carries CI[up] → use footprint_at + group, not a leaf-split

    # === KEPT, eager calculated attributes — feed total_footprint, UNCHANGED =================
    #   energy_footprint, instances_fabrication_footprint
    #   energy_footprint_per_usage_pattern        (this is exactly Device -> UP; per_level recovers it)

    # === NEW — the country-dependent cell-evaluator (the only Device-specific code) ==========
    def footprint_at(self, step, up, phase):  # -> hourly, CI[up] INSIDE (energy phase)
        """Device's footprint in `step` within pattern `up` — the (leaf, up) cell.

        occupancy = step.hourly_avg_occurrences_per_usage_pattern[up]
                    (the Tier-A primitive on UsageJourneyStep: the step's concurrent share of the
                     journey, averaged over its own user_time_spent — so summing it over a journey's
                     steps tiles nb_usage_journeys_in_parallel_per_usage_pattern[up].)

        ENERGY      (country-dependent): (power × 1h) × occupancy × up.country.average_carbon_intensity
        FABRICATION (neutral, no CI)   : device_fabrication_footprint_over_one_hour × occupancy

        Fabrication is neutral-valued but still flows through footprint_at (its CI factor is simply
        absent), so one cell path serves both phases — no separate flat leaf-split is needed because
        the step leaf is already localized to a pattern."""

    # === NOT here — engine-generated (see engine_sketch.py) =================================
    #   Device -> step / UJ / UP / Country
    #     per_level(self, level, phase) = group_cells_by_ancestor(self, level, phase)
    #       = Σ over (step, up) of footprint_at(step, up, phase), grouped by level_ancestor(step, up, level):
    #           level = step    -> the step           (Σ over up:  the step's patterns)
    #           level = UJ       -> up.usage_journey
    #           level = UP       -> up                 (recovers energy_footprint_per_usage_pattern)
    #           level = Country  -> up.country
    #   Each (step, up) cell already carries CI[up], so every regroup is CI-correct by construction.
