"""Authoring scripts that regenerate introductory template JSONs."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True


def _write_template(template_id, build_system):
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.modeling_templates.introductory.registry import INTRODUCTORY_TEMPLATES

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Authoring scripts must run with name-based ids; "
        "import efootprint.modeling_templates.introductory._authoring before building.")
    target = next(tpl.json_path for tpl in INTRODUCTORY_TEMPLATES if tpl.id == template_id)
    system_to_json(build_system(), save_calculated_attributes=False, output_filepath=str(target))
    print(f"Wrote {target}")
