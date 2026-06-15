import json
from datetime import datetime, timezone
from unittest import TestCase

from efootprint.abstract_modeling_classes.explainable_object_dict import (
    WeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
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
        ModelingUpdate([[journey.uj_steps, reordered]])

        self.assertEqual([step_2, step_1], list(journey.uj_steps.keys()))
        self.assertEqual([1, 1], [weight.magnitude for weight in journey.uj_steps.values()])

    def test_simulation_dict_change_preserves_weight_linking_through_set_and_reset(self):
        """Regression test for the simulation ancestors-replaced-by-copies exclusion: weights carried by a
        directly-changed dict must not be replaced by copies — the dict swap manages their linking — so
        set_updated_values / reset_values restore the dict and its weights' linking exactly."""
        system, journey, step_1, step_2, job = build_system(
            lambda s1, s2: {s1: 1, s2: 1}, lambda j: {j: 1}, "sim dict change")
        new_server = Server.from_defaults(
            "sim new server", server_type=ServerTypes.autoscaling(), storage=Storage.from_defaults("sim new storage"))
        new_job = Job.from_defaults("sim new job", server=new_server)

        old_jobs_dict = step_1.jobs
        shared_weight = old_jobs_dict[job]
        new_jobs_dict = to_weighted_explainable_object_dict({**step_1.jobs, new_job: 1})
        new_job_weight = new_jobs_dict[new_job]
        self.assertIs(shared_weight, new_jobs_dict[job])

        simulation = ModelingUpdate(
            [[step_1.jobs, new_jobs_dict]], datetime(2026, 1, 1, 1, tzinfo=timezone.utc))

        # The shared weight is an ancestor outside the computation chain, so without the exclusion it would
        # have been replaced by a copy — corrupting the dict swap's set/reset linking below.
        self.assertIn(
            id(shared_weight), [id(ancestor) for ancestor in simulation.ancestors_not_in_computation_chain])
        self.assertNotIn(
            id(shared_weight), [id(ancestor) for ancestor in simulation.ancestors_to_replace_by_copies])
        self.assertIs(old_jobs_dict, step_1.jobs)
        self.assertIs(shared_weight, step_1.jobs[job])
        self.assertIs(step_1, shared_weight.modeling_obj_container)

        simulation.set_updated_values()
        self.assertIs(new_jobs_dict, step_1.jobs)
        self.assertIs(step_1, shared_weight.modeling_obj_container)
        self.assertIs(step_1, new_job_weight.modeling_obj_container)

        simulation.reset_values()
        self.assertIs(old_jobs_dict, step_1.jobs)
        self.assertIs(shared_weight, step_1.jobs[job])
        self.assertIs(step_1, shared_weight.modeling_obj_container)
        self.assertIsNone(new_job_weight.modeling_obj_container)
