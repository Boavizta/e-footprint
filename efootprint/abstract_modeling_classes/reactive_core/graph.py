"""Pull-based dependency-graph primitives shared by every reactive surface."""

import contextvars
import dataclasses
from contextlib import contextmanager
from typing import Type

_INSTANCE_SLOT_REGISTRY_ATTR = "_reactive_slots"

_VOID = object()

_compute_stack: contextvars.ContextVar[tuple] = contextvars.ContextVar("reactive_compute_stack", default=())

_computation_observer = None

_invalidation_collector: contextvars.ContextVar[set | None] = contextvars.ContextVar(
    "reactive_invalidation_collector", default=None)

_recording_suppressed: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "reactive_recording_suppressed", default=False)


@contextmanager
def observe_computations(callback):
    """Call ``callback(slot)`` after every successful cache-miss computation in this scope.

    Scopes are process-local and may be nested; leaving a scope restores the observer that was active
    before it. The callback receives the coherent, cached slot and may inspect
    ``slot.diagnostic_name`` for a non-user-authored calculation identity. It must not mutate the model,
    pull reactive values, or retain the slot beyond the callback.

    If the callback raises, the just-produced value is dropped, the slot's previous dependency edges
    are restored, and the exception is re-raised. Successful child computations remain cached.
    """
    global _computation_observer
    previous_observer = _computation_observer
    _computation_observer = callback
    try:
        yield
    finally:
        _computation_observer = previous_observer


@contextmanager
def suppress_dependency_recording():
    """Read without recording any dependency edge — for bookkeeping reads that must not couple the
    computation in progress to what they touch (e.g. the computed-dict facade checking a key's
    membership in the key collection: indexing one key deliberately depends on that key's value only,
    never on the key set). Only safe for reads that cannot pull a computed slot (relationship
    collections and reverse lookups), since a nested compute frame would be suppressed too."""
    token = _recording_suppressed.set(True)
    try:
        yield
    finally:
        _recording_suppressed.reset(token)


@contextmanager
def collect_invalidated_slots():
    """Collect every slot visited by any deletion wave triggered inside the block — the write path
    fires waves from several places (explicit invalidations plus the container-transition bumps riding
    along relationship bookkeeping), and post-write guard/output pulls need their union."""
    collected = set()
    token = _invalidation_collector.set(collected)
    try:
        yield collected
    finally:
        _invalidation_collector.reset(token)


class CircularDependencyError(Exception):
    """Computing a slot ended up pulling that same slot again; the message carries the offending chain."""


class _ComputeFrame:
    __slots__ = ("slot", "calculus_reads", "structural_reads")

    def __init__(self, slot):
        self.slot = slot
        self.calculus_reads = set()
        self.structural_reads = set()


class ReactiveSlot:
    """One node of the pull-based dependency graph.

    A slot is either cached (holds a value) or void. ``pull`` returns the cached value or runs the
    getter, recursively computing any void ancestor it pulls. Dependency edges are recorded during the
    computation (``record_calculus_dependency`` / ``record_structural_dependency``) and replace the
    previous edges when it succeeds, so a dependency read only under a stale conditional branch stops
    invalidating the slot. A failed computation keeps the previous edges — over-invalidation is safe,
    a missed edge is not — and leaves the slot void and unmarked, so a later pull simply retries and
    the next deletion wave still traverses it.
    """

    def __init__(self, name: str, getter=None, on_value_dropped=None, diagnostic_name: str | None = None):
        self.name = name
        self.diagnostic_name = diagnostic_name or name.split("[", 1)[0].split(" of ", 1)[0]
        self.getter = getter
        self.on_value_dropped = on_value_dropped
        # Ordinary computed slots stay void after invalidation until the next read pulls them.
        # Guard slots (validation attributes) exist to reject invalid states: they are eagerly
        # re-pulled after every invalidation that voids them, so bad edits fail at update time even
        # when nothing else reads them.
        self.guard = False
        # (descriptor, instance) backreference set on computed-dict key-set slots, so the write path
        # can prune stale facade keys after an invalidation wave without recomputing any value.
        self.key_set_binding = None
        # Label carried by the serialized calculation graph for slots loaded valueless: kept so
        # re-serializing a partially computed model doesn't lose the graph's display labels.
        self.serialized_label = None
        self._value = _VOID
        self._wave_passed = False
        self._dependents = set()
        self._calculus_dependencies = set()
        self._structural_dependencies = set()

    def __repr__(self):
        return f"<ReactiveSlot {self.name} ({'cached' if self.has_cached_value else 'void'})>"

    @property
    def has_cached_value(self) -> bool:
        return self._value is not _VOID

    @property
    def wave_passed(self) -> bool:
        return self._wave_passed

    @property
    def dependents(self) -> frozenset:
        return frozenset(self._dependents)

    @property
    def calculus_dependencies(self) -> frozenset:
        return frozenset(self._calculus_dependencies)

    @property
    def structural_dependencies(self) -> frozenset:
        return frozenset(self._structural_dependencies)

    def pull(self):
        """Return the slot's value, computing it (and recursively any void ancestor it reads) if void."""
        if self._value is not _VOID:
            return self._value
        return self._compute()

    def _drop_value(self):
        if self._value is not _VOID:
            dropped_value = self._value
            self._value = _VOID
            if self.on_value_dropped is not None:
                self.on_value_dropped(dropped_value)

    def _compute(self):
        stack = _compute_stack.get()
        for position, frame in enumerate(stack):
            if frame.slot is self:
                chain = " -> ".join([f.slot.name for f in stack[position:]] + [self.name])
                raise CircularDependencyError(f"Circular dependency between computed slots: {chain}")
        observer = _computation_observer
        frame = _ComputeFrame(self)
        if observer is not None:
            previous_calculus_dependencies = self._calculus_dependencies
            previous_structural_dependencies = self._structural_dependencies
        token = _compute_stack.set(stack + (frame,))
        try:
            value = self.getter()
        finally:
            _compute_stack.reset(token)
            # Cleared on failure too (success re-clears it in attach_cached_value): a failed compute left
            # marked would let a dependent whose getter catches the failure cache a fallback below a
            # marked slot, which the next wave would prune past — a stale value.
            self._wave_passed = False
        self.replace_dependencies(frame.calculus_reads, frame.structural_reads)
        self.attach_cached_value(value)
        if observer is not None:
            try:
                observer(self)
            except Exception:
                self._drop_value()
                self.replace_dependencies(previous_calculus_dependencies, previous_structural_dependencies)
                raise
        return value

    def replace_dependencies(self, calculus_dependencies=frozenset(), structural_dependencies=frozenset()):
        """Install the slot's dependency edges, updating the reverse (dependents) index on both the
        dropped and the added dependencies. Called with each successful computation's recorded reads,
        and directly by the load path to rebuild serialized topology without computing anything."""
        old_dependencies = self._calculus_dependencies | self._structural_dependencies
        new_dependencies = set(calculus_dependencies) | set(structural_dependencies)
        for dependency in old_dependencies - new_dependencies:
            dependency._dependents.discard(self)
        for dependency in new_dependencies - old_dependencies:
            dependency._dependents.add(self)
        for dependency in new_dependencies:
            # A recorded read means the dependency was consumed by a computation that will cache: the
            # dependency's wave marker (whose invariant is "all my dependents are marked") is stale.
            # Getter-less bump nodes rely on this — they never compute, so nothing else clears theirs.
            dependency._wave_passed = False
        self._calculus_dependencies = set(calculus_dependencies)
        self._structural_dependencies = set(structural_dependencies)

    def attach_cached_value(self, value):
        """Cache a value directly — a computation result, or a trusted stored value at load time.
        Clears the wave marker: a freshly cached slot must be reachable by the next deletion wave."""
        if self._value is not _VOID and self._value is not value:
            self._drop_value()
        self._value = value
        self._wave_passed = False


def record_calculus_dependency(slot: ReactiveSlot):
    """Record that the slot currently being computed depends on ``slot`` through a calculation
    (arithmetic ancestry). No-op outside a computation. Only record slots the computation actually
    pulled: wave-pruning soundness relies on every recorded edge tracing a real read (production edges
    derive from the ancestry of values actually obtained, so this holds by construction)."""
    _record_dependency(slot, "calculus_reads")


def record_structural_dependency(slot: ReactiveSlot):
    """Record that the slot currently being computed depends on ``slot`` through a relationship read
    (who read this membership). No-op outside a computation. As for calculus edges, only record slots
    the computation actually pulled."""
    _record_dependency(slot, "structural_reads")


def _record_dependency(slot: ReactiveSlot, read_kind: str):
    if _recording_suppressed.get():
        return
    stack = _compute_stack.get()
    if stack:
        getattr(stack[-1], read_kind).add(slot)


def invalidate(*slots: ReactiveSlot) -> set[ReactiveSlot]:
    """Deletion wave: delete the cached values of ``slots`` and of all their transitive dependents,
    returning the slots the wave visited. The wave prunes at slots whose marker is already set: a
    marked slot's dependents were all marked by the same or an earlier wave, and a dependent can only
    cache a new value after pulling this slot again — which clears the marker whether that compute
    succeeds or fails — so nothing cached can hide below a marked slot (given edges only trace real
    reads, see ``record_calculus_dependency``). Voidness itself cannot prune: after a partial reload,
    cached slots legitimately sit below valueless, unmarked intermediates."""
    if _compute_stack.get():
        computing_chain = " -> ".join(frame.slot.name for frame in _compute_stack.get())
        raise RuntimeError(
            f"Invalidation triggered while computing {computing_chain}: a slot getter must only read "
            f"values, never write inputs or relationships.")
    visited = set()
    work = list(slots)
    while work:
        slot = work.pop()
        if slot._wave_passed:
            continue
        slot._wave_passed = True
        slot._drop_value()
        visited.add(slot)
        work.extend(slot._dependents)
    collector = _invalidation_collector.get()
    if collector is not None:
        collector.update(visited)
    return visited


def computation_in_progress() -> bool:
    """True while a slot computation is on the stack — the guard read hooks use before recording."""
    return bool(_compute_stack.get())


def instance_slot_registry(instance) -> dict:
    """The per-instance slot registry: attribute name -> ReactiveSlot for scalar slots and bump nodes,
    (attribute name, key object) -> ReactiveSlot for dict element slots."""
    registry = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR)
    if registry is None:
        registry = {}
        instance.__dict__[_INSTANCE_SLOT_REGISTRY_ATTR] = registry
    return registry


def peek_instance_slot_registry(instance) -> dict:
    """The per-instance slot registry without creating it — for read-only consumers (serialization)
    that must not mutate the objects they walk."""
    return instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR) or {}


def _node_slot(instance, name, key=None) -> ReactiveSlot:
    """Get or create a getter-less bump node — the graph identity of an input value or a relationship
    membership. Bump nodes never compute: they exist to carry dependents recorded by read hooks and to
    be invalidated by writes."""
    registry = instance_slot_registry(instance)
    registry_key = name if key is None else (name, key)
    slot = registry.get(registry_key)
    if slot is None:
        key_suffix = f"[{getattr(key, 'id', key)}]" if key is not None else ""
        slot = ReactiveSlot(f"{name}{key_suffix} of {getattr(instance, 'id', instance)}")
        registry[registry_key] = slot
    return slot


def record_read_of_node(instance, name, key=None):
    """Structural read hook body: while a computation is in progress, record that it read the given
    relationship or input node."""
    if _compute_stack.get():
        record_structural_dependency(_node_slot(instance, name, key))


def invalidate_node_if_exists(instance, name, key=None):
    """Invalidate the node's dependents if the node was ever materialized — a node nobody ever read or
    computed against has no dependents, so there is nothing to invalidate."""
    registry = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR)
    if registry is None:
        return
    slot = registry.get(name if key is None else (name, key))
    if slot is not None:
        invalidate(slot)


def slot_of_attached_value(value) -> ReactiveSlot:
    """The graph node of an attached value: its backpointer when it was attached by the engine (every
    computed value), else the input bump node of its (container, attribute[, key]) address."""
    slot = value._reactive_slot
    if slot is not None:
        return slot
    container = value.modeling_obj_container
    attr_name = value.attr_name_in_mod_obj_container
    key = value.key_in_dict if value.dict_container is not None else None
    slot = _node_slot(container, attr_name, key)
    value._reactive_slot = slot
    return slot


def record_calculus_edges_from_ancestry(value):
    """Record, against the computation in progress, one calculus edge per direct ancestor of the freshly
    computed value — the arithmetic ancestry is the exact value-level read set of the calculation."""
    ancestors = getattr(value, "direct_ancestors_with_id", None)
    if not ancestors:
        return
    for ancestor in ancestors:
        record_calculus_dependency(slot_of_attached_value(ancestor))


def record_calculus_edges_from_value_structure(value):
    """Record calculus edges for every explainable found in a raw projection value — a bare explainable,
    or dicts / lists / tuples / dataclass instances containing them. An attached explainable contributes
    its own slot; an unattached one the slots of its nearest attached ancestors. This is how computed structures
    holding plain containers capture the input reads that only surface through arithmetic ancestry."""
    if hasattr(value, "direct_ancestors_with_id"):
        if value.modeling_obj_container is not None:
            record_calculus_dependency(slot_of_attached_value(value))
        else:
            record_calculus_edges_from_ancestry(value)
    elif isinstance(value, dict):
        for item in value.values():
            record_calculus_edges_from_value_structure(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            record_calculus_edges_from_value_structure(item)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            record_calculus_edges_from_value_structure(getattr(value, field.name))
