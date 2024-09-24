import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u

MODELING_OBJ_CLASS_PATH = "efootprint.abstract_modeling_classes.modeling_object"


class ModelingObjectForTesting(ModelingObject):
    def __init__(self, name, custom_input=None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input

    def compute_calculated_attributes(self):
        pass

    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class TestModelingObject(unittest.TestCase):

    def setUp(self):
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

    def test_handle_model_input_update_triggers(self):
        value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObj)
        old_value = MagicMock(spec=ObjectLinkedToModelingObj)
        self.modeling_object.attribute = old_value
        self.modeling_object.handle_model_input_update = MagicMock()

        self.modeling_object.attribute = value

        self.modeling_object.handle_model_input_update.assert_called_once_with(old_value)

    def test_handle_model_input_update_single_level_descendants(self):
        mod_obj_container = "mod_obj"
        parent = MagicMock()
        parent.id = 'parent_id'

        child1 = MagicMock()
        child1.id = 'child1_id'
        child1.direct_children_with_id = []
        child1.direct_ancestors_with_id = [parent]

        child2 = MagicMock()
        child2.id = 'child2_id'
        child2.direct_children_with_id = []
        child2.direct_ancestors_with_id = [parent]

        for index, child in enumerate([child1, child2]):
            child.modeling_obj_container = mod_obj_container
            child.attr_name_in_mod_obj_container = f"attr_{index}"

        parent.get_all_descendants_with_id.return_value = [child1, child2]
        parent.direct_children_with_id = [child1, child2]

        with patch(f'{MODELING_OBJ_CLASS_PATH}.ModelingObject.retrieve_update_function_from_attribute_name') \
                as mock_retrieve_update_func:
            mock_retrieve_update_func.return_value = MagicMock()

            self.modeling_object.handle_model_input_update(parent)

            mock_retrieve_update_func.assert_any_call(mod_obj_container, "attr_0")
            mock_retrieve_update_func.assert_any_call(mod_obj_container, "attr_1")

            self.assertEqual(mock_retrieve_update_func.call_count, 2)

    def test_handle_model_input_update_multiple_levels_of_descendants(self):
        mod_obj_container = "mod_obj_container"
        parent = MagicMock()
        parent.id = 'parent_id'

        child1 = MagicMock()
        child1.id = 'child1_id'
        child1.direct_ancestors_with_id = [parent]

        grandchild1 = MagicMock()
        grandchild1.id = 'grandchild1_id'
        grandchild1.direct_children_with_id = []
        grandchild1.direct_ancestors_with_id = [child1]

        grandchild2 = MagicMock()
        grandchild2.id = 'grandchild2_id'
        grandchild2.direct_children_with_id = []
        grandchild2.direct_ancestors_with_id = [child1]

        child1.direct_children_with_id = [grandchild1, grandchild2]
        parent.get_all_descendants_with_id.return_value = [child1, grandchild1, grandchild2]
        parent.direct_children_with_id = [child1]

        for index, child in enumerate([child1, grandchild1, grandchild2]):
            child.modeling_obj_container = mod_obj_container
            child.attr_name_in_mod_obj_container = f"attr_{index}"

        with patch(f'{MODELING_OBJ_CLASS_PATH}.ModelingObject.retrieve_update_function_from_attribute_name') \
                as mock_retrieve_update_func:
            mock_retrieve_update_func.return_value = MagicMock()

            self.modeling_object.handle_model_input_update(parent)

            mock_retrieve_update_func.assert_any_call(mod_obj_container, "attr_0")
            mock_retrieve_update_func.assert_any_call(mod_obj_container, "attr_1")
            mock_retrieve_update_func.assert_any_call(mod_obj_container, "attr_2")

            self.assertEqual(mock_retrieve_update_func.call_count, 3)

    def test_attributes_computation_chain(self):
        dep1 = MagicMock()
        dep2 = MagicMock()
        dep1_sub1 = MagicMock()
        dep1_sub2 = MagicMock()
        dep2_sub1 = MagicMock()
        dep2_sub2 = MagicMock()

        self.modeling_object.modeling_objects_whose_attributes_depend_directly_on_me = [dep1, dep2]
        dep1.modeling_objects_whose_attributes_depend_directly_on_me = [dep1_sub1, dep1_sub2]
        dep2.modeling_objects_whose_attributes_depend_directly_on_me = [dep2_sub1, dep2_sub2]

        for obj in [dep1_sub1, dep1_sub2, dep2_sub1, dep2_sub2]:
            obj.modeling_objects_whose_attributes_depend_directly_on_me = []

        self.assertEqual([self.modeling_object, dep1, dep2, dep1_sub1, dep1_sub2, dep2_sub1, dep2_sub2],
                         self.modeling_object.attributes_computation_chain)

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

        with patch(f'{MODELING_OBJ_CLASS_PATH}.ModelingObject.handle_object_list_link_update') \
                as mock_list_obj_update_func:
            assert mod_obj.custom_input__previous_list_value_set == [val1, val2]
            mod_obj.custom_input += [val3]
            assert mod_obj.custom_input__previous_list_value_set == [val1, val2, val3]
            mock_list_obj_update_func.assert_called_once_with([val1, val2, val3], [val1, val2])

    def test_optimize_attributes_computation_chain_simple_case(self):
        mod_obj1 = MagicMock()
        mod_obj2 = MagicMock()
        mod_obj3 = MagicMock()

        attributes_computation_chain = [mod_obj1, mod_obj2, mod_obj3]

        self.assertEqual([mod_obj1, mod_obj2, mod_obj3],
                         self.modeling_object.optimize_attributes_computation_chain(attributes_computation_chain))

    def test_optimize_attributes_computation_chain_complex_case(self):
        mod_obj1 = MagicMock()
        mod_obj2 = MagicMock()
        mod_obj3 = MagicMock()
        mod_obj4 = MagicMock()
        mod_obj5 = MagicMock()

        attributes_computation_chain = [
            mod_obj1, mod_obj2, mod_obj3, mod_obj4, mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3]

        self.assertEqual([mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3],
                         self.modeling_object.optimize_attributes_computation_chain(attributes_computation_chain))


if __name__ == "__main__":
    unittest.main()
