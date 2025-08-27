from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.core.country import Country
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class EdgeHardwareTestClass(EdgeHardware):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(100 * u.W),
        "lifespan": SourceValue(5 * u.year)
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, edge_usage_pattern):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self._edge_usage_pattern = edge_usage_pattern

    @property
    def edge_usage_pattern(self) -> "EdgeUsagePattern":
        return self._edge_usage_pattern

    def update_unitary_power_over_full_timespan(self):
        self.unitary_power_over_full_timespan = create_source_hourly_values_from_list(
            [1.5, 3], pint_unit=u.W)

    def after_init(self):
        self.trigger_modeling_updates = False


class TestEdgeHardware(TestCase):
    def setUp(self):
        mock_edge_usage_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_country = MagicMock(spec=Country)
        mock_avg_carbon_intensity = MagicMock()
        mock_country.average_carbon_intensity = mock_avg_carbon_intensity
        mock_edge_usage_pattern.country = mock_country
        self.mock_edge_usage_pattern = mock_edge_usage_pattern
        self.mock_avg_carbon_intensity = mock_avg_carbon_intensity

        self.test_edge_hardware = EdgeHardwareTestClass(
            "test edge hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years),
            edge_usage_pattern=mock_edge_usage_pattern)
        
    def test_nb_of_instances_property_no_pattern(self):
        """Test nb_of_instances property when no pattern is set."""
        test_edge_hardware = EdgeHardwareTestClass(
            "test edge hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years),
            edge_usage_pattern=None)
        test_edge_hardware.update_nb_of_instances()
        self.assertIsInstance(test_edge_hardware.nb_of_instances, EmptyExplainableObject)

    def test_nb_of_instances_property_with_pattern(self):
        """Test nb_of_instances property delegates to pattern."""
        mock_instances = create_source_hourly_values_from_list([1, 2, 3])
        self.mock_edge_usage_pattern.nb_edge_usage_journeys_in_parallel = mock_instances

        self.test_edge_hardware.update_nb_of_instances()
        self.assertEqual(mock_instances, self.test_edge_hardware.nb_of_instances)
        set_modeling_obj_containers(self.test_edge_hardware, [])
        
    def test_average_carbon_intensity_no_pattern(self):
        """Test average_carbon_intensity property."""
        test_edge_hardware = EdgeHardwareTestClass(
            "test edge hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years),
            edge_usage_pattern=None)
        self.assertEqual(EmptyExplainableObject(), test_edge_hardware.average_carbon_intensity)
        
    def test_average_carbon_intensity_with_pattern(self):
        """Test average_carbon_intensity property."""
        self.assertEqual(self.mock_avg_carbon_intensity, self.test_edge_hardware.average_carbon_intensity)

    def test_update_instances_energy(self):
        """Test update_instances_energy calculation."""
        power_values = create_source_hourly_values_from_list([100, 200, 300], pint_unit=u.W)
        nb_instances = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.dimensionless)

        with patch.object(self.test_edge_hardware, "unitary_power_over_full_timespan", power_values), \
                patch.object(self.test_edge_hardware, "nb_of_instances", nb_instances):
            self.test_edge_hardware.update_instances_energy()

            # Energy = power (W) * 1 hour * nb_instances, converted to kWh
            # [100*1*1, 200*1*2, 300*1*3] Wh = [100, 400, 900] Wh = [0.1, 0.4, 0.9] kWh
            expected_values = [0.1, 0.4, 0.9]
            self.assertTrue(np.allclose(expected_values, self.test_edge_hardware.instances_energy.value_as_float_list))
            self.assertEqual(u.kWh, self.test_edge_hardware.instances_energy.unit)
            self.assertEqual("Hourly energy consumed by test edge hardware instances",
                             self.test_edge_hardware.instances_energy.label)