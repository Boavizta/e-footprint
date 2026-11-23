"""The narrative of a system saved to its JSON form and loaded back: what the document holds, and what a load
trusts of it.

Its page is drawn from this run (`npm run comprehension:render`, then
`specs/comprehension_harness/narratives/`). The steps are recorded, not asserted: each test asserts what the
round-trip gives, as any test does.
"""
import pytest

from comprehension_harness.python.declare import narrative, planned_test
from efootprint.abstract_modeling_classes.reactive_core import computed_slots
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.comparison.duplication import duplicate_system
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


@pytest.fixture
def system():
    """A system whose footprint was read once, so that its serialized values are computed."""
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    system.total_footprint
    return system


def loaded_system(system_dict):
    class_obj_dict, _, _ = json_to_system(system_dict)
    return next(iter(class_obj_dict["System"].values()))


def is_cached(system) -> bool:
    return computed_slots(type(system))["total_footprint"].peek(system) is not None


@narrative("A system is saved to a file and loaded back")
class TestSystemFile:
    """A save writes each object's inputs and the values already computed, with the calculation graph that
    links them. A load trusts those values only when the document is of this version and holds its graph;
    otherwise every value computes on read, and the values the document held are kept as a baseline."""

    def test_a_system_loaded_at_its_own_version_keeps_its_ids_and_its_values(self, system):
        loaded = loaded_system(system_to_json(system))

        assert loaded.id == system.id
        assert is_cached(loaded)
        assert loaded.total_footprint == system.total_footprint

    def test_an_inputs_only_document_computes_its_values_on_read(self, system):
        loaded = loaded_system(system_to_json(system, save_computed_state=False))

        assert not is_cached(loaded)
        assert loaded.total_footprint == system.total_footprint

    def test_a_document_of_an_earlier_version_is_upgraded_and_keeps_its_values_as_a_baseline(self, system):
        system_dict = system_to_json(system)
        # This version's document under the previous major version: the 26-to-27 handler only drops a key
        # this version no longer writes, so the upgrade runs on a document it accepts.
        system_dict["efootprint_version"] = "26.0.0"

        loaded = loaded_system(system_dict)

        assert not is_cached(loaded)
        assert loaded.has_version_baseline
        assert loaded.total_footprint == system.total_footprint

    def test_a_duplicate_keeps_the_ids_of_its_objects_and_takes_a_system_id_of_its_own(self, system):
        copy = duplicate_system(system)

        assert copy.id != system.id
        assert {obj.id for obj in copy.all_linked_objects} == {obj.id for obj in system.all_linked_objects}
        assert is_cached(copy)

    @planned_test("comparison-file#export: `systems_to_json` refuses two systems sharing a System id, naming the id "
                  "and duplicate_system [distinct-systems]")
    def test_two_systems_sharing_a_system_id_are_refused(self, system):
        ...

    @planned_test("comparison-file#load: systems written by `systems_to_json` come back from `json_to_systems` in "
                  "their order, each as its own save and load gives it [round-trip]")
    def test_systems_saved_to_one_file_load_back_in_their_order(self, system):
        ...
