import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.country import Country
from efootprint.core.hardware.network import Network
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeUsageJourney(TestCase):
    def setUp(self):
        self.mock_edge_device = create_mod_obj_mock(EdgeDevice, name="Mock Device")
        self.mock_edge_device.lifespan = SourceValue(4 * u.year)

        self.mock_edge_need_1 = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Need 1")
        self.mock_edge_need_1.edge_device = self.mock_edge_device

        self.mock_edge_need_2 = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Need 2")
        self.mock_edge_need_2.edge_device = self.mock_edge_device

        self.mock_edge_function_1 = create_mod_obj_mock(EdgeFunction, name="Mock Function 1")
        self.mock_edge_function_1.recurrent_edge_device_needs = [self.mock_edge_need_1]

        self.mock_edge_function_2 = create_mod_obj_mock(EdgeFunction, name="Mock Function 2")
        self.mock_edge_function_2.recurrent_edge_device_needs = [self.mock_edge_need_2]

        self.usage_span = SourceValue(2 * u.year)

        self.edge_usage_journey = EdgeUsageJourney("test edge usage journey",
                                                   edge_functions=[self.mock_edge_function_1, self.mock_edge_function_2],
                                                   usage_span=self.usage_span)

    def test_init(self):
        """Test EdgeUsageJourney initialization."""
        self.assertEqual("test edge usage journey", self.edge_usage_journey.name)
        self.assertEqual([self.mock_edge_function_1, self.mock_edge_function_2], self.edge_usage_journey.edge_functions)
        self.assertEqual("Usage span of test edge usage journey from e-footprint hypothesis", self.edge_usage_journey.usage_span.label)
        self.assertEqual(2 * u.year, self.edge_usage_journey.usage_span.value)

    def test_recurrent_edge_device_needs_property(self):
        """Test recurrent_edge_device_needs property returns unique edge needs from all edge functions."""
        recurrent_edge_device_needs = self.edge_usage_journey.recurrent_edge_device_needs
        self.assertEqual({self.mock_edge_need_1, self.mock_edge_need_2}, set(recurrent_edge_device_needs))

    def test_edge_devices_property(self):
        """Test edge_devices property returns unique edge devices from all edge needs."""
        edge_devices = self.edge_usage_journey.edge_devices
        self.assertEqual([self.mock_edge_device], edge_devices)

    def test_changing_to_usage_span_not_superior_to_edge_device_lifespan_doesnt_raise_error(self):
        mock_edge_device = create_mod_obj_mock(EdgeDevice, name="Mock Device")
        mock_edge_device.lifespan = SourceValue(2 * u.year)

        mock_edge_need = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Need")
        mock_edge_need.edge_device = mock_edge_device

        mock_edge_function = create_mod_obj_mock(EdgeFunction, name="Mock Function")
        mock_edge_function.recurrent_edge_device_needs = [mock_edge_need]

        usage_span = SourceValue(1 * u.year)
        euj = EdgeUsageJourney("test euj", edge_functions=[mock_edge_function], usage_span=usage_span)

        euj.usage_span = SourceValue(2 * u.year)

    def test_edge_usage_patterns_property_multiple_containers(self):
        """Test edge_usage_patterns property returns all containers."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsageJourney, name="Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsageJourney, name="Pattern 2")

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_usage_journey.edge_usage_patterns))

    def test_edge_usage_patterns_property_no_containers(self):
        """Test edge_usage_patterns property when no containers are set."""
        self.assertEqual([], self.edge_usage_journey.edge_usage_patterns)

    def test_systems_property_single_pattern(self):
        """Test systems property with single pattern."""
        mock_pattern = MagicMock()
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_pattern.systems = [mock_system_1, mock_system_2]

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern])
        
        self.assertEqual({mock_system_1, mock_system_2}, set(self.edge_usage_journey.systems))

    def test_systems_property_multiple_patterns(self):
        """Test systems property aggregates across multiple patterns."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsageJourney, name="Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsageJourney, name="Pattern 2")
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_system_3 = MagicMock()
        mock_pattern_1.systems = [mock_system_1, mock_system_2]
        mock_pattern_2.systems = [mock_system_2, mock_system_3]  # mock_system_2 appears in both

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])
        
        systems = self.edge_usage_journey.systems
        # Should deduplicate mock_system_2
        self.assertEqual(3, len(systems))
        self.assertIn(mock_system_1, systems)
        self.assertIn(mock_system_2, systems)
        self.assertIn(mock_system_3, systems)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_no_edge_usage_pattern(self):
        """Test that edge_functions returned as dependent objects."""
        self.assertEqual(len(self.edge_usage_journey.edge_usage_patterns), 0)
        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [self.mock_edge_function_1, self.mock_edge_function_2]
        self.assertEqual(expected_objects, dependent_objects)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_with_edge_usage_patterns(self):
        """Test that edge_functions stay as direct dependents even when patterns are linked."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsageJourney, name="Mock Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsageJourney, name="Mock Pattern 2")

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])

        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [self.mock_edge_function_1, self.mock_edge_function_2]
        self.assertEqual(expected_objects, dependent_objects)
        self.assertEqual(len(expected_objects), len(dependent_objects))

    @patch('efootprint.core.usage.edge.edge_usage_journey.compute_nb_avg_hourly_occurrences')
    def test_update_nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern(self, mock_compute_nb_avg):
        """Test updating journey-level parallel counts per edge usage pattern."""
        mock_result = EmptyExplainableObject()
        mock_compute_nb_avg.return_value = mock_result

        mock_country = create_mod_obj_mock(Country, name="Mock Country")
        mock_country.timezone = MagicMock()
        mock_network = create_mod_obj_mock(Network, name="Mock Network")
        hourly_starts = ExplainableHourlyQuantities(np.array([1.0, 2.0, 3.0]) * u.concurrent,
                                                    datetime(2023, 1, 1, 0, 0, 0), "test hourly starts")
        edge_usage_pattern = EdgeUsagePattern("test edge usage pattern", edge_usage_journey=self.edge_usage_journey,
                                              network=mock_network, country=mock_country,
                                              hourly_edge_usage_journey_starts=hourly_starts)
        utc_starts = ExplainableHourlyQuantities(np.array([1.0, 2.0, 3.0]) * u.concurrent,
                                                 datetime(2023, 1, 1, 0, 0, 0), "UTC starts")
        edge_usage_pattern.utc_hourly_edge_usage_journey_starts = utc_starts
        set_modeling_obj_containers(self.edge_usage_journey, [edge_usage_pattern])

        self.edge_usage_journey.update_nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern()

        mock_compute_nb_avg.assert_called_once_with(utc_starts, self.usage_span)
        self.assertEqual(
            self.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[edge_usage_pattern],
            mock_result)

    def test_update_impact_repartition_weights_uses_parallel_journeys_and_container_occurrences(self):
        self.edge_usage_journey.trigger_modeling_updates = False
        edge_usage_pattern_a = create_mod_obj_mock(EdgeUsagePattern, name="Edge Usage Pattern A")
        edge_usage_pattern_b = create_mod_obj_mock(EdgeUsagePattern, name="Edge Usage Pattern B")
        edge_usage_pattern_a.country = MagicMock()
        edge_usage_pattern_a.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        edge_usage_pattern_b.country = MagicMock()
        edge_usage_pattern_b.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)
        set_modeling_obj_containers(
            # It is currently not possible for an edge usage journey to be linked several times to the same
            # usage pattern, but it might happen someday and the logic will be already tested.
            self.edge_usage_journey, [edge_usage_pattern_a, edge_usage_pattern_a, edge_usage_pattern_b])
        self.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = ExplainableObjectDict({
            edge_usage_pattern_a: SourceValue(2 * u.concurrent),
            edge_usage_pattern_b: SourceValue(5 * u.concurrent),
        })

        self.edge_usage_journey.update_fabrication_impact_repartition_weights()
        self.edge_usage_journey.update_usage_impact_repartition_weights()

        self.assertEqual(4, self.edge_usage_journey.fabrication_impact_repartition_weights[edge_usage_pattern_a].magnitude)
        self.assertEqual(5, self.edge_usage_journey.fabrication_impact_repartition_weights[edge_usage_pattern_b].magnitude)
        self.assertEqual(u.concurrent, self.edge_usage_journey.fabrication_impact_repartition_weights[edge_usage_pattern_a].unit)
        self.assertEqual(400, self.edge_usage_journey.usage_impact_repartition_weights[edge_usage_pattern_a].magnitude)
        self.assertEqual(1000, self.edge_usage_journey.usage_impact_repartition_weights[edge_usage_pattern_b].magnitude)



if __name__ == "__main__":
    unittest.main()
