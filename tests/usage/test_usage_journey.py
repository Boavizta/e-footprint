import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.constants.units import u
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestUsageJourney(TestCase):
    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)
        self.usage_journey = UsageJourney("test user journey", uj_steps=[])
        self.usage_journey.trigger_modeling_updates = False

    def test_servers(self):
        server_1 = MagicMock()
        server_2 = MagicMock()

        job_1 = MagicMock()
        job_2 = MagicMock()
        job_3 = MagicMock()

        job_1.server = server_1
        job_2.server = server_2
        job_3.server = server_1

        with patch.object(UsageJourney, "jobs", new_callable=PropertyMock) as jobs_mock:
            jobs_mock.return_value = [job_1, job_2, job_3]
            self.assertEqual(2, len(self.usage_journey.servers))
            self.assertEqual({server_1, server_2}, set(self.usage_journey.servers))

    def test_storages(self):
        storage_1 = MagicMock()
        storage_2 = MagicMock()

        server_1 = MagicMock(storage=storage_1)
        server_2 = MagicMock(storage=storage_2)

        job_1 = MagicMock()
        job_2 = MagicMock()
        job_3 = MagicMock()

        job_1.server = server_1
        job_2.server = server_2
        job_3.server = server_1

        with patch.object(UsageJourney, "jobs", new_callable=PropertyMock) as jobs_mock:
            jobs_mock.return_value = [job_1, job_2, job_3]
            self.assertEqual(2, len(self.usage_journey.storages))
            self.assertEqual({storage_1, storage_2}, set(self.usage_journey.storages))

    def test_jobs(self):
        job1 = MagicMock()
        job2 = MagicMock()

        uj_step1 = create_mod_obj_mock(UsageJourneyStep, name="Step 1", id="uj_step1")
        uj_step2 = create_mod_obj_mock(UsageJourneyStep, name="Step 2", id="uj_step2")

        uj_step1.jobs = [job1]
        uj_step2.jobs = [job2]
        for uj_step in [uj_step1, uj_step2]:
            uj_step.user_time_spent = SourceValue(5 * u.min)
            uj_step.user_time_spent.set_modeling_obj_container(uj_step, "user_time_spent")

        uj = UsageJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        self.assertEqual(2, len(set(uj.jobs)))
        self.assertEqual({job1, job2}, set(uj.jobs))

    def test_jobs_deduplicates_jobs_repeated_across_and_within_steps(self):
        """A job referenced several times must appear once: downstream per-job
        aggregations would otherwise double-count (and build a depth-N
        explainable tree). Per-step multiplicity stays available on uj_step.jobs.
        """
        job1 = MagicMock()
        job2 = MagicMock()

        uj_step1 = create_mod_obj_mock(UsageJourneyStep, name="Step 1", id="uj_step1")
        uj_step2 = create_mod_obj_mock(UsageJourneyStep, name="Step 2", id="uj_step2")
        uj_step1.jobs = [job1, job1, job1]  # same job referenced three times in one step
        uj_step2.jobs = [job1, job2]        # and again in another step
        for uj_step in [uj_step1, uj_step2]:
            uj_step.user_time_spent = SourceValue(5 * u.min)
            uj_step.user_time_spent.set_modeling_obj_container(uj_step, "user_time_spent")

        uj = UsageJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        self.assertEqual([job1, job2], uj.jobs)

    def test_update_duration_no_step(self):
        expected_duration = EmptyExplainableObject()

        self.assertEqual(self.usage_journey.duration, expected_duration)

    def test_update_duration_with_multiple_steps(self):
        uj_step1 = create_mod_obj_mock(UsageJourneyStep, name="Step 1", id="uj_step1")
        uj_step1.user_time_spent = SourceValue(5 * u.min)
        uj_step1.user_time_spent.set_modeling_obj_container(uj_step1, "user_time_spent")
        uj_step2 = create_mod_obj_mock(UsageJourneyStep, name="Step 2", id="uj_step2")
        uj_step2.user_time_spent = SourceValue(3 * u.min)
        uj_step2.user_time_spent.set_modeling_obj_container(uj_step2, "user_time_spent")
        uj = UsageJourney("test user journey", uj_steps=[uj_step1, uj_step2])
        uj.update_duration()

        self.assertEqual(SourceValue(8 * u.min), uj.duration)

    def test_update_fabrication_impact_repartition_weights_uses_parallel_journeys_and_container_occurrences(self):
        usage_pattern_a = create_mod_obj_mock(UsagePattern, name="Usage Pattern A")
        usage_pattern_b = create_mod_obj_mock(UsagePattern, name="Usage Pattern B")
        # It is currently not possible for a usage journey to be linked several times to the same
        # usage pattern, but it might happen someday and the logic will be already tested.
        set_modeling_obj_containers(self.usage_journey, [usage_pattern_a, usage_pattern_a, usage_pattern_b])
        self.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict({
            usage_pattern_a: SourceValue(3 * u.concurrent),
            usage_pattern_b: SourceValue(4 * u.concurrent),
        })

        self.usage_journey.update_fabrication_impact_repartition_weights()

        self.assertEqual(6, self.usage_journey.fabrication_impact_repartition_weights[usage_pattern_a].magnitude)
        self.assertEqual(4, self.usage_journey.fabrication_impact_repartition_weights[usage_pattern_b].magnitude)
        self.assertEqual(u.concurrent, self.usage_journey.fabrication_impact_repartition_weights[usage_pattern_a].unit)

    def test_usage_impact_repartition_weights_returns_fabrication_weights(self):
        usage_pattern_a = create_mod_obj_mock(UsagePattern, name="Usage Pattern A")
        usage_pattern_b = create_mod_obj_mock(UsagePattern, name="Usage Pattern B")
        set_modeling_obj_containers(self.usage_journey, [usage_pattern_a, usage_pattern_b])
        self.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict({
            usage_pattern_a: SourceValue(2 * u.concurrent),
            usage_pattern_b: SourceValue(4 * u.concurrent),
        })
        self.usage_journey.update_fabrication_impact_repartition_weights()

        self.assertIs(
            self.usage_journey.fabrication_impact_repartition_weights,
            self.usage_journey.usage_impact_repartition_weights,
        )

    def test_step_usage_impact_can_route_through_journey_without_journey_usage_repartition(self):
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Usage Pattern")
        step = UsageJourneyStep("Step", SourceValue(1 * u.min), [])
        usage_journey = UsageJourney("test user journey", uj_steps=[step])
        set_modeling_obj_containers(usage_journey, [usage_pattern])
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict({
            usage_pattern: SourceValue(3 * u.concurrent),
        })
        usage_journey.update_fabrication_impact_repartition_weights()

        step.update_usage_impact_repartition_weights()

        self.assertEqual(3, step.usage_impact_repartition_weights[usage_journey].magnitude)
        self.assertEqual(u.concurrent, step.usage_impact_repartition_weights[usage_journey].unit)

    def test_usage_impact_repartition_is_not_owned_by_usage_journey(self):
        self.assertNotIn("usage_impact_repartition_weights", self.usage_journey.calculated_attributes)
        self.assertNotIn("usage_impact_repartition_weight_sum", self.usage_journey.calculated_attributes)
        self.assertNotIn("usage_impact_repartition", self.usage_journey.calculated_attributes)
        self.assertFalse(hasattr(self.usage_journey, "usage_impact_repartition"))

    def test_attributed_energy_footprint_per_usage_pattern_raises_when_neutral_total_negative(self):
        usage_pattern = create_mod_obj_mock(UsagePattern, name="UP")
        usage_pattern.country_dependent_usage_footprint = SourceValue(10 * u.kg).set_label(
            "UP country-dependent")
        usage_pattern.usage_activity_weight = SourceValue(1 * u.concurrent)
        set_modeling_obj_containers(self.usage_journey, [usage_pattern])
        self.usage_journey.__dict__["attributed_energy_footprint"] = SourceValue(5 * u.kg).set_label(
            "Attributed energy footprint")

        with self.assertRaises(ValueError) as ctx:
            self.usage_journey.attributed_energy_footprint_per_usage_pattern
        self.assertIn("neutral remainder is negative", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
