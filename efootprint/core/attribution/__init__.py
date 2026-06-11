"""The atom model — the attribution layer's single mechanism.

Every impact source decomposes its footprint, exactly once, into ATOMS: the finest
(source, stream, containment cell, usage pattern) slices of hourly footprint, emitted by the
source's ``attribution_atoms(phase)`` generator. Every number this layer serves is the same
operation — group atoms by a key and sum:

- node total at any level   = group by that level's key
- link between two columns  = consecutive nodes of each atom's chain
- skip a column             = leave its level out of the visible set
- exclude a source          = filter its atoms out (no rescale)
- conservation              = Σ(atoms of a stream) == that stream's footprint   (structural)

Caching is two-tier, matching what depends on what: atom values depend only on (source, phase) —
memoized at that key — while groupings depend on the query, so folded results are memoized per
(phase, visible levels, exclude). Both tiers live in each owner's ``render_cache`` (a flushed
cached property), never as model state: they are wiped wholesale by the system-wide
cached-property flush after every ModelingUpdate and after the initial build.

Invariant: calculated attributes never read attribution results — the one-way rule that makes
wholesale lazy flushing correct.
"""
import inspect
from dataclasses import dataclass
from functools import wraps
from itertools import pairwise

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases


@dataclass(frozen=True, eq=False)
class Atom:
    """One finest-grain slice of a source's footprint: an hourly kg series at a containment cell.

    ``source`` and ``stream`` say who emitted it and which physical stream (provisioned / dynamic /
    retention / baseline / single / …) it belongs to. The cell coordinates are source-specific —
    absent ones stay None — and ``up`` is always present. Coarser keys (journey, country) are
    derived from ``up`` in ``chain()``, never stored.
    """
    source: ModelingObject
    stream: str
    value: object  # ExplainableHourlyQuantities | EmptyExplainableObject
    up: ModelingObject
    job: ModelingObject = None
    step: ModelingObject = None
    rsn: ModelingObject = None
    ef: ModelingObject = None
    recn: ModelingObject = None
    redn: ModelingObject = None

    def chain(self):
        """Ordered nodes this atom climbs through, source-ward -> System-ward.

        web job cell     : [source, job, step, up.usage_journey, up, up.country]
        edge job cell    : [source, job, rsn, ef, up.edge_usage_journey, up, up.country]
        device cell      : [source, step, up.usage_journey, up, up.country]
        edge device cell : [source, recn, redn, ef, up.edge_usage_journey, up, up.country]
        """
        journey = (self.up.usage_journey if hasattr(self.up, "usage_journey")
                   else self.up.edge_usage_journey)
        nodes = (self.source, self.job, self.recn, self.rsn, self.redn, self.ef, self.step,
                 journey, self.up, self.up.country)

        return [node for node in nodes if node is not None]


def _hashable(arg):
    return tuple(arg) if isinstance(arg, list) else arg


def flushed_memo(func):
    """Memoize on the first argument's ``render_cache`` — the per-ModelingObject scratch dict wiped by the
    system-wide cached-property flush — keyed by function name + remaining (hashable) args."""
    signature = inspect.signature(func)

    @wraps(func)
    def wrapper(cache_owner, *args, **kwargs):
        bound_args = signature.bind(cache_owner, *args, **kwargs)
        bound_args.apply_defaults()
        normalized_args = tuple(_hashable(arg) for arg in list(bound_args.arguments.values())[1:])
        cache = cache_owner.render_cache
        key = (func.__name__, *normalized_args)
        if key not in cache:
            cache[key] = func(cache_owner, *normalized_args)
        return cache[key]

    return wrapper


@flushed_memo
def atoms_of(source: ModelingObject, phase) -> tuple:
    """TIER 1 — the source's atom list for a life-cycle phase, materialized once per render and reused by
    every fold (atom values are query-invariant)."""
    return tuple(source.attribution_atoms(phase))


def attribution_sources(system) -> list:
    """The system's impact sources that implement the atom contract. By the end of the attribution revamp
    every impact source does; during the strangler migration, sources without a builder simply don't
    contribute atoms yet."""
    return [obj for obj in system.all_linked_objects if hasattr(obj, "attribution_atoms")]


def atoms(system, phase, exclude: tuple = ()):
    """All sources' atoms for a phase, excluded source classes filtered out (exclusion = filter, never
    rescale)."""
    for source in attribution_sources(system):
        if isinstance(source, exclude):
            continue
        yield from atoms_of(source, phase)


@flushed_memo
def node_totals_and_links(system, phase, visible_levels: tuple, exclude: tuple = ()):
    """TIER 2 — the Sankey feed: ``({node: hourly}, {(finer, coarser): hourly})`` for one life-cycle phase.

    ``visible_levels`` is a tuple of ModelingObject classes; a chain node is visible iff it is an instance
    of one of them — skipping a column = leaving its classes out (adjacent visible nodes link directly).
    Each atom contributes its value to every visible node of its chain and to the link between each
    consecutive pair, so Σ incoming == node total == Σ outgoing holds at every node BY CONSTRUCTION —
    no normalization, no rescaling, anywhere. Returned dicts are memoized — treat them as read-only."""
    node_totals, links = {}, {}
    for atom in atoms(system, phase, exclude):
        chain = [node for node in atom.chain() if isinstance(node, visible_levels)]
        for node in chain:
            node_totals[node] = node_totals.get(node, EmptyExplainableObject()) + atom.value
        for finer, coarser in pairwise(chain):
            links[(finer, coarser)] = links.get((finer, coarser), EmptyExplainableObject()) + atom.value

    return node_totals, links


@flushed_memo
def footprint_per_node(system, level, phase, exclude: tuple = ()):
    """Programmatic per-level read: ``{node: hourly}`` grouping each atom by its chain node at ``level``
    (a ModelingObject class or tuple of classes). Atoms with no node at that level don't contribute.
    The returned dict is memoized — treat it as read-only."""
    totals = {}
    for atom in atoms(system, phase, exclude):
        node = next((node for node in atom.chain() if isinstance(node, level)), None)
        if node is not None:
            totals[node] = totals.get(node, EmptyExplainableObject()) + atom.value

    return totals


@flushed_memo
def footprint_per_node_per_source(system, level, phase, exclude: tuple = ()):
    """Per-source variant of ``footprint_per_node``: ``{(source, node): hourly}`` — the footprint of any
    container at ``level`` due to any source, not just leaves.
    The returned dict is memoized — treat it as read-only."""
    totals = {}
    for atom in atoms(system, phase, exclude):
        node = next((node for node in atom.chain() if isinstance(node, level)), None)
        if node is not None:
            key = (atom.source, node)
            totals[key] = totals.get(key, EmptyExplainableObject()) + atom.value

    return totals


def attributed_footprint(obj: ModelingObject, phase: LifeCyclePhases):
    """The object's total attributed footprint for a life-cycle phase: its node entry in
    ``footprint_per_node`` at the object's own class level, summed over the object's systems
    (Empty when system-less)."""
    total = EmptyExplainableObject()
    for system in obj.systems:
        total += footprint_per_node(system, type(obj), phase).get(obj, EmptyExplainableObject())
    label = ("Attributed fabrication footprint" if phase is LifeCyclePhases.MANUFACTURING
             else "Attributed energy footprint")
    return total.to(u.kg).set_label(label)
