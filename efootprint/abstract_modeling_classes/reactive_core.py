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
interface). The descriptors do not drive the reactive engine yet: the computation engine still runs
in an eager shim mode where values are computed eagerly by the push-based machinery
(``calculated_attributes`` ordering, ``ModelingUpdate`` chains), which expects one ``update_<attr>``
method per computed attribute (plus ``update_dict_element_in_<attr>`` for dict attributes). Each
descriptor synthesizes those methods from its getter at class-creation time (``__set_name__``): call
the getter, store the result through the regular ``ModelingObject.__setattr__`` bookkeeping. Computed
values are therefore stored as plain instance attributes exactly as before, and always shadow these
(non-data) descriptors on read; ``__get__`` only fires when no value has been stored yet and mimics a
missing attribute.
"""
import contextvars
from typing import Type

_VOID = object()

_compute_stack: contextvars.ContextVar[tuple] = contextvars.ContextVar("reactive_compute_stack", default=())


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

    def __init__(self, name: str, getter):
        self.name = name
        self.getter = getter
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
        self._calculus_dependencies = set(calculus_dependencies)
        self._structural_dependencies = set(structural_dependencies)

    def attach_cached_value(self, value):
        """Cache a value directly — a computation result, or a trusted stored value at load time.
        Clears the wave marker: a freshly cached slot must be reachable by the next deletion wave."""
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
        slot._value = _VOID
        visited.add(slot)
        work.extend(slot._dependents)
    return visited


def _register_slot(registry_name: str, owner: type, name: str, descriptor):
    if registry_name not in owner.__dict__:
        setattr(owner, registry_name, {})
    owner.__dict__[registry_name][name] = descriptor


def _collect_slots(registry_name: str, cls: type) -> dict:
    slots = {}
    for klass in reversed(cls.__mro__):
        slots.update(klass.__dict__.get(registry_name, {}))
    return slots


def computed_slots(cls: type) -> dict:
    """All computed-attribute descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_computed_slots", cls)


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


class computed_attribute:
    """Non-data descriptor declaring a computed attribute from a getter.

    The getter takes only self and returns the attribute's new value. Calling the descriptor as
    ``ParentClass.<attr>(self)`` runs the parent's getter, mirroring unbound-method syntax for
    overriding getters that refine an inherited calculation.
    """

    def __init__(self, getter):
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
        self._synthesize_update_methods(owner, name)

    def _synthesize_update_methods(self, owner, name):
        getter = self.getter

        def update(instance):
            setattr(instance, name, getter(instance))

        update.__name__ = f"update_{name}"
        update.__qualname__ = f"{owner.__qualname__}.update_{name}"
        update.__doc__ = self.__doc__
        setattr(owner, f"update_{name}", update)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(f"{type(instance).__name__}.{self.attr_name} has not been computed yet")

    def __call__(self, instance, *args):
        return self.getter(instance, *args)


class _ComputedDictAttribute(computed_attribute):
    """Non-data descriptor declaring a computed ExplainableObjectDict attribute.

    The getter takes self plus one key object and returns the value for that key; the key set is the
    collection read from the ``keys`` attribute of the owning object. The synthesized whole-dict
    update resets the dict then delegates per key through ``update_dict_element_in_<attr>`` so that
    subclasses overriding only the per-key getter are dispatched to, exactly as the former
    hand-written orchestrators did.
    """

    def __init__(self, getter, keys: str):
        super().__init__(getter)
        self.keys = keys

    def _synthesize_update_methods(self, owner, name):
        getter = self.getter
        keys_attr = self.keys

        def update_dict_element(instance, key_obj):
            getattr(instance, name)[key_obj] = getter(instance, key_obj)

        update_dict_element.__name__ = f"update_dict_element_in_{name}"
        update_dict_element.__qualname__ = f"{owner.__qualname__}.update_dict_element_in_{name}"
        setattr(owner, f"update_dict_element_in_{name}", update_dict_element)

        def update(instance):
            from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
            setattr(instance, name, ExplainableObjectDict())
            element_update = getattr(instance, f"update_dict_element_in_{name}")
            for key_obj in getattr(instance, keys_attr):
                element_update(key_obj)

        update.__name__ = f"update_{name}"
        update.__qualname__ = f"{owner.__qualname__}.update_{name}"
        update.__doc__ = self.__doc__
        setattr(owner, f"update_{name}", update)


def computed_dict(keys: str):
    """Decorator declaring a computed dict attribute keyed by the objects listed by the ``keys``
    attribute name, e.g. ``@computed_dict(keys="usage_patterns")``."""
    def decorator(getter):
        return _ComputedDictAttribute(getter, keys)
    return decorator


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
        return [mod_obj for mod_obj in instance.modeling_obj_containers if isinstance(mod_obj, member_type)]

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
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
        containers = self._containers_of_member_type(instance)
        if len(containers) > 1:
            raise PermissionError(
                f"{type(instance).__name__} object can only be associated with one {self.member_type_name} "
                f"object but {instance.name} is associated with "
                f"{[mod_obj.name for mod_obj in containers]}")
        return containers[0] if containers else None
