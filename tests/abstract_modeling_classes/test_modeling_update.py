import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import (
    compute_attr_updates_chain_from_mod_objs_computation_chain, ModelingUpdate)
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj


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


if __name__ == '__main__':
    unittest.main()
