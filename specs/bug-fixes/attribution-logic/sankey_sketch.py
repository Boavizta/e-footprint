"""impact_repartition/sankey.py — column-walk renderer over the attribution engine (illustrative sketch).

Replaces today's recursive `_traverse` + `resolve_attributed_footprint_per_source` + spacer-node
machinery with a flat column-walk. The diagram is built one visible column at a time: node sizes come
from engine.node_total(), links from engine.flow(), and the excluded-source set is passed straight
through to both.

  - skip a column  = leave its level out of `visible_levels`; the adjacent visible columns are linked
                     directly (every level exists in the engine, so no spacer nodes are needed).
  - exclude source = pass it in `excluded`; engine.flow / node_total drop its term (no rescale).

Peripheral concerns are unchanged from today and elided here: the System root + life-cycle-phase
columns, object-category / leaf / footprint_breakdown_by_source nodes, small-node aggregation
("Other (N)"), node/link colors, hover & label text, and the plotly figure assembly.

Bodies are sketch-level; helper names (positive, adjacent, ...) stand in for the real implementations.
"""

from efootprint.core.attribution import engine                       # noqa: F401 — sketch
from efootprint.all_classes_in_order import SANKEY_COLUMNS           # noqa: F401 — sketch
from efootprint.core.lifecycle_phases import LifeCyclePhases         # noqa: F401 — sketch


class ImpactRepartitionSankey:

    def __init__(self, system, *, excluded=(), skipped_levels=(), phase_filter=None):
        self.system = system
        self.excluded = excluded                # impact sources (or subtrees) dropped from every flow
        self.skipped_levels = skipped_levels    # SANKEY_COLUMNS entries to hide (collapsed through)
        self.phases = [phase_filter] if phase_filter else [
            LifeCyclePhases.MANUFACTURING, LifeCyclePhases.USAGE]

    def visible_levels(self):
        """SANKEY_COLUMNS (source-ward → System-ward) minus skipped and empty levels."""
        return [level for level in SANKEY_COLUMNS
                if level not in self.skipped_levels and engine.nodes_at(self.system, level, self.excluded)]

    def build(self):
        for phase in self.phases:
            levels = self.visible_levels()

            # 1. NODES — size each from the surviving sources' attribution at its own level
            for level in levels:
                for node in engine.nodes_at(self.system, level, self.excluded):
                    size = engine.node_total(node, level, phase, exclude=self.excluded)
                    if positive(size):                                          # noqa: F821
                        self.add_node(node, level, size)

            # 2. LINKS — one per adjacent visible pair (finer = source-ward, coarser = System-ward).
            #    A finer node usually has exactly one coarser ancestor; on a skipped-column pair
            #    (e.g. Step→UP with the Job/Need columns hidden) it has several, and flow() splits.
            for finer, coarser in adjacent(levels):                            # noqa: F821
                for f_node in engine.nodes_at(self.system, finer, self.excluded):
                    for c_node in engine.ancestors_at(f_node, coarser):
                        value = engine.flow(f_node, finer, c_node, coarser, phase, exclude=self.excluded)
                        if positive(value):                                     # noqa: F821
                            self.add_link(f_node, c_node, value)

        self.aggregate_small_nodes_by_column()    # "Other (N)" per column — unchanged from today
        # System root + phase columns, category / leaf / breakdown nodes, colors, hovers — unchanged

    # add_node / add_link / aggregate_small_nodes_by_column / figure(): mechanics unchanged from today,
    # except links now connect adjacent VISIBLE columns directly — no spacer insertion for skipped ones,
    # and no resolve_*-style rescaling: node_total() and flow() already reflect `excluded`.


# Conservation (the build-time test hook): for every node, Σ of its incoming links == its node size
# == Σ of its outgoing links; and Σ over any column == the system phase total minus excluded sources.
