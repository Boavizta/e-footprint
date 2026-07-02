import unittest
from abc import abstractmethod
from collections import Counter
from unittest import TestCase

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import (
    CircularDependencyError, ReactiveSlot, ReverseCollection, ReverseLink, add_computed_attribute,
    computed_attribute, computed_dict, computed_slots, invalidate, record_calculus_dependency,
    record_structural_dependency, reverse_slots)
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class ReactiveCoreLeaf(ModelingObject):
    default_values = {"power": SourceValue(1 * u.W)}
    calculated_attributes = ["double_power"]

    holders = ReverseCollection("ReactiveCoreHolder")
    unknown_members = ReverseCollection("ReactiveCoreNeverImportedClass")
    single_holder = ReverseLink("ReactiveCoreHolder")

    def __init__(self, name, power: ExplainableQuantity):
        super().__init__(name)
        self.power = power.set_label("Power")
        self.double_power = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @computed_attribute
    def double_power(self):
        """Twice the power."""
        return (self.power * ExplainableQuantity(2 * u.dimensionless, "two")).set_label("Double power")


class ReactiveCoreHolder(ModelingObject):
    default_values = {}
    calculated_attributes = ["value_per_leaf"]

    def __init__(self, name, leaves: list):
        super().__init__(name)
        self.leaves = leaves
        self.value_per_leaf = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @computed_dict(keys="leaves")
    def value_per_leaf(self, leaf):
        """Per-leaf doubled power."""
        return (leaf.power * ExplainableQuantity(2 * u.dimensionless, "two")).set_label(f"Double {leaf.name}")


class ReactiveCoreSubHolder(ReactiveCoreHolder):
    @computed_dict(keys="leaves")
    def value_per_leaf(self, leaf):
        base = ReactiveCoreHolder.value_per_leaf(self, leaf)
        return (base * ExplainableQuantity(10 * u.dimensionless, "ten")).set_label(f"Boosted {leaf.name}")


class ReactiveCoreAbstractBase(ModelingObject):
    default_values = {}
    calculated_attributes = ["derived"]

    def __init__(self, name):
        super().__init__(name)
        self.derived = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @computed_attribute
    @abstractmethod
    def derived(self):
        pass


class ReactiveCoreConcreteChild(ReactiveCoreAbstractBase):
    @computed_attribute
    def derived(self):
        return ExplainableQuantity(1 * u.dimensionless, "one")


class TestComputedAttribute(TestCase):
    def setUp(self):
        self.leaf = ReactiveCoreLeaf("test leaf", SourceValue(3 * u.W))

    def test_set_name_registers_slot(self):
        """Test that declaring a computed attribute registers it in the class slot registry."""
        self.assertIn("double_power", computed_slots(ReactiveCoreLeaf))
        self.assertIsInstance(computed_slots(ReactiveCoreLeaf)["double_power"], computed_attribute)

    def test_class_level_access_returns_descriptor(self):
        """Test that class-level attribute access returns the descriptor with the getter docstring."""
        descriptor = ReactiveCoreLeaf.double_power
        self.assertIsInstance(descriptor, computed_attribute)
        self.assertEqual("Twice the power.", descriptor.__doc__)

    def test_synthesized_update_method_computes_and_stores_through_setattr(self):
        """Test that the synthesized update_<attr> method runs the getter and stores the result with the
        regular ModelingObject bookkeeping (container wiring)."""
        self.leaf.update_double_power()

        self.assertEqual(6, self.leaf.double_power.magnitude)
        self.assertIs(self.leaf, self.leaf.double_power.modeling_obj_container)
        self.assertEqual("double_power", self.leaf.double_power.attr_name_in_mod_obj_container)

    def test_synthesized_update_method_carries_getter_docstring(self):
        """Test that the synthesized update method exposes the getter docstring (doc-as-code consumers)."""
        self.assertEqual("Twice the power.", ReactiveCoreLeaf.update_double_power.__doc__)

    def test_uncomputed_attribute_read_mimics_missing_attribute(self):
        """Test that reading a computed attribute with no stored value raises AttributeError, as before."""
        del self.leaf.__dict__["double_power"]
        with self.assertRaises(AttributeError):
            _ = self.leaf.double_power
        self.assertIsNone(getattr(self.leaf, "double_power", None))

    def test_mismatched_declaration_name_raises(self):
        """Test that declaring a computed attribute under a name differing from its getter raises."""
        with self.assertRaises(ValueError):
            class Broken(ModelingObject):
                @property
                def modeling_objects_whose_attributes_depend_directly_on_me(self):
                    return []

                def _getter(self):
                    return None
                other_name = computed_attribute(_getter)

    def test_abstract_computed_attribute_keeps_class_abstract(self):
        """Test that an abstract computed attribute prevents instantiation until a subclass overrides it."""
        with self.assertRaises(TypeError):
            ReactiveCoreAbstractBase("abstract instance")
        child = ReactiveCoreConcreteChild("concrete instance")
        child.update_derived()
        self.assertEqual(1, child.derived.magnitude)

    def test_add_computed_attribute_on_existing_class(self):
        """Test attaching a dynamically generated computed attribute to an already-created class."""
        class DynamicTarget(ReactiveCoreLeaf):
            calculated_attributes = ReactiveCoreLeaf.calculated_attributes + ["tripled_power"]

            def __init__(self, name, power: ExplainableQuantity):
                super().__init__(name, power)
                self.tripled_power = EmptyExplainableObject()

        def tripled_power(self):
            """Thrice the power."""
            return (self.power * ExplainableQuantity(3 * u.dimensionless, "three")).set_label("Triple power")
        tripled_power.__name__ = "tripled_power"

        add_computed_attribute(DynamicTarget, "tripled_power", tripled_power)

        self.assertIn("tripled_power", computed_slots(DynamicTarget))
        obj = DynamicTarget("dynamic leaf", SourceValue(2 * u.W))
        obj.update_tripled_power()
        self.assertEqual(6, obj.tripled_power.magnitude)
        self.assertEqual("Thrice the power.", DynamicTarget.update_tripled_power.__doc__)


class TestComputedDict(TestCase):
    def setUp(self):
        self.leaf_1 = ReactiveCoreLeaf("dict leaf 1", SourceValue(1 * u.W))
        self.leaf_2 = ReactiveCoreLeaf("dict leaf 2", SourceValue(2 * u.W))
        self.holder = ReactiveCoreHolder("test holder", [self.leaf_1, self.leaf_2])

    def test_synthesized_whole_dict_update_resets_and_populates_per_key(self):
        """Test that update_<attr> resets the dict then populates one entry per key object."""
        self.holder.update_value_per_leaf()

        self.assertEqual([self.leaf_1, self.leaf_2], list(self.holder.value_per_leaf.keys()))
        self.assertEqual(2, self.holder.value_per_leaf[self.leaf_1].magnitude)
        self.assertEqual(4, self.holder.value_per_leaf[self.leaf_2].magnitude)
        self.assertIs(self.holder, self.holder.value_per_leaf.modeling_obj_container)

    def test_synthesized_element_update_refreshes_one_key(self):
        """Test that update_dict_element_in_<attr> recomputes a single key in place."""
        self.holder.update_value_per_leaf()
        self.leaf_1.__dict__["power"] = SourceValue(5 * u.W).set_label("Power")

        self.holder.update_dict_element_in_value_per_leaf(self.leaf_1)

        self.assertEqual(10, self.holder.value_per_leaf[self.leaf_1].magnitude)
        self.assertEqual(4, self.holder.value_per_leaf[self.leaf_2].magnitude)

    def test_whole_dict_update_dispatches_to_overriding_element_getter(self):
        """Test that the parent-synthesized whole-dict update dispatches per-key work through the MRO,
        so a subclass overriding only the per-key getter is honored."""
        sub_holder = ReactiveCoreSubHolder("sub holder", [self.leaf_1])

        ReactiveCoreHolder.update_value_per_leaf(sub_holder)

        self.assertEqual(20, sub_holder.value_per_leaf[self.leaf_1].magnitude)

    def test_overriding_getter_without_docstring_inherits_parent_description(self):
        """Test that an overriding getter without its own docstring keeps the inherited description."""
        self.assertEqual("Per-leaf doubled power.", computed_slots(ReactiveCoreSubHolder)["value_per_leaf"].__doc__)
        self.assertEqual("Per-leaf doubled power.", ReactiveCoreSubHolder.update_value_per_leaf.__doc__)


class TestReverseSlots(TestCase):
    def setUp(self):
        self.leaf = ReactiveCoreLeaf("reverse leaf", SourceValue(1 * u.W))

    def test_reverse_collection_registration(self):
        """Test that reverse-relationship declarations register in the class reverse-slot registry."""
        self.assertEqual({"holders", "unknown_members", "single_holder"}, set(reverse_slots(ReactiveCoreLeaf)))

    def test_reverse_collection_filters_containers_by_lazily_resolved_type(self):
        """Test that a string member type resolves lazily and filters modeling_obj_containers."""
        holder = ReactiveCoreHolder("reverse holder", [self.leaf])
        self.assertEqual([holder], self.leaf.holders)

    def test_reverse_collection_of_never_imported_class_is_empty(self):
        """Test that a member type matching no imported class yields an empty collection."""
        self.assertEqual([], self.leaf.unknown_members)

    def test_reverse_link_returns_single_container_or_none(self):
        """Test that ReverseLink returns the one typed container, or None without one."""
        self.assertIsNone(self.leaf.single_holder)
        holder = ReactiveCoreHolder("link holder", [self.leaf])
        self.assertIs(holder, self.leaf.single_holder)

    def test_reverse_link_with_several_containers_raises(self):
        """Test that ReverseLink raises a PermissionError when several typed containers hold the object."""
        ReactiveCoreHolder("link holder 1", [self.leaf])
        ReactiveCoreHolder("link holder 2", [self.leaf])
        with self.assertRaises(PermissionError):
            _ = self.leaf.single_holder

    def test_reverse_slots_cannot_be_assigned(self):
        """Test that storing a value under a reverse slot raises AttributeError, like the read-only
        properties these declarations replaced (a silent instance-dict shadow would corrupt the reverse
        lookup). object.__setattr__ is the storage path ModelingObject.__setattr__ bookkeeping uses."""
        holder = ReactiveCoreHolder("assignment holder", [self.leaf])
        with self.assertRaises(AttributeError):
            object.__setattr__(self.leaf, "holders", [holder])
        with self.assertRaises(AttributeError):
            object.__setattr__(self.leaf, "single_holder", holder)
        self.assertEqual([holder], self.leaf.holders)


def _source_slot(name: str, values: dict, compute_counts: Counter) -> ReactiveSlot:
    """Synthetic leaf slot reading its value from the shared values dict (tests mutate the dict then
    invalidate the slot, mimicking an input edit)."""
    def getter():
        compute_counts[name] += 1
        return values[name]
    return ReactiveSlot(name, getter)


def _summing_slot(name: str, dependencies: list, compute_counts: Counter) -> ReactiveSlot:
    """Synthetic computed slot summing its dependencies' values, recording one calculus edge per read."""
    def getter():
        compute_counts[name] += 1
        total = 0
        for dependency in dependencies:
            total += dependency.pull()
            record_calculus_dependency(dependency)
        return total
    return ReactiveSlot(name, getter)


class TestReactiveSlotLifecycle(TestCase):
    def setUp(self):
        self.compute_counts = Counter()
        self.values = {"a": 1}
        self.a = _source_slot("a", self.values, self.compute_counts)
        self.b = _summing_slot("b", [self.a], self.compute_counts)

    def test_pull_computes_caches_and_reuses(self):
        """Test that the first pull computes the slot and its void ancestors, and later pulls reuse the
        cached value without recomputing."""
        self.assertFalse(self.b.has_cached_value)

        self.assertEqual(1, self.b.pull())

        self.assertTrue(self.b.has_cached_value)
        self.assertEqual(1, self.b.pull())
        self.assertEqual(1, self.compute_counts["b"])
        self.assertEqual(1, self.compute_counts["a"])

    def test_pull_records_calculus_dependency_edges(self):
        """Test that reads recorded during a computation become the slot's calculus dependency edges,
        mirrored in the dependency's dependents index."""
        self.b.pull()

        self.assertEqual(frozenset([self.a]), self.b.calculus_dependencies)
        self.assertEqual(frozenset(), self.b.structural_dependencies)
        self.assertEqual(frozenset([self.b]), self.a.dependents)

    def test_structural_dependency_recording(self):
        """Test that relationship reads recorded during a computation become structural dependency edges."""
        membership = ReactiveSlot("membership", lambda: ["member 1", "member 2"])

        def getter():
            members = membership.pull()
            record_structural_dependency(membership)
            return len(members)
        member_count = ReactiveSlot("member_count", getter)

        self.assertEqual(2, member_count.pull())
        self.assertEqual(frozenset([membership]), member_count.structural_dependencies)
        self.assertEqual(frozenset(), member_count.calculus_dependencies)
        self.assertEqual(frozenset([member_count]), membership.dependents)

    def test_dependency_recording_outside_computation_is_noop(self):
        """Test that recording a dependency with no computation in progress records nothing."""
        record_calculus_dependency(self.a)
        record_structural_dependency(self.a)

        self.assertEqual(frozenset(), self.a.dependents)

    def test_pull_alone_records_no_implicit_edge(self):
        """Test that pulling a slot inside a computation records no edge by itself — edges come only
        from explicit record calls (in production, the ancestry walk and the relationship read hooks)."""
        untracked_reader = ReactiveSlot("untracked_reader", lambda: self.a.pull() + 1)

        self.assertEqual(2, untracked_reader.pull())

        self.assertEqual(frozenset(), untracked_reader.calculus_dependencies)
        self.assertEqual(frozenset(), self.a.dependents)

    def test_attach_cached_value_caches_without_computing(self):
        """Test that attaching a value caches it without running the getter."""
        self.b.attach_cached_value(42)

        self.assertEqual(42, self.b.pull())
        self.assertEqual(0, self.compute_counts["b"])


class TestInvalidationWave(TestCase):
    def setUp(self):
        self.compute_counts = Counter()
        self.values = {"a": 1}
        self.a = _source_slot("a", self.values, self.compute_counts)
        self.b = _summing_slot("b", [self.a], self.compute_counts)
        self.c = _summing_slot("c", [self.b], self.compute_counts)

    def test_invalidation_deletes_cached_values_downstream_without_computing(self):
        """Test that the deletion wave voids the written slot and all its transitive dependents, and
        never runs a getter."""
        self.c.pull()
        counts_before_wave = dict(self.compute_counts)

        visited = invalidate(self.a)

        self.assertEqual({self.a, self.b, self.c}, visited)
        for slot in (self.a, self.b, self.c):
            self.assertFalse(slot.has_cached_value)
        self.assertEqual(counts_before_wave, dict(self.compute_counts))

    def test_pull_after_invalidation_returns_fresh_value(self):
        """Test that pulling after an input edit plus invalidation recomputes from the new input."""
        self.assertEqual(1, self.c.pull())
        self.values["a"] = 5

        invalidate(self.a)

        self.assertEqual(5, self.c.pull())

    def test_invalidation_recomputes_only_affected_cone(self):
        """Test that pulling after invalidation recomputes only the void cone, reusing cached siblings."""
        self.values["d"] = 10
        d = _source_slot("d", self.values, self.compute_counts)
        e = _summing_slot("e", [d], self.compute_counts)
        f = _summing_slot("f", [self.b, e], self.compute_counts)
        self.assertEqual(11, f.pull())

        invalidate(self.a)
        self.values["a"] = 2
        self.assertEqual(12, f.pull())

        self.assertEqual(2, self.compute_counts["a"])
        self.assertEqual(2, self.compute_counts["b"])
        self.assertEqual(2, self.compute_counts["f"])
        self.assertEqual(1, self.compute_counts["d"])
        self.assertEqual(1, self.compute_counts["e"])

    def test_wave_marker_prunes_already_invalidated_subgraph(self):
        """Test that a wave reaching a slot already marked by a previous wave prunes there instead of
        re-traversing its dependents."""
        self.c.pull()

        first_wave = invalidate(self.a)
        second_wave_from_same_start = invalidate(self.a)
        wave_from_marked_intermediate = invalidate(self.b)

        self.assertEqual({self.a, self.b, self.c}, first_wave)
        self.assertEqual(set(), second_wave_from_same_start)
        self.assertEqual(set(), wave_from_marked_intermediate)

    def test_marker_clears_on_recompute_so_next_wave_traverses_again(self):
        """Test that recomputation clears the wave marker, so a later wave traverses the subgraph again."""
        self.c.pull()
        invalidate(self.a)
        self.c.pull()

        for slot in (self.a, self.b, self.c):
            self.assertFalse(slot.wave_passed)
        self.assertEqual({self.a, self.b, self.c}, invalidate(self.a))

    def test_diamond_wave_visits_each_slot_once(self):
        """Test that a wave through a diamond visits the join slot once, via within-wave marker dedup."""
        left = _summing_slot("left", [self.a], self.compute_counts)
        right = _summing_slot("right", [self.a], self.compute_counts)
        join = _summing_slot("join", [left, right], self.compute_counts)
        join.pull()

        self.assertEqual({self.a, left, right, join}, invalidate(self.a))

    def test_bulk_invalidation_of_several_slots_voids_the_union_of_their_cones(self):
        """Test that one wave started from several written slots visits the union of their dependent
        cones exactly once, voiding and marking a dependent shared by both start slots."""
        self.values["d"] = 10
        d = _source_slot("d", self.values, self.compute_counts)
        join = _summing_slot("join", [self.a, d], self.compute_counts)
        self.c.pull()
        self.assertEqual(11, join.pull())

        visited = invalidate(self.a, d)

        self.assertEqual({self.a, d, self.b, self.c, join}, visited)
        for slot in visited:
            self.assertFalse(slot.has_cached_value)
            self.assertTrue(slot.wave_passed)

    def test_failed_compute_clears_marker_so_next_wave_reaches_fallback_caching_dependent(self):
        """Test that a failed compute clears the wave marker: a dependent whose getter catches the
        failure and caches a fallback with an edge onto the failed slot is still reached by the next
        wave (a retained marker would prune the wave there and leave the fallback value stale)."""
        switches = {"fail": False}

        def fragile_getter():
            value = self.a.pull()
            record_calculus_dependency(self.a)
            if switches["fail"]:
                raise ValueError("synthetic computation failure")
            return value
        fragile = ReactiveSlot("fragile", fragile_getter)

        def catching_getter():
            try:
                value = fragile.pull()
            except ValueError:
                value = -1
            record_calculus_dependency(fragile)
            return value
        catching = ReactiveSlot("catching", catching_getter)

        self.assertEqual(1, catching.pull())
        invalidate(self.a)
        switches["fail"] = True
        self.assertEqual(-1, catching.pull())
        self.assertFalse(fragile.wave_passed)

        switches["fail"] = False
        self.values["a"] = 5
        visited = invalidate(self.a)

        self.assertEqual({self.a, fragile, catching}, visited)
        self.assertFalse(catching.has_cached_value)
        self.assertEqual(5, catching.pull())

    def test_invalidation_during_computation_raises_and_unwinds_stack(self):
        """Test that a getter triggering invalidation raises with the computing chain, and leaves the
        compute stack consistent for later pulls."""
        def writing_getter():
            invalidate(self.a)
            return 0
        writing_slot = ReactiveSlot("writing_slot", writing_getter)

        with self.assertRaises(RuntimeError) as context:
            writing_slot.pull()

        self.assertIn("writing_slot", str(context.exception))
        self.assertEqual(1, self.b.pull())


class TestDependencyEdgeRefresh(TestCase):
    def setUp(self):
        self.compute_counts = Counter()
        self.values = {"a": 1, "b": 2}
        self.a = _source_slot("a", self.values, self.compute_counts)
        self.b = _source_slot("b", self.values, self.compute_counts)

    def test_conditional_dependency_edges_refresh_on_recompute(self):
        """Test that recomputation replaces the dependency edges with exactly the new computation's
        reads, so a dependency read only under the old conditional branch stops invalidating the slot."""
        switches = {"read_a": True}

        def getter():
            source = self.a if switches["read_a"] else self.b
            value = source.pull()
            record_calculus_dependency(source)
            return value
        conditional = ReactiveSlot("conditional", getter)

        self.assertEqual(1, conditional.pull())
        self.assertEqual(frozenset([self.a]), conditional.calculus_dependencies)

        switches["read_a"] = False
        invalidate(conditional)
        self.assertEqual(2, conditional.pull())

        self.assertEqual(frozenset([self.b]), conditional.calculus_dependencies)
        self.assertEqual(frozenset(), self.a.dependents)
        self.assertEqual({self.a}, invalidate(self.a))
        self.assertTrue(conditional.has_cached_value)

    def test_edges_and_marker_survive_valuelessness(self):
        """Test that invalidation deletes the cached value but keeps the slot's topology edges."""
        summing = _summing_slot("summing", [self.a], self.compute_counts)
        summing.pull()

        invalidate(summing)

        self.assertFalse(summing.has_cached_value)
        self.assertTrue(summing.wave_passed)
        self.assertEqual(frozenset([self.a]), summing.calculus_dependencies)
        self.assertEqual(frozenset([summing]), self.a.dependents)

    def test_failed_recompute_keeps_previous_edges_and_leaves_slot_void_and_unmarked(self):
        """Test that a getter raising during recompute keeps the previous dependency edges (safe
        over-approximation), leaves the slot void so a later pull retries and refreshes them, and
        clears the wave marker so the next wave still traverses the slot."""
        switches = {"fail": False}

        def getter():
            if switches["fail"]:
                raise ValueError("synthetic computation failure")
            value = self.a.pull()
            record_calculus_dependency(self.a)
            return value
        fragile = ReactiveSlot("fragile", getter)
        fragile.pull()
        invalidate(fragile)

        switches["fail"] = True
        with self.assertRaises(ValueError):
            fragile.pull()

        self.assertFalse(fragile.has_cached_value)
        self.assertFalse(fragile.wave_passed)
        self.assertEqual(frozenset([self.a]), fragile.calculus_dependencies)
        self.assertEqual(frozenset([fragile]), self.a.dependents)

        switches["fail"] = False
        self.assertEqual(1, fragile.pull())
        self.assertTrue(fragile.has_cached_value)

    def test_dependency_kind_migrates_on_recompute(self):
        """Test that a dependency recorded structurally then arithmetically on recompute moves between
        edge kinds while keeping a single reverse edge."""
        switches = {"structural": True}

        def getter():
            value = self.a.pull()
            if switches["structural"]:
                record_structural_dependency(self.a)
            else:
                record_calculus_dependency(self.a)
            return value
        migrating = ReactiveSlot("migrating", getter)

        migrating.pull()
        self.assertEqual(frozenset([self.a]), migrating.structural_dependencies)
        self.assertEqual(frozenset(), migrating.calculus_dependencies)

        switches["structural"] = False
        invalidate(migrating)
        migrating.pull()

        self.assertEqual(frozenset(), migrating.structural_dependencies)
        self.assertEqual(frozenset([self.a]), migrating.calculus_dependencies)
        self.assertEqual(frozenset([migrating]), self.a.dependents)


class TestComputeStackSafety(TestCase):
    def setUp(self):
        self.compute_counts = Counter()
        self.values = {"a": 1}
        self.a = _source_slot("a", self.values, self.compute_counts)

    def test_cycle_detection_reports_readable_chain(self):
        """Test that a dependency cycle raises with the offending chain spelled out slot by slot."""
        slots = {}
        slots["x"] = ReactiveSlot("x", lambda: slots["y"].pull())
        slots["y"] = ReactiveSlot("y", lambda: slots["z"].pull())
        slots["z"] = ReactiveSlot("z", lambda: slots["x"].pull())

        with self.assertRaises(CircularDependencyError) as context:
            slots["x"].pull()

        self.assertIn("x -> y -> z -> x", str(context.exception))

    def test_direct_self_cycle_detected(self):
        """Test that a slot pulling itself raises with the minimal chain."""
        slots = {}
        slots["selfish"] = ReactiveSlot("selfish", lambda: slots["selfish"].pull())

        with self.assertRaises(CircularDependencyError) as context:
            slots["selfish"].pull()

        self.assertIn("selfish -> selfish", str(context.exception))

    def test_stack_unwinds_after_getter_exception(self):
        """Test that a raising getter leaves the compute stack empty, so later recordings and pulls are
        unaffected by the failed frame."""
        def failing_getter():
            raise ValueError("synthetic computation failure")
        failing = ReactiveSlot("failing", failing_getter)

        with self.assertRaises(ValueError):
            failing.pull()

        record_calculus_dependency(self.a)
        self.assertEqual(frozenset(), self.a.dependents)
        follow_up = _summing_slot("follow_up", [self.a], self.compute_counts)
        self.assertEqual(1, follow_up.pull())
        self.assertEqual(frozenset([self.a]), follow_up.calculus_dependencies)

    def test_stack_unwinds_after_cycle_error_and_fixed_cycle_computes(self):
        """Test that after a cycle error every frame is popped, and breaking the cycle lets the same
        slots compute normally."""
        switches = {"cycle": True}
        slots = {}
        slots["ping"] = ReactiveSlot("ping", lambda: slots["pong"].pull() + 1)
        slots["pong"] = ReactiveSlot("pong", lambda: slots["ping"].pull() + 1 if switches["cycle"] else 0)

        with self.assertRaises(CircularDependencyError):
            slots["ping"].pull()

        record_calculus_dependency(self.a)
        self.assertEqual(frozenset(), self.a.dependents)
        switches["cycle"] = False
        self.assertEqual(1, slots["ping"].pull())

    def test_nested_pull_attributes_edges_to_innermost_frame(self):
        """Test that dependencies recorded inside a nested computation attach to the slot being computed
        there, not to the outer one."""
        membership = ReactiveSlot("membership", lambda: ["member 1"])

        def inner_getter():
            members = membership.pull()
            record_structural_dependency(membership)
            return len(members)
        inner = ReactiveSlot("inner", inner_getter)

        def outer_getter():
            value = inner.pull()
            record_calculus_dependency(inner)
            return value
        outer = ReactiveSlot("outer", outer_getter)

        self.assertEqual(1, outer.pull())

        self.assertEqual(frozenset([inner]), outer.calculus_dependencies)
        self.assertEqual(frozenset(), outer.structural_dependencies)
        self.assertEqual(frozenset([membership]), inner.structural_dependencies)
        self.assertEqual(frozenset([inner]), membership.dependents)


class TestPartialReloadState(TestCase):
    def setUp(self):
        """Simulate a load from a minimal file: the output slot gets its stored value and the topology
        edges are rebuilt, while the intermediate stays valueless and unmarked."""
        self.compute_counts = Counter()
        self.values = {"a": 1}
        self.a = _source_slot("a", self.values, self.compute_counts)
        self.b = _summing_slot("b", [self.a], self.compute_counts)
        self.c = _summing_slot("c", [self.b], self.compute_counts)
        self.c.attach_cached_value(10)
        self.c.replace_dependencies(calculus_dependencies={self.b})
        self.b.replace_dependencies(calculus_dependencies={self.a})

    def test_cached_slot_below_void_ancestors_reads_without_computing(self):
        """Test that pulling a cached slot returns its value directly even when its ancestors are void."""
        self.assertFalse(self.b.has_cached_value)

        self.assertEqual(10, self.c.pull())

        self.assertEqual(0, sum(self.compute_counts.values()))

    def test_wave_traverses_void_unmarked_intermediates_to_reach_cached_descendants(self):
        """Test that the deletion wave crosses valueless, unmarked intermediates so cached slots below
        them are still invalidated."""
        visited = invalidate(self.a)

        self.assertEqual({self.a, self.b, self.c}, visited)
        self.assertFalse(self.c.has_cached_value)

    def test_pull_reconstructs_through_void_ancestors_after_invalidation(self):
        """Test that after an edit invalidates a partially-loaded graph, pulling the output recomputes
        the whole void chain from the inputs and refreshes its edges."""
        self.values["a"] = 3
        invalidate(self.a)

        self.assertEqual(3, self.c.pull())

        self.assertEqual({"a": 1, "b": 1, "c": 1}, dict(self.compute_counts))
        self.assertEqual(frozenset([self.b]), self.c.calculus_dependencies)
        self.assertFalse(self.c.wave_passed)


def _all_registered_classes():
    from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
    # The from-config Boavizta builders are not part of ALL_EFOOTPRINT_CLASSES but carry converted
    # calculated attributes, so the transition-period checks must cover them too.
    from efootprint.builders.hardware.boavizta_server_from_config import (
        BoaviztaServerFromConfig, BoaviztaStorageFromConfig)
    return ALL_EFOOTPRINT_CLASSES + [BoaviztaServerFromConfig, BoaviztaStorageFromConfig]


class TestRegistryMatchesCalculatedAttributes(TestCase):
    def test_every_calculated_attribute_is_a_declared_computed_slot(self):
        """Test that per class, the calculated_attributes list and the computed-slot registry agree —
        a conversion-omission detector for the transition period where both coexist."""
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage

        # EdgeStorage deliberately drops these inherited EdgeComponent attributes from its
        # calculated_attributes (it deletes the corresponding instance state in __init__).
        deliberate_drops = {EdgeStorage: {"power", "idle_power"}}

        for cls in _all_registered_classes():
            declared = set(computed_slots(cls))
            expected_drops = deliberate_drops.get(cls, set())
            self.assertEqual(
                set(cls.calculated_attributes), declared - expected_drops,
                f"calculated_attributes and computed-slot registry diverge for {cls.__name__}")

    def test_every_reverse_slot_member_type_resolves(self):
        """Test that every reverse slot declared on a production class resolves its member-type name to a
        real ModelingObject subclass once all classes are imported — a typo'd name would otherwise
        silently yield an empty collection forever."""
        for cls in _all_registered_classes():
            for name, slot in reverse_slots(cls).items():
                self.assertIsNotNone(
                    slot._resolve_member_type(),
                    f"{cls.__name__}.{name} declares member type {slot.member_type_name}, "
                    f"which matches no ModelingObject subclass")


if __name__ == "__main__":
    unittest.main()
