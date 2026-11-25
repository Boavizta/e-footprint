import json

from comprehension_harness.python.declare import titled
from efootprint.api_utils.system_to_json import system_to_json, systems_to_json
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


@titled("`systems_to_json` writes the dict it returns to the file it is given")
def test_systems_to_json_writes_the_file_it_is_given(tmp_path):
    """Test that systems_to_json writes the dict it returns to the file it is given."""
    system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
    output_filepath = tmp_path / "comparison.json"

    comparison_dict = systems_to_json([system], output_filepath=output_filepath)

    assert comparison_dict == {"models": [system_to_json(system)]}
    assert json.loads(output_filepath.read_text()) == comparison_dict
