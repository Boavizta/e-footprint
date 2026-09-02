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

Caching follows the one paradigm of the reactive graph: each source's ``impact_repartition_rows``
computed structure holds its atoms reduced to period-sum matrix rows, and ``System.impact_repartition_matrix``
concatenates them — computed on first read, cached, and invalidated precisely through recorded
dependency edges like any other slot (no wholesale wipes). The Sankey fold
(``node_totals_and_links``) runs over the matrix's summed scalars and needs no memoization; the
hourly reads (``footprint_per_node`` and friends) fold live atoms on every call.
"""
from abc import abstractmethod
from dataclasses import dataclass

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import (
    computed_structure, computed_structures, evict_transient_structures, record_calculus_edges_from_ancestry)
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases

_CELL_FIELDS = ("job", "step", "rsn", "ef", "recn", "redn")


def _chain_nodes(source, up, journey, job=None, step=None, rsn=None, ef=None, recn=None, redn=None):
    """Ordered nodes an atom climbs through, source-ward -> System-ward.

    Journey identity is explicit because one pattern can now contain several journeys.
    """
    nodes = (source, job, recn, rsn, redn, ef, step, journey, up, up.country)

    return [node for node in nodes if node is not None]


@dataclass(frozen=True, eq=False)
class Atom:
    """One finest-grain slice of a source's footprint: an hourly kg series at a containment cell.

    ``source`` and ``stream`` say who emitted it and which physical stream (provisioned / dynamic /
    retention / baseline / single / …) it belongs to. The cell coordinates are source-specific —
    absent ones stay None — and ``up`` is always present.
    """
    source: ModelingObject
    stream: str
    value: object  # ExplainableHourlyQuantities | EmptyExplainableObject
    up: ModelingObject
    journey: ModelingObject
    job: ModelingObject = None
    step: ModelingObject = None
    rsn: ModelingObject = None
    ef: ModelingObject = None
    recn: ModelingObject = None
    redn: ModelingObject = None

    def chain(self):
        """The atom's ordered chain nodes (see ``_chain_nodes``)."""
        return _chain_nodes(
            self.source, self.up, self.journey, job=self.job, step=self.step, rsn=self.rsn, ef=self.ef, recn=self.recn,
            redn=self.redn)


def _period_sum_in_kg(atom_value) -> float:
    """One atom's value reduced to its period sum in kg — the matrix rows' and folds' single scalar
    reduction (``.to(u.kg)`` raises on a non-mass atom value)."""
    summed = atom_value.sum()
    return 0.0 if isinstance(summed, EmptyExplainableObject) else summed.value.to(u.kg).magnitude


def _atom_row(atom: Atom, phase: LifeCyclePhases) -> dict:
    """The atom's dict-encoded matrix row: source, stream and phase, the cell coordinate ids (absent
    coordinates omitted), and the value reduced to its period sum in kg."""
    row = {"source": atom.source.id, "stream": atom.stream, "phase": phase.value, "up": atom.up.id,
           "journey": atom.journey.id,
           "value": _period_sum_in_kg(atom.value)}
    for cell_field in _CELL_FIELDS:
        node = getattr(atom, cell_field)
        if node is not None:
            row[cell_field] = node.id
    return row


class AttributionSource:
    """Mixin for impact sources implementing the atom contract: an ``attribution_atoms(phase)``
    generator, and the ``impact_repartition_rows`` computed structure summarizing those atoms for the
    system-level repartition matrix."""

    @abstractmethod
    def attribution_atoms(self, phase: LifeCyclePhases):
        pass

    @computed_structure
    def impact_repartition_rows(self) -> tuple:
        """One dict-encoded matrix row per attribution atom of this source, across both life-cycle
        phases, each value reduced to its period sum in kg. Calculus edges are recorded from each
        atom's hourly value before the reduction drops its ancestry, so the rows are invalidated
        exactly like the atoms they summarize."""
        rows = []
        for phase in LifeCyclePhases:
            for atom in self.attribution_atoms(phase):
                record_calculus_edges_from_ancestry(atom.value)
                rows.append(_atom_row(atom, phase))
        return tuple(rows)


def atoms_of(source: ModelingObject, phase) -> tuple:
    """The source's materialized atom list for a life-cycle phase."""
    return tuple(source.attribution_atoms(phase))


def attribution_sources(system) -> list:
    """The system's impact sources that implement the atom contract. Membership is checked on
    ``efootprint_class`` because ``all_linked_objects`` yields contextual proxies, which delegate
    attributes but are not ``AttributionSource`` instances themselves."""
    return [obj for obj in system.all_linked_objects if issubclass(obj.efootprint_class, AttributionSource)]


def atoms(system, phase, exclude: tuple = ()):
    """All sources' atoms for a phase, excluded source classes filtered out (exclusion = filter, never
    rescale)."""
    exclude = tuple(exclude)
    for source in attribution_sources(system):
        if isinstance(source, exclude):
            continue
        yield from source.attribution_atoms(phase)


def _underlying_modeling_object(obj: ModelingObject) -> ModelingObject:
    """Strip a relationship-context wrapper at the matrix boundary.

    Attribution grouping is identity-based and does not need contextual read tracking. Keeping raw objects
    in the fold also prevents every row from repeatedly paying wrapper attribute, hash and ``isinstance``
    costs.
    """
    return obj._value if isinstance(obj, ContextualModelingObjectAttribute) else obj


def evict_attribution_source_intermediates(source: ModelingObject) -> None:
    """Release one source's condensed attribution helpers while retaining their graph topology."""
    evict_transient_structures(_underlying_modeling_object(source))


def impact_repartition_rows_cache_coverage(system) -> tuple[int, int]:
    """Return cached and total attribution-source row slots required by the system matrix.

    This is a peek-only progress surface: relationship proxies are unwrapped before the descriptor
    lookup, and a missing ``impact_repartition_rows`` value remains uncomputed.
    """
    sources = [_underlying_modeling_object(source) for source in attribution_sources(system)]
    cached = sum(
        computed_structures(source.efootprint_class)["impact_repartition_rows"].peek(source) is not None
        for source in sources
    )
    return cached, len(sources)


@dataclass(frozen=True)
class _MatrixFoldContext:
    objects_by_id: dict[str, ModelingObject]
    visible_object_ids: frozenset[str]
    excluded_source_ids: frozenset[str]


def _resolved_row_chain(row: dict, objects_by_id: dict) -> list:
    up = objects_by_id[row["up"]]
    cell_nodes = {cell_field: objects_by_id[row[cell_field]] for cell_field in _CELL_FIELDS if cell_field in row}
    return [_underlying_modeling_object(node) for node in _chain_nodes(
        objects_by_id[row["source"]], up, objects_by_id[row["journey"]], **cell_nodes)]


def _matrix_fold_context(system, visible_levels: tuple, exclude: tuple) -> _MatrixFoldContext:
    raw_objects = (_underlying_modeling_object(obj) for obj in system.all_linked_objects)
    objects_by_id = {obj.id: obj for obj in raw_objects}
    return _MatrixFoldContext(
        objects_by_id=objects_by_id,
        visible_object_ids=frozenset(
            object_id for object_id, obj in objects_by_id.items() if isinstance(obj, visible_levels)),
        excluded_source_ids=frozenset(
            object_id for object_id, obj in objects_by_id.items() if isinstance(obj, exclude)),
    )


def node_totals_and_links_by_phase_in_kg(system, phases: tuple, visible_levels: tuple, exclude: tuple = ()):
    """Fold the cached matrix into kg-float node/link totals for every requested life-cycle phase.

    Object normalization and class visibility are resolved once per fold, outside the matrix loop. The
    result is ``{phase: ({node: kg float}, {(finer, coarser): kg float})}``.

    ``visible_levels`` is a tuple of ModelingObject classes; a chain node is visible iff it is an instance
    of one of them — skipping a column = leaving its classes out (adjacent visible nodes link directly).
    Each row contributes its value to every visible node of its chain and to the link between each
    consecutive pair, so Σ incoming == node total == Σ outgoing holds at every node BY CONSTRUCTION —
    no normalization, no rescaling, anywhere."""
    phases_by_value = {phase.value: phase for phase in phases}
    context = _matrix_fold_context(system, tuple(visible_levels), tuple(exclude))
    folds = {phase: ({}, {}) for phase in phases}
    for row in system.impact_repartition_matrix:
        phase = phases_by_value.get(row["phase"])
        if phase is None or row["source"] in context.excluded_source_ids:
            continue
        node_totals, links = folds[phase]
        chain = [
            node for node in _resolved_row_chain(row, context.objects_by_id)
            if node.id in context.visible_object_ids
        ]
        value = float(row["value"])
        for node in chain:
            node_totals[node] = node_totals.get(node, 0.0) + value
        for index in range(len(chain) - 1):
            pair = (chain[index], chain[index + 1])
            links[pair] = links.get(pair, 0.0) + value

    return folds


def node_totals_and_links_in_kg(system, phase, visible_levels: tuple, exclude: tuple = ()):
    """Single-phase convenience wrapper around :func:`node_totals_and_links_by_phase_in_kg`."""
    return node_totals_and_links_by_phase_in_kg(
        system, (phase,), visible_levels, exclude=exclude)[phase]


def node_totals_and_links(system, phase, visible_levels: tuple, exclude: tuple = ()):
    """Quantity-valued attribution fold for programmatic consumers."""
    node_totals, links = node_totals_and_links_in_kg(system, phase, visible_levels, exclude=exclude)
    return ({node: total * u.kg for node, total in node_totals.items()},
            {pair: total * u.kg for pair, total in links.items()})


def footprint_per_node(system, level, phase, exclude: tuple = ()):
    """Programmatic per-level read: ``{node: hourly}`` grouping each atom by its chain node at ``level``
    (a ModelingObject class or tuple of classes). Atoms with no node at that level don't contribute.
    Folds live atoms on every call — the hourly counterpart of the period-sum matrix."""
    totals = {}
    for atom in atoms(system, phase, exclude):
        node = next((node for node in atom.chain() if isinstance(node, level)), None)
        if node is not None:
            totals[node] = totals.get(node, EmptyExplainableObject()) + atom.value

    return totals


def footprint_per_node_per_source(system, level, phase, exclude: tuple = ()):
    """Per-source variant of ``footprint_per_node``: ``{(source, node): hourly}`` — the footprint of any
    container at ``level`` due to any source, not just leaves."""
    totals = {}
    for atom in atoms(system, phase, exclude):
        node = next((node for node in atom.chain() if isinstance(node, level)), None)
        if node is not None:
            key = (atom.source, node)
            totals[key] = totals.get(key, EmptyExplainableObject()) + atom.value

    return totals


def attributed_footprint(obj: ModelingObject, phase: LifeCyclePhases):
    """The object's total attributed footprint for a life-cycle phase, summed over its systems.

    This targeted on-demand read streams live atoms and accumulates only atoms whose first chain
    node at the object's own class level is the requested object. Use ``footprint_per_node`` when
    totals for every node at a level are needed. Returns Empty when the object is system-less.
    """
    total = EmptyExplainableObject()
    level = type(obj)
    for system in obj.systems:
        for source in attribution_sources(system):
            for atom in source.attribution_atoms(phase):
                node = next((node for node in atom.chain() if isinstance(node, level)), None)
                if node == obj:
                    total += atom.value
            total.finalize_explanation()
            evict_attribution_source_intermediates(source)
    label = ("Attributed fabrication footprint" if phase is LifeCyclePhases.MANUFACTURING
             else "Attributed energy footprint")
    return total.to(u.kg).set_label(label)
