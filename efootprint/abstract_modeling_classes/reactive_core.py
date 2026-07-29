"""Reactive pull engine and declarative descriptors for computed modeling attributes.

Two layers live here.

The reactive engine primitives: ``ReactiveSlot`` — one node of the dependency graph, cached or void,
carrying its dependency edges (calculus edges from arithmetic ancestry, structural edges from
relationship reads) and a one-bit invalidation-wave marker — plus the contextvar compute stack shared
by all slots (it records dependency edges against the slot currently computing and doubles as the
cycle guard) and the ``invalidate`` deletion wave. Slots compute on pull, cache, and are invalidated
by deleting cached values along the recorded edges: stale values are never retained, while dependency
edges and the wave marker survive valuelessness — so a wave can reach cached slots through valueless
intermediates, the normal state after loading a file that stores only some values.

The ``@computed_attribute`` / ``@computed_dict`` descriptors are the single source of truth for how
each computed attribute is derived: the decorated getter's body is the calculation and its docstring
is the doc-as-code description of the attribute (consumed by the mkdocs object reference and the
interface). The descriptors drive the reactive engine: each attribute read resolves to a per-instance
``ReactiveSlot`` (stored in the instance's ``_reactive_slots`` registry) that computes on pull, does
the container bookkeeping the eager ``__setattr__`` used to do, records its calculus edges from the
computed value's arithmetic ancestry, and caches. Input values and relationship memberships get
getter-less bump nodes in the same registry, created lazily when first read during a computation or
first written; writes invalidate those nodes and the deletion wave does the rest. ``@lazy_attribute``
declares read-time projections: slots invalidated through the same graph but never eagerly recomputed,
not serialized under the current contract, holding raw values outside the container bookkeeping.
"""
import contextvars
import dataclasses
from contextlib import contextmanager
from typing import Type

_INSTANCE_SLOT_REGISTRY_ATTR = "_reactive_slots"

_VOID = object()

_compute_stack: contextvars.ContextVar[tuple] = contextvars.ContextVar("reactive_compute_stack", default=())

_invalidation_collector: contextvars.ContextVar[set | None] = contextvars.ContextVar(
    "reactive_invalidation_collector", default=None)

_recording_suppressed: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "reactive_recording_suppressed", default=False)


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
    along relationship bookkeeping), and the eager recompute needs their union."""
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

    def __init__(self, name: str, getter=None, on_value_dropped=None):
        self.name = name
        self.getter = getter
        self.on_value_dropped = on_value_dropped
        # Set when the slot leaves its owner's registry (a dict key left the key set): stale
        # dependents may still pull it, but eager sweeps must not.
        self.discarded = False
        # Lazy slots (read-time projections) are invalidated like any slot but never eagerly
        # recomputed: they stay void until the next read pulls them.
        self.lazy = False
        # Guard slots (validation attributes) exist to reject invalid states: they are eagerly
        # re-pulled after every invalidation that voids them, so bad edits fail at update time even
        # when nothing else reads them.
        self.guard = False
        # Eager sweeps pull lower precedence first: key-set nodes before their sub-slots, so stale
        # sub-slots are discarded before the sweep reaches them.
        self.pull_precedence = 0
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
        frame = _ComputeFrame(self)
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
    its own slot; an unattached one the slots of its nearest attached ancestors. This is how lazy slots
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


def _assert_not_attached_elsewhere(value, instance, attr_name):
    """A getter must return a fresh value: returning another attribute's value object directly would
    alias the same object into two slots (relabeling it in place, and leaving one slot holding an
    unlinked value when the other drops it). Deriving with .copy() keeps the ancestry."""
    container = value.modeling_obj_container
    if container is not None and not (
            container is instance and value.attr_name_in_mod_obj_container == attr_name):
        raise ValueError(
            f"The getter of {attr_name} on {getattr(instance, 'id', instance)} returned a value already attached "
            f"at {value.attr_name_in_mod_obj_container} of {container.id}. Computed getters must return fresh "
            f"values — derive with .copy() instead of returning another attribute directly.")


def _release_value(value):
    """Drop callback for computed slots: unlink the dropped value from its container so ancestor
    children links and container bookkeeping don't accumulate dead values."""
    if value is not None and value.modeling_obj_container is not None:
        value.set_modeling_obj_container(None, None)


# MRO slot collection is on hot paths (every load-time slot resolution, every calculated_attributes
# read): memoized per (registry, class), invalidated by any slot registration (which only happens at
# class-definition time or through add_computed_attribute).
_slot_collection_cache = {}


def _register_slot(registry_name: str, owner: type, name: str, descriptor):
    if registry_name not in owner.__dict__:
        setattr(owner, registry_name, {})
    owner.__dict__[registry_name][name] = descriptor
    _slot_collection_cache.clear()


def _collect_slots(registry_name: str, cls: type) -> dict:
    cache_key = (registry_name, cls)
    slots = _slot_collection_cache.get(cache_key)
    if slots is None:
        slots = {}
        for klass in reversed(cls.__mro__):
            slots.update(klass.__dict__.get(registry_name, {}))
        _slot_collection_cache[cache_key] = slots
    return slots


def computed_slots(cls: type) -> dict:
    """All computed-attribute descriptors visible on cls (name -> descriptor), the most derived
    declaration winning; attributes a subclass removed with removed_computed_attribute are excluded."""
    cache_key = ("computed_slots_filtered", cls)
    slots = _slot_collection_cache.get(cache_key)
    if slots is None:
        slots = {name: descriptor for name, descriptor in _collect_slots("_declared_computed_slots", cls).items()
                 if not isinstance(descriptor, removed_computed_attribute)}
        _slot_collection_cache[cache_key] = slots
    return slots


def _inherited_slot_doc(owner: type, name: str) -> str | None:
    for klass in owner.__mro__[1:]:
        slot = klass.__dict__.get("_declared_computed_slots", {}).get(name)
        if slot is not None and slot.__doc__:
            return slot.__doc__
    return None


def reverse_slots(cls: type) -> dict:
    """All reverse-relationship descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_reverse_slots", cls)


CONTAINERS_NODE_NAME = "__containers__"


def bump_reverse_nodes(value_mod_obj, container):
    """Container-field transition write hook: when value_mod_obj gains or loses ``container``, its
    reverse relationships change — invalidate its generic containers node and every typed reverse slot
    whose member type matches the container."""
    if container is None:
        return
    invalidate_node_if_exists(value_mod_obj, CONTAINERS_NODE_NAME)
    for name, descriptor in reverse_slots(type(value_mod_obj)).items():
        member_type = descriptor._resolve_member_type()
        if member_type is not None and isinstance(container, member_type):
            invalidate_node_if_exists(value_mod_obj, name)


class removed_computed_attribute:
    """Subclass declaration removing an inherited computed attribute: the slot leaves the class
    registry (nothing enumerates or serializes it) and instance reads raise AttributeError, exactly
    like an attribute that does not exist."""

    def __set_name__(self, owner, name):
        self.attr_name = name
        _register_slot("_declared_computed_slots", owner, name, self)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(
            f"{type(instance).__name__} removed the inherited computed attribute {self.attr_name}")

    def __set__(self, instance, value):
        raise AttributeError(
            f"{type(instance).__name__} removed the inherited computed attribute {self.attr_name}")


class computed_attribute:
    """Descriptor declaring a computed attribute from a getter.

    The getter takes only self and returns the attribute's new value. Reading the attribute pulls its
    per-instance ReactiveSlot: cached value if present, else run the getter, attach the result to the
    owner (label/graph/container bookkeeping), record calculus edges from the result's arithmetic
    ancestry, cache. Calling the descriptor as ``ParentClass.<attr>(self)`` runs the parent's getter,
    mirroring unbound-method syntax for overriding getters that refine an inherited calculation.

    Declared bare (``@computed_attribute``) or parametrized (``@computed_attribute(serialize=True)``):
    the ``serialize`` flag marks the slot's cached value for persistence under the minimal
    serialization contract (the single source of truth for "what serializes"), and ``guard=True``
    marks a slot whose getter enforces a user-facing constraint (raising on invalid states) without
    feeding the footprint totals: guard slots eagerly recompute whenever an update invalidates them,
    so invalid edits are rejected at update time. ``<name>_validation`` slots are guards implicitly.
    """

    def __init__(self, getter=None, *, serialize=False, guard=False):
        self.serialize = serialize
        self.guard = guard
        self.getter = None
        if getter is not None:
            self._bind_getter(getter)

    def _bind_getter(self, getter):
        self.getter = getter
        self.attr_name = getter.__name__
        self.__doc__ = getter.__doc__
        self.__isabstractmethod__ = getattr(getter, "__isabstractmethod__", False)

    def __set_name__(self, owner, name):
        if name != self.getter.__name__:
            raise ValueError(
                f"Computed attribute declared as {name} but its getter is named {self.getter.__name__}")
        if self.__doc__ is None:
            # An overriding getter without its own docstring keeps the inherited description,
            # exactly as an overriding method resolved through the MRO used to.
            self.__doc__ = _inherited_slot_doc(owner, name)
        _register_slot("_declared_computed_slots", owner, name, self)

    # The facade of a computed dict survives invalidation (only the key-set sync is redone), so the
    # dict subclass declares no drop-time release.
    _on_value_dropped = staticmethod(_release_value)

    def slot(self, instance) -> ReactiveSlot:
        registry = instance_slot_registry(instance)
        slot = registry.get(self.attr_name)
        if slot is None or slot.getter is None:
            # A bump node may pre-exist under this name if the attribute was read as an input before
            # the descriptor materialized its computing slot (never in practice); computing wins.
            slot = ReactiveSlot(
                f"{self.attr_name} of {getattr(instance, 'id', instance)}", on_value_dropped=self._on_value_dropped)
            slot.getter = self._make_compute_closure(instance, slot)
            slot.guard = self.guard or self.attr_name.endswith("_validation")
            registry[self.attr_name] = slot
        return slot

    def _make_compute_closure(self, instance, slot):
        def compute():
            value = self.getter(instance)
            self._attach_to_owner(instance, value, slot)
            record_calculus_edges_from_ancestry(value)
            return value
        return compute

    def _attach_to_owner(self, instance, value, slot):
        if value is not None:
            _assert_not_attached_elsewhere(value, instance, self.attr_name)
            value.set_modeling_obj_container(instance, self.attr_name)
            value._reactive_slot = slot

    def attach_cached_value(self, instance, value):
        """Store a value in the slot without computing — the load path for stored values, and the
        manual-assignment path tests use to pin a computed attribute."""
        slot = self.slot(instance)
        if slot.has_cached_value and slot._value is not value:
            slot._drop_value()
        # Container linking must precede caching: at load time the calculus graph hooks onto the
        # attached value right after, and expects the container address to be set.
        self._attach_to_owner(instance, value, slot)
        slot.attach_cached_value(value)

    def peek(self, instance):
        """The cached value, or None when the slot is void — never computes (display paths)."""
        slot = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR, {}).get(self.attr_name)
        if slot is not None and slot.has_cached_value:
            return slot._value
        return None

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        slot = self.slot(instance)
        if _compute_stack.get():
            # Conservative read edge: also covers computed values read only in conditionals, which
            # the result's arithmetic ancestry would miss.
            record_calculus_dependency(slot)
        return slot.pull()

    def __set__(self, instance, value):
        # Data-descriptor storage: computed values live in the reactive slot, never in the instance
        # dict, so reads always resolve through the engine.
        self.attach_cached_value(instance, value)

    def __delete__(self, instance):
        # Deleting a computed attribute voids its slot: the next read recomputes.
        slot = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR, {}).get(self.attr_name)
        if slot is not None:
            slot._drop_value()

    def __call__(self, instance, *args):
        if self.getter is None:
            # Parametrized decorator form: @computed_attribute(serialize=True) first builds an
            # unbound descriptor, then this call binds the decorated getter.
            self._bind_getter(instance)
            return self
        return self.getter(instance, *args)


class computed_dict(computed_attribute):
    """Descriptor declaring a computed ExplainableObjectDict attribute.

    The getter takes self plus one key object and returns the value for that key; the key set is the
    collection read from the ``keys`` attribute of the owning object. The attribute resolves to two
    slot layers: a key-set node whose getter reads the key collection and syncs a persistent
    ExplainableObjectDict facade (readers of the whole dict depend on it, so key-set changes reach
    them), and one sub-slot per key holding that key's value (per-key granularity: a value change
    invalidates only its own readers). The facade's read methods pull the slots, so it is always a
    live view.

    Declared as ``@computed_dict(keys="usage_patterns")``. ``guard=True`` marks a dict whose element
    getters enforce user-facing constraints outside the footprint cone (see ``computed_attribute``):
    its key-set node and sub-slots eagerly recompute when invalidated. ``serialize=True`` persists the
    materialized entries under the minimal serialization contract.
    """

    _on_value_dropped = None

    def __init__(self, keys: str, guard=False, serialize=False):
        # Like parametrized computed_attribute, decorator construction precedes getter binding:
        # @computed_dict(keys="jobs") builds this descriptor, then inherited __call__ receives the
        # decorated getter and returns the now-bound descriptor for installation on the class.
        super().__init__(guard=guard, serialize=serialize)
        self.keys = keys

    def slot(self, instance) -> ReactiveSlot:
        slot = super().slot(instance)
        # Eager sweeps must sync the key set before touching sub-slots, so stale sub-slots are
        # discarded before being pulled.
        slot.pull_precedence = -1
        slot.key_set_binding = (self, instance)
        return slot

    def facade(self, instance):
        """Get or create the persistent dict facade — the object returned by every attribute read,
        surviving key-set recomputations so downstream references stay valid."""
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        facades = instance.__dict__.setdefault("_computed_dict_facades", {})
        facade = facades.get(self.attr_name)
        if facade is None:
            facade = ExplainableObjectDict()
            facade.set_modeling_obj_container(instance, self.attr_name)
            facade._computed_facade_of = (instance, self)
            facade._reactive_slot = self.slot(instance)
            facades[self.attr_name] = facade
        return facade

    def discard_stale_keys(self, instance, current_keys):
        """Drop facade entries (and their sub-slots) for keys that left the key collection."""
        facade = self.facade(instance)
        registry = instance_slot_registry(instance)
        for stale_key in [key for key in list(dict.keys(facade)) if key not in current_keys]:
            stale_slot = registry.pop((self.attr_name, stale_key), None)
            if stale_slot is not None:
                stale_slot.discarded = True
            facade._drop_entry_passively(stale_key)

    def _make_compute_closure(self, instance, slot):
        def compute():
            current_keys = list(getattr(instance, self.keys))
            facade = self.facade(instance)
            self.discard_stale_keys(instance, current_keys)
            for key in current_keys:
                self.sub_slot(instance, key).pull()
            ordered_keys = list(dict.fromkeys(current_keys))
            if list(dict.keys(facade)) != ordered_keys:
                # Key order follows the key collection (as a from-scratch rebuild would produce), not
                # insertion history: a key that left and came back returns to its collection position.
                ordered_entries = {key: dict.__getitem__(facade, key) for key in ordered_keys}
                dict.clear(facade)
                dict.update(facade, ordered_entries)
            return facade
        return compute

    def sub_slot(self, instance, key) -> ReactiveSlot:
        registry = instance_slot_registry(instance)
        registry_key = (self.attr_name, key)
        slot = registry.get(registry_key)
        if slot is None:
            slot = ReactiveSlot(
                f"{self.attr_name}[{getattr(key, 'id', key)}] of {getattr(instance, 'id', instance)}",
                on_value_dropped=_release_value)
            slot.getter = self._make_element_compute_closure(instance, key, slot)
            slot.guard = self.guard or self.attr_name.endswith("_validation")
            registry[registry_key] = slot
        return slot

    def _make_element_compute_closure(self, instance, key, slot):
        def compute_element():
            value = self.getter(instance, key)
            self._attach_element(instance, key, value, slot)
            record_calculus_edges_from_ancestry(value)
            return value
        return compute_element

    def _attach_element(self, instance, key, value, slot):
        _assert_not_attached_elsewhere(value, instance, self.attr_name)
        if instance_slot_registry(instance).get((self.attr_name, key)) is slot:
            self.facade(instance)._set_entry_passively(key, value)
        # An orphaned sub-slot (its key left the key set) can still be pulled by a stale dependent:
        # it recomputes for that reader but must not reintroduce its key into the facade.
        value._reactive_slot = slot

    def attach_element_cached_value(self, instance, key, value):
        """Store one key's value without computing (load path, manual per-key assignment in tests)."""
        slot = self.sub_slot(instance, key)
        if slot.has_cached_value and slot._value is not value:
            slot._drop_value()
        self._attach_element(instance, key, value, slot)
        slot.attach_cached_value(value)

    def peek(self, instance):
        """The facade, only when fully cached (key-set node and every entry's sub-slot) — a facade
        with invalidated sub-slots still holds the dropped, unlinked values until the next read syncs
        it, and those must never be observed as current state (display or serialization)."""
        registry = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR, {})
        slot = registry.get(self.attr_name)
        if slot is None or not slot.has_cached_value:
            return None
        facade = slot._value
        for key in dict.keys(facade):
            sub_slot = registry.get((self.attr_name, key))
            if sub_slot is None or not sub_slot.has_cached_value:
                return None
        return facade

    def attach_cached_value(self, instance, value):
        """Store a whole dict without computing: attach each entry as a cached sub-slot and cache the
        synced facade in the key-set node."""
        facade = self.facade(instance)
        input_items = list(dict.items(value)) if isinstance(value, dict) else []
        self.discard_stale_keys(instance, [key for key, item_value in input_items])
        for key, item_value in input_items:
            self.attach_element_cached_value(instance, key, item_value)
        self.slot(instance).attach_cached_value(facade)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        slot = self.slot(instance)
        if _compute_stack.get():
            # Whole-dict reads depend on the key set: key membership is structural.
            record_structural_dependency(slot)
        return slot.pull()


def prune_stale_computed_dict_keys(invalidated_slots):
    """Post-wave write-path pass: for every computed-dict key-set slot the wave visited, drop facade
    keys that left the key collection. The full facade sync only happens on read, so without this
    pass a detached object's facades would keep registering their stale keys' container bookkeeping —
    keeping the detached object reachable (e.g. serialized back into the model). Values are not
    recomputed: only the key collection is read."""
    for slot in invalidated_slots:
        if slot.key_set_binding is None or slot.discarded:
            continue
        descriptor, instance = slot.key_set_binding
        descriptor.discard_stale_keys(instance, list(getattr(instance, descriptor.keys)))


class lazy_attribute:
    """Descriptor declaring a lazy projection slot: computed on first read, cached in the reactive
    graph and invalidated through it like any slot, but excluded from ``calculated_attributes`` (so
    eager sweeps, the current serialization contract and the docs reference never touch it) and never
    eagerly recomputed — after an invalidation it stays void until the next read. Its value is held
    raw, not attached to the owner's explainability bookkeeping, so getters may return plain dicts,
    tuples or dataclass instances of explainable values; the engine records calculus edges from every
    explainable found in the returned structure, on top of the reads recorded while the getter ran.

    Declared bare (``@lazy_attribute``) or parametrized (``@lazy_attribute(serialize=True)``): a
    serialize-flagged lazy slot persists its cached value when materialized (it fills lazily, so a
    save before the first read simply omits it) — the value must then be JSON-native, since raw lazy
    values bypass the explainable serialization machinery."""

    def __init__(self, getter=None, *, serialize=False):
        self.serialize = serialize
        self.getter = None
        if getter is not None:
            self._bind_getter(getter)

    def _bind_getter(self, getter):
        self.getter = getter
        self.attr_name = getter.__name__
        self.__doc__ = getter.__doc__

    def __call__(self, getter):
        if self.getter is not None:
            raise TypeError(f"Lazy attribute {self.attr_name} is not callable")
        self._bind_getter(getter)
        return self

    def __set_name__(self, owner, name):
        if name != self.getter.__name__:
            raise ValueError(
                f"Lazy attribute declared as {name} but its getter is named {self.getter.__name__}")
        _register_slot("_declared_lazy_slots", owner, name, self)

    def slot(self, instance) -> ReactiveSlot:
        registry = instance_slot_registry(instance)
        slot = registry.get(self.attr_name)
        if slot is None or slot.getter is None:
            slot = ReactiveSlot(f"{self.attr_name} of {getattr(instance, 'id', instance)}")
            slot.lazy = True
            slot.getter = self._make_compute_closure(instance)
            registry[self.attr_name] = slot
        return slot

    def _make_compute_closure(self, instance):
        def compute():
            value = self.getter(instance)
            record_calculus_edges_from_value_structure(value)
            return value
        return compute

    def attach_cached_value(self, instance, value):
        """Store a value in the slot without computing — the load path for serialize-flagged lazy
        slots and the pinning path tests use."""
        self.slot(instance).attach_cached_value(value)

    def peek(self, instance):
        """The cached value, or None when the slot is void — never computes (save paths)."""
        slot = instance.__dict__.get(_INSTANCE_SLOT_REGISTRY_ATTR, {}).get(self.attr_name)
        if slot is not None and slot.has_cached_value:
            return slot._value
        return None

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        slot = self.slot(instance)
        if _compute_stack.get():
            record_calculus_dependency(slot)
        return slot.pull()

    def __set__(self, instance, value):
        raise AttributeError(
            f"{self.attr_name} is a lazy projection of {type(instance).__name__} and cannot be assigned: "
            f"change the inputs it derives from instead, or pin it in tests with "
            f"tests.utils.patch_attribute / the descriptor's attach_cached_value.")


def lazy_slots(cls: type) -> dict:
    """All lazy-projection descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_lazy_slots", cls)


def serialized_slots(cls: type) -> dict:
    """All serialize-flagged slot descriptors visible on cls (computed and lazy), name -> descriptor —
    the single source of truth for which slots persist under the minimal serialization contract."""
    return {name: descriptor for name, descriptor in {**computed_slots(cls), **lazy_slots(cls)}.items()
            if descriptor.serialize}


def add_computed_attribute(cls: type, name: str, getter):
    """Attach a computed attribute to an already-created class (for dynamically generated getters,
    where ``__set_name__`` cannot fire automatically)."""
    descriptor = computed_attribute(getter)
    setattr(cls, name, descriptor)
    descriptor.__set_name__(cls, name)


def _find_modeling_class(class_name: str) -> Type | None:
    from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

    def _search(cls):
        matches = [cls] if cls.__name__ == class_name else []
        for subclass in cls.__subclasses__():
            matches += _search(subclass)
        return matches

    matches = list(dict.fromkeys(_search(ModelingObject)))
    if len(matches) > 1:
        raise ValueError(
            f"Several ModelingObject subclasses are named {class_name}: "
            f"{[f'{cls.__module__}.{cls.__qualname__}' for cls in matches]}. Reverse-slot member types resolve "
            f"by class name, so the name must be unambiguous.")
    return matches[0] if matches else None


class ReverseCollection:
    """Declarative reverse relationship: the instances of member_type currently holding this object as
    an attribute (read from modeling_obj_containers). member_type may be a class or a class name; names
    resolve lazily against the ModelingObject subclass tree, replacing the circular-import-driven
    function-local imports of the former property implementations. A name matching no imported class
    yields an empty collection — no instance of it can exist yet."""

    def __init__(self, member_type: type | str):
        self.member_type = member_type

    @property
    def member_type_name(self) -> str:
        return self.member_type if isinstance(self.member_type, str) else self.member_type.__name__

    def __set_name__(self, owner, name):
        self.attr_name = name
        _register_slot("_declared_reverse_slots", owner, name, self)

    def _resolve_member_type(self):
        if isinstance(self.member_type, type):
            return self.member_type
        resolved = _find_modeling_class(self.member_type)
        if resolved is not None:
            self.member_type = resolved
        return resolved

    def _containers_of_member_type(self, instance):
        member_type = self._resolve_member_type()
        if member_type is None:
            return []
        # Read the contextual containers directly rather than through the (hooked) generic
        # modeling_obj_containers property: this typed node is a strict refinement of the generic
        # containers node, so recording both would negate the refinement.
        containers = dict.fromkeys(
            contextual_container.modeling_obj_container
            for contextual_container in instance.contextual_modeling_obj_containers
            if contextual_container.modeling_obj_container is not None)
        return [mod_obj for mod_obj in containers if isinstance(mod_obj, member_type)]

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        record_read_of_node(instance, self.attr_name)
        return self._containers_of_member_type(instance)

    def __set__(self, instance, value):
        # Data-descriptor guard: reverse relationships are derived from modeling_obj_containers and are
        # read-only, exactly like the properties they replaced.
        raise AttributeError(
            f"{type(instance).__name__}.{self.attr_name} is a reverse relationship derived from "
            f"modeling_obj_containers and cannot be set directly.")


class ReverseLink(ReverseCollection):
    """Single-container variant of ReverseCollection: the one member_type instance holding this
    object, None when there is none; several containers raise a PermissionError."""

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        record_read_of_node(instance, self.attr_name)
        containers = self._containers_of_member_type(instance)
        if len(containers) > 1:
            raise PermissionError(
                f"{type(instance).__name__} object can only be associated with one {self.member_type_name} "
                f"object but {instance.name} is associated with "
                f"{[mod_obj.name for mod_obj in containers]}")
        return containers[0] if containers else None
