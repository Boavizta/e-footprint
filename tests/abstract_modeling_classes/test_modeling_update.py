import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytz

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import (
    compute_attr_updates_chain_from_mod_objs_computation_chain, ModelingUpdate)
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.builders.time_builders import create_source_hourly_values_from_list


class TestModelingUpdateFunctions(unittest.TestCase):
    def test_compute_attr_updates_chain_from_mod_objs_computation_chain(self):
        mod_obj_1 = MagicMock()
        mod_obj_2 = MagicMock()

        mod_obj_1.calculated_attributes = ['attr_1', 'attr_2']
        mod_obj_1.attr_1 = "attr_1_value"
        mod_obj_1.attr_2 = "attr_2_value"
        mod_obj_2.calculated_attributes = ['attr_3']
        mod_obj_2.attr_3 = "attr_3_value"

        mod_objs_computation_chain = [mod_obj_1, mod_obj_2]
        result = compute_attr_updates_chain_from_mod_objs_computation_chain(mod_objs_computation_chain)

        self.assertEqual(["attr_1_value", "attr_2_value", "attr_3_value"], result)


class TestModelingUpdate(unittest.TestCase):
    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_wrong_input_types_raises_value_error(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        old_value = MagicMock(spec=ObjectLinkedToModelingObj)
        old_value.modeling_obj_container = MagicMock()
        old_value.attr_name_in_mod_obj_container = MagicMock()
        new_value = 1

        modeling_update.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            modeling_update.parse_changes_list()

    @patch("efootprint.abstract_modeling_classes.modeling_update.optimize_mod_objs_computation_chain")
    def test_compute_compute_mod_objs_computation_chain_case_modeling_object(
            self, mock_optimize_mod_objs_computation_chain):
        mock_optimize_mod_objs_computation_chain.side_effect = lambda x: x
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        old_value = MagicMock(spec=ContextualModelingObjectAttribute)
        new_value = MagicMock(spec=ContextualModelingObjectAttribute)
        mod_obj_container = MagicMock()
        old_value.modeling_obj_container = mod_obj_container

        computation_chain_mock_content = MagicMock()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.return_value = \
            [computation_chain_mock_content]

        modeling_update.changes_list = [[old_value, new_value]]
        with patch.object(ABCAfterInitMeta, "__instancecheck__", new_callable=PropertyMock) as instancecheck_mock:
            instancecheck_mock.return_value = lambda x: x.type == "ModelingObject"
            mod_objs_computation_chain = modeling_update.compute_mod_objs_computation_chain()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.assert_called_once_with(
            old_value, new_value, optimize_chain=False)
        self.assertEqual([computation_chain_mock_content], mod_objs_computation_chain)

    @patch("efootprint.abstract_modeling_classes.modeling_update.optimize_mod_objs_computation_chain")
    def test_compute_compute_mod_objs_computation_chain_case_list(
            self, mock_optimize_mod_objs_computation_chain):
        mock_optimize_mod_objs_computation_chain.side_effect = lambda x: x
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        old_value = MagicMock(spec=ListLinkedToModelingObj)
        new_value = MagicMock(spec=ListLinkedToModelingObj)
        mod_obj_container = MagicMock()
        old_value.modeling_obj_container = mod_obj_container

        computation_chain_mock_content = MagicMock()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists.return_value = \
            [computation_chain_mock_content]

        modeling_update.changes_list = [[old_value, new_value]]
        with patch.object(ABCAfterInitMeta, "__instancecheck__", new_callable=PropertyMock) as instancecheck_mock:
            instancecheck_mock.return_value = lambda x: x.type == "ModelingObject"
            mod_objs_computation_chain = modeling_update.compute_mod_objs_computation_chain()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists.assert_called_once_with(
            old_value, new_value, optimize_chain=False)
        self.assertEqual([computation_chain_mock_content], mod_objs_computation_chain)

    def test_apply_changes_with_mixed_objects(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        old_value_1 = MagicMock(spec=ContextualModelingObjectAttribute)
        new_value_1 = MagicMock(spec=ModelingObject)
        mod_obj_container_1 = MagicMock()
        old_value_1.modeling_obj_container = mod_obj_container_1
        old_value_1.attr_name_in_mod_obj_container = "attr_1"

        old_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        new_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        mod_obj_container_2 = MagicMock()
        old_value_2.modeling_obj_container = mod_obj_container_2
        old_value_2.attr_name_in_mod_obj_container = "attr_2"

        modeling_update.changes_list = [[old_value_1, new_value_1], [old_value_2, new_value_2]]

        modeling_update.apply_changes()

        old_value_1.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_1)
        old_value_2.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_2)

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate.old_sourcevalues")
    def test_compute_ancestors_not_in_computation_chain_with_no_values_to_recompute(self, mock_old_sourcevalues):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        mock_old_sourcevalues.return_value = []
        modeling_update.values_to_recompute = []

        self.assertEqual(modeling_update.compute_ancestors_not_in_computation_chain(), [])

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate.old_sourcevalues")
    def test_compute_ancestors_not_in_computation_chain_with_no_ancestors(self, mock_old_sourcevalues):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        mock_old_sourcevalues.return_value = []

        value_1 = MagicMock()
        value_1.all_ancestors_with_id = []
        value_1.id = 1

        modeling_update.values_to_recompute = [value_1]

        self.assertEqual(modeling_update.compute_ancestors_not_in_computation_chain(), [])

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate.old_sourcevalues")
    def test_compute_ancestors_not_in_computation_chain_with_ancestors(self, mock_old_sourcevalues):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        mock_old_sourcevalues.return_value = []

        value_1 = MagicMock(spec=ExplainableObject)
        value_1.id = 1
        value_2 = MagicMock(spec=ExplainableObject)
        value_2.id = 2
        value_3 = MagicMock(spec=ExplainableObject)
        value_3.id = 3
        value_4 = MagicMock(spec=ExplainableHourlyQuantities)
        value_4.id = 4

        value_1.all_ancestors_with_id = [value_2, value_3, value_4]


        value_2.all_ancestors_with_id = [value_1, value_4]


        modeling_update.values_to_recompute = [value_1, value_2]

        self.assertEqual(modeling_update.compute_ancestors_not_in_computation_chain(), [value_3, value_4])

    def test_compute_hourly_quantities_to_filter_within_modeling_period(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        modeling_update.simulation_date = datetime(2025, 1, 2, tzinfo=pytz.utc)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2))

        for ancestor in [ancestor_1, ancestor_2]:
            ancestor.modeling_obj_container = MagicMock()
            ancestor.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        modeling_update.hourly_quantities_to_filter = modeling_update.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_2, modeling_update.hourly_quantities_to_filter)
        self.assertEqual(modeling_update.hourly_quantities_to_filter, [ancestor_2])

    def test_compute_hourly_quantities_to_filter_simulation_date_outside_modeling_period_raises_error(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        modeling_update.simulation_date = datetime(2024, 12, 31, tzinfo=pytz.utc)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2))
        for ancestor in [ancestor_1, ancestor_2]:
            ancestor.modeling_obj_container = MagicMock()
            ancestor.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        with self.assertRaises(ValueError):
            modeling_update.hourly_quantities_to_filter = modeling_update.compute_hourly_quantities_to_filter()

    def test_compute_hourly_quantities_to_filter_with_multiple_ancestors(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        modeling_update.simulation_date = datetime(2025, 1, 2, tzinfo=pytz.utc)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 1))
        ancestor_3 = create_source_hourly_values_from_list([9, 10, 11, 12], start_date=datetime(2025, 1, 2))

        for ancestor in [ancestor_1, ancestor_2, ancestor_3]:
            ancestor.modeling_obj_container = MagicMock()
            ancestor.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.ancestors_not_in_computation_chain = [ancestor_1, ancestor_2, ancestor_3]

        modeling_update.hourly_quantities_to_filter = modeling_update.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_3, modeling_update.hourly_quantities_to_filter)
        self.assertEqual(modeling_update.hourly_quantities_to_filter, [ancestor_3])

    def test_compute_hourly_quantities_to_filter_with_simulation_date_equal_to_max_date(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        modeling_update.simulation_date = datetime(2025, 1, 2, 23, tzinfo=pytz.utc)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2, 20))

        for ancestor in [ancestor_1, ancestor_2]:
            ancestor.modeling_obj_container = MagicMock()
            ancestor.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        modeling_update.hourly_quantities_to_filter = modeling_update.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_2, modeling_update.hourly_quantities_to_filter)
        self.assertEqual(modeling_update.hourly_quantities_to_filter, [ancestor_2])

    def test_compute_hourly_quantities_to_filter_with_max_date_less_than_simulation_date_raises_error(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        modeling_update.simulation_date = datetime(2025, 1, 1, 10, tzinfo=pytz.utc)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1, 7))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.ancestors_not_in_computation_chain = [ancestor_1]

        with self.assertRaises(ValueError):
            modeling_update.hourly_quantities_to_filter = modeling_update.compute_hourly_quantities_to_filter()

    def test_filter_hourly_quantities_to_filter_with_non_empty_values(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        # Mock the modeling_update date rounded to the previous hour
        modeling_update.simulation_date = datetime(2025, 1, 1, 1, tzinfo=pytz.utc)

        # Create mock hourly quantities using create_source_hourly_values_from_list
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"
        ancestor_1.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.hourly_quantities_to_filter = [ancestor_1]
        modeling_update.filtered_hourly_quantities = []

        modeling_update.filter_hourly_quantities_to_filter()

        # Get the filtered values and compare
        filtered_value = modeling_update.filtered_hourly_quantities[0].value_as_float_list
        expected_filtered_value = [2, 3, 4]  # Values after 2025-01-01 01:00

        self.assertEqual(filtered_value, expected_filtered_value)

        # Check that the index of the filtered value matches the expected timestamp
        self.assertEqual(3, len(modeling_update.filtered_hourly_quantities[0]))
        self.assertEqual(datetime(2025, 1, 1, 1, tzinfo=pytz.utc),
                            modeling_update.filtered_hourly_quantities[0].start_date)

    def test_filter_hourly_quantities_to_filter_with_empty_values(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        # Mock the modeling_update date rounded to the previous hour
        modeling_update.simulation_date = datetime(2025, 1, 2, 1, tzinfo=pytz.utc)

        # Create mock hourly quantities with no values after the modeling_update date
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1, tzinfo=pytz.utc))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"
        time_index = [ancestor_1.start_date + timedelta(hours=i) for i in range(len(ancestor_1.value))]
        mask = [time < modeling_update.simulation_date for time in time_index]
        ancestor_1.value = ancestor_1.value[mask]

        modeling_update.hourly_quantities_to_filter = [ancestor_1]
        modeling_update.filtered_hourly_quantities = []

        # Act
        modeling_update.filter_hourly_quantities_to_filter()

        # Assert that an EmptyExplainableObject was created
        self.assertIsInstance(modeling_update.filtered_hourly_quantities[0], EmptyExplainableObject)

    def test_filter_hourly_quantities_to_filter_with_mixed_values(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        # Mock the modeling_update date rounded to the previous hour
        modeling_update.simulation_date = datetime(2025, 1, 2, 1, tzinfo=pytz.utc)

        # Create mock hourly quantities with some having values after the modeling_update date and some not
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"

        ancestor_2 = create_source_hourly_values_from_list([4, 5], start_date=datetime(2025, 1, 2))
        ancestor_2.modeling_obj_container = MagicMock()
        ancestor_2.attr_name_in_mod_obj_container = "attr_2"

        for ancestor in [ancestor_1, ancestor_2]:
            ancestor.modeling_obj_container = MagicMock()
            ancestor.modeling_obj_container.country.timezone.value = pytz.utc

        modeling_update.hourly_quantities_to_filter = [ancestor_1, ancestor_2]
        modeling_update.filtered_hourly_quantities = []

        modeling_update.filter_hourly_quantities_to_filter()

        # Assert that the first ancestor is an EmptyExplainableObject
        self.assertIsInstance(modeling_update.filtered_hourly_quantities[0], EmptyExplainableObject)

        # Assert that the second ancestor has filtered values
        filtered_value = modeling_update.filtered_hourly_quantities[1].value_as_float_list
        expected_filtered_value = [5]  # Values after 2025-01-02 01:00

        self.assertEqual(filtered_value, expected_filtered_value)

        # Check that the index of the filtered value matches the expected timestamp
        self.assertEqual(1, len(modeling_update.filtered_hourly_quantities[1]))
        self.assertEqual(datetime(2025, 1, 2, 1, tzinfo=pytz.utc),
                         modeling_update.filtered_hourly_quantities[1].start_date)


if __name__ == '__main__':
    unittest.main()
