import unittest
from unittest import TestCase

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    ExplainableObjectDict, WeightedExplainableObjectDict)
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from tests.utils import create_mod_obj_mock
from tests.utils import recompute_attribute


def make_group(name):
    """Create an empty edge-device group."""
    return EdgeDeviceGroup(name)


class TestEdgeDeviceGroupInit(TestCase):

    def test_init_defaults(self):
        group = make_group("My Group")
        self.assertEqual("My Group", group.name)
        self.assertIsInstance(group.sub_group_counts, ExplainableObjectDict)
        self.assertIsInstance(group.edge_device_counts, ExplainableObjectDict)
        # A group with no parents is a root group: reading computes an effective count of 1.
        self.assertEqual(1, group.effective_nb_of_units_within_root.magnitude)

    def test_init_with_provided_empty_dicts(self):
        sub_groups = ExplainableObjectDict()
        devices = ExplainableObjectDict()
        group = EdgeDeviceGroup("G", sub_group_counts=sub_groups, edge_device_counts=devices)
        self.assertIsInstance(group.sub_group_counts, ExplainableObjectDict)
        self.assertIsInstance(group.edge_device_counts, ExplainableObjectDict)
        self.assertEqual({}, group.sub_group_counts)
        self.assertEqual({}, group.edge_device_counts)




class TestEdgeDeviceGroupParentGroups(TestCase):

    def test_standalone_group_has_no_parents(self):
        group = make_group("Standalone")
        self.assertEqual([], group.parent_groups)

    def test_single_parent_group(self):
        parent = make_group("Parent")
        child = make_group("Child")
        parent.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        result = child.parent_groups
        self.assertEqual([parent], result)

    def test_two_parent_groups(self):
        parent_a = make_group("Parent A")
        parent_b = make_group("Parent B")
        child = make_group("Child")
        parent_a.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        parent_b.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        result = child.parent_groups
        self.assertIn(parent_a, result)
        self.assertIn(parent_b, result)
        self.assertEqual(2, len(result))


class TestEdgeDeviceGroupFindRootGroups(TestCase):

    def test_root_group_returns_self(self):
        root = make_group("Root")
        result = root._find_root_groups()
        self.assertEqual([root], result)

    def test_child_returns_parent_root(self):
        root = make_group("Root")
        child = make_group("Child")
        root.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        result = child._find_root_groups()
        self.assertEqual([root], result)

    def test_grandchild_returns_ultimate_root(self):
        root = make_group("Root")
        middle = make_group("Middle")
        grandchild = make_group("Grandchild")
        root.sub_group_counts[middle] = SourceValue(2 * u.dimensionless)
        middle.sub_group_counts[grandchild] = SourceValue(3 * u.dimensionless)
        result = grandchild._find_root_groups()
        self.assertEqual([root], result)

    def test_child_with_two_root_parents(self):
        root_a = make_group("Root A")
        root_b = make_group("Root B")
        child = make_group("Child")
        root_a.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        root_b.sub_group_counts[child] = SourceValue(1 * u.dimensionless)
        result = child._find_root_groups()
        self.assertIn(root_a, result)
        self.assertIn(root_b, result)
        self.assertEqual(2, len(result))

    def test_roots_are_deduplicated_for_diamond_hierarchy(self):
        """When a shared root is reachable through two paths, it appears only once."""
        root = make_group("Root")
        left = make_group("Left")
        right = make_group("Right")
        child = make_group("Child")
        root.sub_group_counts[left] = SourceValue(1 * u.dimensionless)
        root.sub_group_counts[right] = SourceValue(1 * u.dimensionless)
        left.sub_group_counts[child] = SourceValue(1 * u.dimensionless)
        right.sub_group_counts[child] = SourceValue(1 * u.dimensionless)
        result = child._find_root_groups()
        self.assertEqual([root], result)


class TestEdgeDeviceGroupCountsValidation(TestCase):
    """The dimensionless / non-negative count invariant is enforced by WeightedExplainableObjectDict.__setitem__,
    which every mutation path (construction, set, ModelingUpdate value replacement, JSON load) routes through."""

    def setUp(self):
        self.group = make_group("Group")

    def test_valid_dimensionless_count(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(5 * u.dimensionless)

    def test_zero_count_is_valid(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(0 * u.dimensionless)

    def test_non_dimensionless_count_raises(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        with self.assertRaises(ValueError):
            self.group.edge_device_counts[mock_device] = SourceValue(5 * u.kg)

    def test_negative_count_raises(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        with self.assertRaises(ValueError):
            self.group.edge_device_counts[mock_device] = SourceValue(-1 * u.dimensionless)

    def test_sub_group_non_dimensionless_raises(self):
        child = make_group("Child")
        with self.assertRaises(ValueError):
            self.group.sub_group_counts[child] = SourceValue(3 * u.kg)

    def test_sub_group_valid_count(self):
        child = make_group("Child")
        self.group.sub_group_counts[child] = SourceValue(3 * u.dimensionless)


class TestEdgeDeviceGroupNoCycleValidation(TestCase):

    def test_no_cycle_passes_for_simple_hierarchy(self):
        root = make_group("Root")
        child = make_group("Child")
        root.sub_group_counts[child] = SourceValue(1 * u.dimensionless)
        recompute_attribute(root, "no_cycle_validation")
        recompute_attribute(child, "no_cycle_validation")

    def test_direct_self_reference_raises(self):
        group = make_group("Group")
        with self.assertRaises(ValueError) as ctx:
            group.sub_group_counts[group] = SourceValue(1 * u.dimensionless)
        self.assertIn("Cycle detected", str(ctx.exception))
        self.assertEqual({}, group.sub_group_counts)

    def test_two_node_cycle_raises(self):
        a = make_group("A")
        b = make_group("B")
        a.sub_group_counts[b] = SourceValue(1 * u.dimensionless)
        with self.assertRaises(ValueError):
            b.sub_group_counts[a] = SourceValue(1 * u.dimensionless)
        self.assertEqual({}, b.sub_group_counts)

    def test_three_node_cycle_raises(self):
        a = make_group("A")
        b = make_group("B")
        c = make_group("C")
        a.sub_group_counts[b] = SourceValue(1 * u.dimensionless)
        b.sub_group_counts[c] = SourceValue(1 * u.dimensionless)
        with self.assertRaises(ValueError):
            c.sub_group_counts[a] = SourceValue(1 * u.dimensionless)
        self.assertEqual({}, c.sub_group_counts)

    def test_diamond_without_cycle_passes(self):
        root = make_group("Root")
        left = make_group("Left")
        right = make_group("Right")
        shared = make_group("Shared")
        root.sub_group_counts[left] = SourceValue(1 * u.dimensionless)
        root.sub_group_counts[right] = SourceValue(1 * u.dimensionless)
        left.sub_group_counts[shared] = SourceValue(1 * u.dimensionless)
        right.sub_group_counts[shared] = SourceValue(1 * u.dimensionless)
        for g in [root, left, right, shared]:
            recompute_attribute(g, "no_cycle_validation")


class TestEdgeDeviceGroupUpdateEffectiveNbOfUnits(TestCase):

    def test_root_group_effective_nb_is_one(self):
        root = make_group("Root")
        recompute_attribute(root, "effective_nb_of_units_within_root")
        self.assertAlmostEqual(1.0, root.effective_nb_of_units_within_root.value.magnitude)

    def test_root_label_mentions_root(self):
        root = make_group("Root")
        recompute_attribute(root, "effective_nb_of_units_within_root")
        self.assertIn("root", root.effective_nb_of_units_within_root.label.lower())

    def test_child_with_single_parent_count_3(self):
        parent = make_group("Parent")
        child = make_group("Child")
        parent.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        recompute_attribute(parent, "effective_nb_of_units_within_root")
        recompute_attribute(child, "effective_nb_of_units_within_root")
        self.assertAlmostEqual(3.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_grandchild_effective_nb_is_product(self):
        root = make_group("Root")
        middle = make_group("Middle")
        grandchild = make_group("Grandchild")
        root.sub_group_counts[middle] = SourceValue(2 * u.dimensionless)
        middle.sub_group_counts[grandchild] = SourceValue(5 * u.dimensionless)
        recompute_attribute(root, "effective_nb_of_units_within_root")
        recompute_attribute(middle, "effective_nb_of_units_within_root")
        recompute_attribute(grandchild, "effective_nb_of_units_within_root")
        self.assertAlmostEqual(10.0, grandchild.effective_nb_of_units_within_root.value.magnitude)

    def test_child_with_two_parents_sums_contributions(self):
        """Shared sub-group belonging to two roots gets contribution from both."""
        root_a = make_group("Root A")
        root_b = make_group("Root B")
        child = make_group("Child")
        root_a.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        root_b.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        recompute_attribute(root_a, "effective_nb_of_units_within_root")
        recompute_attribute(root_b, "effective_nb_of_units_within_root")
        recompute_attribute(child, "effective_nb_of_units_within_root")
        # 2 * 1 + 3 * 1 = 5
        self.assertAlmostEqual(5.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_effective_nb_is_dimensionless(self):
        root = make_group("Root")
        recompute_attribute(root, "effective_nb_of_units_within_root")
        self.assertTrue(root.effective_nb_of_units_within_root.value.check("[]"))


class TestEdgeDeviceGroupConstructorSugar(TestCase):

    def test_init_with_list_and_plain_number_sugar(self):
        sub_group = make_group("Sub group for sugar")
        mock_device = create_mod_obj_mock(EdgeDevice, "Device for sugar")
        group = EdgeDeviceGroup(
            "Group with sugar", sub_group_counts=[sub_group], edge_device_counts={mock_device: 3})

        self.assertIsInstance(group.sub_group_counts, ExplainableObjectDict)
        self.assertAlmostEqual(1.0, group.sub_group_counts[sub_group].value.magnitude)
        self.assertAlmostEqual(3.0, group.edge_device_counts[mock_device].value.magnitude)

    def test_count_dicts_are_weighted_dicts_enforcing_invariants_on_mutation(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Device with invalid count update")
        group = EdgeDeviceGroup("Group with invalid mutation", edge_device_counts={mock_device: 1})

        self.assertIsInstance(group.edge_device_counts, WeightedExplainableObjectDict)
        with self.assertRaises(ValueError) as ctx:
            group.edge_device_counts[mock_device] = SourceValue(-2 * u.dimensionless)
        self.assertIn("non-negative", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            group.edge_device_counts[mock_device] = SourceValue(3 * u.kg)
        self.assertIn("dimensionless", str(ctx.exception))

    def test_list_sugar_accumulates_duplicates(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Duplicated device")
        group = EdgeDeviceGroup("Group with duplicate sugar", edge_device_counts=[mock_device, mock_device])

        self.assertAlmostEqual(2.0, group.edge_device_counts[mock_device].value.magnitude)

    def test_plain_number_sugar_participates_in_recomputation(self):
        """A device registered through constructor sugar is recomputed by later triggered dict mutations,
        exactly like a device registered through a post-construction setitem."""
        sugar_device = EdgeDevice.from_defaults("Device registered through sugar", components=[])
        other_device = EdgeDevice.from_defaults("Device added after construction", components=[])
        group = EdgeDeviceGroup("Group with sugar recomputation", edge_device_counts={sugar_device: 3})

        group.edge_device_counts[other_device] = SourceValue(2 * u.dimensionless)

        self.assertAlmostEqual(3.0, sugar_device.total_nb_of_units.value.magnitude)
        self.assertAlmostEqual(2.0, other_device.total_nb_of_units.value.magnitude)


class TestEdgeDeviceGroupTriggeredCountUpdates(TestCase):

    def test_existing_edge_device_count_update_recomputes_child_device_total(self):
        root = EdgeDeviceGroup("Root group for existing count update")
        floor = EdgeDeviceGroup("Floor group for existing count update")
        device = EdgeDevice.from_defaults("Edge device for existing count update", components=[])

        root.sub_group_counts[floor] = SourceValue(3 * u.dimensionless)
        floor.edge_device_counts[device] = SourceValue(4 * u.dimensionless)

        self.assertAlmostEqual(12.0, device.total_nb_of_units.value.magnitude)

        floor.edge_device_counts[device] = SourceValue(5 * u.dimensionless)

        self.assertAlmostEqual(5.0, floor.edge_device_counts[device].value.magnitude)
        self.assertAlmostEqual(15.0, device.total_nb_of_units.value.magnitude)


class TestEdgeDeviceGroupSelfDelete(TestCase):

    def test_self_delete_raises_when_group_is_referenced_by_parent_group(self):
        """Test self_delete raises when another group references this group."""
        parent = EdgeDeviceGroup("Parent group")
        child = EdgeDeviceGroup("Child group")
        parent.sub_group_counts[child] = SourceValue(2 * u.dimensionless)

        with self.assertRaises(PermissionError) as context:
            child.self_delete()

        self.assertIn("Parent group", str(context.exception))

    def test_self_delete_recomputes_child_group_when_clearing_sub_groups(self):
        """Test self_delete clears sub_group_counts before deleting the root group."""
        root = EdgeDeviceGroup("Root group")
        child = EdgeDeviceGroup("Child group for deletion")
        root.sub_group_counts[child] = SourceValue(2 * u.dimensionless)

        self.assertAlmostEqual(2.0, child.effective_nb_of_units_within_root.value.magnitude)

        root.self_delete()

        self.assertEqual({}, root.sub_group_counts)
        self.assertEqual([], child.parent_groups)
        self.assertAlmostEqual(1.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_self_delete_recomputes_edge_devices_when_clearing_edge_device_counts(self):
        """Test self_delete clears edge_device_counts before deleting the root group."""
        group = EdgeDeviceGroup("Device group for deletion")
        edge_device = EdgeDevice.from_defaults("Device referenced by deleted group", components=[])
        group.edge_device_counts[edge_device] = SourceValue(3 * u.dimensionless)
        self.assertAlmostEqual(3.0, edge_device.total_nb_of_units.value.magnitude)

        group.self_delete()

        self.assertEqual({}, group.edge_device_counts)
        self.assertEqual([], edge_device.parent_groups)
        self.assertAlmostEqual(1.0, edge_device.total_nb_of_units.value.magnitude)


if __name__ == "__main__":
    unittest.main()
