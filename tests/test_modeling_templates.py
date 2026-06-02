"""Tests for the ``efootprint.modeling_templates.how_to`` package.

Each test is parametrized over ``HOW_TO_TEMPLATES`` so adding a new template
automatically exercises load, compute, doc cross-references, and round-trip
stability against its authoring script.
"""
import importlib
import inspect
import json
from collections import Counter
from pathlib import Path

import pytest

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromConstant,
)
from efootprint.modeling_templates import load_introductory_template_system, load_template_system
from efootprint.modeling_templates.how_to.registry import HOW_TO_TEMPLATES, HowToTemplate
from efootprint.modeling_templates.introductory.registry import (
    INTRODUCTORY_TEMPLATES,
    IntroductoryTemplate,
)

MKDOCS_SOURCEFILES = (
    Path(__file__).resolve().parent.parent / "docs_sources" / "mkdocs_sourcefiles")

_template_params = pytest.mark.parametrize(
    "tpl", HOW_TO_TEMPLATES, ids=lambda t: t.id)
_introductory_template_params = pytest.mark.parametrize(
    "tpl", INTRODUCTORY_TEMPLATES, ids=lambda t: t.id)


def _modeling_object_ids(system_data: dict) -> list[str]:
    metadata_keys = {"efootprint_version", "Sources"}
    return [
        payload["id"]
        for class_key, objects_by_id in system_data.items()
        if class_key not in metadata_keys
        for payload in objects_by_id.values()
    ]


def _assert_input_timeseries_are_editable_builders(system, template_id: str) -> None:
    checked = []
    for obj in [system, *system.all_linked_objects]:
        obj = obj._value if isinstance(obj, ContextualModelingObjectAttribute) else obj
        init_params = inspect.signature(type(obj).__init__).parameters
        for attr_name in init_params:
            if attr_name in ("self", "name") or not hasattr(obj, attr_name):
                continue
            value = getattr(obj, attr_name)
            if isinstance(value, ExplainableHourlyQuantities):
                assert isinstance(value, ExplainableHourlyQuantitiesFromFormInputs), (
                    f"{template_id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableHourlyQuantitiesFromFormInputs so it is editable in the interface.")
                assert value.form_inputs["modeling_duration_value"] == 3
                assert value.form_inputs["modeling_duration_unit"] == "year"
                checked.append((obj, attr_name))
            elif isinstance(value, ExplainableRecurrentQuantities):
                assert isinstance(value, ExplainableRecurrentQuantitiesFromConstant), (
                    f"{template_id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableRecurrentQuantitiesFromConstant so it is editable in the interface.")
                checked.append((obj, attr_name))
    assert checked, f"{template_id}: expected at least one input timeseries to validate."


@_template_params
def test_template_json_exists_and_loads(tpl: HowToTemplate):
    assert tpl.json_path.is_file(), f"{tpl.json_path} does not exist"
    with open(tpl.json_path) as f:
        json.load(f)


@_template_params
def test_template_modeling_object_ids_are_globally_unique(tpl: HowToTemplate):
    with open(tpl.json_path) as f:
        system_data = json.load(f)
    duplicates = [
        object_id for object_id, count in Counter(_modeling_object_ids(system_data)).items()
        if count > 1
    ]
    assert duplicates == [], (
        f"Template {tpl.id} has duplicate modeling-object ids: {duplicates}. "
        "Object ids are global in the interface cache, even across different classes.")


@_template_params
def test_template_loads_via_json_to_system(tpl: HowToTemplate):
    system = load_template_system(tpl.id)
    assert system is not None
    assert system.__class__.__name__ == "System"


@_template_params
def test_template_computes_total_footprint(tpl: HowToTemplate):
    system = load_template_system(tpl.id)
    assert not isinstance(system.total_footprint, EmptyExplainableObject), (
        f"Template {tpl.id} produced an empty total_footprint")


@_template_params
def test_template_input_timeseries_are_editable_builders(tpl: HowToTemplate):
    _assert_input_timeseries_are_editable_builders(load_template_system(tpl.id), tpl.id)


@_template_params
def test_authoring_script_round_trips_to_committed_json(tpl: HowToTemplate):
    authoring = importlib.import_module(
        f"efootprint.modeling_templates.how_to._authoring.{tpl.id}")
    freshly_built = system_to_json(
        authoring.build_system(), save_calculated_attributes=False)
    with open(tpl.json_path) as f:
        committed = json.load(f)
    assert freshly_built == committed, (
        f"Template {tpl.id} JSON does not match the output of build_system(); "
        f"re-run `python -m efootprint.modeling_templates.how_to._authoring.{tpl.id}` "
        f"and commit the regenerated JSON.")


def test_metadata_schema():
    ids_seen: set[str] = set()
    for tpl in HOW_TO_TEMPLATES:
        for field in ("id", "name", "description", "doc_path"):
            value = getattr(tpl, field)
            assert isinstance(value, str) and value.strip(), (
                f"{tpl.id}.{field} must be a non-empty string")
        assert tpl.category == "how_to", f"{tpl.id} category must be 'how_to'"
        assert tpl.id not in ids_seen, f"Duplicate template id {tpl.id}"
        ids_seen.add(tpl.id)


@_template_params
def test_template_doc_path_exists(tpl: HowToTemplate):
    target = MKDOCS_SOURCEFILES / tpl.doc_path
    assert target.is_file(), (
        f"Template {tpl.id} doc_path {target} does not exist; "
        f"the prose track must land the matching How-to page.")


@_template_params
def test_how_to_page_references_template(tpl: HowToTemplate):
    """The How-to page must point at its template via the interactive deep link."""
    text = (MKDOCS_SOURCEFILES / tpl.doc_path).read_text()
    assert "interface_base_url" in text and f"/{tpl.id}" in text, (
        f"How-to page {tpl.doc_path} does not link to template {tpl.id} via "
        f"the interface_base_url deep link.")


def test_web_database_guides_link_to_ecommerce_interface_template():
    for doc_path in ("database_modeling.md", "server_to_server_interaction.md"):
        text = (MKDOCS_SOURCEFILES / doc_path).read_text()
        assert "interface_base_url" in text and "/ecommerce" in text


@_introductory_template_params
def test_introductory_template_json_exists_and_loads(tpl: IntroductoryTemplate):
    assert tpl.json_path.is_file(), f"{tpl.json_path} does not exist"
    with open(tpl.json_path) as f:
        json.load(f)


@_introductory_template_params
def test_introductory_template_loads_via_json_to_system(tpl: IntroductoryTemplate):
    system = load_introductory_template_system(tpl.id)
    assert system is not None
    assert system.__class__.__name__ == "System"


@_introductory_template_params
def test_introductory_template_input_timeseries_are_editable_builders(tpl: IntroductoryTemplate):
    _assert_input_timeseries_are_editable_builders(load_introductory_template_system(tpl.id), tpl.id)


@_introductory_template_params
def test_introductory_authoring_script_round_trips_to_committed_json(tpl: IntroductoryTemplate):
    authoring = importlib.import_module(
        f"efootprint.modeling_templates.introductory._authoring.{tpl.id}")
    freshly_built = system_to_json(
        authoring.build_system(), save_calculated_attributes=False)
    with open(tpl.json_path) as f:
        committed = json.load(f)
    assert freshly_built == committed, (
        f"Introductory template {tpl.id} JSON does not match the output of build_system(); "
        f"re-run `python -m efootprint.modeling_templates.introductory._authoring.{tpl.id}` "
        f"and commit the regenerated JSON.")
