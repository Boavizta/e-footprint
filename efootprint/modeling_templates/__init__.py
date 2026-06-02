"""Public API for the modeling-templates sub-package.

Templates are reference systems that ship with e-footprint and back the
how-to pages in the mkdocs documentation. Each is regenerable from a Python
constructor under ``how_to/_authoring/`` and loadable via ``json_to_system``.

Imports inside ``load_template_system`` are kept lazy so that authoring
scripts (under ``how_to/_authoring/``) can flip ``_use_name_as_id`` on the
``Source`` class before ``api_utils.json_to_system`` triggers
``constants.sources`` to instantiate the source singletons.
"""
from efootprint.modeling_templates.how_to.registry import HOW_TO_TEMPLATES, HowToTemplate
from efootprint.modeling_templates.introductory.registry import (
    INTRODUCTORY_TEMPLATES,
    IntroductoryTemplate,
)


def list_how_to_templates() -> list[HowToTemplate]:
    """Return the registered how-to templates with their metadata."""
    return list(HOW_TO_TEMPLATES)


def get_template(template_id: str) -> HowToTemplate:
    for tpl in HOW_TO_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    raise KeyError(template_id)


def list_introductory_templates() -> list[IntroductoryTemplate]:
    """Return library-owned introductory templates with their metadata."""
    return list(INTRODUCTORY_TEMPLATES)


def get_introductory_template(template_id: str) -> IntroductoryTemplate:
    for tpl in INTRODUCTORY_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    raise KeyError(template_id)


def load_template_system(template_id: str):
    import json
    from efootprint.api_utils.json_to_system import json_to_system
    tpl = get_template(template_id)
    with open(tpl.json_path) as f:
        class_obj_dict, _, _ = json_to_system(json.load(f))
    return next(iter(class_obj_dict["System"].values()))


def load_introductory_template_system(template_id: str):
    import json
    from efootprint.api_utils.json_to_system import json_to_system
    tpl = get_introductory_template(template_id)
    with open(tpl.json_path) as f:
        class_obj_dict, _, _ = json_to_system(json.load(f))
    return next(iter(class_obj_dict["System"].values()))
