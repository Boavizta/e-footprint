"""Tests for the v21 Source-id serialization shape.

Covers:
- Top-level "Sources" block round-trip with shared-source identity restored.
- Sentinel ids (`user_data`, `hypothesis`) pinned, re-identified with the live Python singletons.
- Round-trip over every concrete ExplainableObject subclass with a source.
"""
from datetime import datetime
from unittest import TestCase

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, Source, explainable_object_from_json)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.api_utils.json_to_system import build_sources_dict_from_system_dict, json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.timeseries.explainable_hourly_quantities_from_form_inputs import (
    ExplainableHourlyQuantitiesFromFormInputs)
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server

from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


class TestSentinelIds(TestCase):
    def test_sentinel_ids_are_pinned(self):
        # These sentinel id strings are part of the on-disk schema. Renaming them silently breaks
        # every saved JSON that references them.
        self.assertEqual("user_data", Sources.USER_DATA.id)
        self.assertEqual("hypothesis", Sources.HYPOTHESIS.id)


class TestSourceJson(TestCase):
    def test_source_to_json_emits_id_name_link(self):
        source = Source("My source", "https://example.com", id="my-id")
        self.assertEqual({"id": "my-id", "name": "My source", "link": "https://example.com"}, source.to_json())

    def test_source_normalises_empty_link_to_none(self):
        self.assertIsNone(Source("name", "").link)
        self.assertIsNone(Source("name", None).link)

    def test_explainable_to_json_emits_source_as_id_ref(self):
        source = Source("test source", "https://example.com")
        eo = ExplainableQuantity(1 * u.kg, label="test", source=source)
        json_dict = eo.to_json()
        self.assertEqual(source.id, json_dict["source"])


class TestTopLevelSourcesBlockRoundTrip(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()

    def test_top_level_sources_block_present(self):
        system_dict = system_to_json(self.system, save_calculated_attributes=False)
        self.assertIn("Sources", system_dict)
        for source_id, source_payload in system_dict["Sources"].items():
            self.assertEqual(source_id, source_payload["id"])
            self.assertIn("name", source_payload)
            self.assertIn("link", source_payload)

    def test_inline_source_no_longer_present_in_explainable_payloads(self):
        system_dict = system_to_json(self.system, save_calculated_attributes=False)
        for class_key, class_dict in system_dict.items():
            if class_key in ("efootprint_version", "Sources") or not isinstance(class_dict, dict):
                continue
            for obj_dict in class_dict.values():
                for value in obj_dict.values():
                    if isinstance(value, dict) and "source" in value:
                        self.assertIsInstance(value["source"], str)

    def test_source_identity_restored_across_round_trip(self):
        system_dict = system_to_json(self.system, save_calculated_attributes=False)
        class_obj_dict, flat_obj_dict, _ = json_to_system(system_dict)
        sources_seen_by_id = {}
        for mod_obj in flat_obj_dict.values():
            for value in mod_obj.__dict__.values():
                if isinstance(value, ExplainableObject) and value.source is not None:
                    seen = sources_seen_by_id.setdefault(value.source.id, value.source)
                    self.assertIs(seen, value.source)

    def test_sentinels_re_identify_with_live_singletons(self):
        system_dict = system_to_json(self.system, save_calculated_attributes=False)
        class_obj_dict, flat_obj_dict, _ = json_to_system(system_dict)
        for mod_obj in flat_obj_dict.values():
            for value in mod_obj.__dict__.values():
                if isinstance(value, ExplainableObject) and value.source is not None:
                    if value.source.id == "hypothesis":
                        self.assertIs(Sources.HYPOTHESIS, value.source)
                    elif value.source.id == "user_data":
                        self.assertIs(Sources.USER_DATA, value.source)


class TestAllExplainableSubclassesRoundTrip(TestCase):
    """Ensure every concrete ExplainableObject subclass round-trips its source, confidence,
    and comment via the centralized loader."""

    def _round_trip(self, eo, source):
        json_dict = eo.to_json()
        self.assertEqual(source.id, json_dict["source"])
        self.assertEqual("medium", json_dict.get("confidence"))
        self.assertEqual("a test comment", json_dict.get("comment"))
        loaded = explainable_object_from_json(json_dict, {source.id: source})
        self.assertIs(source, loaded.source)
        self.assertEqual("medium", loaded.confidence)
        self.assertEqual("a test comment", loaded.comment)
        return loaded

    def test_explainable_quantity(self):
        source = Source("custom source", "https://example.com")
        self._round_trip(
            ExplainableQuantity(2 * u.kg, label="x", source=source, confidence="medium", comment="a test comment"),
            source)

    def test_explainable_hourly_quantities(self):
        source = Source("hourly source", None)
        self._round_trip(ExplainableHourlyQuantities(
            Quantity(np.array([1.0, 2.0], dtype=np.float32), u.W),
            start_date=datetime(2024, 1, 1), label="hq", source=source, confidence="medium",
            comment="a test comment"), source)

    def test_explainable_recurrent_quantities(self):
        source = Source("recurrent source", None)
        self._round_trip(ExplainableRecurrentQuantities(
            Quantity(np.array([1.0, 2.0], dtype=np.float32), u.W), label="rq", source=source,
            confidence="medium", comment="a test comment"), source)

    def test_explainable_timezone(self):
        source = Source("tz source", None)
        self._round_trip(
            ExplainableTimezone(pytz.timezone("Europe/Paris"), label="tz", source=source,
                                confidence="medium", comment="a test comment"),
            source)

    def test_explainable_dict(self):
        source = Source("dict source", None)
        self._round_trip(
            ExplainableDict({"a": 1}, label="d", source=source, confidence="medium", comment="a test comment"),
            source)

    def test_explainable_hourly_quantities_from_form_inputs(self):
        source = Source("form source", None)
        form_inputs = {
            "start_date": "2024-01-01", "modeling_duration_value": 1, "modeling_duration_unit": "month",
            "initial_volume": 10, "initial_volume_unit": "occurrence", "initial_volume_timespan": "day",
            "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "month",
        }
        self._round_trip(ExplainableHourlyQuantitiesFromFormInputs(
            form_inputs, label="form", source=source, confidence="medium", comment="a test comment"), source)

    def test_explainable_recurrent_quantities_from_constant(self):
        source = Source("rq const source", None)
        form_inputs = {"constant_value": 1.0, "constant_unit": "watt"}
        self._round_trip(ExplainableRecurrentQuantitiesFromConstant(
            form_inputs, label="rqc", source=source, confidence="medium", comment="a test comment"), source)


class TestBuildSourcesDict(TestCase):
    def test_substitutes_live_sentinels(self):
        system_dict = {
            "Sources": {
                "user_data": {"id": "user_data", "name": "user data", "link": None},
                "hypothesis": {"id": "hypothesis", "name": "e-footprint hypothesis", "link": None},
                "abc123": {"id": "abc123", "name": "Other", "link": None},
            }
        }
        sources_dict = build_sources_dict_from_system_dict(system_dict)
        self.assertIs(Sources.USER_DATA, sources_dict["user_data"])
        self.assertIs(Sources.HYPOTHESIS, sources_dict["hypothesis"])
        self.assertEqual("Other", sources_dict["abc123"].name)

    def test_handles_missing_sources_block(self):
        sources_dict = build_sources_dict_from_system_dict({})
        self.assertEqual({}, sources_dict)


class TestSystemToJsonOnNonSystemObject(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()

    def test_system_to_json_does_not_raise_on_non_system_object(self):
        """Regression: no AttributeError when calling system_to_json on a non-System ModelingObject.
        Previously collect_referenced_sources used all_linked_objects, a System-only attribute."""
        server = next(obj for obj in self.system.all_linked_objects if isinstance(obj, Server))
        result = system_to_json(server, save_calculated_attributes=False)
        self.assertIn("efootprint_version", result)
        self.assertIn("Server", result)
