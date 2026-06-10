"""impact_repartition/sankey.py — column-walk renderer over the attribution fold (illustrative sketch).

Replaces today's recursive `_traverse` + `resolve_attributed_footprint_per_source` + rescaling
machinery. The data layer is ONE call per phase:
attribution.node_totals_and_links(system, phase, visible_levels, exclude) — conservation is
already structural there (see attribution_sketch.py). Everything in this file is presentation.

  - skip a column  = leave its level out of `visible_levels`; adjacent visible columns link directly.
  - exclude source = pass it in `excluded`; its atoms are filtered out (no rescale).
  - the fabrication/energy split is per-phase by construction: the fold is called once per
    life-cycle phase and the phase columns stay separate end to end, as today.

Peripheral concerns unchanged from today and elided here: the System root + life-cycle-phase
columns, object-category nodes, footprint_breakdown_by_source decorations (EdgeDevice ->
EdgeComponent), small-node aggregation ("Other (N)"), ExternalAPIServer -> ExternalAPI display
normalization, node/link colors, hover & label text, and the plotly figure assembly.

Spacer nodes survive ONLY as geometry: in a mixed web + edge diagram a web Job -> Step link
visually crosses the edge-only RSN/REDN column; spacers carry it across without touching values.
"""

from efootprint.core import attribution                              # noqa: F401 — sketch
from efootprint.all_classes_in_order import SANKEY_COLUMNS           # noqa: F401 — sketch
from efootprint.core.lifecycle_phases import LifeCyclePhases         # noqa: F401 — sketch


class ImpactRepartitionSankey:

    def __init__(self, system, *, excluded=(), skipped_levels=(), phase_filter=None):
        self.system = system
        self.excluded = excluded                # impact-source classes dropped from every flow
        self.skipped_levels = skipped_levels    # SANKEY_COLUMNS entries to hide (collapsed through)
        self.phases = [phase_filter] if phase_filter else [
            LifeCyclePhases.MANUFACTURING, LifeCyclePhases.USAGE]

    def visible_levels(self):
        """SANKEY_COLUMNS (source-ward → System-ward) minus skipped and empty levels."""

    def build(self):
        for phase in self.phases:
            node_totals, links = attribution.node_totals_and_links(
                self.system, phase, self.visible_levels(), exclude=self.excluded)

            for node, size in node_totals.items():
                if positive(size):                                   # noqa: F821
                    self.add_node(node, level_of(node), size, phase)  # noqa: F821

            for (finer, coarser), value in links.items():
                if positive(value):                                  # noqa: F821
                    self.add_link(finer, coarser, value, phase)

        self.aggregate_small_nodes_by_column()    # "Other (N)" per column — unchanged from today
        self.insert_geometry_spacers()            # pure geometry; values untouched
        # System root + phase columns, category / breakdown nodes, colors, hovers — unchanged

    # add_node / add_link / aggregate_small_nodes_by_column / figure(): mechanics unchanged from
    # today, except no resolve_*-style rescaling exists anywhere: node_totals and links already
    # reflect `excluded` and `skipped_levels`.


# Conservation (already structural in the fold; kept as a regression test): for every node,
# Σ incoming == node size == Σ outgoing; Σ over any column == the system phase total minus
# excluded sources.
