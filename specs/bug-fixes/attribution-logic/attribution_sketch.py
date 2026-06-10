"""core/attribution/ — the atom model (illustrative sketch for plan.html; not runnable).

One concept: every impact source decomposes its footprint, exactly once, into ATOMS — the finest
(source, stream, containment cell, usage pattern) slices of hourly footprint. Every number the
attribution layer serves is the same operation: group atoms by a key and sum.

    - node total at any level   = group by that level's key
    - link between two columns  = consecutive nodes of each atom's chain
    - skip a column             = leave its level out of the visible set
    - exclude a source          = filter its atoms out (no rescale)
    - exclude a subtree         = filter atoms by coordinate
    - conservation              = Σ(atoms of a stream) == that stream's footprint   (structural)

Caching is two-tier, matching what depends on what: atom VALUES depend only on (source, phase) —
cached at that key, built once per render and reused by every fold — while GROUPINGS depend on the
query, so folded results are memoized per (phase, visible_levels, exclude). Toggling a skipped
column or an exclusion re-accumulates cached series; it never rebuilds values. Both tiers live in
the render cache, never as model state, and are flushed wholesale on every ModelingUpdate.
"""

from dataclasses import dataclass


# ============================================================================================
# THE ATOM
# ============================================================================================
@dataclass(frozen=True)
class Atom:
    source: "ModelingObject"               # noqa: F821 — the impact source that emitted it
    stream: str                            # "provisioned" | "dynamic" | "retention" | "baseline" | ...
    value: "ExplainableHourlyQuantities"   # noqa: F821 — hourly kg, labeled, e.g.
                                           # "Server A provisioned footprint via Job J in Step S (Pattern P)"
    up: "UsagePattern | EdgeUsagePattern"  # noqa: F821 — always present
    # cell coordinates — source-specific, absent ones stay None:
    job: "JobBase" = None                  # noqa: F821 — Server / Storage / Network / ExternalAPI
    step: "UsageJourneyStep" = None        # noqa: F821 — web-triggered cells, and Device
    rsn: "RecurrentServerNeed" = None      # noqa: F821 — edge-triggered cells
    ef: "EdgeFunction" = None              # noqa: F821 — edge chains (server-side AND EdgeDevice)
    recn: "RecurrentEdgeComponentNeed" = None   # noqa: F821 — EdgeDevice
    redn: "RecurrentEdgeDeviceNeed" = None      # noqa: F821 — EdgeDevice

    def chain(self):
        """Ordered nodes this atom climbs through, source-ward -> System-ward. Coarser keys are
        DERIVED from up, never stored; absent coordinates drop out.

        web job cell     : [source, job, step, up.usage_journey, up, up.country]
        edge job cell    : [source, job, rsn, ef, up.edge_usage_journey, up, up.country]
        device cell      : [source, step, up.usage_journey, up, up.country]
        edge device cell : [source, recn, redn, ef, up.edge_usage_journey, up, up.country]
        """


# ============================================================================================
# SOURCE CONTRACT — one generator per source; ALL the physics lives in the builders
# --------------------------------------------------------------------------------------------
#   class ServerBase:    def attribution_atoms(self, phase) -> Iterator[Atom]
#   (shapes: server_base_sketch.py · device_sketch.py · edge_device_sketch.py)
#
# Whether a source is neutral-CI (Server, Storage, ExternalAPI, Device fabrication) or
# country-dependent (Network, Device energy, EdgeDevice energy) is invisible here: CI[up] either
# is or isn't a factor inside the builder. The fold never knows.
# ============================================================================================


@flushed_memo  # noqa: F821 — TIER 1: atom values are query-invariant, built once per (source, phase)
def atoms_of(source, phase) -> tuple:
    """The source's atom list, materialized once per render. ~35 KB per atom per modeled year
    (one float32 hourly series) -> a few MB for typical models."""
    return tuple(source.attribution_atoms(phase))


def atoms(system, phase, exclude=()):
    """All sources' atoms, excluded sources filtered out (exclusion = filter, never rescale)."""
    for source in system.impact_sources:                              # noqa: F821
        if isinstance(source, exclude):
            continue
        yield from atoms_of(source, phase)


# ============================================================================================
# THE FOLD — the renderer's whole data layer, one pass
# ============================================================================================
@flushed_memo  # noqa: F821 — TIER 2: keyed by (phase, visible_levels, exclude); groupings are query-dependent
def node_totals_and_links(system, phase, visible_levels, exclude=()):
    """Sankey feed. Each atom contributes its value to every node of its (visible) chain and to
    the link between each consecutive pair — so Σ incoming == node total == Σ outgoing holds at
    every node BY CONSTRUCTION. No normalization, no rescaling, anywhere."""
    node_totals, links = AccumulatorDict(), AccumulatorDict()         # noqa: F821 — missing key -> Empty
    for atom in atoms(system, phase, exclude):
        chain = [node for node in atom.chain() if level_of(node) in visible_levels]  # noqa: F821
        for node in chain:
            node_totals[node] += atom.value
        for finer, coarser in pairwise(chain):                        # noqa: F821
            links[(finer, coarser)] += atom.value
    return node_totals, links


@flushed_memo  # noqa: F821
def footprint_per_node(system, level, phase, exclude=()):
    """Programmatic per-level dict {node: hourly} — replaces attributed_*_footprint_per_source.
    Group atoms by their node at `level`; atoms with no node at that level don't contribute.
    The per-source variant groups by (source, node): the footprint of any container due to any
    source, at every level — not just leaves."""


# Levels are the SANKEY_COLUMNS entries. A column can mix web and edge classes
# ([EdgeFunction, UsageJourneyStep] · [RecurrentEdgeDeviceNeed, RecurrentServerNeed] ·
# [JobBase, RecurrentEdgeComponentNeed]) — each atom's chain resolves the right node for its
# family, so the fold never needs to know which side an atom comes from.
#
# Renderer: see sankey_sketch.py. Extending: a new source implements attribution_atoms() and
# nothing else; a new level is one chain entry + one SANKEY_COLUMNS entry.
