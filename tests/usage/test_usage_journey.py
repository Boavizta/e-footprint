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

    def test_update_impact_repartition_weights_uses_parallel_journeys_and_container_occurrences(self):
        usage_pattern_a = create_mod_obj_mock(UsagePattern, name="Usage Pattern A")
        usage_pattern_b = create_mod_obj_mock(UsagePattern, name="Usage Pattern B")
        # It is currently not possible for a usage journey to be linked several times to the same
        # usage pattern, but it might happen someday and the logic will be already tested.
        set_modeling_obj_containers(self.usage_journey, [usage_pattern_a, usage_pattern_a, usage_pattern_b])
        self.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict({
            usage_pattern_a: SourceValue(3 * u.concurrent),
            usage_pattern_b: SourceValue(4 * u.concurrent),
        })

        self.usage_journey.update_impact_repartition_weights()

        self.assertEqual(6, self.usage_journey.impact_repartition_weights[usage_pattern_a].magnitude)
        self.assertEqual(4, self.usage_journey.impact_repartition_weights[usage_pattern_b].magnitude)
        self.assertEqual(u.concurrent, self.usage_journey.impact_repartition_weights[usage_pattern_a].unit)


if __name__ == "__main__":
    unittest.main()
