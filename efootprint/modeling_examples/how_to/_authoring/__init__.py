"""Authoring scripts that regenerate the how-to example JSONs.

Each script exposes a ``build_system()`` constructor and calls ``_write_example``
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


def _write_example(example_id, build_system):
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.modeling_examples.how_to.registry import HOW_TO_EXAMPLES

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Authoring scripts must run with name-based ids; "
        "import efootprint.modeling_examples.how_to._authoring before building.")
    target = next(example.json_path for example in HOW_TO_EXAMPLES if example.id == example_id)
    system_to_json(build_system(), save_computed_state=False, output_filepath=str(target))
    print(f"Wrote {target}")
