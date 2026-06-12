import json
from datetime import datetime
from unittest import TestCase

from efootprint.abstract_modeling_classes.explainable_object_dict import WeightedExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
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
        f"usage pattern {suffix}", journey, [Device.laptop(f"laptop {suffix}")],
        Network.from_defaults(f"network {suffix}"), Countries.FRANCE(),
        create_source_hourly_values_from_list([10, 4, 20, 8], datetime(2026, 1, 1)))
    system = System(f"system {suffix}", [usage_pattern], edge_usage_patterns=[])

    return system, journey, step_1, step_2, job


class TestWeightedRelationships(TestCase):
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
        system_json = system_to_json(system, save_calculated_attributes=False)

        class_obj_dict, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(system_json)))
        reloaded_journey = flat_obj_dict[journey.id]

        self.assertIsInstance(reloaded_journey.uj_steps, WeightedExplainableObjectDict)
        self.assertEqual(
            [2, 0.5], [weight.magnitude for weight in reloaded_journey.uj_steps.values()])
        reloaded_step_1 = flat_obj_dict[step_1.id]
        self.assertIsInstance(reloaded_step_1.jobs, WeightedExplainableObjectDict)
        self.assertEqual([3], [weight.magnitude for weight in reloaded_step_1.jobs.values()])
        self.assertEqual(SourceValue((2 * 5 + 0.5 * 20) * u.min), reloaded_journey.duration)

        reloaded_system = list(class_obj_dict["System"].values())[0]
        self.assertEqual(
            system.total_footprint.value_as_float_list, reloaded_system.total_footprint.value_as_float_list)
        self.assertEqual(system_json, system_to_json(reloaded_system, save_calculated_attributes=False))

    def test_weights_change_computed_results(self):
        baseline_system, *_ = build_system(lambda s1, s2: {s1: 1, s2: 1}, lambda j: {j: 1}, "baseline")
        weighted_system, *_ = build_system(lambda s1, s2: {s1: 2, s2: 1}, lambda j: {j: 3}, "scaled")

        self.assertNotEqual(
            baseline_system.total_footprint.value_as_float_list, weighted_system.total_footprint.value_as_float_list)
