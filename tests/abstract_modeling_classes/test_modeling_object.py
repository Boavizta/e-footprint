import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues, SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern

MODELING_OBJ_CLASS_PATH = "efootprint.abstract_modeling_classes.modeling_object"


class ModelingObjectForTesting(ModelingObject):
    default_values =  {}

    def __init__(self, name, custom_input: ObjectLinkedToModelingObj=None,
                 custom_input2: ObjectLinkedToModelingObj=None, custom_list_input: list=None,
                 mod_obj_input1: ModelingObject=None, mod_obj_input2: ModelingObject=None):
        super().__init__(name)
        if custom_input:
            self.custom_input = custom_input
        if custom_input2:
            self.custom_input2 = custom_input2
        if custom_list_input:
            self.custom_list_input = custom_list_input
        if mod_obj_input1:
            self.mod_obj_input1 = mod_obj_input1
        if mod_obj_input2:
            self.mod_obj_input2 = mod_obj_input2

    @property
    def class_as_simple_str(self):
        return "System"

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

    def test_setattr_already_assigned_value(self):
        input_value = create_source_hourly_values_from_list([1, 2, 5], pint_unit=u.occurrence)
        child_obj = ModelingObjectForTesting("child_object", custom_input=input_value)
        parent_obj = ModelingObjectForTesting("parent_object", mod_obj_input1=child_obj)

        self.assertEqual(child_obj, parent_obj.mod_obj_input1)
        self.assertIn(parent_obj, child_obj.modeling_obj_containers)

        parent_obj.mod_obj_input1 = child_obj
        self.assertEqual(child_obj, parent_obj.mod_obj_input1)
        self.assertIn(parent_obj, child_obj.modeling_obj_containers)

        child_obj.custom_input = create_source_hourly_values_from_list([4, 5, 6], pint_unit=u.occurrence)

        self.assertEqual([4, 5, 6], parent_obj.mod_obj_input1.custom_input.value_as_float_list)

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate")
    def test_input_change_triggers_modeling_update(self, mock_modeling_update):
        old_value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObj)
        mod_obj = ModelingObjectForTesting("test", custom_input=old_value)

        value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObj)
        mod_obj.custom_input = value

        mock_modeling_update.assert_called_once_with([[old_value, value]])

    def test_input_change_sets_modeling_obj_containers(self):
        custom_input = MagicMock(spec=ExplainableObject)
        parent_obj = ModelingObjectForTesting(name="parent_object", custom_input=custom_input)
        parent_obj.trigger_modeling_updates = False
        new_input = MagicMock(spec=ExplainableObject)

        parent_obj.custom_input = new_input

        new_input.set_modeling_obj_container.assert_called_once_with(parent_obj, "custom_input")
        custom_input.set_modeling_obj_container.assert_has_calls([call(parent_obj, "custom_input"), call(None, None)])

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

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate")
    def test_list_attribute_update_works_with_classical_syntax(self, mock_modeling_update):
        val1 = MagicMock(spec=ModelingObject)
        val2 = MagicMock(spec=ModelingObject)
        val3 = MagicMock(spec=ModelingObject)

        mod_obj = ModelingObjectForTesting("test mod obj", custom_input=ListLinkedToModelingObj([val1, val2]))

        mod_obj.custom_input = ListLinkedToModelingObj([val1, val2, val3])
        mock_modeling_update.assert_called_once_with([[[val1, val2], [val1, val2, val3]]])

    @patch("efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ModelingUpdate")
    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate")
    def test_list_attribute_update_works_with_list_condensed_addition_syntax(
            self, mock_modeling_update_mod_update, mock_modeling_update_list):
        val1 = MagicMock(spec=ModelingObject)
        val2 = MagicMock(spec=ModelingObject)
        val3 = MagicMock(spec=ModelingObject)

        mod_obj = ModelingObjectForTesting("test mod obj", custom_input=ListLinkedToModelingObj([val1, val2]))

        self.assertEqual(mod_obj.custom_input, [val1, val2])
        mod_obj.custom_input += [val3]
        mock_modeling_update_list.assert_called_once_with([[[val1, val2], [val1, val2, val3]]])

    def test_list_attribute_update_works_with_list_condensed_addition_syntax__no_mocking(
            self):
        val1 = MagicMock(spec=ModelingObject)
        val2 = MagicMock(spec=ModelingObject)
        val3 = MagicMock(spec=ModelingObject)

        mod_obj = ModelingObjectForTesting("test mod obj", custom_list_input=ListLinkedToModelingObj([val1, val2]))

        self.assertEqual(mod_obj.custom_list_input, [val1, val2])
        mod_obj.custom_list_input += [val3]
        self.assertEqual(mod_obj.custom_list_input, [val1, val2, val3])

    def test_optimize_mod_objs_computation_chain_simple_case(self):
        mod_obj1 = MagicMock(id=1)
        mod_obj2 = MagicMock(id=2)
        mod_obj3 = MagicMock(id=3)

        for mod_obj in [mod_obj1, mod_obj3]:
            mod_obj.systems = None

        magic_system = MagicMock()
        mod_obj2.systems = [magic_system]

        mod_obj1.efootprint_class = UsageJourney
        mod_obj2.efootprint_class = UsagePattern
        mod_obj3.efootprint_class = Job

        attributes_computation_chain = [mod_obj1, mod_obj2, mod_obj3]

        self.assertEqual([mod_obj1, mod_obj2, mod_obj3, magic_system],
                         optimize_mod_objs_computation_chain(attributes_computation_chain))

    def test_optimize_mod_objs_computation_chain_complex_case(self):
        mod_obj1 = MagicMock(id=1)
        mod_obj2 = MagicMock(id=2)
        mod_obj3 = MagicMock(id=3)
        mod_obj4 = MagicMock(id=4)
        mod_obj5 = MagicMock(id=5)

        for mod_obj in [mod_obj1, mod_obj2, mod_obj3, mod_obj4, mod_obj5]:
            mod_obj.systems = None

        mod_obj5.efootprint_class = UsageJourney
        mod_obj1.efootprint_class = UsagePattern
        mod_obj2.efootprint_class = Job
        mod_obj4.efootprint_class = Server
        mod_obj3.efootprint_class = Storage

        attributes_computation_chain = [
            mod_obj1, mod_obj2, mod_obj3, mod_obj4, mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3]

        self.assertEqual([mod_obj5, mod_obj1, mod_obj2, mod_obj4, mod_obj3],
                         optimize_mod_objs_computation_chain(attributes_computation_chain))

    def test_mod_obj_attributes(self):
        attr1 = MagicMock(spec=ModelingObject)
        attr2 = MagicMock(spec=ModelingObject)
        mod_obj = ModelingObjectForTesting("test mod obj", mod_obj_input1=attr1, mod_obj_input2=attr2)

        self.assertEqual([attr1, attr2], mod_obj.mod_obj_attributes)

    def test_to_json_correct_export_with_child(self):
        custom_input = MagicMock(spec=ExplainableObject)
        child_obj = ModelingObjectForTesting(name="child_object", custom_input=custom_input)
        parent_obj = ModelingObjectForTesting(name="parent_object",mod_obj_input1=child_obj)
        parent_obj.trigger_modeling_updates = False

        parent_obj.none_attr = None
        parent_obj.empty_list_attr = ListLinkedToModelingObj([])
        parent_obj.source_value_attr = SourceValue(1* u.dimensionless, source=None)

        expected_json = {'name': 'parent_object',
             'id': parent_obj.id,
             'mod_obj_input1': child_obj.id,
             'none_attr': None,
             'empty_list_attr': [],
             'source_value_attr': {'label': 'unnamed source',
              'value': 1.0,
              'unit': 'dimensionless'}
         }
        json_output = parent_obj.to_json()
        self.assertEqual(expected_json, json_output)


    def test_invalid_input_type_error(self):
        custom_input = MagicMock(spec=ExplainableObject)
        parent_obj = ModelingObjectForTesting(name="parent_object", custom_input=custom_input)
        parent_obj.trigger_modeling_updates = False

        with self.assertRaises(AssertionError):
            parent_obj.int_attr = 42

if __name__ == "__main__":
    unittest.main()
