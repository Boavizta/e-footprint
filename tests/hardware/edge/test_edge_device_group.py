import unittest
from unittest import TestCase

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from tests.utils import create_mod_obj_mock


def make_group(name):
    """Create an EdgeDeviceGroup with trigger disabled."""
    g = EdgeDeviceGroup(name)
    g.trigger_modeling_updates = False
    g.sub_group_counts.trigger_modeling_updates = False
    g.edge_device_counts.trigger_modeling_updates = False
    return g


class TestEdgeDeviceGroupInit(TestCase):

    def test_init_defaults(self):
        group = make_group("My Group")
        self.assertEqual("My Group", group.name)
        self.assertIsInstance(group.sub_group_counts, ExplainableObjectDict)
        self.assertIsInstance(group.edge_device_counts, ExplainableObjectDict)
        self.assertIsInstance(group.counts_validation, EmptyExplainableObject)
        self.assertIsInstance(group.effective_nb_of_units_within_root, EmptyExplainableObject)

    def test_init_with_provided_empty_dicts(self):
        sub_groups = ExplainableObjectDict()
        devices = ExplainableObjectDict()
        group = EdgeDeviceGroup("G", sub_group_counts=sub_groups, edge_device_counts=devices)
        group.trigger_modeling_updates = False
        self.assertIsInstance(group.sub_group_counts, ExplainableObjectDict)
        self.assertIsInstance(group.edge_device_counts, ExplainableObjectDict)
        self.assertEqual({}, group.sub_group_counts)
        self.assertEqual({}, group.edge_device_counts)

    def test_modeling_objects_whose_attributes_depend_on_me_empty(self):
        group = make_group("G")
        self.assertEqual([], group.modeling_objects_whose_attributes_depend_directly_on_me)

    def test_modeling_objects_whose_attributes_depend_on_me_combines_sub_groups_and_devices(self):
        group = make_group("Group")
        child_group = make_group("Child")
        mock_device = create_mod_obj_mock(EdgeDevice, "Device")
        group.sub_group_counts[child_group] = SourceValue(2 * u.dimensionless)
        group.edge_device_counts[mock_device] = SourceValue(3 * u.dimensionless)
        result = group.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertIn(child_group, result)
        self.assertIn(mock_device, result)


class TestEdgeDeviceGroupFindParentGroups(TestCase):

    def test_standalone_group_has_no_parents(self):
        group = make_group("Standalone")
        self.assertEqual([], group._find_parent_groups())

    def test_single_parent_group(self):
        parent = make_group("Parent")
        child = make_group("Child")
        parent.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        result = child._find_parent_groups()
        self.assertEqual([parent], result)

    def test_two_parent_groups(self):
        parent_a = make_group("Parent A")
        parent_b = make_group("Parent B")
        child = make_group("Child")
        parent_a.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        parent_b.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        result = child._find_parent_groups()
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

    def setUp(self):
        self.group = make_group("Group")

    def test_valid_dimensionless_count(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(5 * u.dimensionless)
        self.group.update_counts_validation()
        self.assertIsInstance(self.group.counts_validation, EmptyExplainableObject)

    def test_zero_count_is_valid(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(0 * u.dimensionless)
        self.group.update_counts_validation()

    def test_non_dimensionless_count_raises(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(5 * u.kg)
        with self.assertRaises(ValueError):
            self.group.update_counts_validation()

    def test_negative_count_raises(self):
        mock_device = create_mod_obj_mock(EdgeDevice, "Dev")
        self.group.edge_device_counts[mock_device] = SourceValue(-1 * u.dimensionless)
        with self.assertRaises(ValueError):
            self.group.update_counts_validation()

    def test_sub_group_non_dimensionless_raises(self):
        child = make_group("Child")
        self.group.sub_group_counts[child] = SourceValue(3 * u.kg)
        with self.assertRaises(ValueError):
            self.group.update_counts_validation()

    def test_sub_group_valid_count(self):
        child = make_group("Child")
        self.group.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        self.group.update_counts_validation()

    def test_empty_counts_passes_validation(self):
        self.group.update_counts_validation()


class TestEdgeDeviceGroupUpdateEffectiveNbOfUnits(TestCase):

    def test_root_group_effective_nb_is_one(self):
        root = make_group("Root")
        root.update_effective_nb_of_units_within_root()
        self.assertAlmostEqual(1.0, root.effective_nb_of_units_within_root.value.magnitude)

    def test_root_label_mentions_root(self):
        root = make_group("Root")
        root.update_effective_nb_of_units_within_root()
        self.assertIn("root", root.effective_nb_of_units_within_root.label.lower())

    def test_child_with_single_parent_count_3(self):
        parent = make_group("Parent")
        child = make_group("Child")
        parent.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        parent.update_effective_nb_of_units_within_root()
        child.update_effective_nb_of_units_within_root()
        self.assertAlmostEqual(3.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_grandchild_effective_nb_is_product(self):
        root = make_group("Root")
        middle = make_group("Middle")
        grandchild = make_group("Grandchild")
        root.sub_group_counts[middle] = SourceValue(2 * u.dimensionless)
        middle.sub_group_counts[grandchild] = SourceValue(5 * u.dimensionless)
        root.update_effective_nb_of_units_within_root()
        middle.update_effective_nb_of_units_within_root()
        grandchild.update_effective_nb_of_units_within_root()
        self.assertAlmostEqual(10.0, grandchild.effective_nb_of_units_within_root.value.magnitude)

    def test_child_with_two_parents_sums_contributions(self):
        """Shared sub-group belonging to two roots gets contribution from both."""
        root_a = make_group("Root A")
        root_b = make_group("Root B")
        child = make_group("Child")
        root_a.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        root_b.sub_group_counts[child] = SourceValue(3 * u.dimensionless)
        root_a.update_effective_nb_of_units_within_root()
        root_b.update_effective_nb_of_units_within_root()
        child.update_effective_nb_of_units_within_root()
        # 2 * 1 + 3 * 1 = 5
        self.assertAlmostEqual(5.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_effective_nb_is_dimensionless(self):
        root = make_group("Root")
        root.update_effective_nb_of_units_within_root()
        self.assertTrue(root.effective_nb_of_units_within_root.value.check("[]"))


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
        self.assertEqual([], child._find_parent_groups())
        self.assertAlmostEqual(1.0, child.effective_nb_of_units_within_root.value.magnitude)

    def test_self_delete_recomputes_edge_devices_when_clearing_edge_device_counts(self):
        """Test self_delete clears edge_device_counts before deleting the root group."""
        group = EdgeDeviceGroup("Device group for deletion")
        edge_device = EdgeDevice.from_defaults("Device referenced by deleted group", components=[])
        group.edge_device_counts[edge_device] = SourceValue(3 * u.dimensionless)
        self.assertAlmostEqual(3.0, edge_device.total_nb_of_units.value.magnitude)

        group.self_delete()

        self.assertEqual({}, group.edge_device_counts)
        self.assertEqual([], edge_device._find_parent_groups())
        self.assertAlmostEqual(1.0, edge_device.total_nb_of_units.value.magnitude)


if __name__ == "__main__":
    unittest.main()
