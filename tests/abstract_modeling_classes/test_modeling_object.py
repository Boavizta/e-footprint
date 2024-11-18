import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.abstract_modeling_classes.explainable_object_base_class import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues, SourceValue
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u

MODELING_OBJ_CLASS_PATH = "efootprint.abstract_modeling_classes.modeling_object"


class ModelingObjectForTesting(ModelingObject):
    def __init__(self, name, custom_input=None, custom_input2=None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input
        if custom_input2 is not None:
            self.custom_input2 = custom_input2

    def compute_calculated_attributes(self):
        pass

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class TestModelingObject(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)

        self.modeling_object = ModelingObjectForTesting("test_object")

    def test_setattr_sets_modeling_obj_container(self):
        value = MagicMock(spec=ObjectLinkedToModelingObj, modeling_obj_container=None)

        self.modeling_object.attribute = value

        value.set_modeling_obj_container.assert_called_once_with(self.modeling_object, "attribute")

    def test_setattr_already_assigned_value(self):
        input_value = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 5], pint_unit=u.dimensionless))
        child_obj = ModelingObjectForTesting("child_object", custom_input=input_value)
        parent_obj = ModelingObjectForTesting("parent_object", custom_input=child_obj)

        self.assertEqual(child_obj, parent_obj.custom_input)
        self.assertIn(parent_obj, child_obj.modeling_obj_containers)

        with patch.object(ModelingObjectForTesting, "handle_object_link_update", new_callable=PropertyMock) \
                as mock_update:
            parent_obj.custom_input = child_obj
            # Test that the value is not changed when we re-assigned the same object to the same attribute
            # and that the handle_object_link_update method is not called
            mock_update.assert_not_called()
            self.assertEqual(child_obj, parent_obj.custom_input)
            self.assertIn(parent_obj, child_obj.modeling_obj_containers)

        # Test that the value is changed when we change the attribute value
        child_obj.custom_input = SourceHourlyValues(
            create_hourly_usage_df_from_list([4, 5, 6], pint_unit=u.dimensionless))

        self.assertEqual([4, 5, 6], parent_obj.custom_input.custom_input.value_as_float_list)

    @patch("efootprint.abstract_modeling_classes.modeling_object.launch_update_function_chain")
    def test_input_change_triggers_launch_update_function_chain(self, mock_launch_update_function_chain):
        value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObj)
        old_value = MagicMock(spec=ObjectLinkedToModelingObj)
        old_value.update_function_chain = MagicMock()
        self.modeling_object.attribute = old_value

        self.modeling_object.attribute = value

        mock_launch_update_function_chain.assert_called_once_with(old_value.update_function_chain)

    def test_attributes_computation_chain(self):
        dep1 = MagicMock()
        dep2 = MagicMock()
        dep1_sub1 = MagicMock()
        dep1_sub2 = MagicMock()
        dep2_sub1 = MagicMock()
        dep2_sub2 = MagicMock()

        with patch.object(ModelingObjectForTesting, "modeling_objects_whose_attributes_depend_directly_on_me",
                          new_callable=PropertyMock) as mock_modeling_objects_whose_attributes_depend_directly_on_me:
            mock_modeling_objects_whose_attributes_depend_directly_on_me.return_value = [dep1, dep2]
            dep1.modeling_objects_whose_attributes_depend_directly_on_me = [dep1_sub1, dep1_sub2]
            dep2.modeling_objects_whose_attributes_depend_directly_on_me = [dep2_sub1, dep2_sub2]

            for obj in [dep1_sub1, dep1_sub2, dep2_sub1, dep2_sub2]:
                obj.modeling_objects_whose_attributes_depend_directly_on_me = []

            self.assertEqual([self.modeling_object, dep1, dep2, dep1_sub1, dep1_sub2, dep2_sub1, dep2_sub2],
                             self.modeling_object.mod_objs_computation_chain)

    def test_list_attribute_update_works_with_classical_syntax(self):
        val1 = MagicMock()
        val2 = MagicMock()
        val3 = MagicMock()

        mod_obj = ModelingObjectForTesting("test mod obj", custom_input=[val1, val2])

        with patch(f'{MODELING_OBJ_CLASS_PATH}.ModelingObject.handle_object_list_link_update') \
                as mock_list_obj_update_func:
            mod_obj.custom_input = [val1, val2, val3]
            mock_list_obj_update_func.assert_called_once_with([val1, val2, val3], [val1, val2])

    def test_list_attribute_update_works_with_list_condensed_addition_syntax(self):
        val1 = MagicMock()
        val2 = MagicMock()
        val3 = MagicMock()

        mod_obj = ModelingObjectForTesting("test mod obj", custom_input=[val1, val2])

        self.assertEqual(mod_obj.custom_input, [val1, val2])
        mod_obj.custom_input += [val3]
        self.assertEqual(mod_obj.custom_input.previous_values, [val1, val2, val3])

    def test_optimize_mod_objs_computation_chain_simple_case(self):
        mod_obj1 = MagicMock()
        mod_obj2 = MagicMock()
        mod_obj3 = MagicMock()

        attributes_computation_chain = [mod_obj1, mod_obj2, mod_obj3]

        self.assertEqual([mod_obj1, mod_obj2, mod_obj3],
                         optimize_mod_objs_computation_chain(attributes_computation_chain))

    def test_optimize_mod_objs_computation_chain_complex_case(self):
        mod_obj1 = MagicMock()
        mod_obj2 = MagicMock()
        mod_obj3 = MagicMock()
        mod_obj4 = MagicMock()
        mod_obj5 = MagicMock()

        attributes_computation_chain = [
            mod_obj1, mod_obj2, mod_obj3, mod_obj4, mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3]

        self.assertEqual([mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3],
                         optimize_mod_objs_computation_chain(attributes_computation_chain))

    def test_mod_obj_attributes(self):
        attr1 = MagicMock(spec=ModelingObject)
        attr2 = MagicMock(spec=ModelingObject)
        mod_obj = ModelingObjectForTesting("test mod obj", custom_input=attr1, custom_input2=attr2)

        self.assertEqual([attr1, attr2], mod_obj.mod_obj_attributes)

    def test_to_json_correct_export_with_child(self):
        child_obj = ModelingObjectForTesting(name="child_object", custom_input="child_value")
        parent_obj = ModelingObjectForTesting(name="parent_object",custom_input=child_obj)

        parent_obj.string_attr = "test_string"
        parent_obj.int_attr = 42
        parent_obj.none_attr = None
        parent_obj.empty_list_attr = []
        parent_obj.source_value_attr = SourceValue(1* u.dimensionless, source=None)

        expected_json = {'name': 'parent_object',
             'id': parent_obj.id,
             'custom_input': child_obj.id,
             'string_attr': 'test_string',
             'int_attr': 42,
             'none_attr': None,
             'empty_list_attr': [],
             'source_value_attr': {'label': 'unnamed source',
              'value': 1.0,
              'unit': 'dimensionless'}
         }
        json_output = parent_obj.to_json()
        self.assertEqual(expected_json, json_output)


    def test_to_json_invalid_type_error(self):
        child_obj = ModelingObjectForTesting(name="child_object", custom_input="child_value")
        parent_obj = ModelingObjectForTesting(name="parent_object", custom_input=child_obj)

        parent_obj.string_attr = "test_string"
        parent_obj.int_attr = 42
        parent_obj.none_attr = None
        parent_obj.empty_list_attr = []
        parent_obj.source_value_attr = SourceValue(1 * u.dimensionless, source=None)
        parent_obj.bool_attr = True

        with self.assertRaises(ValueError) as context:
            parent_obj.to_json()
            self.assertIn("is not handled in to_json", str(context.exception))

if __name__ == "__main__":
    unittest.main()
