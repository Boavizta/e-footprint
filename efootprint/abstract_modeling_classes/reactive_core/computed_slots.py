"""Descriptors and declaration registries for reactive computed modeling attributes."""

from enum import StrEnum

from .graph import (
    ReactiveSlot, computation_in_progress, instance_slot_registry, peek_instance_slot_registry,
    record_calculus_dependency,
    record_calculus_edges_from_ancestry, record_calculus_edges_from_value_structure,
    record_structural_dependency,
)

# MRO slot collection is on hot paths (every load-time slot resolution, every calculated_attributes
# read): memoized per (registry, class), invalidated by any slot registration (which only happens at
# class-definition time or through add_computed_attribute).
_slot_collection_cache = {}


class ComputationPurpose(StrEnum):
    """Purpose declared only on meaningful computation outputs; intermediate membership is derived
    from the realized dependency graph rather than repeated on every descriptor."""

    FOOTPRINT = "footprint"


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
    marks a slot whose getter can intentionally reject an invalid state: guard slots eagerly recompute
    whenever an update invalidates them, so invalid edits are rejected at update time even when that
    slot lies outside the selected eager-output cone. ``purposes`` marks meaningful output roots;
    intermediate membership is derived from the materialized dependency graph.
    """

    def __init__(self, getter=None, *, serialize=False, guard=False, purposes=()):
        self.serialize = serialize
        self.guard = guard
        self.purposes = frozenset(ComputationPurpose(purpose) for purpose in purposes)
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

    # Ordinary computed values are detached from their owner when their cached slot value is dropped.
    _on_value_dropped = staticmethod(_release_value)

    def slot(self, instance) -> ReactiveSlot:
        registry = instance_slot_registry(instance)
        slot = registry.get(self.attr_name)
        if slot is None:
            slot = ReactiveSlot(
                f"{self.attr_name} of {getattr(instance, 'id', instance)}", on_value_dropped=self._on_value_dropped,
                diagnostic_name=f"{type(instance).__name__}.{self.attr_name}")
            slot.getter = self._make_compute_closure(instance, slot)
            slot.guard = self.guard
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
        slot = peek_instance_slot_registry(instance).get(self.attr_name)
        if slot is not None and slot.has_cached_value:
            return slot._value
        return None

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        slot = self.slot(instance)
        if computation_in_progress():
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
        slot = peek_instance_slot_registry(instance).get(self.attr_name)
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
    collection read from the ``keys`` attribute of the owning object. Keys are normally ModelingObjects,
    but may be stable frozen value coordinates with a derived ``id``. The attribute resolves to two
    slot layers: a key-set node whose getter reads the key collection and syncs a persistent
    ExplainableObjectDict facade (readers of the whole dict depend on it, so key-set changes reach
    them), and one sub-slot per key holding that key's value (per-key granularity: a value change
    invalidates only its own readers). The facade's read methods pull the slots, so it is always a
    live view.

    Declared as ``@computed_dict(keys="usage_patterns")``. ``guard=True`` marks a dict whose element
    getters can intentionally reject an invalid state (see ``computed_attribute``): its key-set node
    and sub-slots eagerly recompute when invalidated. ``serialize=True`` persists the materialized
    entries under the minimal serialization contract.
    """

    # The persistent dict facade remains attached to its owner across key-set invalidations.
    _on_value_dropped = None

    def __init__(self, keys: str, guard=False, serialize=False, purposes=()):
        # Like parametrized computed_attribute, decorator construction precedes getter binding:
        # @computed_dict(keys="jobs") builds this descriptor, then inherited __call__ receives the
        # decorated getter and returns the now-bound descriptor for installation on the class.
        super().__init__(guard=guard, serialize=serialize, purposes=purposes)
        self.keys = keys

    def slot(self, instance) -> ReactiveSlot:
        slot = super().slot(instance)
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
            stale_slot = registry.pop((self.attr_name, stale_key))
            # This element no longer belongs to the model's validation boundary. Clearing the
            # existing policy flag also keeps a pre-pruning invalidation set from pulling it.
            stale_slot.guard = False
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
                on_value_dropped=_release_value, diagnostic_name=f"{type(instance).__name__}.{self.attr_name}")
            slot.getter = self._make_element_compute_closure(instance, key, slot)
            slot.guard = self.guard
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
        self.facade(instance)._set_entry_passively(key, value)
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
        registry = peek_instance_slot_registry(instance)
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
        if computation_in_progress():
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
        if slot.key_set_binding is None:
            continue
        descriptor, instance = slot.key_set_binding
        descriptor.discard_stale_keys(instance, list(getattr(instance, descriptor.keys)))


class computed_structure:
    """Descriptor declaring one reactively cached arbitrary structure.

    The result is held raw in one slot rather than attached to the owner's explainability bookkeeping,
    so getters may return dicts, tuples, dataclass instances, scalars, or nested combinations. The
    engine recursively records calculus edges from explainables within the returned structure, in
    addition to reads recorded while the getter ran.

    Declared bare (``@computed_structure``) or parametrized. ``serialize=True`` persists a materialized
    value; ``transient=True`` marks an intermediate that an owning calculation may explicitly evict after
    reducing it. Eviction drops only the value and preserves graph edges, so cached descendants still
    invalidate correctly. Serialized structures must be JSON-native because they bypass explainable
    serialization."""

    def __init__(self, getter=None, *, serialize=False, transient=False):
        if serialize and transient:
            raise ValueError("A computed structure cannot be both serialized and transient")
        self.serialize = serialize
        self.transient = transient
        self.getter = None
        if getter is not None:
            self._bind_getter(getter)

    def _bind_getter(self, getter):
        self.getter = getter
        self.attr_name = getter.__name__
        self.__doc__ = getter.__doc__

    def __call__(self, getter):
        if self.getter is not None:
            raise TypeError(f"Computed structure {self.attr_name} is not callable")
        self._bind_getter(getter)
        return self

    def __set_name__(self, owner, name):
        if name != self.getter.__name__:
            raise ValueError(
                f"Computed structure declared as {name} but its getter is named {self.getter.__name__}")
        _register_slot("_declared_computed_structures", owner, name, self)

    def slot(self, instance) -> ReactiveSlot:
        registry = instance_slot_registry(instance)
        slot = registry.get(self.attr_name)
        if slot is None:
            slot = ReactiveSlot(
                f"{self.attr_name} of {getattr(instance, 'id', instance)}",
                diagnostic_name=f"{type(instance).__name__}.{self.attr_name}")
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
        """Store a value without computing — used by loading and test pinning."""
        self.slot(instance).attach_cached_value(value)

    def peek(self, instance):
        """The cached value, or None when the slot is void — never computes (save paths)."""
        slot = peek_instance_slot_registry(instance).get(self.attr_name)
        if slot is not None and slot.has_cached_value:
            return slot._value
        return None

    def evict_cached_value(self, instance):
        """Drop this structure's cached value while preserving its dependency edges."""
        slot = peek_instance_slot_registry(instance).get(self.attr_name)
        if slot is not None:
            slot._drop_value()

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        slot = self.slot(instance)
        if computation_in_progress():
            record_calculus_dependency(slot)
        return slot.pull()

    def __set__(self, instance, value):
        raise AttributeError(
            f"{self.attr_name} is a computed structure of {type(instance).__name__} and cannot be assigned: "
            f"change the inputs it derives from instead, or pin it in tests with "
            f"tests.utils.patch_attribute / the descriptor's attach_cached_value.")


def computed_structures(cls: type) -> dict:
    """All computed-structure descriptors visible on cls, with the most-derived declaration winning."""
    return _collect_slots("_declared_computed_structures", cls)


def evict_transient_structures(instance):
    """Drop materialized transient structures without invalidating their cached dependents."""
    for descriptor in computed_structures(type(instance)).values():
        if descriptor.transient:
            descriptor.evict_cached_value(instance)


def computation_slots_for_purpose(instance, purpose: ComputationPurpose) -> frozenset[ReactiveSlot]:
    """Materialized computing slots upstream of this instance's outputs tagged with ``purpose``.

    The query follows the actual per-instance dependency topology, including materialized computed-dict
    element slots. A declared but never-computed output has no runtime graph membership and is therefore
    absent; slots with no getter are input and relationship nodes, not computations, and are traversed but
    not returned.
    """
    purpose = ComputationPurpose(purpose)
    tagged_names = {
        name for name, descriptor in computed_slots(type(instance)).items() if purpose in descriptor.purposes
    }
    roots = []
    for registry_key, slot in peek_instance_slot_registry(instance).items():
        attr_name = registry_key[0] if isinstance(registry_key, tuple) else registry_key
        if attr_name not in tagged_names or slot.getter is None:
            continue
        if slot.has_cached_value or slot.calculus_dependencies or slot.structural_dependencies:
            roots.append(slot)

    visited = set()
    computations = set()
    work = roots
    while work:
        slot = work.pop()
        if slot in visited:
            continue
        visited.add(slot)
        if slot.getter is not None:
            computations.add(slot)
        work.extend(slot.calculus_dependencies)
        work.extend(slot.structural_dependencies)
    return frozenset(computations)


def serialized_slots(cls: type) -> dict:
    """All serialize-flagged slot descriptors visible on cls, name -> descriptor —
    the single source of truth for which slots persist under the minimal serialization contract."""
    return {name: descriptor for name, descriptor in {**computed_slots(cls), **computed_structures(cls)}.items()
            if descriptor.serialize}


def add_computed_attribute(cls: type, name: str, getter):
    """Attach a computed attribute to an already-created class (for dynamically generated getters,
    where ``__set_name__`` cannot fire automatically)."""
    descriptor = computed_attribute(getter)
    setattr(cls, name, descriptor)
    descriptor.__set_name__(cls, name)
