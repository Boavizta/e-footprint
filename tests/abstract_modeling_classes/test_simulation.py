import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject, ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.simulation import (
    compute_update_function_chain_from_mod_obj_computation_chain,
    get_explainable_objects_from_update_function_chain, Simulation
)
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from tests.abstract_modeling_classes.test_modeling_object import ModelingObjectForTesting


class TestSimulationFunctions(unittest.TestCase):
    @patch('efootprint.abstract_modeling_classes.simulation.retrieve_update_function_from_mod_obj_and_attr_name')
    def test_compute_update_function_chain_from_mod_obj_computation_chain(self, mock_retrieve_update_function):
        mod_obj_1 = MagicMock()
        mod_obj_2 = MagicMock()

        mod_obj_1.calculated_attributes = ['attr_1', 'attr_2']
        mod_obj_2.calculated_attributes = ['attr_3']

        mock_retrieve_update_function.side_effect = ['func_1', 'func_2', 'func_3']

        mod_objs_computation_chain = [mod_obj_1, mod_obj_2]
        result = compute_update_function_chain_from_mod_obj_computation_chain(mod_objs_computation_chain)

        self.assertEqual(result, ['func_1', 'func_2', 'func_3'])
        self.assertEqual(mock_retrieve_update_function.call_count, 3)

    def test_get_explainable_objects_from_update_function_chain(self):
        update_func_1 = MagicMock()
        update_func_2 = MagicMock()

        update_func_1.__name__ = 'update_expl_obj_1'
        update_func_2.__name__ = 'update_expl_obj_2'

        modeling_obj_container_1 = MagicMock()
        modeling_obj_container_2 = MagicMock()

        modeling_obj_container_1.expl_obj_1 = 'ExplObj1'
        modeling_obj_container_2.expl_obj_2 = 'ExplObj2'

        update_func_1.__self__ = modeling_obj_container_1
        update_func_2.__self__ = modeling_obj_container_2

        update_function_chain = [update_func_1, update_func_2]

        result = get_explainable_objects_from_update_function_chain(update_function_chain)

        self.assertEqual(result, ['ExplObj1', 'ExplObj2'])

    def test_get_explainable_objects_from_update_function_chain_raises_error(self):
        update_func_1 = MagicMock()
        update_func_1.__name__ = 'update_expl_obj_1'

        modeling_obj_container_1 = MagicMock()
        modeling_obj_container_1.expl_obj_1 = None  # Simulate missing explainable object

        update_func_1.__self__ = modeling_obj_container_1

        update_function_chain = [update_func_1]

        with self.assertRaises(ValueError):
            get_explainable_objects_from_update_function_chain(update_function_chain)


class TestSimulation(unittest.TestCase):
    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_same_type_explainable_object(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        old_value = ExplainableObject(1, "a")
        new_value = ExplainableObject(2, "b")
        new_value.modeling_obj_container = None

        simulation.changes_list = [(old_value, new_value)]
        simulation.old_sourcevalues = []
        simulation.new_sourcevalues = []

        simulation.compute_new_and_old_source_values_and_mod_obj_link_lists()

        self.assertIn(old_value, simulation.old_sourcevalues)
        self.assertIn(new_value, simulation.new_sourcevalues)

    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_different_types_raises_value_error(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        old_value = ExplainableObject(1, "a")
        new_value = EmptyExplainableObject()

        simulation.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            simulation.compute_new_and_old_source_values_and_mod_obj_link_lists()

    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_new_value_has_mod_obj_container_raises_error(
            self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        old_value = ExplainableObject(1, "a")
        new_value = ExplainableObject(2, "b")
        new_value.modeling_obj_container = MagicMock()

        simulation.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            simulation.compute_new_and_old_source_values_and_mod_obj_link_lists()

    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_list_linked_to_modeling_obj(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        old_value = ListLinkedToModelingObj([ModelingObjectForTesting("old value")])
        new_value = [ModelingObjectForTesting("new value 1"), ModelingObjectForTesting("new value 2")]

        simulation.changes_list = [(old_value, new_value)]
        simulation.old_mod_obj_links = []
        simulation.new_mod_obj_links = []

        simulation.compute_new_and_old_source_values_and_mod_obj_link_lists()

        self.assertIn(old_value, simulation.old_mod_obj_links)
        self.assertIsInstance(simulation.new_mod_obj_links[0], ListLinkedToModelingObj)
        self.assertIn(new_value, simulation.new_mod_obj_links)

    def test_compute_new_and_old_source_values_and_mod_obj_link_lists_wrong_input_types_raises_value_error(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        old_value = 0
        new_value = 1

        simulation.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            simulation.compute_new_and_old_source_values_and_mod_obj_link_lists()

    def test_compute_update_function_chains_from_mod_obj_links_updates_case_modeling_object(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        old_value = MagicMock(type="ModelingObject")
        new_value = MagicMock()
        mod_obj_container = MagicMock()
        old_value.modeling_obj_container = mod_obj_container

        # Mocking the returned computation chain and update function chain
        computation_chain_mock = MagicMock()
        update_function_chain_mock = MagicMock()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.return_value = \
            computation_chain_mock

        simulation.old_mod_obj_links = [old_value]
        simulation.new_mod_obj_links = [new_value]
        simulation.update_function_chains_from_mod_obj_links_updates = []
        from efootprint.abstract_modeling_classes import simulation as simulation_module
        with patch.object(ABCAfterInitMeta, "__instancecheck__", new_callable=PropertyMock) as instancecheck_mock,\
                patch.object(simulation_module, "compute_update_function_chain_from_mod_obj_computation_chain",
                             new_callable=PropertyMock) as compute_update_func_chain_mock:
            instancecheck_mock.return_value = lambda x: x.type == "ModelingObject"
            compute_update_func_chain_mock.return_value = update_function_chain_mock
            simulation.compute_update_function_chains_from_mod_obj_links_updates()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.assert_called_once_with(
            old_value, new_value)
        compute_update_func_chain_mock.assert_called_once_with(computation_chain_mock)

        self.assertIn(update_function_chain_mock, simulation.update_function_chains_from_mod_obj_links_updates)

    @patch(
        "efootprint.abstract_modeling_classes.simulation.compute_update_function_chain_from_mod_obj_computation_chain")
    def test_compute_update_function_chains_from_mod_obj_links_updates_case_list(self, compute_update_func_chain_mock):
        update_function_chain_mock = MagicMock()
        compute_update_func_chain_mock.return_value = update_function_chain_mock
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        old_value = MagicMock(spec=ListLinkedToModelingObj)
        new_value = MagicMock()
        mod_obj_container = MagicMock()
        old_value.modeling_obj_container = mod_obj_container

        computation_chain_mock = MagicMock()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists.return_value = \
            computation_chain_mock

        simulation.old_mod_obj_links = [old_value]
        simulation.new_mod_obj_links = [new_value]
        simulation.update_function_chains_from_mod_obj_links_updates = []

        simulation.compute_update_function_chains_from_mod_obj_links_updates()

        mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists.assert_called_once_with(
            old_value, new_value)
        compute_update_func_chain_mock.assert_called_once_with(computation_chain_mock)

        self.assertIn(update_function_chain_mock, simulation.update_function_chains_from_mod_obj_links_updates)

    @patch(
        "efootprint.abstract_modeling_classes.simulation.compute_update_function_chain_from_mod_obj_computation_chain")
    def test_compute_update_function_chains_from_mod_obj_links_updates_with_mixed_objects(
            self, compute_update_func_chain_mock):
        update_function_chain_mock_1 = MagicMock()
        update_function_chain_mock_2 = MagicMock()
        compute_update_func_chain_mock.side_effect = [update_function_chain_mock_1, update_function_chain_mock_2]
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        # First item: ModelingObject
        old_value_1 = MagicMock(spec=ModelingObject)
        new_value_1 = MagicMock(spec=ModelingObject)
        mod_obj_container_1 = MagicMock()
        old_value_1.modeling_obj_container = mod_obj_container_1

        # Second item: ListLinkedToModelingObj
        old_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        new_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        mod_obj_container_2 = MagicMock()
        old_value_2.modeling_obj_container = mod_obj_container_2

        # Mocking the returned computation chains and update function chains
        computation_chain_mock_1 = MagicMock()
        computation_chain_mock_2 = MagicMock()

        mod_obj_container_1.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.return_value = \
            computation_chain_mock_1
        mod_obj_container_2.compute_mod_objs_computation_chain_from_old_and_new_lists.return_value = \
            computation_chain_mock_2

        simulation.old_mod_obj_links = [old_value_1, old_value_2]
        simulation.new_mod_obj_links = [new_value_1, new_value_2]
        simulation.update_function_chains_from_mod_obj_links_updates = []

        simulation.compute_update_function_chains_from_mod_obj_links_updates()

        mod_obj_container_1.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs.assert_called_once_with(
            old_value_1, new_value_1)
        mod_obj_container_2.compute_mod_objs_computation_chain_from_old_and_new_lists.assert_called_once_with(
            old_value_2, new_value_2)

        compute_update_func_chain_mock.assert_any_call(computation_chain_mock_1)
        compute_update_func_chain_mock.assert_any_call(computation_chain_mock_2)

        self.assertIn(update_function_chain_mock_1, simulation.update_function_chains_from_mod_obj_links_updates)
        self.assertIn(update_function_chain_mock_2, simulation.update_function_chains_from_mod_obj_links_updates)

    def test_create_new_mod_obj_links_with_mixed_objects(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        # First item: ModelingObject
        old_value_1 = MagicMock(spec=ModelingObject)
        new_value_1 = MagicMock(spec=ModelingObject)
        mod_obj_container_1 = MagicMock()
        old_value_1.modeling_obj_container = mod_obj_container_1
        old_value_1.attr_name_in_mod_obj_container = "attr_1"

        # Second item: ListLinkedToModelingObj
        old_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        new_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        mod_obj_container_2 = MagicMock()
        old_value_2.modeling_obj_container = mod_obj_container_2
        old_value_2.attr_name_in_mod_obj_container = "attr_2"

        simulation.old_mod_obj_links = [old_value_1, old_value_2]
        simulation.new_mod_obj_links = [new_value_1, new_value_2]

        simulation.create_new_mod_obj_links()

        # Assertions for ModelingObject
        new_value_1.add_obj_to_modeling_obj_containers.assert_called_once_with(mod_obj_container_1)
        self.assertEqual(mod_obj_container_1.__dict__["attr_1"], new_value_1)

        # Assertions for ListLinkedToModelingObj
        new_value_2.set_modeling_obj_container.assert_called_once_with(mod_obj_container_2, "attr_2")
        new_value_2.register_previous_values.assert_called_once()
        self.assertEqual(mod_obj_container_2.__dict__["attr_2"], new_value_2)

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_no_values_to_recompute(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__
        simulation.values_to_recompute = []

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual(simulation.hourly_quantities_ancestors_not_in_computation_chain, [])

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_no_ancestors(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        value_1 = MagicMock()
        value_1.all_ancestors_with_id = []
        value_1.id = 1

        simulation.values_to_recompute = [value_1]

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual(simulation.hourly_quantities_ancestors_not_in_computation_chain, [])

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_non_hourly_quantities_ancestors(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        value_1 = MagicMock()
        ancestor_1 = MagicMock(spec=ExplainableObject) # Not an ExplainableHourlyQuantities instance
        ancestor_1.id = 2

        value_1.all_ancestors_with_id = [ancestor_1]
        value_1.id = 1

        simulation.values_to_recompute = [value_1]

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual(simulation.hourly_quantities_ancestors_not_in_computation_chain, [])

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_hourly_quantities_ancestors(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        value_1 = MagicMock()
        ancestor_1 = MagicMock(spec=ExplainableHourlyQuantities)
        ancestor_1.id = 2

        value_1.all_ancestors_with_id = [ancestor_1]
        value_1.id = 1

        simulation.values_to_recompute = [value_1]

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual([ancestor_1], simulation.hourly_quantities_ancestors_not_in_computation_chain)

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_duplicate_ancestors(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        value_1 = MagicMock()
        value_2 = MagicMock()

        ancestor_1 = MagicMock(spec=ExplainableHourlyQuantities)
        ancestor_1.id = 2

        value_1.all_ancestors_with_id = [ancestor_1]
        value_1.id = 1

        value_2.all_ancestors_with_id = [ancestor_1]  # Duplicate ancestor
        value_2.id = 3

        simulation.values_to_recompute = [value_1, value_2]

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual(len(simulation.hourly_quantities_ancestors_not_in_computation_chain), 1)
        self.assertIn(ancestor_1, simulation.hourly_quantities_ancestors_not_in_computation_chain)

    def test_compute_hourly_quantities_ancestors_not_in_computation_chain_with_ancestor_in_computation_chain(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        value_1 = MagicMock()
        ancestor_1 = MagicMock(spec=ExplainableHourlyQuantities)
        ancestor_1.id = 1  # Same ID as value_1, should be ignored

        value_1.all_ancestors_with_id = [ancestor_1]
        value_1.id = 1

        simulation.values_to_recompute = [value_1]

        simulation.compute_hourly_quantities_ancestors_not_in_computation_chain()

        self.assertEqual(simulation.hourly_quantities_ancestors_not_in_computation_chain, [])

    def test_compute_hourly_quantities_to_filter_within_modeling_period(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        simulation.simulation_date_as_hourly_freq = datetime(2025, 1, 2)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2))

        simulation.hourly_quantities_ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        simulation.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_2, simulation.hourly_quantities_to_filter)
        self.assertEqual(simulation.hourly_quantities_to_filter, [ancestor_2])

    def test_compute_hourly_quantities_to_filter_simulation_date_outside_modeling_period_raises_error(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        simulation.simulation_date_as_hourly_freq = datetime(2024, 12, 31)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2))

        simulation.hourly_quantities_ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        with self.assertRaises(ValueError):
            simulation.compute_hourly_quantities_to_filter()

    def test_compute_hourly_quantities_to_filter_with_multiple_ancestors(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        simulation.simulation_date_as_hourly_freq = datetime(2025, 1, 2)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 1))
        ancestor_3 = create_source_hourly_values_from_list([9, 10, 11, 12], start_date=datetime(2025, 1, 2))

        simulation.hourly_quantities_ancestors_not_in_computation_chain = [ancestor_1, ancestor_2, ancestor_3]

        simulation.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_3, simulation.hourly_quantities_to_filter)
        self.assertEqual(simulation.hourly_quantities_to_filter, [ancestor_3])

    def test_compute_hourly_quantities_to_filter_with_simulation_date_equal_to_max_date(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        simulation.simulation_date_as_hourly_freq = datetime(2025, 1, 2, 23)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_2 = create_source_hourly_values_from_list([5, 6, 7, 8], start_date=datetime(2025, 1, 2, 20))

        simulation.hourly_quantities_ancestors_not_in_computation_chain = [ancestor_1, ancestor_2]

        simulation.compute_hourly_quantities_to_filter()

        self.assertIn(ancestor_2, simulation.hourly_quantities_to_filter)
        self.assertEqual(simulation.hourly_quantities_to_filter, [ancestor_2])

    def test_compute_hourly_quantities_to_filter_with_max_date_less_than_simulation_date_raises_error(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        simulation.simulation_date_as_hourly_freq = datetime(2025, 1, 1, 10)

        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1, 7))

        simulation.hourly_quantities_ancestors_not_in_computation_chain = [ancestor_1]

        with self.assertRaises(ValueError):
            simulation.compute_hourly_quantities_to_filter()

    def test_filter_hourly_quantities_to_filter_with_non_empty_values(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        # Mock the simulation date rounded to the previous hour
        simulation.simulation_date_as_hourly_freq = pd.Timestamp("2025-01-02 01:00").to_period(freq="h")

        # Create mock hourly quantities using create_source_hourly_values_from_list
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3, 4], start_date=datetime(2025, 1, 1))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"

        simulation.hourly_quantities_to_filter = [ancestor_1]
        simulation.filtered_hourly_quantities = []

        # Act
        simulation.filter_hourly_quantities_to_filter()

        # Get the filtered values and compare
        filtered_value = simulation.filtered_hourly_quantities[0].value_as_float
        expected_filtered_value = [4]  # Values after 2025-01-02 01:00

        self.assertEqual(filtered_value, expected_filtered_value)

        # Check that the index of the filtered value matches the expected timestamp
        filtered_index = simulation.filtered_hourly_quantities[0].value.index
        expected_index = pd.period_range(start="2025-01-02 03:00", periods=1, freq='h')

        pd.testing.assert_index_equal(filtered_index, expected_index)

    def test_filter_hourly_quantities_to_filter_with_empty_values(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        # Mock the simulation date rounded to the previous hour
        simulation.simulation_date_as_hourly_freq = pd.Timestamp("2025-01-02 01:00").to_period(freq="h")

        # Create mock hourly quantities with no values after the simulation date
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"
        ancestor_1.value = ancestor_1.value[
            ancestor_1.value.index < simulation.simulation_date_as_hourly_freq]

        simulation.hourly_quantities_to_filter = [ancestor_1]
        simulation.filtered_hourly_quantities = []

        # Act
        simulation.filter_hourly_quantities_to_filter()

        # Assert that an EmptyExplainableObject was created
        self.assertIsInstance(simulation.filtered_hourly_quantities[0], EmptyExplainableObject)

        # Check that no values are present
        self.assertEqual(len(simulation.filtered_hourly_quantities[0].value), 0)

    def test_filter_hourly_quantities_to_filter_with_mixed_values(self):
        simulation = Simulation.__new__(Simulation)  # Bypass __init__

        # Mock the simulation date rounded to the previous hour
        simulation.simulation_date_as_hourly_freq = pd.Timestamp("2025-01-02 01:00").to_period(freq="h")

        # Create mock hourly quantities with some having values after the simulation date and some not
        ancestor_1 = create_source_hourly_values_from_list([1, 2, 3], start_date=datetime(2025, 1, 1))
        ancestor_1.modeling_obj_container = MagicMock()
        ancestor_1.attr_name_in_mod_obj_container = "attr_1"

        ancestor_2 = create_source_hourly_values_from_list([4, 5], start_date=datetime(2025, 1, 2))
        ancestor_2.modeling_obj_container = MagicMock()
        ancestor_2.attr_name_in_mod_obj_container = "attr_2"

        # Mock values such that ancestor_1 has no valid values after the simulation date
        ancestor_1.value = ancestor_1.value[
            ancestor_1.value.index < simulation.simulation_date_as_hourly_freq]

        simulation.hourly_quantities_to_filter = [ancestor_1, ancestor_2]
        simulation.filtered_hourly_quantities = []

        # Act
        simulation.filter_hourly_quantities_to_filter()

        # Assert that the first ancestor is an EmptyExplainableObject
        self.assertIsInstance(simulation.filtered_hourly_quantities[0], EmptyExplainableObject)

        # Assert that the second ancestor has filtered values
        filtered_value = simulation.filtered_hourly_quantities[1].value_as_float
        expected_filtered_value = [5]  # Values after 2025-01-02 01:00

        self.assertEqual(filtered_value, expected_filtered_value)

        # Check that the index of the filtered value matches the expected timestamp
        filtered_index = simulation.filtered_hourly_quantities[1].value.index
        expected_index = pd.period_range(start="2025-01-02 03:00", periods=1, freq='h')

        pd.testing.assert_index_equal(filtered_index, expected_index)


if __name__ == '__main__':
    unittest.main()
