import json
from copy import copy, deepcopy
from unittest import TestCase

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject,
    Source,
    explainable_object_from_json,
)
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.timeseries import (
    ExplainableRecurrentQuantitiesFromConstant,
    ExplainableRecurrentQuantitiesFromWeeklyPattern,
    WeeklyPatternValidationError,
)
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass


def weekly_form_inputs():
    return {
        "unit": "concurrent",
        "profiles": [
            {
                "name": "weekday",
                "days": [0, 1, 2, 3, 4],
                "baseline": 1,
                "ranges": [
                    {"start": 0, "end": 8, "value": 0.25},
                    {"start": 8, "end": 18, "value": 2},
                    {"start": 18, "end": 24, "value": -1},
                ],
            },
            {"name": "weekend", "days": [5, 6], "baseline": 3, "ranges": []},
            {"name": "unused", "days": [], "baseline": 99, "ranges": [{"start": 0, "end": 24, "value": 50}]},
        ],
    }


class TestExplainableRecurrentQuantitiesFromWeeklyPattern(TestCase):
    def assert_validation_error(self, form_inputs, path, code):
        with self.assertRaises(WeeklyPatternValidationError) as context:
            ExplainableRecurrentQuantitiesFromWeeklyPattern(form_inputs)
        self.assertIn(path, [error["path"] for error in context.exception.errors])
        matching = [error for error in context.exception.errors if error["path"] == path]
        self.assertIn(code, [error["code"] for error in matching])
        self.assertTrue(all(set(error) == {"path", "code", "message"} for error in context.exception.errors))
        self.assertTrue(all(error["message"] for error in context.exception.errors))

    def test_composition_produces_canonical_float32_week_and_keeps_unused_profiles(self):
        """Test profiles compose Monday first with baselines, adjacent ranges, and unused authored profiles."""
        form_inputs = weekly_form_inputs()

        result = ExplainableRecurrentQuantitiesFromWeeklyPattern(form_inputs, label="Weekly workload")

        expected_weekday = np.array([0.25] * 8 + [2] * 10 + [-1] * 6, dtype=np.float32)
        expected = np.concatenate([expected_weekday] * 5 + [np.full(24, 3, dtype=np.float32)] * 2)
        np.testing.assert_array_equal(expected, result.magnitude)
        self.assertEqual(np.float32, result.magnitude.dtype)
        self.assertEqual(168, len(result.value))
        self.assertEqual("concurrent", str(result.unit))
        self.assertEqual(form_inputs, result.form_inputs)

    def test_profile_count_must_be_between_one_and_seven(self):
        """Test empty and over-limit profile lists report the stable profile-count error."""
        for profiles in ([], [
            {"name": f"profile {index}", "days": list(range(7)) if index == 0 else [], "baseline": 0, "ranges": []}
            for index in range(8)
        ]):
            with self.subTest(profile_count=len(profiles)):
                self.assert_validation_error(
                    {"unit": "concurrent", "profiles": profiles}, "profiles", "profile_count"
                )

    def test_profile_names_are_non_empty_case_sensitive_and_unique(self):
        """Test blank and repeated names fail while names differing only by case remain distinct."""
        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][0]["name"] = "   "
        self.assert_validation_error(form_inputs, "profiles[0].name", "empty_profile_name")

        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][1]["name"] = "weekday"
        self.assert_validation_error(form_inputs, "profiles[1].name", "duplicate_profile_name")

        form_inputs["profiles"][1]["name"] = "Weekday"
        ExplainableRecurrentQuantitiesFromWeeklyPattern(form_inputs)

    def test_days_require_valid_integer_indices_and_exactly_one_owner(self):
        """Test invalid, duplicate, and missing day assignments expose normalized error paths."""
        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][0]["days"].append(7)
        self.assert_validation_error(form_inputs, "profiles[0].days[5]", "invalid_day")

        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][1]["days"].append(0)
        self.assert_validation_error(form_inputs, "profiles[1].days[2]", "duplicate_day_assignment")

        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][1]["days"].remove(6)
        self.assert_validation_error(form_inputs, "profiles", "missing_day_assignment")

    def test_baselines_and_range_values_must_be_finite_numbers(self):
        """Test non-numeric and non-finite authored values report their precise field paths."""
        for field_path, mutate in (
            ("profiles[0].baseline", lambda inputs: inputs["profiles"][0].update(baseline=np.nan)),
            ("profiles[0].ranges[1].value", lambda inputs: inputs["profiles"][0]["ranges"][1].update(value=np.inf)),
        ):
            with self.subTest(field_path=field_path):
                form_inputs = weekly_form_inputs()
                mutate(form_inputs)
                self.assert_validation_error(form_inputs, field_path, "invalid_number")

    def test_range_hours_are_integral_bounded_and_in_increasing_order(self):
        """Test range bounds, within-range order, chronological order, and overlap are validated."""
        invalid_cases = (
            ("start", -1, "profiles[0].ranges[0].start", "invalid_start_hour"),
            ("start", 1.5, "profiles[0].ranges[0].start", "invalid_start_hour"),
            ("end", 25, "profiles[0].ranges[0].end", "invalid_end_hour"),
            ("end", 0, "profiles[0].ranges[0].end", "invalid_end_hour"),
            ("start", 8, "profiles[0].ranges[0].start", "invalid_range"),
        )
        for field, value, path, code in invalid_cases:
            with self.subTest(field=field, value=value):
                form_inputs = weekly_form_inputs()
                form_inputs["profiles"][0]["ranges"][0][field] = value
                self.assert_validation_error(form_inputs, path, code)

        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][0]["ranges"][1]["start"] = 6
        self.assert_validation_error(form_inputs, "profiles[0].ranges[1].start", "ranges_overlap")

        form_inputs = weekly_form_inputs()
        form_inputs["profiles"][0]["ranges"][1], form_inputs["profiles"][0]["ranges"][2] = (
            form_inputs["profiles"][0]["ranges"][2],
            form_inputs["profiles"][0]["ranges"][1],
        )
        self.assert_validation_error(form_inputs, "profiles[0].ranges[2].start", "ranges_not_ordered")

    def test_negative_values_are_intrinsically_valid(self):
        """Test the builder leaves attribute-specific negative-value policy to the owning model."""
        result = ExplainableRecurrentQuantitiesFromWeeklyPattern(weekly_form_inputs())
        self.assertEqual(-1, result.magnitude.min())

    def test_copy_preserves_authored_state_and_metadata_without_aliasing(self):
        """Test shallow copying retains all authoring metadata while deep-copying nested profiles."""
        source = Source("meter", "https://example.test/meter")
        original = ExplainableRecurrentQuantitiesFromWeeklyPattern(
            weekly_form_inputs(), label="Weekly workload", source=source, confidence="high", comment="Measured"
        )

        copied = copy(original)

        self.assertEqual(original.form_inputs, copied.form_inputs)
        self.assertIsNot(original.form_inputs, copied.form_inputs)
        self.assertIsNot(original.form_inputs["profiles"][0], copied.form_inputs["profiles"][0])
        self.assertEqual("Weekly workload", copied.label)
        self.assertEqual(source.id, copied.source.id)
        self.assertEqual("high", copied.confidence)
        self.assertEqual("Measured", copied.comment)

    def test_json_matcher_round_trip_preserves_authored_state_metadata_and_constant_loading(self):
        """Test direct JSON loading selects the weekly matcher and leaves constant-builder matching unchanged."""
        source = Source("meter", "https://example.test/meter")
        original = ExplainableRecurrentQuantitiesFromWeeklyPattern(
            weekly_form_inputs(), label="Weekly workload", source=source, confidence="medium", comment="Measured"
        )

        serialized = json.loads(json.dumps(original.to_json()))
        loaded = explainable_object_from_json(serialized, {source.id: source})

        self.assertIsInstance(loaded, ExplainableRecurrentQuantitiesFromWeeklyPattern)
        self.assertEqual(original.form_inputs, loaded.form_inputs)
        np.testing.assert_array_equal(original.magnitude, loaded.magnitude)
        self.assertEqual("Weekly workload", loaded.label)
        self.assertIs(source, loaded.source)
        self.assertEqual("medium", loaded.confidence)
        self.assertEqual("Measured", loaded.comment)

        constant = ExplainableObject.from_json_dict(
            ExplainableRecurrentQuantitiesFromConstant(
                {"constant_value": 4, "constant_unit": "concurrent"}, label="Constant"
            ).to_json()
        )
        self.assertIsInstance(constant, ExplainableRecurrentQuantitiesFromConstant)

    def test_system_json_round_trip_preserves_unused_profiles_and_metadata(self):
        """Test a weekly builder survives the complete system serialization and hydration path."""
        system, _ = IntegrationTestSimpleEdgeSystemBaseClass.generate_simple_edge_system()
        ram_need = next(
            obj for obj in system.all_linked_objects
            if isinstance(obj, RecurrentEdgeComponentNeed) and obj.name == "RAM need"
        )
        form_inputs = weekly_form_inputs()
        form_inputs["unit"] = "gigabyte_ram"
        source = Source("meter", "https://example.test/meter")
        weekly_need = RecurrentEdgeComponentNeed(
            "Weekly RAM need",
            edge_component=ram_need.edge_component,
            recurrent_need=ExplainableRecurrentQuantitiesFromWeeklyPattern(
                form_inputs, label="Recurrent need", source=source, confidence="high", comment="Measured"
            ),
        )
        recurrent_device_need = ram_need.recurrent_edge_device_needs[0]
        recurrent_device_need.recurrent_edge_component_needs = [
            *recurrent_device_need.recurrent_edge_component_needs,
            weekly_need,
        ]

        serialized = json.loads(json.dumps(system_to_json(system, save_computed_state=False)))
        _, flat_objects, _ = json_to_system(serialized)
        loaded_need = flat_objects[weekly_need.id].recurrent_need

        self.assertIsInstance(loaded_need, ExplainableRecurrentQuantitiesFromWeeklyPattern)
        self.assertEqual(form_inputs, loaded_need.form_inputs)
        self.assertEqual("Recurrent need", loaded_need.label)
        self.assertEqual(source.id, loaded_need.source.id)
        self.assertEqual("high", loaded_need.confidence)
        self.assertEqual("Measured", loaded_need.comment)

    def test_form_inputs_for_display_describes_each_authored_parameter(self):
        """Test the comparison surface exposes readable profile values instead of the computed array."""
        result = ExplainableRecurrentQuantitiesFromWeeklyPattern(weekly_form_inputs())

        self.assertEqual("concurrent", result.form_inputs_for_display["unit"])
        self.assertEqual("weekday", result.form_inputs_for_display["profile 1 name"])
        self.assertEqual("Mon, Tue, Wed, Thu, Fri", result.form_inputs_for_display["profile 1 days"])
        self.assertEqual("1 concurrent", result.form_inputs_for_display["profile 1 baseline"])
        self.assertEqual("08:00–18:00 = 2 concurrent", result.form_inputs_for_display["profile 1 range 2"])
        self.assertEqual("none", result.form_inputs_for_display["profile 3 days"])
