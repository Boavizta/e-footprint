from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class ConcreteEdgeComponent(EdgeComponent):
    """Concrete implementation of EdgeComponent for testing."""
    compatible_root_units = [u.cpu_core]
    default_values = {
        "carbon_footprint_fabrication_per_unit": SourceValue(20 * u.kg),
        "power_per_unit": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power_per_unit": SourceValue(10 * u.W),
        "nb_of_units": SourceValue(1 * u.dimensionless),
    }

    def update_unitary_power_per_usage_pattern(self):
        pass


class TestEdgeComponent(TestCase):
    def setUp(self):
        self.component = ConcreteEdgeComponent(
            name="Test Component",
            carbon_footprint_fabrication_per_unit=SourceValue(20 * u.kg),
            power_per_unit=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power_per_unit=SourceValue(10 * u.W)
        )
        self.component.trigger_modeling_updates = False
        self.component.update_carbon_footprint_fabrication()
        self.component.update_power()
        self.component.update_idle_power()

    def test_update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern(self):
        """Test fabrication footprint per edge device calculation for a single pattern."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Test Journey")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: SourceValue(10 * u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey

        self.component.update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern(mock_pattern)

        # Component intensity: 20 kg / 5 year = 4 kg/year
        # Per hour: 4 kg/year / (365.25 * 24) kg/hour
        # For 10 instances: 10 * (4 / 8766) kg
        expected_footprint = 10 * (20 / 5) / (365.25 * 24)

        result = self.component.fabrication_footprint_per_edge_device_per_usage_pattern[mock_pattern]
        self.assertAlmostEqual(expected_footprint, result.value.to(u.kg).magnitude, places=5)
        self.assertIn("Test Component", result.label)
        self.assertIn("Test Pattern", result.label)

    def test_update_dict_element_in_energy_per_edge_device_per_usage_pattern(self):
        """Test energy per edge device calculation for a single pattern."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Test Journey")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 20], pint_unit=u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey

        unitary_power = create_source_hourly_values_from_list([30, 40], pint_unit=u.W)
        self.component.unitary_power_per_usage_pattern = ExplainableObjectDict({mock_pattern: unitary_power})

        self.component.update_dict_element_in_energy_per_edge_device_per_usage_pattern(mock_pattern)

        # Energy = nb_instances * unitary_power * 1 hour = [10, 20] * [30, 40] W * 1 hour = [300, 800] Wh
        expected_energy = [300, 800]

        result = self.component.energy_per_edge_device_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_energy, result.value.to(u.Wh).magnitude))
        self.assertIn("Test Component", result.label)

    def test_update_dict_element_in_energy_footprint_per_edge_device_per_usage_pattern(self):
        """Test energy footprint per edge device calculation for a single pattern."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_country = MagicMock()
        mock_country.average_carbon_intensity = SourceValue(0.5 * u.kg / u.kWh)
        mock_pattern.country = mock_country

        energy_per_edge_device = create_source_hourly_values_from_list([1000, 2000], pint_unit=u.Wh)
        self.component.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict(
            {mock_pattern: energy_per_edge_device})

        self.component.update_dict_element_in_energy_footprint_per_edge_device_per_usage_pattern(mock_pattern)

        # Energy footprint = [1000, 2000] Wh * 0.5 kg/kWh = [0.5, 1.0] kg
        expected_footprint = [0.5, 1.0]

        result = self.component.energy_footprint_per_edge_device_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))

    def test_update_total_unitary_hourly_need_per_usage_pattern(self):
        """Test summing unitary hourly need across recurrent component needs."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")
        mock_need_1 = create_mod_obj_mock(RecurrentEdgeComponentNeed, "Need 1")
        mock_need_2 = create_mod_obj_mock(RecurrentEdgeComponentNeed, "Need 2")
        mock_need_1.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        mock_need_2.edge_usage_patterns = [mock_pattern_1]
        mock_need_1.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
            mock_pattern_2: create_source_hourly_values_from_list([4, 4], pint_unit=u.cpu_core * u.concurrent),
        })
        mock_need_2.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: create_source_hourly_values_from_list([6, 6], pint_unit=u.cpu_core * u.concurrent),
        })
        set_modeling_obj_containers(self.component, [mock_need_1, mock_need_2])

        self.component.update_total_unitary_hourly_need_per_usage_pattern()

        self.assertTrue(np.allclose(
            [16, 16], self.component.total_unitary_hourly_need_per_usage_pattern[mock_pattern_1].magnitude
        ))
        self.assertTrue(np.allclose(
            [4, 4], self.component.total_unitary_hourly_need_per_usage_pattern[mock_pattern_2].magnitude
        ))

    def test_update_fabrication_footprint_per_edge_device(self):
        """Test summing fabrication footprint per edge device across patterns."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

        footprint_1 = create_source_hourly_values_from_list([10, 20], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([5, 10], pint_unit=u.kg)
        self.component.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.component.update_fabrication_footprint_per_edge_device()

        # Sum: [10, 20] + [5, 10] = [15, 30]
        result = self.component.fabrication_footprint_per_edge_device
        self.assertTrue(np.allclose([15, 30], result.value.to(u.kg).magnitude))

    def test_update_energy_per_edge_device(self):
        """Test summing energy per edge device across patterns."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

        energy_1 = create_source_hourly_values_from_list([100, 200], pint_unit=u.Wh)
        energy_2 = create_source_hourly_values_from_list([50, 100], pint_unit=u.Wh)
        self.component.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: energy_1,
            mock_pattern_2: energy_2
        })

        self.component.update_energy_per_edge_device()

        # Sum: [100, 200] + [50, 100] = [150, 300]
        result = self.component.energy_per_edge_device
        self.assertTrue(np.allclose([150, 300], result.value.to(u.Wh).magnitude))

    def test_update_energy_footprint_per_edge_device(self):
        """Test summing energy footprint per edge device across patterns."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

        footprint_1 = create_source_hourly_values_from_list([1, 2], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([0.5, 1], pint_unit=u.kg)
        self.component.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.component.update_energy_footprint_per_edge_device()

        # Sum: [1, 2] + [0.5, 1] = [1.5, 3]
        result = self.component.energy_footprint_per_edge_device
        self.assertTrue(np.allclose([1.5, 3], result.value.to(u.kg).magnitude))

    def test_update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern_with_nb_of_units(self):
        """Test nb_of_units multiplies fabrication footprint per edge device."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern with units")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey with units")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: SourceValue(2 * u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey
        self.component.nb_of_units = SourceValue(3 * u.dimensionless)
        self.component.update_carbon_footprint_fabrication()

        self.component.update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern(mock_pattern)

        expected_footprint = 2 * ((20 / 5) * 3) / (365.25 * 24)
        result = self.component.fabrication_footprint_per_edge_device_per_usage_pattern[mock_pattern]
        self.assertAlmostEqual(expected_footprint, result.value.to(u.kg).magnitude, places=5)

    def test_update_dict_element_in_energy_per_edge_device_per_usage_pattern_with_nb_of_units(self):
        """Test nb_of_units multiplies energy per edge device."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern energy units")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey energy units")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([2, 1], pint_unit=u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey
        self.component.nb_of_units = SourceValue(3 * u.dimensionless)
        self.component.update_power()
        self.component.update_idle_power()
        self.component.unitary_power_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: create_source_hourly_values_from_list([30, 60], pint_unit=u.W)
        })

        self.component.update_dict_element_in_energy_per_edge_device_per_usage_pattern(mock_pattern)

        result = self.component.energy_per_edge_device_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose([60, 60], result.value.to(u.Wh).magnitude))


class TestEdgeComponentJsonRoundTrip(TestCase):
    def test_json_round_trip_with_used_and_unused_components(self):
        """Test JSON save and reload of an edge system where one component is used and another is unused."""
        # Create two components: one will be linked to a need, the other unused
        cpu_component = EdgeCPUComponent.from_defaults("used CPU component")
        ram_component = EdgeRAMComponent.from_defaults("unused RAM component")

        edge_device = EdgeDevice.from_defaults(
            "test edge device", components=[cpu_component, ram_component])

        # Only create a need for the CPU component, leaving RAM unused
        cpu_need = RecurrentEdgeComponentNeed(
            "CPU need", edge_component=cpu_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))

        edge_device_need = RecurrentEdgeDeviceNeed(
            "test edge device need", edge_device=edge_device,
            recurrent_edge_component_needs=[cpu_need])

        edge_function = EdgeFunction(
            "test edge function", recurrent_edge_device_needs=[edge_device_need], recurrent_server_needs=[])

        edge_usage_journey = EdgeUsageJourney.from_defaults(
            "test edge usage journey", edge_functions=[edge_function])

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        edge_usage_pattern = EdgeUsagePattern(
            "test edge usage pattern", edge_usage_journey=edge_usage_journey,
            network=Network.wifi_network(), country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [1000, 1000, 2000, 2000, 3000, 3000, 1000, 1000, 2000], start_date))

        system = System("test edge system", [], edge_usage_patterns=[edge_usage_pattern])

        # Save to JSON without calculated attributes and reload
        # That tests that the RAM dict calculated attributes have been duly initialized as dicts.
        system_json = system_to_json(system, save_calculated_attributes=False)
        _, flat_obj_dict = json_to_system(system_json)
