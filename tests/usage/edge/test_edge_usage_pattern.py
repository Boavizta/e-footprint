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
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.country import Country
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers
from tests.utils import recompute_attribute


class TestEdgeUsagePattern(TestCase):
    @staticmethod
    def hourly_starts():
        return ExplainableHourlyQuantities(
            np.array([1.0, 2.0, 3.0, 4.0, 5.0]) * u.concurrent,
            datetime(2023, 1, 1), "test hourly starts")

    def test_containment_inventory_counts_actual_paths_across_bundles(self):
        shared_component_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, "Shared component need")
        device_need = create_mod_obj_mock(RecurrentEdgeDeviceNeed, "Shared device need")
        device_need.recurrent_edge_component_needs = [shared_component_need, shared_component_need]
        server_need = create_mod_obj_mock(RecurrentServerNeed, "Shared server need")
        first_function = create_mod_obj_mock(EdgeFunction, "First function")
        first_function.recurrent_edge_device_needs = [device_need]
        first_function.recurrent_server_needs = [server_need]
        second_function = create_mod_obj_mock(EdgeFunction, "Second function")
        second_function.recurrent_edge_device_needs = [device_need]
        second_function.recurrent_server_needs = [server_need]
        first = EdgeUsageJourney("First bundle", [first_function])
        second = EdgeUsageJourney("Second bundle", [second_function])
        pattern = EdgeUsagePattern(
            "Multi-bundle pattern", [first, second], self.mock_network, self.mock_country,
            self.hourly_starts())

        inventory = pattern.containment_inventory
        self.assertEqual(4, sum(path.nb_occurrences for path in inventory.component_need_paths))
        self.assertEqual(2, sum(path.nb_occurrences for path in inventory.server_need_paths))

    def test_edge_journey_list_invariants_hold_on_construction_and_live_mutation(self):
        with self.assertRaises(ValueError):
            EdgeUsagePattern(
                "Empty pattern", [], self.mock_network, self.mock_country, self.hourly_starts())
        with self.assertRaises(ValueError):
            EdgeUsagePattern(
                "Duplicate pattern", [self.mock_edge_usage_journey, self.mock_edge_usage_journey],
                self.mock_network, self.mock_country, self.hourly_starts())

        live_journey = EdgeUsageJourney("Live bundle", [])
        live_pattern = EdgeUsagePattern(
            "Live pattern", [live_journey], Network.wifi_network(), Countries.FRANCE(), self.hourly_starts())
        System("Live edge system", [], [live_pattern])
        with self.assertRaises(ValueError):
            live_pattern.edge_usage_journeys = []
        self.assertEqual([live_journey], live_pattern.edge_usage_journeys)

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

        self.edge_usage_pattern = EdgeUsagePattern("test edge usage pattern", edge_usage_journeys=[self.mock_edge_usage_journey],
                                                   network=self.mock_network, country=self.mock_country,
                                                   hourly_deployment_starts=self.real_hourly_starts)

    def test_init(self):
        """Test EdgeUsagePattern initialization."""
        self.assertEqual("test edge usage pattern", self.edge_usage_pattern.name)
        self.assertEqual([self.mock_edge_usage_journey], self.edge_usage_pattern.edge_usage_journeys)
        self.assertEqual(self.mock_country, self.edge_usage_pattern.country)
        self.assertEqual(self.mock_network, self.edge_usage_pattern.network)
        self.assertEqual(self.real_hourly_starts, self.edge_usage_pattern.hourly_deployment_starts)

        # Reading the computed attribute computes it on demand.
        self.assertEqual(
            len(self.edge_usage_pattern.hourly_deployment_starts),
            len(self.edge_usage_pattern.utc_hourly_deployment_starts))


    def test_recurrent_edge_device_needs(self):
        """Test recurrent_edge_device_needs property delegates to edge_usage_journey."""
        self.assertEqual([self.mock_edge_need], self.edge_usage_pattern.recurrent_edge_device_needs)

    def test_systems(self):
        """Test systems property returns modeling_obj_containers."""
        mock_system = MagicMock(spec=ModelingObject)
        mock_system.systems = [mock_system]
        set_modeling_obj_containers(self.edge_usage_pattern, [mock_system])

        self.assertEqual([mock_system], self.edge_usage_pattern.systems)

    def test_update_utc_hourly_deployment_starts(self):
        """Test update_utc_hourly_deployment_starts method."""
        mock_utc_result = ExplainableHourlyQuantities(
            np.array([1.0, 2.0, 3.0]) * u.concurrent,
            datetime(2023, 1, 1, 0, 0, 0),
            "UTC result"
        )

        # Patch at class level because __slots__ prevents instance-level patching
        with patch.object(ExplainableHourlyQuantities, 'convert_to_utc',
                          return_value=mock_utc_result) as mock_convert:
            recompute_attribute(self.edge_usage_pattern, "utc_hourly_deployment_starts")
            mock_convert.assert_called_once_with(local_timezone=self.mock_country.timezone)

            self.assertEqual(self.edge_usage_pattern.utc_hourly_deployment_starts, mock_utc_result)


if __name__ == "__main__":
    unittest.main()
