import unittest
from unittest.mock import MagicMock, PropertyMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage


class TestModelingUpdate(unittest.TestCase):
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
