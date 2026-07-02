import unittest
from abc import abstractmethod
from unittest import TestCase

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import (
    ReverseCollection, ReverseLink, add_computed_attribute, computed_attribute, computed_dict, computed_slots,
    reverse_slots)
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


class TestRegistryMatchesCalculatedAttributes(TestCase):
    def test_every_calculated_attribute_is_a_declared_computed_slot(self):
        """Test that per class, the calculated_attributes list and the computed-slot registry agree —
        a conversion-omission detector for the transition period where both coexist."""
        from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage

        # EdgeStorage deliberately drops these inherited EdgeComponent attributes from its
        # calculated_attributes (it deletes the corresponding instance state in __init__).
        deliberate_drops = {EdgeStorage: {"power", "idle_power"}}

        for cls in ALL_EFOOTPRINT_CLASSES:
            declared = set(computed_slots(cls))
            expected_drops = deliberate_drops.get(cls, set())
            self.assertEqual(
                set(cls.calculated_attributes), declared - expected_drops,
                f"calculated_attributes and computed-slot registry diverge for {cls.__name__}")


if __name__ == "__main__":
    unittest.main()
