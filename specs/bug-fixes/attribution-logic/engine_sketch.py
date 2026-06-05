"""core/attribution/engine.py — attribution engine (illustrative sketch for plan.html; not runnable).

Pure functions over the source/container contract. The only cross-cutting attribution code, and not a
ModelingObject. One primitive (`per_level`) does the work; the public folds are thin reads over it.
Because every value is an absolute, additively-decomposed footprint (never a normalized share):
    - skip a column  = select the level you want (every level always exists)
    - exclude source = drop its term from the sum (no rescale)
    - exclude subtree = re-sum the surviving finer nodes (additive re-aggregate)

Bodies are sketched; helper names (weighted_redistribution, group_cells_by_ancestor, ...) stand in
for the real implementations.
"""


# ============================================================================================
# CONTRACT  (what classes expose — everything below is generic)
# --------------------------------------------------------------------------------------------
#   source     attribution_leaf       : JobBase | UsageJourneyStep | RecurrentEdgeComponentNeed
#              attribution_neutral_ci : bool
#     neutral      attributed_<phase>_footprint_per_<leaf>  -> {leaf: hourly}   # Server, Storage
#     country-dep  footprint_at(leaf, up, phase)            -> hourly, CI[up] inside  # Network, Device, EdgeDevice
#   container  weight_for(level)       -> {node: hourly}    # Tier-A occurrence/data/storage split
#    (leaf)    attribution_total       -> hourly            # = hourly_avg_occurrences_across_usage_patterns
#              attribution_level                            # the column this container occupies
#   topology   level_ancestor / ancestors_at(node, level) · nodes_at(level, exclude)   # web + edge chain
# ============================================================================================


@flushed_cached  # noqa: F821 — cached per (source, level, phase); cleared by the wholesale flush
def per_level(source, level, phase) -> dict:  # {node: hourly}
    """The one primitive: `source`'s footprint attributed to every node at `level`."""
    if source.attribution_neutral_ci:                        # Server, Storage — redistribute a per-job scalar
        return weighted_redistribution(source, level, phase)
    return group_cells_by_ancestor(source, level, phase)     # Network, Device, EdgeDevice — sum CI-bearing cells


def weighted_redistribution(source, level, phase):
    """Neutral climb: split each per-leaf footprint across the nodes at `level` by the leaf's own
    dimensionless occurrence weight. Valid only because CI is constant for these sources, so a
    dimensionless weight cannot blend carbon intensities.

        Σ_leaf  leaf_split[leaf] × leaf.weight_for(level)[node] / leaf.attribution_total
    """
    totals = ExplainableObjectDict()                         # {node: hourly}; missing key → Empty
    for leaf, leaf_value in source.leaf_split(phase).items():     # the flat atom {leaf: hourly}
        for node, w in leaf.weight_for(level).items():            # Tier-A occurrence split {node: hourly}
            totals[node] += leaf_value * divide_or_fallback(w, leaf.attribution_total, fallback=0)
    return totals


def group_cells_by_ancestor(source, level, phase):
    """Country-dependent climb: sum the source's (leaf, up) cells into the nodes at `level`.

    Each cell footprint_at(leaf, up) already carries CI[up], so summation never blends carbon
    intensities — a high-CI pattern just contributes a larger value, not a larger share of a blended
    total. No weight on the climb: above the leaf every up has exactly one journey and one country,
    so a cell maps to a single node (a lookup, not a split).

        Σ over (leaf, up) of footprint_at(leaf, up)   grouped by   level_ancestor(leaf, up, level)
    """
    totals = ExplainableObjectDict()                         # {node: hourly}; missing key → Empty
    for leaf in source.attribution_leaves:                   # Device → its steps; Network → its jobs
        for up in leaf.usage_patterns:                       # patterns the leaf appears in (web + edge)
            node = level_ancestor(leaf, up, level)
            totals[node] += source.footprint_at(leaf, up, phase)   # CI[up] stays inside this term
    return totals


def level_ancestor(leaf, up, level):
    """The single node at `level` the (leaf, up) cell rolls into — a lookup, because above the leaf
    each up has exactly one journey and one country (web and edge alike)."""
    if level is leaf.attribution_level:          # the source's own finest column (Device → step, EdgeDevice → RECN)
        return leaf
    return {USAGE_JOURNEY: up.usage_journey,      # edge analogue: up.edge_usage_journey
            USAGE_PATTERN: up,                    #                up (an EdgeUsagePattern)
            COUNTRY:       up.country}[level]


# Note — a source attributing below a single container (Network reaches both Job and Step) iterates a
# 2-part finest cell, e.g. (job, step, up): footprint_at routes the job's per-(step, up) data volume
# through Network.energy_footprint_for_data_volume_and_usage_pattern(.., up). Same rule, finer cell.


def node_total(node, level, phase, exclude=()):
    """Node size = the surviving sources' per-level contribution to `node`."""
    return sum(per_level(s, level, phase)[node] for s in sources() if s not in exclude)  # noqa: F821


# Topology metadata — the adjacent pairs where one column is a function of the other, so no joint
# weight is needed (each usage pattern has exactly one journey and one country).
_CLEAN_PAIRS = {(USAGE_PATTERN, COUNTRY), (USAGE_JOURNEY, USAGE_PATTERN),                       # noqa: F821
                (EDGE_USAGE_PATTERN, COUNTRY), (EDGE_USAGE_JOURNEY, EDGE_USAGE_PATTERN)}         # noqa: F821


def flow(finer_node, finer_level, coarser_node, coarser_level, phase, exclude=()):
    """Sankey link value: the footprint at `finer_node` (source-ward column) that rolls up into its
    ancestor `coarser_node` (System-ward column), summed over the surviving sources.

    Conserves — the test hook:
        Σ over finer_node's coarser-ancestors of flow == node_total(finer_node, finer_level, ...)
        Σ over coarser_node's finer-children   of flow == node_total(coarser_node, coarser_level, ...)
    """
    if (finer_level, coarser_level) in _CLEAN_PAIRS:
        # Cardinality-1 side: the usage pattern's whole total crosses the edge (one journey / one
        # country per pattern), so the link is just its node_total — no joint weight, no split.
        node, level = ((finer_node, finer_level) if finer_level in (USAGE_PATTERN, EDGE_USAGE_PATTERN)  # noqa: F821
                       else (coarser_node, coarser_level))
        return node_total(node, level, phase, exclude)
    return joint_flow(finer_node, finer_level, coarser_node, coarser_level, phase, exclude)


@render_memoized  # noqa: F821 — per-build cache; the only 2-keyed quantity, never stored on the model
def joint_flow(finer_node, finer_level, coarser_node, coarser_level, phase, exclude):
    """Genuinely many-to-many pair (Job↔Step; or Step↔UP / Job↔UP once a column is skipped): the
    (finer_node, coarser_node) joint cell, resolved per source and summed."""
    total = EmptyExplainableObject()                                           # noqa: F821
    for s in sources():                                                        # noqa: F821
        if s in exclude:
            continue
        resolve = neutral_joint if s.attribution_neutral_ci else country_dep_joint
        total += resolve(s, finer_node, coarser_node, phase)
    return total


def is_under(node, up, *containers):
    """True if a finest cell — its container chain `containers` (e.g. (job, step) · (step,) · (recn,))
    running in pattern `up` — sits beneath `node`: node equals one of the cell's containers, or one of
    its pattern-determined ancestors (UP / journey / country). One rule, web and edge."""
    return (node in containers or node is up
            or node in (up.country, getattr(up, "usage_journey", None),
                        getattr(up, "edge_usage_journey", None)))


def neutral_joint(source, finer_node, coarser_node, phase):
    """One neutral source's (Server, Storage) contribution to the (finer, coarser) joint cell.

    Localize each job's flat leaf-split footprint to its per-(step, up) occurrence atoms, keep the
    atoms sitting under BOTH nodes, and weight by atom / job-total. Summing the kept atoms over the
    unconstrained dimension recovers the right single-level weight, so this one formula serves every
    neutral pair — Job↔Step (Σ over up), Job↔UP (Σ over step), Step↔UP (the bare atom):

        Σ_job leaf_split[job] × Σ_{(step,up) under both nodes} atom(job, step, up) / job_total
        atom(job, step, up) = job.get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step)
    """
    total = EmptyExplainableObject()                                           # noqa: F821
    for job, job_footprint in source.leaf_split(phase).items():                # {job: hourly}
        for step, up in job.occurrence_cells():                                # the (step, up) the job runs in
            if is_under(finer_node, up, job, step) and is_under(coarser_node, up, job, step):
                atom = job.get_hourly_avg_occurrences_per_usage_pattern_per_step(up, step)
                total += job_footprint * divide_or_fallback(                   # noqa: F821
                    atom, job.hourly_avg_occurrences_across_usage_patterns, fallback=0)
    return total


def country_dep_joint(source, finer_node, coarser_node, phase):
    """One country-dependent source's (Network, Device, EdgeDevice) contribution to the (finer,
    coarser) joint cell: sum the source's footprint_at cells sitting under BOTH nodes. CI[up] is
    inside each term, so the sum is CI-correct and needs no weight — never a CI-blind split.
    (Device cell = (step, up) · Network = (job, step, up) · EdgeDevice = (recurrent_edge_component_need, up).)

        Σ_{(leaf…, up) under both nodes} footprint_at(leaf…, up)
    """
    total = EmptyExplainableObject()                                           # noqa: F821
    for footprint, up, containers in source.footprint_cells(phase):            # footprint_at over the finest cells
        if is_under(finer_node, up, *containers) and is_under(coarser_node, up, *containers):
            total += footprint
    return total


# Renderer = column-walk over the visible levels (see sankey_sketch.py): node sizes via node_total(),
# links via flow() for each adjacent visible pair, the excluded-source set passed straight through.
# No recursion, no spacer nodes, no resolve_attributed_footprint_per_source.
#
# Extending: a new source implements the contract and nothing else; a new level is one topology
# entry + the matching Tier-A weight dict.
