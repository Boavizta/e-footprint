import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases
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


class ImpactRepartitionCachingModelingObject(ModelingObject):
    default_values = {}

    def __init__(self, name, targets: list = None, energy_footprint: ExplainableObject = None):
        super().__init__(name)
        self.targets = targets or []
        if energy_footprint is not None:
            self.energy_footprint = energy_footprint

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []

    def update_dict_element_in_usage_impact_repartition_weights(self, modeling_object):
        self.usage_impact_repartition_weights[modeling_object] = ExplainableQuantity(
            1 * u.concurrent, label=f"{modeling_object.name} weight in {self.name} impact repartition")

    def update_usage_impact_repartition_weights(self):
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for modeling_object in self.targets:
            self.update_dict_element_in_usage_impact_repartition_weights(modeling_object)


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

    def test_update_impact_repartition_weights_uses_container_weight_sums_and_occurrences(self):
        child = ModelingObjectForTesting("weighted_child")
        parent_a = ModelingObjectForTesting("weighted_parent_a", mod_obj_input1=child, mod_obj_input2=child)
        parent_b = ModelingObjectForTesting("weighted_parent_b", mod_obj_input1=child)
        weight_target_a = ModelingObjectForTesting("weight_target_a")
        weight_target_b = ModelingObjectForTesting("weight_target_b")
        weight_target_c = ModelingObjectForTesting("weight_target_c")
        parent_a.usage_impact_repartition_weights = ExplainableObjectDict({
            weight_target_a: ExplainableQuantity(2 * u.concurrent, label="parent a weight 1"),
            weight_target_b: ExplainableQuantity(3 * u.concurrent, label="parent a weight 2"),
        })
        parent_b.usage_impact_repartition_weights = ExplainableObjectDict({
            weight_target_c: ExplainableQuantity(7 * u.concurrent, label="parent b weight"),
        })

        child.update_usage_impact_repartition_weights()

        self.assertEqual(10, child.usage_impact_repartition_weights[parent_a].magnitude)
        self.assertEqual(7, child.usage_impact_repartition_weights[parent_b].magnitude)
        self.assertEqual(u.concurrent, child.usage_impact_repartition_weights[parent_a].unit)

    def test_update_impact_repartition_normalizes_weights(self):
        child = ModelingObjectForTesting("repartition_child")
        parent_a = ModelingObjectForTesting("repartition_parent_a")
        parent_b = ModelingObjectForTesting("repartition_parent_b")
        child.usage_impact_repartition_weights = ExplainableObjectDict({
            parent_a: ExplainableQuantity(2 * u.concurrent, label="parent a weight"),
            parent_b: ExplainableQuantity(6 * u.concurrent, label="parent b weight"),
        })

        child.update_usage_impact_repartition_weight_sum()
        child.update_usage_impact_repartition()

        self.assertEqual(8, child.usage_impact_repartition_weight_sum.magnitude)
        self.assertAlmostEqual(0.25, child.usage_impact_repartition[parent_a].magnitude)
        self.assertAlmostEqual(0.75, child.usage_impact_repartition[parent_b].magnitude)
        self.assertEqual(u.concurrent, child.usage_impact_repartition[parent_a].unit)

    def test_update_dict_element_in_impact_repartition_returns_empty_object_when_weight_sum_is_zero(self):
        child = ModelingObjectForTesting("zero_weight_child")
        parent = ModelingObjectForTesting("zero_weight_parent")
        child.usage_impact_repartition_weights = ExplainableObjectDict({
            parent: ExplainableQuantity(0 * u.concurrent, label="zero weight"),
        })

        child.update_usage_impact_repartition_weight_sum()
        child.update_dict_element_in_usage_impact_repartition(parent)

        self.assertIsInstance(child.usage_impact_repartition[parent], EmptyExplainableObject)

    def test_attributed_footprint_per_source_returns_source_values_for_impact_sources(self):
        source = ModelingObjectForTesting("full_source")
        source.trigger_modeling_updates = False
        source.__setattr__("energy_footprint", SourceValue(5 * u.kg), check_input_validity=False)
        source.__setattr__("instances_fabrication_footprint", SourceValue(2 * u.kg), check_input_validity=False)
        source.trigger_modeling_updates = True

        attributed_footprint_per_source = source.attributed_footprint_per_source

        self.assertTrue(source.is_impact_source)
        self.assertEqual(2, attributed_footprint_per_source[LifeCyclePhases.MANUFACTURING][source].magnitude)
        self.assertEqual(5, attributed_footprint_per_source[LifeCyclePhases.USAGE][source].magnitude)

    def test_attributed_energy_footprint_per_source_propagates_through_usage_impact_repartition(self):
        source = ModelingObjectForTesting("energy_source")
        source.trigger_modeling_updates = False
        source.__setattr__("energy_footprint", SourceValue(12 * u.kg), check_input_validity=False)
        source.trigger_modeling_updates = True
        child = ModelingObjectForTesting("energy_child")
        source.usage_impact_repartition = ExplainableObjectDict({
            child: ExplainableQuantity(0.25 * u.concurrent, label="source to child energy attribution"),
        })

        attributed_energy_footprint_per_source = child.attributed_energy_footprint_per_source

        self.assertEqual(3, attributed_energy_footprint_per_source[source].magnitude)
        self.assertEqual(3, child.attributed_energy_footprint.magnitude)

    def test_attributed_fabrication_footprint_per_source_propagates_through_fabrication_impact_repartition(self):
        source = ModelingObjectForTesting("fabrication_source")
        source.trigger_modeling_updates = False
        source.__setattr__("instances_fabrication_footprint", SourceValue(8 * u.kg), check_input_validity=False)
        source.trigger_modeling_updates = True
        child = ModelingObjectForTesting("fabrication_child")
        source.fabrication_impact_repartition = ExplainableObjectDict({
            child: ExplainableQuantity(0.5 * u.concurrent, label="source to child fabrication attribution"),
        })

        attributed_fabrication_footprint_per_source = child.attributed_fabrication_footprint_per_source

        self.assertEqual(4, attributed_fabrication_footprint_per_source[source].magnitude)
        self.assertEqual(4, child.attributed_fabrication_footprint.magnitude)

    def test_invalidate_impact_repartition_cache_non_recursive_only_clears_current_object_cache(self):
        source = ModelingObjectForTesting("cache_source")
        source.trigger_modeling_updates = False
        source.__setattr__("energy_footprint", SourceValue(10 * u.kg), check_input_validity=False)
        source.trigger_modeling_updates = True
        child = ModelingObjectForTesting("cache_child")
        source.usage_impact_repartition = ExplainableObjectDict({
            child: ExplainableQuantity(1 * u.concurrent, label="source to child attribution"),
        })

        _ = source.attributed_energy_footprint
        _ = child.attributed_energy_footprint

        source.invalidate_impact_repartition_cache()

        self.assertNotIn("attributed_energy_footprint", source.__dict__)
        self.assertIn("attributed_energy_footprint", child.__dict__)

    def test_update_impact_repartition_invalidates_cached_attributed_energy_footprint_recursively(self):
        root = ImpactRepartitionCachingModelingObject("root", energy_footprint=SourceValue(10 * u.kg))
        grandchild = ImpactRepartitionCachingModelingObject("grandchild")
        child = ImpactRepartitionCachingModelingObject("child", targets=[grandchild])
        root.trigger_modeling_updates = False
        root.targets = [child]
        root.trigger_modeling_updates = True

        child.update_usage_impact_repartition_weights()
        child.update_usage_impact_repartition_weight_sum()
        child.update_usage_impact_repartition()
        root.update_usage_impact_repartition_weights()
        root.update_usage_impact_repartition_weight_sum()
        root.update_usage_impact_repartition()

        self.assertEqual(10, grandchild.attributed_energy_footprint.magnitude)
        self.assertIn("attributed_energy_footprint", child.__dict__)
        self.assertIn("attributed_energy_footprint", grandchild.__dict__)

        root.trigger_modeling_updates = False
        root.targets = []
        root.trigger_modeling_updates = True

        root.update_usage_impact_repartition_weights()
        root.update_usage_impact_repartition_weight_sum()
        root.update_usage_impact_repartition()

        self.assertNotIn("attributed_energy_footprint", child.__dict__)
        self.assertNotIn("attributed_energy_footprint", grandchild.__dict__)
        self.assertEqual(0, grandchild.attributed_energy_footprint.magnitude)

    def test_replacing_usage_impact_repartition_updates_explainable_object_dicts_containers(self):
        parent = ImpactRepartitionCachingModelingObject("parent_source", energy_footprint=SourceValue(10 * u.kg))
        old_child = ImpactRepartitionCachingModelingObject("old_child")
        new_child = ImpactRepartitionCachingModelingObject("new_child")
        old_repartition = ExplainableObjectDict({
            old_child: ExplainableQuantity(1 * u.concurrent, label="old child repartition")})

        parent.usage_impact_repartition = old_repartition

        self.assertEqual([old_repartition], old_child.explainable_object_dicts_containers)
        self.assertEqual(10, old_child.attributed_energy_footprint.magnitude)

        parent.usage_impact_repartition = ExplainableObjectDict({
            new_child: ExplainableQuantity(1 * u.concurrent, label="new child repartition")})

        self.assertIsNone(old_repartition.modeling_obj_container)
        self.assertEqual([], old_child.explainable_object_dicts_containers)
        self.assertEqual([parent.usage_impact_repartition], new_child.explainable_object_dicts_containers)

        old_child.invalidate_impact_repartition_cache(recursive=True)
        new_child.invalidate_impact_repartition_cache(recursive=True)

        self.assertEqual(0, old_child.attributed_energy_footprint.magnitude)
        self.assertEqual(10, new_child.attributed_energy_footprint.magnitude)

    def test_from_json_dict_initializes_dict_calculated_attributes_as_explainable_object_dict(self):
        """Test that from_json_dict uses ExplainableObjectDict for attributes with update_dict_element_in_ methods."""
        obj = ImpactRepartitionCachingModelingObject("dict_attr_obj", targets=[])
        json_dict = obj.to_json()

        restored, _ = ImpactRepartitionCachingModelingObject.from_json_dict(json_dict, flat_obj_dict={})

        self.assertIsInstance(restored.usage_impact_repartition_weights, ExplainableObjectDict)

    def test_to_json_skips_cached_impact_repartition_properties(self):
        source = ImpactRepartitionCachingModelingObject("source", energy_footprint=SourceValue(10 * u.kg))
        _ = source.attributed_energy_footprint

        json_output = source.to_json()

        self.assertNotIn("attributed_energy_footprint", json_output)
        self.assertNotIn("attributed_energy_footprint_per_source", json_output)

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


if __name__ == "__main__":
    unittest.main()
