"""Tests for the ``efootprint.modeling_templates.how_to`` package.

Each test is parametrized over ``HOW_TO_TEMPLATES`` so adding a new template
automatically exercises load, compute, doc cross-references, and round-trip
stability against its authoring script.
"""
import importlib
import json
from pathlib import Path

import pytest

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.modeling_templates import load_template_system
from efootprint.modeling_templates.how_to.registry import HOW_TO_TEMPLATES, HowToTemplate

MKDOCS_SOURCEFILES = (
    Path(__file__).resolve().parent.parent / "docs_sources" / "mkdocs_sourcefiles")

_template_params = pytest.mark.parametrize(
    "tpl", HOW_TO_TEMPLATES, ids=lambda t: t.id)


@_template_params
def test_template_json_exists_and_loads(tpl: HowToTemplate):
    assert tpl.json_path.is_file(), f"{tpl.json_path} does not exist"
    with open(tpl.json_path) as f:
        json.load(f)


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
