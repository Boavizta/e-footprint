import unittest
from unittest.mock import patch, PropertyMock, MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


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


class TestContextualModObjAttribute(unittest.TestCase):
    def test_contextual_modeling_object_attribute(self):
        modeling_obj = ModelingObjectForTesting(name="TestObject", custom_input=42)
        modeling_obj_container = ModelingObjectForTesting(name="container")

        contextual_attribute = ContextualModelingObjectAttribute(
            value=modeling_obj, modeling_obj_container=modeling_obj_container, attr_name_in_mod_obj_container="attr")

        self.assertTrue(isinstance(contextual_attribute, ModelingObject))
        self.assertEqual(42, contextual_attribute.custom_input)
        self.assertEqual([], contextual_attribute.systems)

    def test_works_when_setting_attr_to_variable(self):
        custom_input = MagicMock(name="custom_input")
        modeling_obj = ModelingObjectForTesting(name="test", custom_input=custom_input)
        other_modeling_obj = ModelingObjectForTesting(name="other")

        with patch.object(ModelingObject, "register_footprint_values_in_systems_before_change",
                          new_callable=PropertyMock) as mock1, \
            patch.object(ModelingObject, "handle_object_link_update", new_callable=PropertyMock) as mock2:
            mock1.return_value = lambda x: True
            mock2.return_value = lambda x, y: True
            modeling_obj.custom_input = other_modeling_obj

            test = modeling_obj.custom_input

            self.assertTrue(isinstance(test, ContextualModelingObjectAttribute))
            self.assertEqual(test.modeling_obj_container, modeling_obj)
