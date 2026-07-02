import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj


class TestModelingUpdate(unittest.TestCase):
    def test_parse_changes_list_wrong_input_types_raises_value_error(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        old_value = MagicMock(spec=ObjectLinkedToModelingObj)
        old_value.modeling_obj_container = MagicMock()
        old_value.attr_name_in_mod_obj_container = MagicMock()
        new_value = 1

        modeling_update.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            modeling_update.parse_changes_list()

    def test_apply_changes_with_mixed_objects(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        old_value_1 = MagicMock(spec=ContextualModelingObjectAttribute)
        new_value_1 = MagicMock(spec=ContextualModelingObjectAttribute)
        old_value_1.modeling_obj_container = MagicMock()
        old_value_1.attr_name_in_mod_obj_container = "attr_1"

        old_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        new_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        old_value_2.modeling_obj_container = MagicMock()
        old_value_2.attr_name_in_mod_obj_container = "attr_2"

        modeling_update.changes_list = [[old_value_1, new_value_1], [old_value_2, new_value_2]]

        modeling_update.apply_changes()

        old_value_1.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_1)
        old_value_2.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_2)


if __name__ == '__main__':
    unittest.main()
