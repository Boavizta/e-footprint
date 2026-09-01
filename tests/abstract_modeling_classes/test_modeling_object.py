import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call

from efootprint.abstract_modeling_classes.explainable_object_dict import (
    ExplainableObjectDict, WeightedExplainableObjectDict)
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.abstract_modeling_classes.reactive_core import computed_dict
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from tests.utils import attach_input

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

    @property
    def systems(self):
        return []


class CalculatedDictModelingObject(ModelingObject):
    default_values = {}

    def __init__(self, name, targets: list = None):
        super().__init__(name)
        self.targets = targets or []

    @property
    def systems(self):
        return []

    @computed_dict(keys="targets")
    def calculated_dict(self, modeling_object):
        return ExplainableQuantity(1 * u.concurrent, label=f"{modeling_object.name} calculated value")


class CanonicalParentModelingObject(ModelingObjectForTesting):
    pass


class CanonicalChildModelingObject(CanonicalParentModelingObject):
    pass


class LifecycleModelingObject(ModelingObject):
    def __init__(self, name, value: ExplainableObject):
        super().__init__(name)
        self.value = value

    def after_init(self):
        self.value = SourceValue(2 * u.dimensionless, label="after init value")


class SignatureTarget(ModelingObjectForTesting):
    pass


class SignatureTargetChild(SignatureTarget):
    pass


class OtherSignatureTarget(ModelingObjectForTesting):
    pass


class SignatureValidationModel(ModelingObject):
    def __init__(
            self, name, target: "SignatureTarget | None", targets: list["SignatureTarget"],
            weights: WeightedExplainableObjectDict["SignatureTarget"]):
        super().__init__(name)
        self.target = target
        self.targets = targets
        self.weights = weights

    @property
    def systems(self):
        return []


class UnresolvableSignatureModel(ModelingObject):
    def __init__(self, name, value: "MissingSignatureType"):
        super().__init__(name)
        self.value = value


class UnsupportedSignatureModel(ModelingObject):
    def __init__(self, name, targets: tuple[SignatureTarget, ...]):
        super().__init__(name)
        self.targets = targets


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

    @patch("efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate")
    def test_construction_and_after_init_are_passive_then_later_assignment_is_transactional(
            self, mock_modeling_update):
        initial_value = SourceValue(1 * u.dimensionless, label="initial value")

        mod_obj = LifecycleModelingObject("lifecycle object", initial_value)

        mock_modeling_update.assert_not_called()
        after_init_value = mod_obj.value
        self.assertEqual(2, after_init_value.magnitude)

        replacement = SourceValue(3 * u.dimensionless, label="replacement value")
        mod_obj.value = replacement

        mock_modeling_update.assert_called_once_with([[after_init_value, replacement]])

    def test_input_change_sets_modeling_obj_containers(self):
        custom_input = MagicMock(spec=ExplainableObject)
        parent_obj = ModelingObjectForTesting(name="parent_object", custom_input=custom_input)
        new_input = MagicMock(spec=ExplainableObject)

        attach_input(parent_obj, "custom_input", new_input)

        new_input.set_modeling_obj_container.assert_called_once_with(parent_obj, "custom_input")
        custom_input.set_modeling_obj_container.assert_has_calls([call(parent_obj, "custom_input"), call(None, None)])

    @patch("efootprint.all_classes_in_order.CANONICAL_CLASSES", [CanonicalParentModelingObject])
    def test_canonical_class_returns_first_matching_canonical_class(self):
        """Test canonical class property resolves the first matching canonical class."""
        child_obj = CanonicalChildModelingObject("child_object")

        self.assertIs(CanonicalParentModelingObject, CanonicalChildModelingObject.canonical_class)
        self.assertIs(CanonicalParentModelingObject, child_obj.canonical_class)


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
        mock_modeling_update_list.assert_called_once()
        changes = mock_modeling_update_list.call_args.args[0]
        self.assertIs(mod_obj.custom_input, changes[0][0])
        self.assertEqual([val1, val2, val3], changes[0][1])

    def test_list_attribute_update_works_with_list_condensed_addition_syntax__no_mocking(
            self):
        from tests.utils import create_mod_obj_mock
        val1 = create_mod_obj_mock(ModelingObject, "val1")
        val2 = create_mod_obj_mock(ModelingObject, "val2")
        # The added member gets its guard slots pulled through a subtree walk reading mod_obj_attributes.
        val3 = create_mod_obj_mock(ModelingObject, "val3", mod_obj_attributes=[])

        mod_obj = ModelingObjectForTesting("test mod obj", custom_list_input=ListLinkedToModelingObj([val1, val2]))

        self.assertEqual(mod_obj.custom_list_input, [val1, val2])
        mod_obj.custom_list_input += [val3]
        self.assertEqual(mod_obj.custom_list_input, [val1, val2, val3])



    def test_mod_obj_attributes(self):
        attr1 = MagicMock(spec=ModelingObject)
        attr2 = MagicMock(spec=ModelingObject)
        mod_obj = ModelingObjectForTesting("test mod obj", mod_obj_input1=attr1, mod_obj_input2=attr2)

        self.assertEqual([attr1, attr2], mod_obj.mod_obj_attributes)

    def test_mod_obj_attributes_includes_structural_dict_keys(self):
        attr1 = MagicMock(spec=ModelingObject)
        dict_key = ModelingObjectForTesting("dict key")
        mod_obj = ModelingObjectForTesting(
            "test mod obj", mod_obj_input1=attr1,
            custom_dict_input={dict_key: SourceValue(2 * u.dimensionless)})

        self.assertEqual([attr1, dict_key], mod_obj.mod_obj_attributes)
        # Dicts sever their keys’ backward links as a whole, so self_delete’s unlink loop must not see them.
        self.assertEqual([attr1], mod_obj.contextual_mod_obj_attributes)

    def test_mod_obj_attributes_excludes_keys_of_dicts_that_arent_init_attributes(self):
        dict_key = ModelingObjectForTesting("dict key")
        mod_obj = ModelingObjectForTesting("test mod obj")
        attach_input(mod_obj, "dict_that_isnt_an_init_attribute", ExplainableObjectDict(
            {dict_key: SourceValue(2 * u.dimensionless)}))

        self.assertEqual([], mod_obj.mod_obj_attributes)

    def test_to_json_correct_export_with_child(self):
        custom_input = MagicMock(spec=ExplainableObject)
        child_obj = ModelingObjectForTesting(name="child_object", custom_input=custom_input)
        parent_obj = ModelingObjectForTesting(name="parent_object",mod_obj_input1=child_obj)

        attach_input(parent_obj, "none_attr", None)
        attach_input(parent_obj, "empty_list_attr", ListLinkedToModelingObj([]))
        attach_input(parent_obj, "source_value_attr", SourceValue(1* u.dimensionless, source=None))

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

        with self.assertRaises(AssertionError):
            attach_input(parent_obj, "int_attr", 42)

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
        attach_input(detached_parent, "custom_list_input", ListLinkedToModelingObj([other_child]))

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

    def test_modeling_update_replacement_preserves_structural_dict_parent_recovery(self):
        old_child = ModelingObjectForTesting("old_dict_child")
        new_child = ModelingObjectForTesting("new_dict_child")
        parent = ModelingObjectForTesting(
            "dict_parent",
            custom_dict_input=ExplainableObjectDict({
                old_child: SourceValue(1 * u.dimensionless, label="old dict child count"),
            }),
        )

        ModelingUpdate([[
            parent.custom_dict_input,
            ExplainableObjectDict({new_child: SourceValue(2 * u.dimensionless, label="new dict child count")}),
        ]])

        self.assertEqual([], old_child.modeling_obj_containers)
        self.assertEqual([parent], new_child.modeling_obj_containers)

    def test_signature_validation_resolves_union_forward_refs_and_contextual_wrappers(self):
        """Test replacement accepts the resolved declared type through its contextual relationship wrapper."""
        old_target = SignatureTarget("old target")
        owner = SignatureValidationModel(
            "signature owner", old_target, [], WeightedExplainableObjectDict())
        new_target = SignatureTargetChild("new target")

        owner.target = new_target

        self.assertEqual(new_target, owner.target)
        with self.assertRaises(TypeError):
            owner.target = OtherSignatureTarget("wrong target")
        self.assertEqual(new_target, owner.target)

    def test_signature_validation_checks_list_members(self):
        """Test a parameterized list accepts declared subclasses and rejects unrelated members before mutation."""
        old_target = SignatureTarget("old list target")
        owner = SignatureValidationModel(
            "list signature owner", None, [old_target], WeightedExplainableObjectDict())
        new_target = SignatureTargetChild("new list target")

        owner.targets = [new_target]

        self.assertEqual([new_target], owner.targets)
        with self.assertRaises(TypeError):
            owner.targets = [OtherSignatureTarget("wrong list target")]
        self.assertEqual([new_target], owner.targets)

    def test_signature_validation_keeps_weighted_dict_key_and_value_contracts_distinct(self):
        """Test a weighted dict's generic type checks keys without misclassifying an entry value as a key."""
        key = SignatureTarget("weighted key")
        initial_weight = SourceValue(1 * u.dimensionless, label="initial weight")
        owner = SignatureValidationModel(
            "weighted signature owner", None, [], WeightedExplainableObjectDict({key: initial_weight}))
        replacement_weight = ExplainableQuantity(2 * u.dimensionless, label="replacement weight")

        owner.weights[key] = replacement_weight

        self.assertIs(replacement_weight, owner.weights[key])
        invalid_weights = WeightedExplainableObjectDict({
            OtherSignatureTarget("wrong weighted key"): SourceValue(1 * u.dimensionless, label="weight"),
        })
        with self.assertRaises(TypeError):
            owner.weights = invalid_weights
        self.assertEqual([key], list(owner.weights))

    def test_signature_validation_preserves_weighted_dict_type_and_batch_atomicity(self):
        """Test an unweighted dict cannot replace a weighted input or let an earlier batch change apply."""
        old_target = SignatureTarget("weighted batch old target")
        key = SignatureTarget("weighted batch key")
        weights = WeightedExplainableObjectDict({
            key: SourceValue(1 * u.dimensionless, label="initial batch weight"),
        })
        owner = SignatureValidationModel("weighted batch owner", old_target, [], weights)
        new_target = SignatureTargetChild("weighted batch new target")
        unweighted = ExplainableObjectDict({
            key: SourceValue(2 * u.dimensionless, label="unweighted replacement"),
        })

        with self.assertRaises(TypeError):
            ModelingUpdate([[owner.target, new_target], [owner.weights, unweighted]])

        self.assertIs(old_target, owner.target._value)
        self.assertIs(weights, owner.weights)
        self.assertIsInstance(owner.weights, WeightedExplainableObjectDict)

        owner.weights = {key: SourceValue(3 * u.dimensionless, label="raw replacement")}

        self.assertIsInstance(owner.weights, WeightedExplainableObjectDict)
        self.assertEqual(3, owner.weights[key].magnitude)

    def test_signature_validation_fails_closed_when_forward_ref_cannot_be_resolved(self):
        """Test an unresolved declared input annotation is rejected instead of bypassing type validation."""
        with self.assertRaisesRegex(TypeError, "Could not resolve UnresolvableSignatureModel.__init__"):
            UnresolvableSignatureModel("unresolvable signature owner", SourceObject("value"))

    def test_signature_validation_fails_closed_for_unsupported_annotation(self):
        with self.assertRaisesRegex(TypeError, "Unsupported ModelingObject input annotation"):
            UnsupportedSignatureModel("unsupported signature owner", (SignatureTarget("target"),))

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
