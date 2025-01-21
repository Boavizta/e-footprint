import unittest
from unittest.mock import MagicMock, Mock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ModelingObjectForTesting(ModelingObject):
    @classmethod
    def default_values(cls):
        return {}

    def __init__(self, name, custom_input: ObjectLinkedToModelingObj = None, mod_obj_input: ModelingObject = None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input
        if mod_obj_input is not None:
            self.mod_obj_input = mod_obj_input

    def after_init(self):
        self.trigger_modeling_updates = False

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
        custom_input = MagicMock(spec=ObjectLinkedToModelingObj)
        modeling_obj = ModelingObjectForTesting(name="TestObject", custom_input=custom_input)
        modeling_obj_container = ModelingObjectForTesting(name="container")

        contextual_attribute = ContextualModelingObjectAttribute(
            value=modeling_obj, modeling_obj_container=modeling_obj_container, attr_name_in_mod_obj_container="attr")

        self.assertTrue(isinstance(contextual_attribute, ModelingObject))
        self.assertEqual(custom_input, contextual_attribute.custom_input)
        self.assertEqual([], contextual_attribute.systems)

    def test_works_when_setting_attr_to_variable(self):
        custom_input = MagicMock(name="mod obj input", spec=ModelingObject)
        custom_input.contextual_modeling_obj_containers = []
        modeling_obj = ModelingObjectForTesting(name="test", mod_obj_input=custom_input)
        other_modeling_obj = ModelingObjectForTesting(name="other")

        modeling_obj.mod_obj_input = other_modeling_obj

        self.assertTrue(isinstance(modeling_obj.mod_obj_input, ContextualModelingObjectAttribute))
        self.assertEqual(modeling_obj.mod_obj_input.modeling_obj_container, modeling_obj)
