import unittest
from functools import cached_property
from unittest.mock import patch, MagicMock, PropertyMock, call

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import (
    ModelingObject, class_cached_property_names, flush_cached_properties_system_wide,
    optimize_mod_objs_computation_chain)
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
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

    def __init__(self, name, custom_input: ObjectLinkedToModelingObjBase=None,
                 custom_input2: ObjectLinkedToModelingObjBase=None, custom_list_input: list=None,
                 custom_dict_input: ExplainableObjectDict = None,
                 mod_obj_input1: ModelingObject=None, mod_obj_input2: ModelingObject=None):
        super().__init__(name)
        if custom_input:
            self.custom_input = custom_input
        if custom_input2:
            self.custom_input2 = custom_input2
        if custom_list_input:
            self.custom_list_input = custom_list_input
        if custom_dict_input:
            self.custom_dict_input = ExplainableObjectDict(custom_dict_input)
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


class CachedPropertyModelingObject(ModelingObject):
    default_values = {}

    @cached_property
    def custom_lazy_projection(self):
        return ExplainableQuantity(7 * u.kg, label="custom lazy projection")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class CalculatedDictModelingObject(ModelingObject):
    default_values = {}
    calculated_attributes = ["calculated_dict"]

    def __init__(self, name, targets: list = None):
        super().__init__(name)
        self.targets = targets or []
        self.calculated_dict = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []

    def update_dict_element_in_calculated_dict(self, modeling_object):
        self.calculated_dict[modeling_object] = ExplainableQuantity(
            1 * u.concurrent, label=f"{modeling_object.name} calculated value")

    def update_calculated_dict(self):
        self.calculated_dict = ExplainableObjectDict()
        for modeling_object in self.targets:
            self.update_dict_element_in_calculated_dict(modeling_object)


class CanonicalParentModelingObject(ModelingObjectForTesting):
    pass


class CanonicalChildModelingObject(CanonicalParentModelingObject):
    pass


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
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObjBase)
        mod_obj = ModelingObjectForTesting("test", custom_input=old_value)

        value = MagicMock(
            modeling_obj_container=None, left_parent=None, right_parent=None, spec=ObjectLinkedToModelingObjBase)
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

    @patch("efootprint.all_classes_in_order.CANONICAL_COMPUTATION_ORDER", [CanonicalParentModelingObject])
    def test_canonical_class_returns_first_matching_canonical_class(self):
        """Test canonical class property resolves the first matching canonical class."""
        child_obj = CanonicalChildModelingObject("child_object")

        self.assertIs(CanonicalParentModelingObject, CanonicalChildModelingObject.canonical_class)
        self.assertIs(CanonicalParentModelingObject, child_obj.canonical_class)

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

        mod_obj1.efootprint_class = UsagePattern
        mod_obj2.efootprint_class = UsageJourney
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

        mod_obj5.efootprint_class = UsagePattern
        mod_obj1.efootprint_class = UsageJourney
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

    def test_copy_with_clones_object_linked_inputs(self):
        source_value = SourceValue(10 * u.dimensionless)
        mod_obj = ModelingObjectForTesting("original", custom_input=source_value)

        copied = mod_obj.copy_with()

        self.assertEqual(copied.name, "original copy")
        self.assertIsNot(mod_obj.custom_input, copied.custom_input)
        self.assertEqual(mod_obj.custom_input.value, copied.custom_input.value)

    def test_copy_with_requires_modeling_object_overrides(self):
        child = ModelingObjectForTesting("child")
        parent = ModelingObjectForTesting("parent", mod_obj_input1=child)

        with self.assertRaisesRegex(ValueError, "mod_obj_input1"):
            parent.copy_with()

    def test_copy_with_requires_list_overrides(self):
        child = ModelingObjectForTesting("child")
        parent = ModelingObjectForTesting(
            "parent", custom_list_input=ListLinkedToModelingObj([child]))

        with self.assertRaisesRegex(ValueError, "custom_list_input"):
            parent.copy_with()

    def test_copy_with_supports_overrides(self):
        child = ModelingObjectForTesting("child")
        parent = ModelingObjectForTesting(
            "parent",
            custom_input=SourceValue(5 * u.dimensionless),
            mod_obj_input1=child,
            custom_list_input=ListLinkedToModelingObj([child]),
        )
        new_child = ModelingObjectForTesting("new child")

        copied = parent.copy_with(
            name="parent clone",
            mod_obj_input1=new_child,
            custom_list_input=[new_child],
        )

        self.assertEqual(copied.name, "parent clone")
        self.assertEqual(copied.mod_obj_input1, new_child)
        self.assertEqual(copied.custom_list_input, [new_child])
        self.assertEqual(copied.custom_input.value, parent.custom_input.value)

    def test_nb_of_occurrences_per_container_counts_repeated_links_and_ignores_detached_containers(self):
        child = ModelingObjectForTesting("occurrence_child")
        parent_a = ModelingObjectForTesting(
            "occurrence_parent_a", mod_obj_input1=child, mod_obj_input2=child)
        parent_b = ModelingObjectForTesting(
            "occurrence_parent_b", custom_list_input=ListLinkedToModelingObj([child, child]))
        other_child = ModelingObjectForTesting("other_occurrence_child")
        detached_parent = ModelingObjectForTesting(
            "detached_occurrence_parent", custom_list_input=ListLinkedToModelingObj([child, other_child]))
        detached_parent.trigger_modeling_updates = False
        detached_parent.custom_list_input = ListLinkedToModelingObj([other_child])
        detached_parent.trigger_modeling_updates = True

        occurrences = child.nb_of_occurrences_per_container

        self.assertEqual(2, len(occurrences))
        self.assertEqual(2, occurrences[parent_a].magnitude)
        self.assertEqual(2, occurrences[parent_b].magnitude)
        self.assertEqual(u.dimensionless, occurrences[parent_a].unit)
        self.assertEqual(u.dimensionless, occurrences[parent_b].unit)
        self.assertNotIn(detached_parent, occurrences)

    def test_from_json_dict_initializes_dict_calculated_attributes_as_explainable_object_dict(self):
        """Test that from_json_dict uses ExplainableObjectDict for attributes with update_dict_element_in_ methods."""
        obj = CalculatedDictModelingObject("dict_attr_obj", targets=[])
        json_dict = obj.to_json()

        restored, _ = CalculatedDictModelingObject.from_json_dict(json_dict, flat_obj_dict={})

        self.assertIsInstance(restored.calculated_dict, ExplainableObjectDict)

    def test_class_cached_property_names_discovers_cached_properties_across_mro(self):
        """Test that auto-discovery finds cached properties declared on the base class and on subclasses."""
        names = class_cached_property_names(CachedPropertyModelingObject)

        self.assertIn("custom_lazy_projection", names)
        self.assertIn("render_cache", names)

    def test_flush_cached_properties_pops_every_materialized_cached_property(self):
        """Test that flush_cached_properties clears subclass-declared cached properties and the render cache,
        without needing any manual registry."""
        obj = CachedPropertyModelingObject("flush_target")
        self.assertEqual(7, obj.custom_lazy_projection.magnitude)
        obj.render_cache["memo_key"] = "memo_value"

        obj.flush_cached_properties()

        self.assertNotIn("custom_lazy_projection", obj.__dict__)
        self.assertNotIn("render_cache", obj.__dict__)

    def test_to_json_and_setattr_skip_auto_discovered_cached_properties(self):
        """Test that a materialized subclass cached property is excluded from to_json and from update logic."""
        obj = CachedPropertyModelingObject("json_target")
        _ = obj.custom_lazy_projection
        _ = obj.render_cache

        self.assertIn("custom_lazy_projection", obj.attributes_that_shouldnt_trigger_update_logic)
        json_output = obj.to_json()

        self.assertNotIn("custom_lazy_projection", json_output)
        self.assertNotIn("render_cache", json_output)

    def test_flush_cached_properties_system_wide_sweeps_all_linked_objects(self):
        """Test that the system-wide flush reaches every object linked to the systems of the given objects."""
        linked_member = CachedPropertyModelingObject("linked_member")
        _ = linked_member.custom_lazy_projection

        class FakeSystem(CachedPropertyModelingObject):
            @property
            def all_linked_objects(self):
                return [linked_member]

            @property
            def systems(self):
                return [self]

        fake_system = FakeSystem("fake_system")
        _ = fake_system.custom_lazy_projection

        flush_cached_properties_system_wide([fake_system])

        self.assertNotIn("custom_lazy_projection", linked_member.__dict__)
        self.assertNotIn("custom_lazy_projection", fake_system.__dict__)

    def test_modeling_update_replacement_preserves_structural_dict_parent_recovery(self):
        old_child = ModelingObjectForTesting("old_dict_child")
        new_child = ModelingObjectForTesting("new_dict_child")
        parent = ModelingObjectForTesting(
            "dict_parent",
            custom_dict_input=ExplainableObjectDict({
                old_child: SourceValue(1 * u.dimensionless, label="old dict child count"),
            }),
        )

        with patch("efootprint.all_classes_in_order.CANONICAL_COMPUTATION_ORDER", [ModelingObjectForTesting]):
            ModelingUpdate([[
                parent.custom_dict_input,
                ExplainableObjectDict({new_child: SourceValue(2 * u.dimensionless, label="new dict child count")}),
            ]])

        self.assertEqual([], old_child.modeling_obj_containers)
        self.assertEqual([parent], new_child.modeling_obj_containers)

class TestValidationAttributes(unittest.TestCase):
    def test_validation_attributes_returns_attributes_ending_with_validation(self):
        """Test that validation_attributes filters only _validation suffixed attributes."""
        obj = ModelingObjectForTesting("test")
        with patch.object(type(obj), "calculated_attributes", new_callable=PropertyMock,
                          return_value=["lifespan_validation", "energy_footprint",
                                        "component_needs_edge_device_validation", "fabrication_footprint"]):
            self.assertEqual(["lifespan_validation", "component_needs_edge_device_validation"],
                             obj.validation_attributes)

    def test_calculated_attributes_without_validations_excludes_validation_attributes(self):
        """Test that calculated_attributes_without_validations excludes _validation suffixed attributes."""
        obj = ModelingObjectForTesting("test")
        with patch.object(type(obj), "calculated_attributes", new_callable=PropertyMock,
                          return_value=["lifespan_validation", "energy_footprint",
                                        "component_needs_edge_device_validation", "fabrication_footprint"]):
            self.assertEqual(["energy_footprint", "fabrication_footprint"],
                             obj.calculated_attributes_without_validations)

    def test_no_validation_attributes_returns_empty_list(self):
        """Test that validation_attributes returns empty list when no validations exist."""
        obj = ModelingObjectForTesting("test")
        with patch.object(type(obj), "calculated_attributes", new_callable=PropertyMock,
                          return_value=["energy_footprint", "fabrication_footprint"]):
            self.assertEqual([], obj.validation_attributes)
            self.assertEqual(["energy_footprint", "fabrication_footprint"],
                             obj.calculated_attributes_without_validations)


class TestCheckBelongingToAuthorizedValues(unittest.TestCase):
    """Pins the dotted-path traversal in `conditional_list_values['depends_on']`. Single-segment
    paths (back-compat) and multi-segment paths must both resolve through `getattr`, and a missing
    intermediate attribute must short-circuit to the existing "value not set" error.

    Synthetic attributes are written through `object.__setattr__` to bypass the framework's
    input-validation / update machinery — the unit under test here is the conditional-list lookup,
    not the setter."""

    def _make_obj(self, depends_on: str):
        obj = ModelingObjectForTesting("test")
        a_value, b_value = SourceObject("a"), SourceObject("b")
        object.__setattr__(obj, "conditional_list_values", {
            "child": {
                "depends_on": depends_on,
                "conditional_list_values": {a_value: [SourceObject("x")], b_value: [SourceObject("y")]},
            }
        })
        return obj, a_value, b_value

    def test_single_segment_path_resolves_via_getattr(self):
        obj, a_value, _ = self._make_obj("parent_attr")
        object.__setattr__(obj, "parent_attr", a_value)
        obj.check_belonging_to_authorized_values("child", SourceObject("x"), {})
        with self.assertRaises(ValueError):
            obj.check_belonging_to_authorized_values("child", SourceObject("y"), {})

    def test_dotted_path_traverses_each_segment(self):
        obj, a_value, _ = self._make_obj("intermediate.parent_attr")
        intermediate = MagicMock()
        intermediate.parent_attr = a_value
        object.__setattr__(obj, "intermediate", intermediate)
        obj.check_belonging_to_authorized_values("child", SourceObject("x"), {})
        with self.assertRaises(ValueError):
            obj.check_belonging_to_authorized_values("child", SourceObject("y"), {})

    def test_dotted_path_short_circuits_when_intermediate_is_none(self):
        obj, _, _ = self._make_obj("intermediate.parent_attr")
        object.__setattr__(obj, "intermediate", None)
        with self.assertRaisesRegex(ValueError, "intermediate.parent_attr"):
            obj.check_belonging_to_authorized_values("child", SourceObject("x"), {})


if __name__ == "__main__":
    unittest.main()
