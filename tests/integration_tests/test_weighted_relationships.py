import json
from datetime import datetime
from unittest import TestCase

import numpy as np
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    PositiveWeightedExplainableObjectDict, WeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.job import Job, JobOccurrenceCoordinate
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system(uj_steps_builder, jobs_builder, suffix):
    """Build a small web system whose uj_steps / jobs relationship values are produced by the given builders."""
    storage = Storage.from_defaults(f"storage {suffix}")
    server = Server.from_defaults(f"server {suffix}", server_type=ServerTypes.autoscaling(), storage=storage)
    job = Job.from_defaults(f"job {suffix}", server=server)
    step_1 = UsageJourneyStep(f"step 1 {suffix}", SourceValue(5 * u.min), jobs_builder(job))
    step_2 = UsageJourneyStep(f"step 2 {suffix}", SourceValue(20 * u.min), jobs_builder(job))
    journey = UsageJourney(f"journey {suffix}", uj_steps_builder(step_1, step_2))
    usage_pattern = UsagePattern(
        f"usage pattern {suffix}", [journey], [Device.laptop(f"laptop {suffix}")],
        Network.from_defaults(f"network {suffix}"), Countries.FRANCE(),
        create_source_hourly_values_from_list([10, 4, 20, 8], datetime(2026, 1, 1)))
    system = System(f"system {suffix}", [usage_pattern], edge_usage_patterns=[])

    return system, journey, step_1, step_2, job


class TestWeightedRelationships(TestCase):
    def test_pattern_journey_weights_create_distinct_shared_child_coordinates(self):
        storage = Storage.from_defaults("multi journey storage")
        server = Server.from_defaults("multi journey server", storage=storage)
        job = Job.from_defaults("shared multi journey job", server=server)
        step = UsageJourneyStep("shared multi journey step", SourceValue(1 * u.hour), [job])
        first = UsageJourney("first weighted journey", [step])
        second = UsageJourney("second weighted journey", [step])
        pattern = UsagePattern(
            "multi journey pattern", {first: 0.5, second: 2}, [Device.laptop("multi journey laptop")],
            Network.from_defaults("multi journey network"), Countries.FRANCE(),
            create_source_hourly_values_from_list([4, 2], datetime(2026, 1, 1)))
        System("multi journey system", [pattern], [])

        first_coordinate = JobOccurrenceCoordinate(pattern, journey=first, step=step)
        second_coordinate = JobOccurrenceCoordinate(pattern, journey=second, step=step)
        first_occurrences = job.hourly_avg_occurrences_per_coordinate[first_coordinate]
        second_occurrences = job.hourly_avg_occurrences_per_coordinate[second_coordinate]
        np.testing.assert_allclose(second_occurrences.magnitude, 4 * first_occurrences.magnitude)
        self.assertEqual({first, second}, {cell.journey for cell in job.attribution_cells})
        self.assertTrue(all(
            weight.label == "Journeys per pattern occurrence" for weight in pattern.usage_journeys.values()))
        with self.assertRaises(ValueError):
            pattern.usage_journeys[first] = SourceValue(0 * u.dimensionless)
        self.assertEqual(0.5, pattern.usage_journeys[first].magnitude)

    def test_all_weights_at_one_match_list_sugar_results(self):
        """A system built with list sugar computes exactly the same footprint as one built with explicit
        weight-1 dicts — the pre-feature semantics are the all-multipliers-at-1 case."""
        list_system, *_ = build_system(
            lambda s1, s2: [s1, s2], lambda job: [job], "list sugar")
        dict_system, *_ = build_system(
            lambda s1, s2: {s1: 1, s2: 1}, lambda job: {job: 1}, "explicit weights")

        self.assertEqual(
            list_system.total_footprint.value_as_float_list, dict_system.total_footprint.value_as_float_list)

    def test_json_round_trip_preserves_non_default_weights(self):
        system, journey, step_1, step_2, job = build_system(
            lambda s1, s2: {s1: 2, s2: 0.5}, lambda j: {j: 3}, "weighted")
        pattern = system.usage_patterns[0]
        second_journey = UsageJourney("second weighted pattern journey", [step_1])
        pattern.usage_journeys[journey] = SourceValue(1.5 * u.dimensionless, Sources.USER_DATA)
        pattern.usage_journeys[second_journey] = SourceValue(0.25 * u.dimensionless, Sources.USER_DATA)
        system_json = system_to_json(system, save_computed_state=False)

        class_obj_dict, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(system_json)))
        reloaded_journey = flat_obj_dict[journey.id]

        self.assertIsInstance(reloaded_journey.uj_steps, WeightedExplainableObjectDict)
        self.assertEqual(
            [2, 0.5], [weight.magnitude for weight in reloaded_journey.uj_steps.values()])
        reloaded_step_1 = flat_obj_dict[step_1.id]
        self.assertIsInstance(reloaded_step_1.jobs, WeightedExplainableObjectDict)
        self.assertEqual([3], [weight.magnitude for weight in reloaded_step_1.jobs.values()])
        self.assertEqual(SourceValue((2 * 5 + 0.5 * 20) * u.min), reloaded_journey.duration)
        reloaded_pattern = flat_obj_dict[pattern.id]
        self.assertIsInstance(reloaded_pattern.usage_journeys, PositiveWeightedExplainableObjectDict)
        self.assertEqual(
            [journey.id, second_journey.id], [reloaded.id for reloaded in reloaded_pattern.usage_journeys])
        self.assertEqual([1.5, 0.25], [weight.magnitude for weight in reloaded_pattern.usage_journeys.values()])
        self.assertTrue(all(
            weight.source == Sources.USER_DATA for weight in reloaded_pattern.usage_journeys.values()))

        reloaded_system = list(class_obj_dict["System"].values())[0]
        self.assertEqual(
            system.total_footprint.value_as_float_list, reloaded_system.total_footprint.value_as_float_list)
        self.assertEqual(system_json, system_to_json(reloaded_system, save_computed_state=False))

    def test_edge_plural_relationship_and_pattern_span_round_trip(self):
        first = EdgeUsageJourney("first round-trip edge journey", [])
        second = EdgeUsageJourney("second round-trip edge journey", [])
        pattern = EdgeUsagePattern(
            "round-trip edge pattern", [first, second], Network.wifi_network(), Countries.FRANCE(),
            create_source_hourly_values_from_list([1], datetime(2026, 1, 1)),
            usage_span=SourceValue(2 * u.year, Sources.USER_DATA))
        system = System("round-trip edge system", [], [pattern])
        system_json = system_to_json(system, save_computed_state=False)

        class_obj_dict, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(system_json)))
        reloaded_pattern = flat_obj_dict[pattern.id]

        self.assertEqual(
            [first.id, second.id], [journey.id for journey in reloaded_pattern.edge_usage_journeys])
        self.assertEqual(SourceValue(2 * u.year, Sources.USER_DATA), reloaded_pattern.usage_span)
        reloaded_system = next(iter(class_obj_dict["System"].values()))
        self.assertEqual(system_json, system_to_json(reloaded_system, save_computed_state=False))

    def test_weights_change_computed_results(self):
        baseline_system, *_ = build_system(lambda s1, s2: {s1: 1, s2: 1}, lambda j: {j: 1}, "baseline")
        weighted_system, *_ = build_system(lambda s1, s2: {s1: 2, s2: 1}, lambda j: {j: 3}, "scaled")

        self.assertNotEqual(
            baseline_system.total_footprint.value_as_float_list, weighted_system.total_footprint.value_as_float_list)

    def test_weights_appear_in_derivations(self):
        """Spec criterion: multipliers are explainable — the weight is cited in the derivation of journey
        duration and of job occurrences, like any other model parameter."""
        system, journey, step_1, step_2, job = build_system(
            lambda s1, s2: {s1: 2, s2: 0.5}, lambda j: {j: 3}, "explained")
        usage_pattern = system.usage_patterns[0]

        self.assertIn("Times per journey", journey.duration.explain())
        self.assertIn("Times per step", job.hourly_occurrences_per_usage_pattern[usage_pattern].explain())

    def test_reordering_uj_steps_is_applied_not_skipped(self):
        """Regression: reordering uj_steps (same steps and weights, only the order changes) must be
        applied. Dict equality ignores key order, so ModelingUpdate used to skip the swap as a no-op
        and the new order was silently dropped."""
        system, journey, step_1, step_2, job = build_system(
            lambda s1, s2: {s1: 1, s2: 1}, lambda j: {j: 1}, "reorder")
        self.assertEqual([step_1, step_2], list(journey.uj_steps.keys()))

        reordered = to_weighted_explainable_object_dict({step_2: 1, step_1: 1})
        update = ModelingUpdate([[journey.uj_steps, reordered]])

        self.assertEqual([step_2, step_1], list(journey.uj_steps.keys()))
        self.assertEqual([1, 1], [weight.magnitude for weight in journey.uj_steps.values()])

        update.rollback()

        self.assertIsInstance(journey.uj_steps, WeightedExplainableObjectDict)
        self.assertEqual([step_1, step_2], list(journey.uj_steps.keys()))
        self.assertEqual([1, 1], [weight.magnitude for weight in journey.uj_steps.values()])
