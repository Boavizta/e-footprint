import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectDictKey
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    ExplainableObjectDict, WeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock


class ModelingObjectForContainerTest(ModelingObject):
    default_values = {}
    calculated_attributes = ["calculated_dict"]

    def __init__(self, name):
        super().__init__(name)
        self.attr_name = None
        self.other_attr = None
        self.calculated_dict = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class ModelingObjectWithInputDictForContainerTest(ModelingObject):
    default_values = {}

    def __init__(self, name, input_dict: ExplainableObjectDict = None):
        super().__init__(name)
        self.input_dict = ExplainableObjectDict(input_dict or {})

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class TestExplainableObjectDict(unittest.TestCase):

    def setUp(self):
        self.mock_modeling_obj = create_mod_obj_mock(ModelingObject, name="mock_modeling_obj", id="mock_id")

        self.mock_explainable_obj = MagicMock(spec=ExplainableObject)
        self.mock_explainable_obj.id = "mock_explainable_id"
        self.mock_explainable_obj.to_json.return_value = {"key": "value"}

        self.mock_empty_obj = MagicMock(spec=EmptyExplainableObject)
        self.mock_empty_obj.id = "empty_obj_id"

        self.dict_obj = ExplainableObjectDict()

    def test_initialization(self):
        self.assertIsNone(self.dict_obj.modeling_obj_container)
        self.assertIsNone(self.dict_obj.attr_name_in_mod_obj_container)
        self.assertEqual(len(self.dict_obj), 0)

    def test_set_modeling_obj_container(self):
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")

        self.assertEqual(self.dict_obj.modeling_obj_container, self.mock_modeling_obj)
        self.assertEqual(self.dict_obj.attr_name_in_mod_obj_container, "attr_name")

        # Test setting a conflicting modeling object
        other_mock_modeling_obj = create_mod_obj_mock(ModelingObject, name="other_mock_modeling_obj", id="other_mock_id")

        with self.assertRaises(PermissionError):
            self.dict_obj.set_modeling_obj_container(other_mock_modeling_obj, "another_attr")

    def test_all_ancestors_with_id(self):
        child_obj = MagicMock(spec=ExplainableObject)
        child_obj.all_ancestors_with_id = [MagicMock(id="ancestor_1"), MagicMock(id="ancestor_2")]
        child_obj2 = MagicMock(spec=ExplainableObject)
        child_obj2.all_ancestors_with_id = [MagicMock(id="ancestor_1"), MagicMock(id="ancestor_3")]
        self.dict_obj["child"] = child_obj
        self.dict_obj["child2"] = child_obj2

        ancestors = self.dict_obj.all_ancestors_with_id
        self.assertEqual(len(ancestors), 3)
        self.assertEqual(["ancestor_1", "ancestor_2", "ancestor_3"], [a.id for a in ancestors])

    def test_setitem_with_valid_value(self):
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.dict_obj["key"] = self.mock_explainable_obj

        self.assertIn("key", self.dict_obj)
        self.mock_explainable_obj.set_modeling_obj_container.assert_called_with(
            new_modeling_obj_container=self.mock_modeling_obj, attr_name="attr_name"
        )

    def test_setitem_with_invalid_value(self):
        with self.assertRaises(ValueError):
            self.dict_obj["key"] = "Invalid value"

    def test_set_modeling_obj_container_registers_and_unregisters_modeling_object_keys(self):
        modeled_key = create_mod_obj_mock(ModelingObject, name="tracked_key", id="tracked_key")
        self.dict_obj[modeled_key] = SourceValue(1 * u.dimensionless, label="tracked value")

        self.assertEqual([], modeled_key.explainable_object_dicts_containers)

        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.assertEqual([self.dict_obj], modeled_key.explainable_object_dicts_containers)

        self.dict_obj.set_modeling_obj_container(None, None)
        self.assertEqual([], modeled_key.explainable_object_dicts_containers)

    def test_delitem_unregisters_modeling_object_keys_and_unlinks_removed_values(self):
        modeled_key = create_mod_obj_mock(
            ModelingObject, name="tracked_key_for_deletion", id="tracked_key_for_deletion")
        tracked_value = SourceValue(2 * u.dimensionless, label="tracked deletion value")
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.dict_obj[modeled_key] = tracked_value

        del self.dict_obj[modeled_key]

        self.assertEqual([], modeled_key.explainable_object_dicts_containers)
        self.assertIsNone(tracked_value.modeling_obj_container)
        self.assertIsNone(tracked_value.attr_name_in_mod_obj_container)

    def test_clear_unregisters_all_modeling_object_keys(self):
        first_key = create_mod_obj_mock(ModelingObject, name="first_tracked_key", id="first_tracked_key")
        second_key = create_mod_obj_mock(ModelingObject, name="second_tracked_key", id="second_tracked_key")
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.dict_obj[first_key] = SourceValue(1 * u.dimensionless, label="first clear value")
        self.dict_obj[second_key] = SourceValue(2 * u.dimensionless, label="second clear value")

        self.dict_obj.clear()

        self.assertEqual([], first_key.explainable_object_dicts_containers)
        self.assertEqual([], second_key.explainable_object_dicts_containers)
        self.assertEqual(0, len(self.dict_obj))

    def test_detached_dict_does_not_unlink_already_modeled_values(self):
        real_modeling_obj = ModelingObjectForContainerTest("real_modeling_obj")
        modeled_value = ExplainableQuantity(3 * u.dimensionless, label="modeled value")
        modeled_value.set_modeling_obj_container(real_modeling_obj, "attr_name")
        modeled_child = ExplainableQuantity(
            6 * u.dimensionless, label="modeled child", left_parent=modeled_value, operator="duplicate")
        modeled_child.set_modeling_obj_container(real_modeling_obj, "other_attr")

        detached_dict = ExplainableObjectDict()
        detached_dict["preserved"] = modeled_value

        self.assertEqual(real_modeling_obj, modeled_value.modeling_obj_container)
        self.assertEqual("attr_name", modeled_value.attr_name_in_mod_obj_container)
        self.assertIn(modeled_child, modeled_value.direct_children_with_id)

    def test_to_json(self):
        self.dict_obj[self.mock_modeling_obj] = self.mock_explainable_obj
        json_output = self.dict_obj.to_json()
        self.assertEqual(json_output, {"mock_id": {"key": "value"}})

    def test_repr(self):
        self.dict_obj[self.mock_modeling_obj] = self.mock_explainable_obj
        repr_output = repr(self.dict_obj)
        self.assertTrue("mock_id" in repr_output)

    def test_str(self):
        mock_modeling_obj = create_mod_obj_mock(
            ModelingObject, name="mock_modeling_obj", id="mock_modeling_obj_id", class_as_simple_str="ModelingObject"
        )
        self.dict_obj[mock_modeling_obj] = self.mock_explainable_obj
        str_output = str(self.dict_obj)
        self.assertTrue("mock_modeling_obj_id" in str_output)
        self.assertTrue("mock_modeling_obj" in str_output)
        self.assertTrue("ModelingObject" in str_output)

class TestExplainableObjectDictTriggerFlag(unittest.TestCase):

    def test_trigger_defaults_false(self):
        d = ExplainableObjectDict()
        self.assertFalse(d.trigger_modeling_updates)

    def test_trigger_can_be_set_to_true(self):
        d = ExplainableObjectDict()
        d.trigger_modeling_updates = True
        self.assertTrue(d.trigger_modeling_updates)

    def test_no_trigger_setitem_stores_value(self):
        d = ExplainableObjectDict()
        val = SourceValue(1 * u.dimensionless)
        d["key"] = val
        self.assertIs(d["key"], val)

    def test_no_trigger_setitem_replaces_existing_key(self):
        d = ExplainableObjectDict()
        val1 = SourceValue(1 * u.dimensionless)
        val2 = SourceValue(2 * u.dimensionless)
        d["key"] = val1
        d["key"] = val2
        self.assertIs(d["key"], val2)

    def test_no_trigger_delitem_removes_key(self):
        d = ExplainableObjectDict()
        val = SourceValue(1 * u.dimensionless)
        d["key"] = val
        del d["key"]
        self.assertNotIn("key", d)

    def test_init_with_input_dict_respects_no_trigger(self):
        val = SourceValue(5 * u.dimensionless)
        d = ExplainableObjectDict({"k": val})
        self.assertIs(d["k"], val)
        self.assertFalse(d.trigger_modeling_updates)

    def test_trigger_flag_on_dict_with_modeling_obj_container(self):
        """Even when linked to a modeling object, trigger defaults to False."""
        real_obj = ModelingObjectForContainerTest("test_obj")
        d = ExplainableObjectDict()
        d.set_modeling_obj_container(real_obj, "attr_name")
        self.assertFalse(d.trigger_modeling_updates)


class TestExplainableObjectDictStructuralContext(unittest.TestCase):

    def test_structural_input_dict_populates_contextual_containers(self):
        child_a = ModelingObjectForContainerTest("child_a")
        child_b = ModelingObjectForContainerTest("child_b")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_with_input_dict",
            input_dict={
                child_a: SourceValue(1 * u.dimensionless, label="child a count"),
                child_b: SourceValue(2 * u.dimensionless, label="child b count"),
            },
        )

        self.assertEqual([owner], child_a.modeling_obj_containers)
        self.assertEqual([owner], child_b.modeling_obj_containers)
        contextual_link = next(
            container for container in child_a.contextual_modeling_obj_containers
            if isinstance(container, ContextualModelingObjectDictKey))
        self.assertIs(owner, contextual_link.modeling_obj_container)
        self.assertEqual("input_dict", contextual_link.attr_name_in_mod_obj_container)
        self.assertIs(owner.input_dict, contextual_link.dict_container)
        self.assertIs(child_a, contextual_link.key_in_dict)

    def test_calculated_dict_does_not_populate_contextual_containers(self):
        impacted_object = ModelingObjectForContainerTest("impacted_object")
        owner = ModelingObjectForContainerTest("owner_with_calculated_dict")

        owner.calculated_dict = ExplainableObjectDict({
            impacted_object: SourceValue(1 * u.concurrent, label="calculated value")})

        self.assertEqual([], impacted_object.modeling_obj_containers)
        self.assertEqual([owner.calculated_dict], impacted_object.explainable_object_dicts_containers)

    def test_replacing_structural_dict_updates_contextual_containers(self):
        old_child = ModelingObjectForContainerTest("old_child")
        new_child = ModelingObjectForContainerTest("new_child")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_for_replacement",
            input_dict={old_child: SourceValue(1 * u.dimensionless, label="old child count")},
        )

        owner.trigger_modeling_updates = False
        owner.input_dict = ExplainableObjectDict({
            new_child: SourceValue(2 * u.dimensionless, label="new child count")})
        owner.trigger_modeling_updates = True

        self.assertEqual([], old_child.modeling_obj_containers)
        self.assertEqual([owner], new_child.modeling_obj_containers)

    def test_structural_dict_entry_insertion_and_removal_keep_contextual_containers_in_sync(self):
        existing_child = ModelingObjectForContainerTest("existing_child")
        inserted_child = ModelingObjectForContainerTest("inserted_child")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_for_mutation",
            input_dict={existing_child: SourceValue(1 * u.dimensionless, label="existing child count")},
        )

        owner.input_dict.trigger_modeling_updates = False
        owner.input_dict[inserted_child] = SourceValue(3 * u.dimensionless, label="inserted child count")
        self.assertEqual([owner], inserted_child.modeling_obj_containers)

        del owner.input_dict[inserted_child]
        self.assertEqual([], inserted_child.modeling_obj_containers)

    def test_detaching_structural_dict_removes_key_contextual_containers(self):
        """Regression: set_modeling_obj_container(None, None) used to only zero the stale
        container's fields instead of removing it from the key's list, leaving zombie
        ContextualModelingObjectDictKey entries behind on every apply/revert cycle inside
        ModelingUpdate."""
        child = ModelingObjectForContainerTest("child_for_detach_check")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_for_detach_check",
            input_dict={child: SourceValue(1 * u.dimensionless, label="child count")},
        )

        self.assertEqual(
            1,
            sum(
                isinstance(c, ContextualModelingObjectDictKey)
                for c in child.contextual_modeling_obj_containers
            ),
        )

        # Simulate the apply/revert/apply cycle that ModelingUpdate performs when swapping
        # the dict in and out of its container during sort logic.
        owner.input_dict.set_modeling_obj_container(None, None)
        owner.input_dict.set_modeling_obj_container(owner, "input_dict")
        owner.input_dict.set_modeling_obj_container(None, None)

        self.assertEqual(
            [],
            [c for c in child.contextual_modeling_obj_containers
             if isinstance(c, ContextualModelingObjectDictKey)],
        )

        owner.input_dict.set_modeling_obj_container(owner, "input_dict")
        dict_key_containers = [
            c for c in child.contextual_modeling_obj_containers
            if isinstance(c, ContextualModelingObjectDictKey)
        ]
        self.assertEqual(1, len(dict_key_containers))
        live = dict_key_containers[0]
        self.assertIs(owner, live.modeling_obj_container)
        self.assertEqual("input_dict", live.attr_name_in_mod_obj_container)
        self.assertIs(owner.input_dict, live.dict_container)

    def test_triggered_existing_entry_update_on_structural_dict_replaces_value(self):
        existing_child = ModelingObjectForContainerTest("existing_child_for_update")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_for_existing_entry_update",
            input_dict={existing_child: SourceValue(1 * u.dimensionless, label="initial child count")},
        )

        owner.input_dict.trigger_modeling_updates = True
        owner.input_dict[existing_child] = SourceValue(3 * u.dimensionless, label="updated child count")

        self.assertEqual(3, owner.input_dict[existing_child].value.magnitude)
        self.assertEqual(owner, owner.input_dict[existing_child].modeling_obj_container)
        self.assertEqual("input_dict", owner.input_dict[existing_child].attr_name_in_mod_obj_container)


class TestToWeightedExplainableObjectDict(unittest.TestCase):

    def setUp(self):
        self.key_a = create_mod_obj_mock(ModelingObject, name="key_a", id="key_a")
        self.key_b = create_mod_obj_mock(ModelingObject, name="key_b", id="key_b")

    def test_none_returns_empty_weighted_explainable_object_dict(self):
        result = to_weighted_explainable_object_dict(None)
        self.assertIsInstance(result, WeightedExplainableObjectDict)
        self.assertEqual({}, result)

    def test_list_entries_get_weight_one_and_duplicates_accumulate(self):
        result = to_weighted_explainable_object_dict([self.key_a, self.key_b, self.key_b])
        self.assertEqual([self.key_a, self.key_b], list(result.keys()))
        self.assertEqual(1, result[self.key_a].value.magnitude)
        self.assertEqual(2, result[self.key_b].value.magnitude)
        self.assertTrue(result[self.key_b].value.check("[]"))

    def test_plain_number_values_are_wrapped_as_dimensionless_hypothesis_source_values(self):
        result = to_weighted_explainable_object_dict({self.key_a: 3, self.key_b: 0.5})
        self.assertIsInstance(result[self.key_a], SourceValue)
        self.assertEqual(3, result[self.key_a].value.magnitude)
        self.assertEqual(0.5, result[self.key_b].value.magnitude)
        self.assertTrue(result[self.key_a].value.check("[]"))
        self.assertEqual(Sources.HYPOTHESIS, result[self.key_a].source)

    def test_explainable_object_values_are_passed_through_unchanged(self):
        weight = SourceValue(4 * u.dimensionless, label="hand-declared weight")
        result = to_weighted_explainable_object_dict({self.key_a: weight})
        self.assertIs(weight, result[self.key_a])
        self.assertEqual("hand-declared weight", result[self.key_a].label)

    def test_weight_label_is_applied_to_wrapped_values_only(self):
        passthrough_weight = SourceValue(4 * u.dimensionless, label="my own label")
        result = to_weighted_explainable_object_dict(
            {self.key_a: 2, self.key_b: passthrough_weight}, weight_label="Times per step")
        self.assertEqual("Times per step", result[self.key_a].label)
        self.assertEqual("my own label", result[self.key_b].label)

    def test_zero_weight_is_accepted(self):
        result = to_weighted_explainable_object_dict({self.key_a: 0})
        self.assertEqual(0, result[self.key_a].value.magnitude)

    def test_negative_plain_number_raises(self):
        with self.assertRaises(ValueError) as ctx:
            to_weighted_explainable_object_dict({self.key_a: -1})
        self.assertIn("non-negative", str(ctx.exception))

    def test_negative_explainable_object_raises(self):
        with self.assertRaises(ValueError):
            to_weighted_explainable_object_dict({self.key_a: SourceValue(-2 * u.dimensionless)})

    def test_non_dimensionless_explainable_object_raises(self):
        with self.assertRaises(ValueError) as ctx:
            to_weighted_explainable_object_dict({self.key_a: SourceValue(3 * u.kg)})
        self.assertIn("dimensionless", str(ctx.exception))

    def test_invalid_value_type_raises(self):
        with self.assertRaises(ValueError):
            to_weighted_explainable_object_dict({self.key_a: "3"})

    def test_non_quantity_explainable_object_value_raises(self):
        with self.assertRaises(ValueError) as ctx:
            to_weighted_explainable_object_dict({self.key_a: EmptyExplainableObject()})
        self.assertIn("ExplainableQuantity", str(ctx.exception))

    def test_invalid_input_type_raises(self):
        with self.assertRaises(ValueError):
            to_weighted_explainable_object_dict(self.key_a)

    def test_normalized_dict_keys_register_as_structural_relationship(self):
        """A normalizer-built dict passed at construction registers its keys exactly like a hand-built dict:
        the keys know their containing dict and gain a contextual dict-key container pointing at the owner."""
        key = ModelingObjectForContainerTest("weighted_key")
        owner = ModelingObjectWithInputDictForContainerTest(
            "owner_of_weighted_dict", input_dict=to_weighted_explainable_object_dict([key, key]))

        self.assertEqual([owner.input_dict], key.explainable_object_dicts_containers)
        contextual_dict_keys = [container for container in key.contextual_modeling_obj_containers
                                if isinstance(container, ContextualModelingObjectDictKey)]
        self.assertEqual(1, len(contextual_dict_keys))
        self.assertEqual(owner, contextual_dict_keys[0].modeling_obj_container)
        self.assertEqual("input_dict", contextual_dict_keys[0].attr_name_in_mod_obj_container)
        self.assertEqual(2, owner.input_dict[key].value.magnitude)


class TestWeightedExplainableObjectDict(unittest.TestCase):
    """The weight invariant (ExplainableQuantity, dimensionless, non-negative) must hold on every __setitem__,
    not only at the normalizer's constructor boundary."""

    def setUp(self):
        self.key = create_mod_obj_mock(ModelingObject, name="weighted_dict_key", id="weighted_dict_key")
        self.weighted_dict = to_weighted_explainable_object_dict({self.key: 1})

    def test_setitem_rejects_negative_weight(self):
        with self.assertRaises(ValueError) as ctx:
            self.weighted_dict[self.key] = SourceValue(-2 * u.dimensionless)
        self.assertIn("non-negative", str(ctx.exception))

    def test_setitem_rejects_non_dimensionless_weight(self):
        with self.assertRaises(ValueError) as ctx:
            self.weighted_dict[self.key] = SourceValue(3 * u.kg)
        self.assertIn("dimensionless", str(ctx.exception))

    def test_setitem_rejects_non_quantity_value(self):
        with self.assertRaises(ValueError) as ctx:
            self.weighted_dict[self.key] = EmptyExplainableObject()
        self.assertIn("ExplainableQuantity", str(ctx.exception))

    def test_valid_setitem_still_works(self):
        self.weighted_dict[self.key] = SourceValue(5 * u.dimensionless, label="updated weight")
        self.assertEqual(5, self.weighted_dict[self.key].value.magnitude)


if __name__ == "__main__":
    unittest.main()
