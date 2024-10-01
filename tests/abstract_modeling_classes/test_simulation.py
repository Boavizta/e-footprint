import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.simulation import (
    compute_update_function_chain_from_mod_obj_computation_chain,
    get_explainable_objects_from_update_function_chain, Simulation
)
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


if __name__ == '__main__':
    unittest.main()
