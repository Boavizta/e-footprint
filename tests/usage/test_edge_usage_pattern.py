import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch
from datetime import datetime
import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.country import Country
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestEdgeUsagePattern(TestCase):
    def setUp(self):
        self.mock_edge_usage_journey = MagicMock(spec=EdgeUsageJourney)
        self.mock_edge_usage_journey.id = "mock_edge_journey"
        self.mock_edge_usage_journey.name = "Mock Edge Journey"
        self.mock_edge_process = MagicMock(spec=RecurrentEdgeProcess)
        self.mock_edge_process.name = "Mock Edge Processes"
        self.mock_edge_computer = MagicMock(spec=EdgeComputer)
        self.mock_edge_usage_journey.edge_processes = [self.mock_edge_process]
        self.mock_edge_usage_journey.edge_computer = self.mock_edge_computer
        
        self.mock_country = MagicMock(spec=Country)
        self.mock_country.name = "Mock Country"
        self.mock_country.timezone = MagicMock()
        
        start_date = datetime(2023, 1, 1, 0, 0, 0)
        hourly_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0]) * u.dimensionless
        self.real_hourly_starts = ExplainableHourlyQuantities(hourly_data, start_date, "test hourly starts")
        
        self.edge_usage_pattern = EdgeUsagePattern(
            "test edge usage pattern",
            edge_usage_journey=self.mock_edge_usage_journey,
            country=self.mock_country,
            hourly_edge_usage_journey_starts=self.real_hourly_starts
        )
        self.edge_usage_pattern.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeUsagePattern initialization."""
        self.assertEqual("test edge usage pattern", self.edge_usage_pattern.name)
        self.assertEqual(self.mock_edge_usage_journey, self.edge_usage_pattern.edge_usage_journey)
        self.assertEqual(self.mock_country, self.edge_usage_pattern.country)
        self.assertEqual(self.real_hourly_starts, self.edge_usage_pattern.hourly_edge_usage_journey_starts)
        
        # Check that calculated attributes are initialized as EmptyExplainableObject
        self.assertIsInstance(self.edge_usage_pattern.utc_hourly_edge_usage_journey_starts, EmptyExplainableObject)
        self.assertIsInstance(self.edge_usage_pattern.nb_edge_usage_journeys_in_parallel, EmptyExplainableObject)

    def test_calculated_attributes(self):
        """Test the calculated_attributes property matches the actual implementation."""
        expected_attributes = ["utc_hourly_edge_usage_journey_starts", "nb_edge_usage_journeys_in_parallel"]
        self.assertEqual(expected_attributes, self.edge_usage_pattern.calculated_attributes)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that edge processes and edge_computer are returned as dependent object."""
        dependent_objects = self.edge_usage_pattern.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_process, self.mock_edge_computer], dependent_objects)

    def test_edge_processes(self):
        """Test edge_processes property delegates to edge_usage_journey."""
        self.assertEqual([self.mock_edge_process], self.edge_usage_pattern.edge_processes)

    def test_systems(self):
        """Test systems property returns modeling_obj_containers."""
        mock_system = MagicMock(spec=ModelingObject)
        mock_system.systems = [mock_system]
        set_modeling_obj_containers(self.edge_usage_pattern, [mock_system])

        self.assertEqual([mock_system], self.edge_usage_pattern.systems)

    @patch('efootprint.core.usage.edge_usage_pattern.compute_nb_avg_hourly_occurrences')
    def test_update_nb_edge_usage_journeys_in_parallel(self, mock_compute_nb_avg):
        """Test update_nb_edge_usage_journeys_in_parallel method."""
        mock_result = EmptyExplainableObject()
        mock_compute_nb_avg.return_value = mock_result
        
        mock_duration = SourceValue(30 * u.min)
        self.mock_edge_usage_journey.usage_span = mock_duration
        
        utc_starts = ExplainableHourlyQuantities(
            np.array([1.0, 2.0, 3.0]) * u.dimensionless,
            datetime(2023, 1, 1, 0, 0, 0),
            "UTC starts"
        )
        self.edge_usage_pattern.utc_hourly_edge_usage_journey_starts = utc_starts
        
        self.edge_usage_pattern.update_nb_edge_usage_journeys_in_parallel()
        mock_compute_nb_avg.assert_called_once_with(utc_starts, mock_duration)
        
        self.assertEqual(self.edge_usage_pattern.nb_edge_usage_journeys_in_parallel, mock_result)

    def test_update_utc_hourly_edge_usage_journey_starts(self):
        """Test update_utc_hourly_edge_usage_journey_starts method."""
        mock_utc_result = ExplainableHourlyQuantities(
            np.array([1.0, 2.0, 3.0]) * u.dimensionless,
            datetime(2023, 1, 1, 0, 0, 0),
            "UTC result"
        )
        
        with patch.object(self.edge_usage_pattern.hourly_edge_usage_journey_starts, 'convert_to_utc',
                          return_value=mock_utc_result) as mock_convert:
            
            self.edge_usage_pattern.update_utc_hourly_edge_usage_journey_starts()
            mock_convert.assert_called_once_with(local_timezone=self.mock_country.timezone)
            
            self.assertEqual(self.edge_usage_pattern.utc_hourly_edge_usage_journey_starts, mock_utc_result)


if __name__ == "__main__":
    unittest.main()