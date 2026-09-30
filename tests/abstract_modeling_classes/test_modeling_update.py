import unittest
from unittest.mock import MagicMock, PropertyMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern


class TestModelingUpdate(unittest.TestCase):
    def test_conditional_empty_choice_rejects_zero_and_accepts_reconciled_batch(self):
        """Test zero is invalid for an empty-only count, through dependent and controller edits."""
        server = Server.from_defaults("Conditional count", storage=Storage.from_defaults("Conditional storage"))
        original_count = server.fixed_nb_of_instances
        with self.assertRaisesRegex(ValueError, "not in the list"):
            ModelingUpdate([[original_count, SourceValue(0 * u.concurrent)]])
        self.assertIs(server.fixed_nb_of_instances, original_count)

        ModelingUpdate([[server.server_type, ServerTypes.on_premise()],
                        [server.fixed_nb_of_instances, SourceValue(0 * u.concurrent)]])
        original_type, original_count = server.server_type, server.fixed_nb_of_instances
        with self.assertRaisesRegex(ValueError, "not in the list"):
            ModelingUpdate([[original_type, ServerTypes.autoscaling()]])
        self.assertIs(server.server_type, original_type)
        self.assertIs(server.fixed_nb_of_instances, original_count)

        empty = EmptyExplainableObject()
        update = ModelingUpdate([[server.server_type, ServerTypes.autoscaling()], [original_count, empty]])
        self.assertEqual(len(update.changes_list), 2)
        self.assertIs(server.fixed_nb_of_instances, empty)

    def test_equal_timeseries_keep_authored_changes_and_builder_transitions(self):
        """Test equal hourly arrays retain changed form inputs and raw/builder transitions."""
        form_inputs = {
            "start_date": "2025-01-01", "modeling_duration_value": 1, "modeling_duration_unit": "month",
            "initial_volume": 1000, "initial_volume_timespan": "month",
            "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "year",
        }
        series = ExplainableHourlyQuantitiesFromFormInputs(form_inputs)
        pattern = UsagePattern(
            "Authored timeseries", {UsageJourney("Empty journey", {}): 1}, [],
            Network.from_defaults("Timeseries network"), Countries.FRANCE(), series)
        changed_inputs = {**form_inputs, "net_growth_rate_timespan": "month"}
        changed = ExplainableHourlyQuantitiesFromFormInputs(changed_inputs)
        raw = ExplainableHourlyQuantities(series.value.copy(), series.start_date, label="Raw timeseries")
        for replacement in (changed, raw, ExplainableHourlyQuantitiesFromFormInputs(changed_inputs)):
            with self.subTest(builder=type(replacement).__name__):
                self.assertEqual(pattern.hourly_occurrences, replacement)
                update = ModelingUpdate([[pattern.hourly_occurrences, replacement]])
                self.assertEqual(len(update.changes_list), 1)
                self.assertIs(pattern.hourly_occurrences, replacement)
                _, restored, _ = json_to_system(system_to_json(pattern, save_computed_state=False))
                self.assertEqual(restored[pattern.id].hourly_occurrences.to_json(), replacement.to_json())

        current = pattern.hourly_occurrences
        update = ModelingUpdate([[current, ExplainableHourlyQuantitiesFromFormInputs(changed_inputs)]])
        self.assertEqual(update.changes_list, [])
        self.assertIs(pattern.hourly_occurrences, current)

    def test_optional_zero_and_empty_are_distinct_changes_and_round_trip(self):
        """Test explicit zero and omitted Server counts survive edits and serialization in both directions."""
        server = Server.from_defaults("Optional count", storage=Storage.from_defaults("Storage"),
                                      server_type=ServerTypes.on_premise())
        for new_value in (SourceValue(0 * u.concurrent), EmptyExplainableObject()):
            self.assertEqual(server.fixed_nb_of_instances, new_value)
            update = ModelingUpdate([[server.fixed_nb_of_instances, new_value]])
            self.assertEqual(len(update.changes_list), 1)
            self.assertIs(server.fixed_nb_of_instances, new_value)
            _, restored, _ = json_to_system(system_to_json(server, save_computed_state=False))
            self.assertEqual(isinstance(restored[server.id].fixed_nb_of_instances, EmptyExplainableObject),
                             isinstance(new_value, EmptyExplainableObject))

        empty = server.fixed_nb_of_instances
        update = ModelingUpdate([[empty, EmptyExplainableObject()]])
        self.assertEqual(update.changes_list, [])
        self.assertIs(server.fixed_nb_of_instances, empty)

    def test_optional_presence_change_rolls_back_with_rejected_sibling(self):
        """Test a rejected batch restores the original optional-count object and sibling."""
        server = Server.from_defaults(
            "Rollback count", storage=Storage.from_defaults("Rollback storage"),
            server_type=ServerTypes.on_premise(), fixed_nb_of_instances=SourceValue(0 * u.concurrent))
        original = server.fixed_nb_of_instances
        server_type = server.server_type
        with self.assertRaisesRegex(ValueError, "not in the list"):
            ModelingUpdate([[original, EmptyExplainableObject()], [server_type, SourceObject("unknown")]])
        self.assertIs(server.fixed_nb_of_instances, original)
        self.assertIs(server.server_type, server_type)

    def test_default_pulls_guards_but_leaves_ordinary_invalidated_slots_void(self):
        """Test the default update validates guards without eagerly pulling ordinary computations."""
        pulls = []
        ordinary_slot = ReactiveSlot("ordinary", lambda: pulls.append("ordinary"))
        guard_slot = ReactiveSlot("guard", lambda: pulls.append("guard"))
        guard_slot.guard = True
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)
        modeling_update.system = MagicMock()
        modeling_update.eager_outputs = None
        modeling_update.newly_linked_mod_objs = []

        affected_count = modeling_update.pull_eagerly({ordinary_slot, guard_slot})

        self.assertEqual(2, affected_count)
        self.assertEqual(["guard"], pulls)
        self.assertTrue(guard_slot.has_cached_value)
        self.assertFalse(ordinary_slot.has_cached_value)

    def test_explicit_eager_outputs_are_pulled(self):
        """Test callers can opt into pulling selected outputs after validation."""
        output_owner = MagicMock()
        selected_output = PropertyMock(return_value="computed")
        type(output_owner).selected_output = selected_output
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)
        modeling_update.system = MagicMock()
        modeling_update.eager_outputs = [(output_owner, "selected_output")]
        modeling_update.newly_linked_mod_objs = []

        modeling_update.pull_eagerly(set())

        selected_output.assert_called_once_with()

    def test_parse_changes_list_wrong_input_types_raises_value_error(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__
        old_value = MagicMock(spec=ObjectLinkedToModelingObj)
        old_value.modeling_obj_container = MagicMock()
        old_value.attr_name_in_mod_obj_container = MagicMock()
        new_value = 1

        modeling_update.changes_list = [(old_value, new_value)]

        with self.assertRaises(ValueError):
            modeling_update.parse_changes_list()

    def test_apply_changes_with_mixed_objects(self):
        modeling_update = ModelingUpdate.__new__(ModelingUpdate)  # Bypass __init__

        old_value_1 = MagicMock(spec=ContextualModelingObjectAttribute)
        new_value_1 = MagicMock(spec=ContextualModelingObjectAttribute)
        old_value_1.modeling_obj_container = MagicMock()
        old_value_1.attr_name_in_mod_obj_container = "attr_1"

        old_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        new_value_2 = MagicMock(spec=ListLinkedToModelingObj)
        old_value_2.modeling_obj_container = MagicMock()
        old_value_2.attr_name_in_mod_obj_container = "attr_2"

        modeling_update.changes_list = [[old_value_1, new_value_1], [old_value_2, new_value_2]]

        modeling_update.apply_changes()

        old_value_1.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_1)
        old_value_2.replace_in_mod_obj_container_without_recomputation.assert_called_once_with(new_value_2)


if __name__ == '__main__':
    unittest.main()
