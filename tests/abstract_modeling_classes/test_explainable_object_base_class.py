from copy import copy
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    _apply_json_metadata
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import Source, SourceValue
from efootprint.builders.timeseries.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import (
    computed_attribute, computed_dict, computed_structure, instance_slot_registry, observe_computations,
    slot_of_attached_value)


class ChildrenLinksLeaf(ModelingObject):
    default_values = {}

    def __init__(self, name, power: ExplainableQuantity):
        super().__init__(name)
        self.power = power.set_label("Power")

    @computed_attribute
    def double_power(self):
        return (self.power * ExplainableQuantity(2 * u.dimensionless, "two")).set_label("Double power")

    @computed_attribute
    def quadruple_power(self):
        return (self.double_power * ExplainableQuantity(2 * u.dimensionless, "two")).set_label("Quadruple power")


class ChildrenLinksHolder(ModelingObject):
    default_values = {}

    def __init__(self, name, leaf: ChildrenLinksLeaf):
        super().__init__(name)
        self.leaf = leaf

    @property
    def selected_leaves(self):
        return [self.leaf] if self.leaf.double_power.magnitude > 0 else []

    @computed_dict(keys="selected_leaves")
    def power_per_selected_leaf(self, leaf):
        return leaf.power.copy().set_label(f"Power of selected {leaf.name}")

    @computed_structure
    def double_power_magnitude(self):
        return self.leaf.double_power.magnitude


class TestExplainableObjectBaseClass(TestCase):
    def setUp(self) -> None:
        self.a = ExplainableObject(1, "a")
        self.b = ExplainableObject(2, "b")

        self.c = ExplainableObject(3, "c")
        self.c.left_parent = self.a
        self.c.right_parent = self.b
        self.c.operator = "+"
        self.c.direct_ancestors_with_id = [self.a, self.b]

        self.d = ExplainableObject(4, "d")
        self.d.left_parent = self.c
        self.d.right_parent = self.a
        self.d.operator = "+"
        self.d.direct_ancestors_with_id = [self.c, self.a]

        self.e = ExplainableObject(5, "e")
        self.e.left_parent = self.c
        self.e.right_parent = self.b
        self.e.operator = "+"
        self.e.label = None
        self.e.direct_ancestors_with_id = [self.c, self.b]

        self.f = ExplainableObject(6, "f")
        self.f.left_parent = self.e
        self.f.right_parent = self.a
        self.f.operator = "+"
        self.f.direct_ancestors_with_id = [self.a]

        self.g = ExplainableObject(2, "g")
        self.g.left_parent = self.d
        self.g.operator = "root square"
        self.g.direct_ancestors_with_id = [self.d]

        self.modeling_obj_container_mock = MagicMock()
        self.modeling_obj_container_mock.id = 1
        self.modeling_obj_container_mock.name = "Model1"

        for expl_obj in [self.a, self.b, self.c, self.d, self.f, self.g]:
            expl_obj.set_modeling_obj_container(MagicMock(), "attr_name")

    def test_copy_should_set_modeling_obj_container_to_none(self):
        a = ExplainableObject(1, "a")
        a.modeling_obj_container = "obj"
        from copy import copy
        b = copy(a)

        self.assertEqual("a", b.label)
        self.assertEqual(1, b.value)
        self.assertIsNone(b.modeling_obj_container)

    def test_creation_with_label(self):
        eo = ExplainableObject(value=5, label="Label A")
        self.assertEqual(eo.value, 5)
        self.assertEqual(eo.label, "Label A")
        self.assertIsNone(eo.left_parent)
        self.assertIsNone(eo.right_parent)

    def test_creation_without_label_and_child(self):
        with self.assertRaises(ValueError):
            ExplainableObject(value=5)

    def test_set_modeling_obj_container_without_label(self):
        self.a.label = None
        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")

    def test_set_modeling_obj_container_with_different_modeling_object_should_raise_PermissionError(self):
        self.a.left_parent = MagicMock()
        self.a.modeling_obj_container = MagicMock()
        self.a.modeling_obj_container.id = 2
        self.a.modeling_obj_container.name = "Model2"
        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")

    def test_set_modeling_obj_container_success(self):
        self.a.set_modeling_obj_container(None, None)
        self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")
        self.assertEqual(self.a.modeling_obj_container, self.modeling_obj_container_mock)
        self.assertEqual(self.a.attr_name_in_mod_obj_container, "attr1")

    def test_unattached_value_has_no_children(self):
        self.assertEqual([], ExplainableObject(1, "unattached").direct_children_with_id)

    def test_value_attached_by_hand_has_no_children(self):
        """Test that children come from the slot graph only: a value built by hand outside a computation
        records no read, so its operand lists no child."""
        leaf = ChildrenLinksLeaf("hand leaf", SourceValue(1 * u.W))
        hand_built = ExplainableQuantity(2 * u.W, label="hand built", left_parent=leaf.power, operator="duplicate")
        hand_built.set_modeling_obj_container(ChildrenLinksHolder("hand holder", leaf), "hand_attr")

        self.assertEqual([leaf.power], hand_built.direct_ancestors_with_id)
        self.assertEqual([], leaf.power.direct_children_with_id)

    def test_children_are_the_explainable_calculus_dependents_only(self):
        """Test that a value read by a computed-dict key set and by a computed structure lists neither as a
        child, only the computed attribute whose formula uses it."""
        leaf = ChildrenLinksLeaf("leaf", SourceValue(1 * u.W))
        holder = ChildrenLinksHolder("holder", leaf)
        _ = leaf.quadruple_power, dict(holder.power_per_selected_leaf), holder.double_power_magnitude
        double_power_slot = slot_of_attached_value(leaf.double_power)
        key_set_slot = instance_slot_registry(holder)["power_per_selected_leaf"]
        structure_slot = instance_slot_registry(holder)["double_power_magnitude"]
        for non_explainable_reader in (key_set_slot, structure_slot):
            self.assertIn(double_power_slot, non_explainable_reader.calculus_dependencies)

        self.assertEqual([leaf.quadruple_power], leaf.double_power.direct_children_with_id)

    def test_loaded_value_derives_ancestors_from_formula_leaves_on_first_read(self):
        """Test that a loaded value computes nothing at load, then derives its ancestors from the formula's
        attached leaves, left to right and deduplicated, pulling a void operand and skipping inline
        constants."""
        leaf = ChildrenLinksLeaf("loaded leaf", SourceValue(1 * u.W))
        constant = ExplainableQuantity(3 * u.dimensionless, "three")
        loaded = ExplainableQuantity(9 * u.W, label="loaded")
        computed = []
        with observe_computations(lambda slot: computed.append(slot.diagnostic_name)):
            loaded.initialize_calculus_graph_data_from_json(
                {"explain_nested_tuples": [
                    [leaf.power.full_str_tuple_id, "*", constant.to_json()], "+",
                    [str((leaf.id, "double_power", None)), "+", leaf.power.full_str_tuple_id]]},
                {leaf.id: leaf})
            self.assertEqual([], computed)
            ancestors = loaded.direct_ancestors_with_id

        self.assertEqual([leaf.power, leaf.double_power], ancestors)
        self.assertEqual(["ChildrenLinksLeaf.double_power"], computed)

    def test_all_ancestors_with_id(self):
        descendant = ExplainableObject(0, "descendant")
        parent1 = ExplainableObject(1, "parent1")
        parent1.modeling_obj_container = MagicMock(id="parent1_mod_obj_container")
        parent1.attr_name_in_mod_obj_container = "parent1"
        parent2 = ExplainableObject(2, "parent2")
        parent2.modeling_obj_container = MagicMock(id="parent2_mod_obj_container")
        parent2.attr_name_in_mod_obj_container = "parent2"
        grandparent1 = ExplainableObject(3, "grandparent1")
        grandparent1.modeling_obj_container = MagicMock(id="grandparent1_mod_obj_container")
        grandparent1.attr_name_in_mod_obj_container = "grandparent1"
        grandparent2 = ExplainableObject(4, "grandparent2")
        grandparent2.modeling_obj_container = MagicMock(id="grandparent2_mod_obj_container")
        grandparent2.attr_name_in_mod_obj_container = "grandparent2"

        descendant.direct_ancestors_with_id.append(parent1)
        descendant.direct_ancestors_with_id.append(parent2)
        parent1.direct_ancestors_with_id.append(grandparent1)
        parent2.direct_ancestors_with_id.append(grandparent2)

        ancestors = descendant.all_ancestors_with_id
        ancestors_labels = [ancestor.label for ancestor in ancestors]

        self.assertEqual(len(ancestors), 4)
        self.assertListEqual(ancestors_labels, ["parent1", "grandparent1", "parent2", "grandparent2"])

    def test_direct_children(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        left_parent.modeling_obj_container = MagicMock(name="lc_mod_obj_name", id="lc_mod_obj_id")
        left_parent.attr_name_in_mod_obj_container = "left_parent"
        right_parent.modeling_obj_container = MagicMock(name="rc_mod_obj_name", id="rc_mod_obj_id")
        right_parent.attr_name_in_mod_obj_container = "right_parent"

        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent")
        self.assertEqual([left_parent, right_parent], eo.direct_ancestors_with_id)





    def test_set_label(self):
        eo = ExplainableObject(value=5, label="Label A")
        eo.set_label("Intermediate A")
        self.assertEqual(eo.label, "Intermediate A")

    def test_has_child_property(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        eo_with_child = ExplainableObject(value=7, left_parent=left_parent, label="Parent")
        eo_without_child = ExplainableObject(value=7, label="Parent")
        self.assertTrue(eo_with_child.has_parent)
        self.assertFalse(eo_without_child.has_parent)

    def test_explain_simple_sum(self):
        self.assertEqual("c = a + b = 1 + 2 = 3", self.c.explain(pretty_print=False))

    def test_explain_nested_sum(self):
        self.assertEqual("d = c + a = 3 + 1 = 4", self.d.explain(pretty_print=False))

    def test_explain_should_skip_calculus_element_without_label(self):
        self.assertEqual("f = c + b + a = 3 + 2 + 1 = 6", self.f.explain(pretty_print=False))

    def test_explain_without_right_parent(self):
        self.assertEqual("g = root square (d) = root square (4) = 2", self.g.explain(pretty_print=False))

    def test_explain_should_put_right_parenthesis_in_complex_calculations(self):
        self.d.set_modeling_obj_container(None, None)
        self.c.set_modeling_obj_container(None, None)
        self.c.left_parent = self.a
        self.c.right_parent = self.b
        self.d.left_parent = self.c
        self.d.right_parent = self.a
        h = ExplainableObject(1, None, self.c, self.c, "/")
        i = ExplainableObject(2, None, h, self.g, "*")
        j = ExplainableObject(-1, "k", i, self.c, "-")
        j.set_modeling_obj_container(MagicMock(), "attr_name")
        self.assertEqual("k = ((a + b) / (a + b)) * g - (a + b) = ((1 + 2) / (1 + 2)) * 2 - (1 + 2) = -1", j.explain(
            pretty_print=False))
        self.d.set_modeling_obj_container(MagicMock(), "attr_name")
        self.c.set_modeling_obj_container(MagicMock(), "attr_name")

    def test_explain_without_children(self):
        eo = ExplainableObject(value=5, label="Label A")
        result = eo.explain()
        self.assertEqual(result, "Label A = 5")

    def test_compute_explain_nested_tuples(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent",
                               operator="+")
        result = eo.compute_explain_nested_tuples()
        self.assertEqual(result, (left_parent, "+", right_parent))

    def test_finalized_explanation_remains_composable(self):
        """Test a finalized formula can become a parent of another calculation without retaining value parents."""
        a = ExplainableObject(value=1, label="a")
        b = ExplainableObject(value=2, label="b")
        a.set_modeling_obj_container(MagicMock(), "a")
        b.set_modeling_obj_container(MagicMock(), "b")
        subtotal = ExplainableObject(value=3, left_parent=a, right_parent=b, operator="+")

        subtotal.finalize_explanation()
        total = ExplainableObject(value=6, label="total", left_parent=subtotal, right_parent=subtotal, operator="+")
        total.finalize_explanation()

        self.assertIsNone(subtotal.left_parent)
        self.assertIsNone(subtotal.right_parent)
        self.assertIsNone(total.left_parent)
        self.assertIsNone(total.right_parent)
        self.assertEqual("total = a + b + a + b = 1 + 2 + 1 + 2 = 6", total.explain(pretty_print=False))
        self.assertIs(total, total.finalize_explanation())
        self.assertEqual("total = a + b + a + b = 1 + 2 + 1 + 2 = 6", total.explain(pretty_print=False))

    def test_attached_finalized_parent_remains_a_concise_formula_boundary(self):
        """Test a stored formula on an attached value stays collapsed in downstream explanations."""
        a = ExplainableObject(value=1, label="a")
        b = ExplainableObject(value=2, label="b")
        a.set_modeling_obj_container(MagicMock(), "a")
        b.set_modeling_obj_container(MagicMock(), "b")
        subtotal = ExplainableObject(value=3, label="subtotal", left_parent=a, right_parent=b, operator="+")
        subtotal.set_modeling_obj_container(MagicMock(), "subtotal")
        total = ExplainableObject(value=6, label="total", left_parent=subtotal, right_parent=subtotal, operator="+")

        total.finalize_explanation()

        self.assertEqual("total = subtotal + subtotal = 3 + 3 = 6", total.explain(pretty_print=False))

    def test_print_flat_tuple_formula(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent",
                               operator="+")
        
        self.assertEqual(eo.print_flat_tuple_formula((left_parent, "+", right_parent), False), "Label L + Label R")
        self.assertEqual(eo.print_flat_tuple_formula((left_parent, "+", right_parent), True), "3 + 4")

    def test_explain_should_skip_empty_added_as_sum_start_value(self):
        value = ExplainableQuantity(1 * u.kg, label="a")
        value.set_modeling_obj_container(MagicMock(), "value")
        result = sum([value], start=EmptyExplainableObject()).set_label("result")
        result.set_modeling_obj_container(MagicMock(), "result")

        self.assertEqual("result = a = 1 kg = 1 kg", result.explain(pretty_print=False))

    def test_explain_should_skip_empty_subtracted_operand(self):
        value = ExplainableQuantity(1 * u.kg, label="a")
        value.set_modeling_obj_container(MagicMock(), "value")
        result = (value - EmptyExplainableObject()).set_label("result")
        result.set_modeling_obj_container(MagicMock(), "result")

        self.assertEqual("result = a = 1 kg = 1 kg", result.explain(pretty_print=False))

    def test_pretty_print_calculation(self):
        calc_str = "Label A = Label L + Label R = 3 + 4 = 7"
        result = ExplainableObject.pretty_print_calculation(calc_str)
        expected_result = """Label A
=
Label L + Label R
=
3 + 4
=
7"""
        self.assertEqual(expected_result, result)

    def test_set_mod_obj_cont_raises_error_if_value_already_linked_to_another_modeling_obj_container_and_children(self):
        self.a.modeling_obj_container = MagicMock(id="mod obj id")
        new_parent_mod_obj = MagicMock(id="another obj id")
        self.a.left_parent = "non null left child"

        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(new_parent_mod_obj, "test_attr_name")

    def test_to_json_for_timezone(self):
        source = Source("source name", "source link")
        timezone_expl = ExplainableTimezone(pytz.timezone("Europe/Paris"), "timezone", source=source)

        self.assertEqual(
            {"zone": "Europe/Paris", "label": "timezone", "source": source.id}, timezone_expl.to_json())

    def test_invalid_confidence_level_raises(self):
        with self.assertRaises(AssertionError):
            ExplainableQuantity(1 * u.kg, label="x", confidence="excellent")

    def test_confidence_and_comment_default_to_none(self):
        eo = ExplainableObject(value=1, label="a")
        self.assertIsNone(eo.confidence)
        self.assertIsNone(eo.comment)

    def test_to_json_omits_confidence_and_comment_when_none(self):
        eo = ExplainableQuantity(1 * u.kg, label="x")
        json_dict = eo.to_json()
        self.assertNotIn("confidence", json_dict)
        self.assertNotIn("comment", json_dict)

    def test_to_json_emits_confidence_and_comment_when_set(self):
        eo = ExplainableQuantity(1 * u.kg, label="x", confidence="medium", comment="cross-checked")
        json_dict = eo.to_json()
        self.assertEqual("medium", json_dict["confidence"])
        self.assertEqual("cross-checked", json_dict["comment"])

    def test_round_trip_confidence_and_comment(self):
        source = Source("src", None)
        eo = ExplainableQuantity(2 * u.kg, label="q", source=source, confidence="high", comment="my note")
        json_dict = eo.to_json()
        loaded = ExplainableObject.from_json_dict(json_dict)
        _apply_json_metadata(loaded, json_dict, {source.id: source})
        self.assertEqual("high", loaded.confidence)
        self.assertEqual("my note", loaded.comment)
        self.assertIs(source, loaded.source)

    def test_copy_propagates_confidence_and_comment(self):
        form_inputs_hourly = {
            "start_date": "2024-01-01", "modeling_duration": 1, "modeling_duration_unit": "year",
            "initial_volume": 10, "initial_volume_unit": "occurrence", "initial_volume_timespan": "day",
            "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "month",
        }
        instances = [
            ExplainableQuantity(3 * u.kg, label="q", confidence="low", comment="note"),
            ExplainableHourlyQuantities(
                Quantity(np.array([1.0], dtype=np.float32), u.W),
                start_date=datetime(2024, 1, 1), label="hq", confidence="low", comment="note"),
            ExplainableHourlyQuantitiesFromFormInputs(
                form_inputs_hourly, label="form", confidence="low", comment="note"),
            ExplainableRecurrentQuantitiesFromConstant(
                {"constant_value": 1.0, "constant_unit": "watt"}, label="rqc", confidence="low", comment="note"),
        ]
        for eo in instances:
            copied = copy(eo)
            self.assertEqual("low", copied.confidence, msg=type(eo).__name__)
            self.assertEqual("note", copied.comment, msg=type(eo).__name__)

    def test_loading_old_json_without_confidence_and_comment_yields_none(self):
        json_dict = {"value": 1, "unit": "kilogram", "label": "x"}
        loaded = ExplainableObject.from_json_dict(json_dict)
        _apply_json_metadata(loaded, json_dict, {})
        self.assertIsNone(loaded.confidence)
        self.assertIsNone(loaded.comment)

    def test_bool_value_round_trips_as_bool_not_string(self):
        # Bool values reach the base-class to_json / from_json_dict branch (no dedicated subclass).
        # The reconstructed value must remain typed bool — round-tripping as the string "True"
        # would silently break truth-checks downstream (e.g. EcoLogits with_audio).
        for original in (True, False):
            eo = ExplainableObject(value=original, label="with_audio")
            json_dict = eo.to_json()
            self.assertEqual(original, json_dict["value"])
            self.assertIsInstance(json_dict["value"], bool)

            loaded = ExplainableObject.from_json_dict(json_dict)
            self.assertEqual(original, loaded.value)
            self.assertIsInstance(loaded.value, bool)
