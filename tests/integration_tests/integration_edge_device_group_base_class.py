"""Integration tests base class for EdgeDeviceGroup hierarchical grouping."""
from datetime import datetime

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass

NB_FLOORS = 3
NB_DEVICES_PER_FLOOR = 4
EXPECTED_TOTAL_DEVICES = NB_FLOORS * NB_DEVICES_PER_FLOOR  # 12


class IntegrationEdgeDeviceGroupBaseClass(IntegrationTestBaseClass):
    """Base class for EdgeDeviceGroup integration tests.

    Hierarchy:
        building_group (root)  ── contains floor_group × NB_FLOORS
        floor_group            ── contains edge_device × NB_DEVICES_PER_FLOOR
        Total devices per ensemble = NB_FLOORS × NB_DEVICES_PER_FLOOR = 12
    """

    REF_JSON_FILENAME = "edge_device_group_system"
    OBJECT_NAMES_MAP = {
        "building_group": "building group",
        "floor_group": "floor group",
        "edge_device": "grouped edge device",
    }

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

        return system, start_date

    @classmethod
    def setUpClass(cls):
        system, start_date = cls.generate_edge_device_group_system()
        cls._setup_from_system(system, start_date)

    # ------------------------------------------------------------------
    # run_test_* methods (auto-converted to test_* by AutoTestMethodsMeta)
    # ------------------------------------------------------------------

    def run_test_edge_device_group_linked_to_system(self):
        all_objects = self.system.all_linked_objects
        self.assertIn(self.floor_group, all_objects)
        self.assertIn(self.building_group, all_objects)

    def run_test_structural_group_dict_keys_populate_contextual_parents(self):
        self.assertIn(self.building_group, self.floor_group.modeling_obj_containers)
        self.assertIn(self.floor_group, self.edge_device.modeling_obj_containers)

    def run_test_contextual_parentage_survives_structural_dict_update(self):
        initial_sub_group_counts = self.building_group.sub_group_counts
        updated_sub_group_counts = ExplainableObjectDict(
            {self.floor_group: SourceValue((NB_FLOORS + 1) * u.dimensionless)}
        )

        self.building_group.sub_group_counts = updated_sub_group_counts

        try:
            self.assertIn(self.building_group, self.floor_group.modeling_obj_containers)
            self.assertAlmostEqual(NB_FLOORS + 1, self.floor_group.effective_nb_of_units_within_root.value.magnitude)
            self.assertAlmostEqual((NB_FLOORS + 1) * NB_DEVICES_PER_FLOOR, self.edge_device.total_nb_of_units.value.magnitude)
            self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        finally:
            self.building_group.sub_group_counts = initial_sub_group_counts

        self.assertAlmostEqual(NB_FLOORS, self.floor_group.effective_nb_of_units_within_root.value.magnitude)
        self.assertAlmostEqual(EXPECTED_TOTAL_DEVICES, self.edge_device.total_nb_of_units.value.magnitude)
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_existing_edge_device_count_update_recomputes_hierarchy(self):
        self.floor_group.edge_device_counts[self.edge_device] = SourceValue((NB_DEVICES_PER_FLOOR + 1) * u.dimensionless)

        self.assertAlmostEqual(
            NB_DEVICES_PER_FLOOR + 1,
            self.floor_group.edge_device_counts[self.edge_device].value.magnitude,
        )
        self.assertAlmostEqual(
            NB_FLOORS * (NB_DEVICES_PER_FLOOR + 1),
            self.edge_device.total_nb_of_units.value.magnitude,
        )

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

        self.assertIn(reloaded_building, reloaded_floor.modeling_obj_containers)
        self.assertIn(reloaded_floor, reloaded_device.modeling_obj_containers)

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
