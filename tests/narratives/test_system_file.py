"""The narrative of a system saved to its JSON form and loaded back: what the document holds, and what a load
trusts of it.

Its page is drawn from this run (`npm run comprehension:render`, then
`specs/comprehension_harness/narratives/`). The steps are recorded, not asserted: each test asserts what the
round-trip gives, as any test does.
"""
import pytest

from comprehension_harness.python.declare import narrative, titled
from efootprint.abstract_modeling_classes.reactive_core import computed_slots
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import load_systems, load_system
from efootprint.api_utils.system_to_json import system_to_json, systems_to_json
from efootprint.comparison.duplication import duplicate_system
from efootprint.constants.units import u
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


@pytest.fixture
def system():
    """A system whose footprint was read once, so that its serialized values are computed."""
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    system.total_footprint
    return system


def is_cached(system) -> bool:
    return computed_slots(type(system))["total_footprint"].peek(system) is not None


@narrative("A system is saved to a file and loaded back")
class TestSystemFile:
    """A save writes each object's inputs and the values already computed, with the calculation graph that
    links them. A load trusts those values only when the document is of this version and holds its graph;
    otherwise every value computes on read, and the values the document held are kept as a baseline."""

    def test_a_system_loaded_at_its_own_version_keeps_its_ids_and_its_values(self, system):
        loaded = load_system(system_to_json(system))

        assert loaded.id == system.id
        assert is_cached(loaded)
        assert loaded.total_footprint == system.total_footprint

    def test_an_inputs_only_document_computes_its_values_on_read(self, system):
        loaded = load_system(system_to_json(system, save_computed_state=False))

        assert not is_cached(loaded)
        assert loaded.total_footprint == system.total_footprint

    def test_a_document_of_an_earlier_version_is_upgraded_and_keeps_its_values_as_a_baseline(self, system):
        system_dict = system_to_json(system)
        # This version's document under the previous major version: the 26-to-27 handler only drops a key
        # this version no longer writes, so the upgrade runs on a document it accepts.
        system_dict["efootprint_version"] = "26.0.0"

        loaded, = load_systems({"models": [system_dict]})

        assert not is_cached(loaded)
        assert loaded.has_version_baseline
        assert loaded.total_footprint == system.total_footprint

    def test_a_duplicate_keeps_the_ids_of_its_objects_and_takes_a_system_id_of_its_own(self, system):
        copy = duplicate_system(system)

        assert copy.id != system.id
        assert {obj.id for obj in copy.all_linked_objects} == {obj.id for obj in system.all_linked_objects}
        assert is_cached(copy)

    @titled("comparison-file#export: `systems_to_json` refuses two systems sharing a System id, naming the id and "
            "duplicate_system [distinct-systems]")
    def test_two_systems_sharing_a_system_id_are_refused(self, system):
        with pytest.raises(ValueError) as error:
            systems_to_json([system, load_system(system_to_json(system))])

        assert system.id in str(error.value)
        assert "duplicate_system" in str(error.value)

    @titled("comparison-file#load: systems written by `systems_to_json` come back from `load_systems` in their "
            "order, each as its own save and load gives it [round-trip]")
    def test_systems_saved_to_one_file_load_back_in_their_order(self, system):
        other = duplicate_system(system)
        other.servers[0].base_ram_consumption = SourceValue(400 * u.MB_ram)
        other.total_footprint

        systems = [other, system, duplicate_system(system)]
        loaded_systems = load_systems(systems_to_json(systems))

        assert [system_to_json(loaded) for loaded in loaded_systems] == [system_to_json(item) for item in systems]
        assert all(is_cached(loaded) for loaded in loaded_systems)
