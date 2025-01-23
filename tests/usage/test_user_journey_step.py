import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.constants.units import u


class TestUserJourneyStep(TestCase):
    def test_user_journey_step_without_job_doesnt_break(self):
        uj_step_without_job = UserJourneyStep("", user_time_spent=SourceValue(2 * u.min), jobs=[])

    def test_self_delete_should_raise_error_if_self_has_associated_uj(self):
        user_time_spent = SourceValue(10 * u.s)
        user_time_spent.value.check = lambda x: x == "[time]"
        uj_step = UserJourneyStep("test uj step", user_time_spent=user_time_spent, jobs=[])
        uj_step.trigger_modeling_updates = False
        uj = MagicMock(spec=UserJourney)
        uj.name = "uj"
        uj_step.contextual_modeling_obj_containers = [ContextualModelingObjectAttribute(uj_step, uj, "uj_steps")]

        with self.assertRaises(PermissionError):
            uj_step.self_delete()


if __name__ == "__main__":
    unittest.main()
