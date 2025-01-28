import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.constants.units import u


class TestUsageJourneyStep(TestCase):
    def test_usage_journey_step_without_job_doesnt_break(self):
        uj_step_without_job = UsageJourneyStep("", user_time_spent=SourceValue(2 * u.min), jobs=[])

    def test_self_delete_should_raise_error_if_self_has_associated_uj(self):
        user_time_spent = SourceValue(10 * u.s)
        user_time_spent.value.check = lambda x: x == "[time]"
        uj_step = UsageJourneyStep("test uj step", user_time_spent=user_time_spent, jobs=[])
        uj_step.trigger_modeling_updates = False
        uj = MagicMock(spec=UsageJourney)
        uj.name = "uj"
        uj_step.contextual_modeling_obj_containers = [ContextualModelingObjectAttribute(uj_step, uj, "uj_steps")]

        with self.assertRaises(PermissionError):
            uj_step.self_delete()


if __name__ == "__main__":
    unittest.main()
