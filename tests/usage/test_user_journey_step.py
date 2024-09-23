import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.constants.units import u


class TestUserJourneyStep(TestCase):
    def test_user_journey_step_without_job_doesnt_break(self):
        uj_step_without_job = UserJourneyStep(
            "", user_time_spent=SourceValue(2 * u.min), jobs=[])

    def test_self_delete_should_raise_error_if_self_has_associated_uj(self):
        uj_step = UserJourneyStep(
            "test uj step", user_time_spent=MagicMock(), jobs=[])
        uj = UserJourney("uj", uj_steps=[uj_step])
        uj_step.modeling_obj_containers = [uj]

        with self.assertRaises(PermissionError):
            uj_step.self_delete()

if __name__ == "__main__":
    unittest.main()
