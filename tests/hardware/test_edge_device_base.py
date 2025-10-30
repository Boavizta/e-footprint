from unittest import TestCase
from unittest.mock import MagicMock, patch
from typing import List

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.core.country import Country
from efootprint.core.hardware.edge.edge_device_base import EdgeDeviceBase
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeDeviceBaseTestClass(EdgeDeviceBase):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(100 * u.W),
        "lifespan": SourceValue(5 * u.year)
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, edge_usage_patterns):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self._edge_usage_patterns = edge_usage_patterns if edge_usage_patterns is not None else []

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self._edge_usage_patterns

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.unitary_power_per_usage_pattern[usage_pattern] = create_source_hourly_values_from_list(
                [1.5, 3], pint_unit=u.W).set_label(f"Unitary power for {self.name} in {usage_pattern.name}")

    def after_init(self):
        self.trigger_modeling_updates = False


class TestEdgeHardwareBase(TestCase):
    def setUp(self):
        mock_edge_usage_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_edge_usage_pattern.name = "Mock Usage Pattern"
        mock_edge_usage_pattern.id = "mock_edge_usage_pattern"
        mock_edge_usage_pattern.nb_edge_usage_journeys_in_parallel = EmptyExplainableObject()
        mock_country = MagicMock(spec=Country)
        mock_avg_carbon_intensity = MagicMock()
        mock_country.average_carbon_intensity = mock_avg_carbon_intensity
        mock_edge_usage_pattern.country = mock_country
        self.mock_edge_usage_pattern = mock_edge_usage_pattern
        self.mock_avg_carbon_intensity = mock_avg_carbon_intensity

        self.test_edge_device = EdgeDeviceBaseTestClass(
            "test edge device", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years),
            edge_usage_patterns=[mock_edge_usage_pattern])

    def test_init_sets_empty_explainable_objects(self):
        """Test that init sets ExplainableObjectDict for per-pattern calculations."""
        self.assertIsInstance(self.test_edge_device.unitary_power_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.test_edge_device.nb_of_instances_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.test_edge_device.instances_energy_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.test_edge_device.energy_footprint_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(
            self.test_edge_device.instances_fabrication_footprint_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.test_edge_device.nb_of_instances, EmptyExplainableObject)
        self.assertIsInstance(self.test_edge_device.instances_fabrication_footprint, EmptyExplainableObject)
        self.assertIsInstance(self.test_edge_device.instances_energy, EmptyExplainableObject)
        self.assertIsInstance(self.test_edge_device.energy_footprint, EmptyExplainableObject)

    def test_update_nb_of_instances_per_usage_pattern(self):
        """Test update_nb_of_instances_per_usage_pattern aggregates all patterns."""
        mock_usage_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_usage_pattern2.name = "Mock Usage Pattern 2"
        mock_usage_pattern2.id = "mock_usage_pattern2"
        
        # Update test device to have two patterns
        self.test_edge_device._edge_usage_patterns = [self.mock_edge_usage_pattern, mock_usage_pattern2]
        
        with patch.object(
                EdgeDeviceBase, "update_dict_element_in_nb_of_instances_per_usage_pattern") as mock_update:
            self.test_edge_device.update_nb_of_instances_per_usage_pattern()
            
            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(self.mock_edge_usage_pattern)
            mock_update.assert_any_call(mock_usage_pattern2)

    def test_update_dict_element_in_nb_of_instances_per_usage_pattern(self):
        """Test update_dict_element_in_nb_of_instances_per_usage_pattern calculation."""
        mock_instances = create_source_hourly_values_from_list([1, 2, 3])
        with patch.object(self.mock_edge_usage_pattern, "nb_edge_usage_journeys_in_parallel", mock_instances):
            self.test_edge_device.update_dict_element_in_nb_of_instances_per_usage_pattern(
                self.mock_edge_usage_pattern)
        
        result = self.test_edge_device.nb_of_instances_per_usage_pattern[self.mock_edge_usage_pattern]
        self.assertEqual("Number of test edge device instances for Mock Usage Pattern", result.label)
        self.assertEqual(mock_instances, result)

    def test_update_instances_fabrication_footprint_per_usage_pattern(self):
        """Test update_instances_fabrication_footprint_per_usage_pattern aggregates all patterns."""
        mock_usage_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_usage_pattern2.name = "Mock Usage Pattern 2"
        mock_usage_pattern2.id = "mock_usage_pattern2"
        
        # Update test device to have two patterns
        self.test_edge_device._edge_usage_patterns = [self.mock_edge_usage_pattern, mock_usage_pattern2]
        
        with patch.object(
                EdgeDeviceBase, "update_dict_element_in_instances_fabrication_footprint_per_usage_pattern") as mock_update:
            self.test_edge_device.update_instances_fabrication_footprint_per_usage_pattern()
            
            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(self.mock_edge_usage_pattern)
            mock_update.assert_any_call(mock_usage_pattern2)

    def test_update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(self):
        """Test update_dict_element_in_instances_fabrication_footprint_per_usage_pattern calculation."""
        mock_instances = {
            self.mock_edge_usage_pattern: create_source_hourly_values_from_list([2, 4], pint_unit=u.concurrent)}
        with patch.object(self.test_edge_device, "nb_of_instances_per_usage_pattern", mock_instances), \
                patch.object(self.test_edge_device, "carbon_footprint_fabrication", SourceValue(120 * u.kg)), \
                patch.object(self.test_edge_device, "lifespan", SourceValue(6 * u.year)):
            self.test_edge_device.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(
                self.mock_edge_usage_pattern)
        
        result = self.test_edge_device.instances_fabrication_footprint_per_usage_pattern[self.mock_edge_usage_pattern]
        # fabrication_footprint = nb_instances * carbon_footprint_fabrication / lifespan
        # = [2, 4] * 120 kg / (6 years * 365.25 * 24 hours/year)
        expected_hourly_footprint = 120 / (6 * 365.25 * 24)  # kg/hour
        expected_values = [2 * expected_hourly_footprint, 4 * expected_hourly_footprint]
        
        self.assertTrue(np.allclose(expected_values, result.value.magnitude))
        self.assertEqual(u.kg, result.unit)
        self.assertEqual(
            "Hourly test edge device instances fabrication footprint for Mock Usage Pattern", result.label)

    def test_update_instances_energy_per_usage_pattern(self):
        """Test update_instances_energy_per_usage_pattern aggregates all patterns."""
        mock_usage_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_usage_pattern2.name = "Mock Usage Pattern 2"
        mock_usage_pattern2.id = "mock_usage_pattern2"
        
        # Update test device to have two patterns
        self.test_edge_device._edge_usage_patterns = [self.mock_edge_usage_pattern, mock_usage_pattern2]
        
        with patch.object(
                EdgeDeviceBase, "update_dict_element_in_instances_energy_per_usage_pattern") as mock_update:
            self.test_edge_device.update_instances_energy_per_usage_pattern()
            
            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(self.mock_edge_usage_pattern)
            mock_update.assert_any_call(mock_usage_pattern2)

    def test_update_dict_element_in_instances_energy_per_usage_pattern(self):
        """Test update_dict_element_in_instances_energy_per_usage_pattern calculation."""
        mock_instances = {
            self.mock_edge_usage_pattern: create_source_hourly_values_from_list([1, 2], pint_unit=u.concurrent)}
        mock_power = {
            self.mock_edge_usage_pattern: create_source_hourly_values_from_list([1.5, 3], pint_unit=u.W)
        }

        with patch.object(self.test_edge_device, "unitary_power_per_usage_pattern", mock_power), \
            patch.object(self.test_edge_device, "nb_of_instances_per_usage_pattern", mock_instances):
            self.test_edge_device.update_dict_element_in_instances_energy_per_usage_pattern(
                self.mock_edge_usage_pattern)
        
        result = self.test_edge_device.instances_energy_per_usage_pattern[self.mock_edge_usage_pattern]
        # energy = nb_instances * unitary_power * 1 hour
        # = [1, 2] * [1.5, 3] W * 1 hour = [1.5, 6] Wh
        expected_values = create_source_hourly_values_from_list([1.5, 6], pint_unit=u.Wh)
        
        self.assertEqual(expected_values, result)
        self.assertEqual("Hourly energy consumed by test edge device instances for Mock Usage Pattern", result.label)

    def test_update_energy_footprint_per_usage_pattern(self):
        """Test update_energy_footprint_per_usage_pattern aggregates all patterns."""
        mock_usage_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_usage_pattern2.name = "Mock Usage Pattern 2"
        mock_usage_pattern2.id = "mock_usage_pattern2"
        
        # Update test device to have two patterns
        self.test_edge_device._edge_usage_patterns = [self.mock_edge_usage_pattern, mock_usage_pattern2]
        
        with patch.object(
                EdgeDeviceBase, "update_dict_element_in_energy_footprint_per_usage_pattern") as mock_update:
            self.test_edge_device.update_energy_footprint_per_usage_pattern()
            
            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(self.mock_edge_usage_pattern)
            mock_update.assert_any_call(mock_usage_pattern2)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern(self):
        """Test update_dict_element_in_energy_footprint_per_usage_pattern calculation."""
        instances_energy_per_usage_pattern = {
            self.mock_edge_usage_pattern: create_source_hourly_values_from_list([1, 2], pint_unit=u.kWh)}
        mock_carbon_intensity = SourceValue(100 * u.g / u.kWh)

        with patch.object(self.mock_edge_usage_pattern.country, 'average_carbon_intensity', mock_carbon_intensity), \
                patch.object(self.test_edge_device, "instances_energy_per_usage_pattern",
                             instances_energy_per_usage_pattern):
            self.test_edge_device.update_dict_element_in_energy_footprint_per_usage_pattern(
                self.mock_edge_usage_pattern)
            
            result = self.test_edge_device.energy_footprint_per_usage_pattern[self.mock_edge_usage_pattern]
            # energy_footprint = instances_energy * carbon_intensity
            # energy_footprint = [1, 2] kWh * [100] g/kWh = [100, 200] g
            expected_values = [100, 200]
            
            self.assertTrue(np.allclose(expected_values, result.value.magnitude))
            self.assertEqual(u.g, result.unit)
            self.assertEqual("test edge device energy footprint for Mock Usage Pattern", result.label)

    def test_sum_calculated_attribute_across_usage_patterns(self):
        """Test sum_calculated_attribute_across_usage_patterns method."""
        # Create a second usage pattern
        mock_usage_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_usage_pattern2.name = "Mock Usage Pattern 2"
        mock_usage_pattern2.id = "mock_usage_pattern2"
        
        # Set up mock instances for both patterns
        mock_instances1 = create_source_hourly_values_from_list([1, 2], pint_unit=u.concurrent)
        mock_instances2 = create_source_hourly_values_from_list([2, 3], pint_unit=u.concurrent)
        
        # Update test device to have two patterns
        self.test_edge_device._edge_usage_patterns = [self.mock_edge_usage_pattern, mock_usage_pattern2]
        
        # Set up mock instances for both patterns
        self.mock_edge_usage_pattern.nb_edge_usage_journeys_in_parallel = mock_instances1
        mock_usage_pattern2.nb_edge_usage_journeys_in_parallel = mock_instances2
        
        self.test_edge_device.update_nb_of_instances_per_usage_pattern()
        
        # Test the sum method
        result = self.test_edge_device.sum_calculated_attribute_across_usage_patterns(
            "nb_of_instances_per_usage_pattern", "total instances")
        
        # Sum should be [1+2, 2+3] = [3, 5]
        expected_values = [3, 5]
        self.assertTrue(np.allclose(expected_values, result.value.magnitude))
        self.assertEqual("test edge device total instances across usage patterns", result.label)

    def test_update_aggregated_attributes(self):
        """Test that aggregated attributes are properly updated."""
        mock_instances = create_source_hourly_values_from_list([1, 2], pint_unit=u.concurrent)
        self.mock_edge_usage_pattern.nb_edge_usage_journeys_in_parallel = mock_instances
        
        # Update per-pattern and aggregated attributes
        self.test_edge_device.update_nb_of_instances_per_usage_pattern()
        self.test_edge_device.update_unitary_power_per_usage_pattern()
        self.test_edge_device.update_instances_fabrication_footprint_per_usage_pattern()
        self.test_edge_device.update_instances_energy_per_usage_pattern()
        
        self.test_edge_device.update_nb_of_instances()
        self.test_edge_device.update_instances_fabrication_footprint()
        self.test_edge_device.update_instances_energy()
        
        # Check that aggregated attributes are not EmptyExplainableObject anymore
        self.assertNotIsInstance(self.test_edge_device.nb_of_instances, EmptyExplainableObject)
        self.assertNotIsInstance(self.test_edge_device.instances_fabrication_footprint, EmptyExplainableObject)
        self.assertNotIsInstance(self.test_edge_device.instances_energy, EmptyExplainableObject)
        
        # Check labels
        self.assertEqual("test edge device total instances across usage patterns", 
                        self.test_edge_device.nb_of_instances.label)
        self.assertEqual("test edge device total fabrication footprint across usage patterns", 
                        self.test_edge_device.instances_fabrication_footprint.label)
        self.assertEqual("test edge device total instances energy across usage patterns", 
                        self.test_edge_device.instances_energy.label)

    def test_edge_device_no_patterns(self):
        """Test EdgeHardware behavior with no usage patterns."""
        test_edge_device = EdgeDeviceBaseTestClass(
            "test edge device", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years),
            edge_usage_patterns=None)
        
        # All per-pattern dicts should be empty
        self.assertEqual(0, len(test_edge_device.unitary_power_per_usage_pattern))
        self.assertEqual(0, len(test_edge_device.nb_of_instances_per_usage_pattern))
        self.assertEqual(0, len(test_edge_device.instances_energy_per_usage_pattern))
        self.assertEqual(0, len(test_edge_device.energy_footprint_per_usage_pattern))
        self.assertEqual(0, len(test_edge_device.instances_fabrication_footprint_per_usage_pattern))
        
        # Aggregated attributes should remain as EmptyExplainableObject
        test_edge_device.update_nb_of_instances()
        test_edge_device.update_instances_fabrication_footprint()
        test_edge_device.update_instances_energy()
        test_edge_device.update_energy_footprint()
        
        self.assertIsInstance(test_edge_device.nb_of_instances, EmptyExplainableObject)
        self.assertIsInstance(test_edge_device.instances_fabrication_footprint, EmptyExplainableObject)
        self.assertIsInstance(test_edge_device.instances_energy, EmptyExplainableObject)
        self.assertIsInstance(test_edge_device.energy_footprint, EmptyExplainableObject)