import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.constants.units import u


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

        uj_step1 = MagicMock()
        uj_step2 = MagicMock()

        uj_step1.jobs = [job1]
        uj_step2.jobs = [job2]

        uj = UsageJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        self.assertEqual(2, len(set(uj.jobs)))
        self.assertEqual({job1, job2}, set(uj.jobs))

    def test_update_duration_no_step(self):
        self.usage_journey.update_duration()
        expected_duration = EmptyExplainableObject()

        self.assertEqual(self.usage_journey.duration, expected_duration)

    def test_update_duration_with_multiple_steps(self):
        uj_step1 = MagicMock()
        uj_step1.user_time_spent = SourceValue(5 * u.min)
        uj_step2 = MagicMock()
        uj_step2.user_time_spent = SourceValue(3 * u.min)
        uj = UsageJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        uj.update_duration()

        self.assertEqual(SourceValue(8 * u.min), uj.duration)


if __name__ == "__main__":
    unittest.main()
