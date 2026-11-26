"""Authoring scripts that regenerate introductory example JSONs."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.narrate import planned

planned("executable-modeling-documentation#baseline-generation:explicit-intro-ids", "Move name-based id setup from package import into the explicit regeneration kernel before scenario imports.")
ModelingObject._use_name_as_id = True
Source._use_name_as_id = True


def _write_example(example_id, build_system):
    planned.remove("executable-modeling-documentation#baseline-generation", "Replace the constructor writer with explicit percent-source baseline regeneration in documentation tooling.")
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.modeling_examples.introductory.registry import INTRODUCTORY_EXAMPLES

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Authoring scripts must run with name-based ids; "
        "import efootprint.modeling_examples.introductory._authoring before building.")
    target = next(example.json_path for example in INTRODUCTORY_EXAMPLES if example.id == example_id)
    system_to_json(build_system(), save_computed_state=False, output_filepath=str(target))
    print(f"Wrote {target}")
