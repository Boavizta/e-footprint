import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject

MODELING_OBJ_CLASS_PATH = "efootprint.abstract_modeling_classes.modeling_object"


class ModelingObjectForTesting(ModelingObject):
    def __init__(self, name, custom_input=None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input

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
        value = MagicMock(modeling_obj_container=None)

        with patch(f"{MODELING_OBJ_CLASS_PATH}.type", lambda x: ExplainableObject):
            self.modeling_object.attribute = value

        value.set_modeling_obj_container.assert_called_once_with(self.modeling_object, "attribute")

    def test_input_change_triggers_launch_update_function_chain(self):
        value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, mock_type=ExplainableObject)
        old_value = MagicMock(mock_type=ExplainableObject)
        old_value.update_function_chain = MagicMock()
        self.modeling_object.attribute = old_value
        launch_update_function_chain = MagicMock()

        with patch(f"{MODELING_OBJ_CLASS_PATH}.type", lambda x: x.mock_type),\
                patch(f"{MODELING_OBJ_CLASS_PATH}.launch_update_function_chain",
                      launch_update_function_chain):
            self.modeling_object.attribute = value

            launch_update_function_chain.assert_called_once_with(old_value.update_function_chain)

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


if __name__ == "__main__":
    unittest.main()
