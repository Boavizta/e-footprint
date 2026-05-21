"""Authoring scripts that regenerate the how-to template JSONs.

Each script exposes a ``build_system()`` constructor and calls ``_write_template``
in its ``__main__`` block. IDs are pinned to readable, name-based slugs (rather
than the default per-process uuids) so the committed JSON is reviewable and stable
across regenerations. Importing this package flips the ``_use_name_as_id`` flag
on both ``ModelingObject`` and ``Source`` *before* any other efootprint import
loads, so that source constants instantiated at module-import time also use
name-based ids.
"""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True


def _write_template(template_id, build_system):
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.modeling_templates.how_to.registry import HOW_TO_TEMPLATES

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Authoring scripts must run with name-based ids; "
        "import efootprint.modeling_templates.how_to._authoring before building.")
    target = next(tpl.json_path for tpl in HOW_TO_TEMPLATES if tpl.id == template_id)
    system_to_json(build_system(), save_calculated_attributes=False, output_filepath=str(target))
    print(f"Wrote {target}")
