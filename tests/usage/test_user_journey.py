import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.user_journey import UserJourney
from efootprint.constants.units import u


class TestUserJourney(TestCase):
    def setUp(self):
        self.user_journey = UserJourney("test user journey", uj_steps=[])
        self.user_journey.dont_handle_input_updates = True

    def test_servers(self):
        server_1 = MagicMock()
        server_2 = MagicMock()

        job_1 = MagicMock()
        job_2 = MagicMock()
        job_3 = MagicMock()

        job_1.server = server_1
        job_2.server = server_2
        job_3.server = server_1

        with patch.object(UserJourney, "jobs", new_callable=PropertyMock) as jobs_mock:
            jobs_mock.return_value = [job_1, job_2, job_3]
            self.assertEqual(2, len(self.user_journey.servers))
            self.assertEqual({server_1, server_2}, set(self.user_journey.servers))

    def test_storages(self):
        job_1 = MagicMock()
        job_2 = MagicMock()
        job_3 = MagicMock()

        storage_1 = MagicMock()
        storage_2 = MagicMock()

        job_1.storage = storage_1
        job_2.storage = storage_2
        job_3.storage = storage_1

        with patch.object(UserJourney, "jobs", new_callable=PropertyMock) as jobs_mock:
            jobs_mock.return_value = [job_1, job_2, job_3]
            self.assertEqual(2, len(self.user_journey.storages))
            self.assertEqual({storage_1, storage_2}, set(self.user_journey.storages))

    def test_jobs(self):
        job1 = MagicMock()
        job2 = MagicMock()

        uj_step1 = MagicMock()
        uj_step2 = MagicMock()

        uj_step1.jobs = [job1]
        uj_step2.jobs = [job2]

        uj = UserJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        self.assertEqual(2, len(set(uj.jobs)))
        self.assertEqual({job1, job2}, set(uj.jobs))

    def test_update_duration_no_step(self):
        self.user_journey.update_duration()
        expected_duration = EmptyExplainableObject()

        self.assertEqual(self.user_journey.duration, expected_duration)

    def test_update_duration_with_multiple_steps(self):
        uj_step1 = MagicMock()
        uj_step1.user_time_spent = SourceValue(5 * u.min)
        uj_step2 = MagicMock()
        uj_step2.user_time_spent = SourceValue(3 * u.min)
        uj = UserJourney("test user journey", uj_steps=[uj_step1, uj_step2])

        uj.update_duration()

        self.assertEqual(SourceValue(8 * u.min), uj.duration)


if __name__ == "__main__":
    unittest.main()
