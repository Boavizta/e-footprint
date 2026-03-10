import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.country import Country
from efootprint.core.hardware.network import Network
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeUsagePattern(TestCase):
    def setUp(self):
        self.mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, name="Mock Edge Journey")
        self.mock_edge_need = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Edge Need")
        self.mock_server_need = create_mod_obj_mock(RecurrentServerNeed, name="Mock Server Need")
        self.mock_edge_usage_journey.recurrent_edge_device_needs = [self.mock_edge_need]
        self.mock_edge_usage_journey.recurrent_server_needs = [self.mock_server_need]

        self.mock_country = create_mod_obj_mock(Country, name="Mock Country")
        self.mock_country.timezone = MagicMock()

        self.mock_network = create_mod_obj_mock(Network, name="Mock Network")

        start_date = datetime(2023, 1, 1, 0, 0, 0)
        hourly_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0]) * u.concurrent
        self.real_hourly_starts = ExplainableHourlyQuantities(hourly_data, start_date, "test hourly starts")

        self.edge_usage_pattern = EdgeUsagePattern("test edge usage pattern", edge_usage_journey=self.mock_edge_usage_journey,
                                                   network=self.mock_network, country=self.mock_country,
                                                   hourly_edge_usage_journey_starts=self.real_hourly_starts)
        self.edge_usage_pattern.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeUsagePattern initialization."""
        self.assertEqual("test edge usage pattern", self.edge_usage_pattern.name)
        self.assertEqual(self.mock_edge_usage_journey, self.edge_usage_pattern.edge_usage_journey)
        self.assertEqual(self.mock_country, self.edge_usage_pattern.country)
        self.assertEqual(self.mock_network, self.edge_usage_pattern.network)
        self.assertEqual(self.real_hourly_starts, self.edge_usage_pattern.hourly_edge_usage_journey_starts)

        self.assertIsInstance(self.edge_usage_pattern.utc_hourly_edge_usage_journey_starts, EmptyExplainableObject)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that the journey is the direct dependent of a usage pattern."""
        dependent_objects = self.edge_usage_pattern.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_usage_journey], dependent_objects)

    def test_recurrent_edge_device_needs(self):
        """Test recurrent_edge_device_needs property delegates to edge_usage_journey."""
        self.assertEqual([self.mock_edge_need], self.edge_usage_pattern.recurrent_edge_device_needs)

    def test_systems(self):
        """Test systems property returns modeling_obj_containers."""
        mock_system = MagicMock(spec=ModelingObject)
        mock_system.systems = [mock_system]
        set_modeling_obj_containers(self.edge_usage_pattern, [mock_system])

        self.assertEqual([mock_system], self.edge_usage_pattern.systems)

    def test_update_utc_hourly_edge_usage_journey_starts(self):
        """Test update_utc_hourly_edge_usage_journey_starts method."""
        mock_utc_result = ExplainableHourlyQuantities(
            np.array([1.0, 2.0, 3.0]) * u.concurrent,
            datetime(2023, 1, 1, 0, 0, 0),
            "UTC result"
        )

        # Patch at class level because __slots__ prevents instance-level patching
        with patch.object(ExplainableHourlyQuantities, 'convert_to_utc',
                          return_value=mock_utc_result) as mock_convert:
            self.edge_usage_pattern.update_utc_hourly_edge_usage_journey_starts()
            mock_convert.assert_called_once_with(local_timezone=self.mock_country.timezone)

            self.assertEqual(self.edge_usage_pattern.utc_hourly_edge_usage_journey_starts, mock_utc_result)


if __name__ == "__main__":
    unittest.main()
