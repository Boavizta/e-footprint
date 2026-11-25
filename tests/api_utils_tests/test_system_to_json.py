import json

import pytest

from comprehension_harness.python.declare import titled
from efootprint.abstract_modeling_classes.reactive_core import computed_slots
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import load_system, load_systems
from efootprint.api_utils.system_to_json import system_to_json, systems_to_json
from efootprint.comparison.duplication import duplicate_system
from efootprint.constants.units import u
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


@titled("`systems_to_json` writes the dict it returns to the file it is given")
def test_systems_to_json_writes_the_file_it_is_given(tmp_path):
    """Test that systems_to_json writes the dict it returns to the file it is given."""
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    output_filepath = tmp_path / "comparison.json"

    comparison_dict = systems_to_json([system], output_filepath=output_filepath)

    assert comparison_dict == {"models": [system_to_json(system)]}
    assert json.loads(output_filepath.read_text()) == comparison_dict


@titled("`systems_to_json` refuses two systems sharing a System id, naming the id and "
        "duplicate_system")
def test_two_systems_sharing_a_system_id_are_refused():
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    with pytest.raises(ValueError) as error:
        systems_to_json([system, load_system(system_to_json(system))])

    assert system.id in str(error.value)
    assert "duplicate_system" in str(error.value)


@titled("systems written by `systems_to_json` come back from `load_systems` in their "
        "order, each as its own save and load gives it")
def test_systems_saved_to_one_file_load_back_in_their_order():
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    system.total_footprint
    other = duplicate_system(system)
    other.servers[0].base_ram_consumption = SourceValue(400 * u.MB_ram)
    other.total_footprint

    systems = [other, system, duplicate_system(system)]
    loaded_systems = load_systems(systems_to_json(systems))

    assert [system_to_json(loaded) for loaded in loaded_systems] == [system_to_json(item) for item in systems]
    assert all(computed_slots(type(loaded))["total_footprint"].peek(loaded) is not None
               for loaded in loaded_systems)
