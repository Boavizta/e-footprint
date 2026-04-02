"""Integration tests base class for EdgeDeviceGroup hierarchical grouping."""
import os
from datetime import datetime
from unittest import TestCase

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

INTEGRATION_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

NB_FLOORS = 3
NB_DEVICES_PER_FLOOR = 4
EXPECTED_TOTAL_DEVICES = NB_FLOORS * NB_DEVICES_PER_FLOOR  # 12


class IntegrationEdgeDeviceGroupBaseClass(TestCase):
    """Base class for EdgeDeviceGroup integration tests.

    Hierarchy:
        building_group (root)  ── contains floor_group × NB_FLOORS
        floor_group            ── contains edge_device × NB_DEVICES_PER_FLOOR
        Total devices per ensemble = NB_FLOORS × NB_DEVICES_PER_FLOOR = 12
    """

    @staticmethod
    def generate_edge_device_group_system():
        ram_component = EdgeRAMComponent.from_defaults("edge RAM component")
        cpu_component = EdgeCPUComponent.from_defaults("edge CPU component")

        edge_device = EdgeDevice.from_defaults(
            "grouped edge device", components=[ram_component, cpu_component])

        ram_need = RecurrentEdgeComponentNeed(
            "RAM need",
            edge_component=ram_component,
            recurrent_need=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB_ram)),
        )
        cpu_need = RecurrentEdgeComponentNeed(
            "CPU need",
            edge_component=cpu_component,
            recurrent_need=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
        )
        edge_device_need = RecurrentEdgeDeviceNeed(
            "grouped edge device need",
            edge_device=edge_device,
            recurrent_edge_component_needs=[ram_need, cpu_need],
        )
        edge_function = EdgeFunction(
            "grouped edge function",
            recurrent_edge_device_needs=[edge_device_need],
            recurrent_server_needs=[],
        )
        edge_usage_journey = EdgeUsageJourney.from_defaults(
            "grouped edge usage journey", edge_functions=[edge_function])

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        edge_usage_pattern = EdgeUsagePattern(
            "grouped edge usage pattern",
            edge_usage_journey=edge_usage_journey,
            network=Network.wifi_network(),
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [1000, 1000, 2000, 2000, 3000, 3000, 1000, 1000, 2000], start_date),
        )

        floor_group = EdgeDeviceGroup(
            "floor group",
            sub_group_counts={},
            edge_device_counts={edge_device: SourceValue(NB_DEVICES_PER_FLOOR * u.dimensionless)},
        )
        building_group = EdgeDeviceGroup(
            "building group",
            sub_group_counts={floor_group: SourceValue(NB_FLOORS * u.dimensionless)},
            edge_device_counts={},
        )

        system = System("Edge Device Group System", [], edge_usage_patterns=[edge_usage_pattern])

        return system, start_date, building_group, floor_group, edge_device

    @classmethod
    def setUpClass(cls):
        system, start_date, building_group, floor_group, edge_device = cls.generate_edge_device_group_system()
        cls.system = system
        cls.start_date = start_date
        cls.building_group = building_group
        cls.floor_group = floor_group
        cls.edge_device = edge_device

    # ------------------------------------------------------------------
    # run_test_* methods (auto-converted to test_* by AutoTestMethodsMeta)
    # ------------------------------------------------------------------

    def run_test_building_group_effective_nb_is_one(self):
        self.assertAlmostEqual(
            1.0,
            self.building_group.effective_nb_of_units_within_root.value.magnitude,
        )

    def run_test_floor_group_effective_nb_equals_nb_floors(self):
        self.assertAlmostEqual(
            NB_FLOORS,
            self.floor_group.effective_nb_of_units_within_root.value.magnitude,
        )

    def run_test_edge_device_total_nb_equals_total_devices(self):
        self.assertAlmostEqual(
            EXPECTED_TOTAL_DEVICES,
            self.edge_device.total_nb_of_units.value.magnitude,
        )

    def run_test_edge_device_group_linked_to_system(self):
        all_objects = self.system.all_linked_objects
        self.assertIn(self.floor_group, all_objects)
        self.assertIn(self.building_group, all_objects)

    def run_test_footprint_is_nonzero(self):
        total = self.system.total_footprint
        self.assertGreater(float(str(total).split()[0]), 0)

    def run_test_system_to_json_and_back_preserves_group_counts(self):
        """JSON round-trip must preserve sub_group_counts and edge_device_counts."""
        system_json = system_to_json(self.system, save_calculated_attributes=False)
        _, flat_obj_dict = json_to_system(system_json)

        reloaded_building = flat_obj_dict[self.building_group.id]
        reloaded_floor = flat_obj_dict[self.floor_group.id]
        reloaded_device = flat_obj_dict[self.edge_device.id]

        self.assertEqual(1, len(reloaded_building.sub_group_counts))
        self.assertIn(reloaded_floor, reloaded_building.sub_group_counts)
        self.assertAlmostEqual(
            NB_FLOORS,
            reloaded_building.sub_group_counts[reloaded_floor].value.magnitude,
        )

        self.assertEqual(1, len(reloaded_floor.edge_device_counts))
        self.assertIn(reloaded_device, reloaded_floor.edge_device_counts)
        self.assertAlmostEqual(
            NB_DEVICES_PER_FLOOR,
            reloaded_floor.edge_device_counts[reloaded_device].value.magnitude,
        )

    def run_test_json_round_trip_recalculates_correct_effective_nb(self):
        """After a JSON round-trip, calculated attributes are correct."""
        system_json = system_to_json(self.system, save_calculated_attributes=False)
        _, flat_obj_dict = json_to_system(system_json)

        reloaded_building = flat_obj_dict[self.building_group.id]
        reloaded_floor = flat_obj_dict[self.floor_group.id]
        reloaded_device = flat_obj_dict[self.edge_device.id]

        self.assertAlmostEqual(
            1.0,
            reloaded_building.effective_nb_of_units_within_root.value.magnitude,
        )
        self.assertAlmostEqual(
            NB_FLOORS,
            reloaded_floor.effective_nb_of_units_within_root.value.magnitude,
        )
        self.assertAlmostEqual(
            EXPECTED_TOTAL_DEVICES,
            reloaded_device.total_nb_of_units.value.magnitude,
        )

    def run_test_no_groups_backward_compat_total_nb_is_one(self):
        """An EdgeDevice not linked to any group must report total_nb = 1."""
        cpu = EdgeCPUComponent.from_defaults("ungrouped CPU")
        device = EdgeDevice.from_defaults("ungrouped device", components=[cpu])
        cpu_need = RecurrentEdgeComponentNeed(
            "ungrouped CPU need", edge_component=cpu,
            recurrent_need=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))
        need = RecurrentEdgeDeviceNeed(
            "ungrouped device need", edge_device=device,
            recurrent_edge_component_needs=[cpu_need])
        func = EdgeFunction("ungrouped func", recurrent_edge_device_needs=[need],
                            recurrent_server_needs=[])
        journey = EdgeUsageJourney.from_defaults("ungrouped journey", edge_functions=[func])
        start = datetime.strptime("2025-01-01", "%Y-%m-%d")
        pattern = EdgeUsagePattern(
            "ungrouped pattern", edge_usage_journey=journey,
            network=Network.wifi_network(), country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [100, 100, 200], start))
        System("ungrouped system", [], edge_usage_patterns=[pattern])

        self.assertAlmostEqual(1.0, device.total_nb_of_units.value.magnitude)
