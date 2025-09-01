import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_storage import EdgeStorage, NegativeCumulativeStorageNeedError
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestEdgeStorage(TestCase):
    def setUp(self):
        self.edge_storage = EdgeStorage(
            name="Test EdgeStorage",
            storage_capacity=SourceValue(1 * u.TB),
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB),
            idle_power=SourceValue(0 * u.W),
            base_storage_need=SourceValue(0 * u.TB),
            lifespan=SourceValue(6 * u.years)
        )
        self.edge_storage.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeStorage initialization."""
        self.assertEqual("Test EdgeStorage", self.edge_storage.name)
        self.assertEqual(1 * u.TB, self.edge_storage.storage_capacity.value)
        self.assertEqual(160 * u.kg / u.TB, self.edge_storage.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(1.3 * u.W / u.TB, self.edge_storage.power_per_storage_capacity.value)
        self.assertEqual(0 * u.W, self.edge_storage.idle_power.value)
        self.assertEqual(0 * u.TB, self.edge_storage.base_storage_need.value)
        self.assertEqual(6 * u.years, self.edge_storage.lifespan.value)

    def test_init_sets_empty_explainable_objects(self):
        """Test that initialization sets proper empty explainable objects."""
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        self.assertIsInstance(self.edge_storage.unitary_storage_delta_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern, ExplainableObjectDict)

    def test_labels_are_set_correctly(self):
        """Test that all attributes have correct labels."""
        self.assertIn("Fabrication carbon footprint of Test EdgeStorage per storage capacity",
                     self.edge_storage.carbon_footprint_fabrication_per_storage_capacity.label)
        self.assertIn("Power of Test EdgeStorage per storage capacity",
                     self.edge_storage.power_per_storage_capacity.label)
        self.assertIn("Idle power of Test EdgeStorage", self.edge_storage.idle_power.label)
        self.assertIn("Storage capacity of Test EdgeStorage", self.edge_storage.storage_capacity.label)
        self.assertIn("Test EdgeStorage initial storage need", self.edge_storage.base_storage_need.label)

    def test_ssd_classmethod(self):
        """Test SSD factory method."""
        ssd = EdgeStorage.ssd(name="Custom SSD")
        self.assertEqual("Custom SSD", ssd.name)
        self.assertEqual(160 * u.kg / u.TB, ssd.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(1.3 * u.W / u.TB, ssd.power_per_storage_capacity.value)
        self.assertEqual(6 * u.years, ssd.lifespan.value)
        self.assertEqual(0 * u.W, ssd.idle_power.value)
        self.assertEqual(1 * u.TB, ssd.storage_capacity.value)
        self.assertEqual(0 * u.TB, ssd.base_storage_need.value)

    def test_ssd_classmethod_with_kwargs(self):
        """Test SSD factory method with custom parameters."""
        ssd = EdgeStorage.ssd(
            name="Custom SSD",
            storage_capacity=SourceValue(2 * u.TB),
            lifespan=SourceValue(8 * u.years)
        )
        self.assertEqual("Custom SSD", ssd.name)
        self.assertEqual(2 * u.TB, ssd.storage_capacity.value)
        self.assertEqual(8 * u.years, ssd.lifespan.value)
        # Other values should remain as defaults
        self.assertEqual(160 * u.kg / u.TB, ssd.carbon_footprint_fabrication_per_storage_capacity.value)

    def test_hdd_classmethod(self):
        """Test HDD factory method."""
        hdd = EdgeStorage.hdd(name="Custom HDD")
        self.assertEqual("Custom HDD", hdd.name)
        self.assertEqual(20 * u.kg / u.TB, hdd.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(4.2 * u.W / u.TB, hdd.power_per_storage_capacity.value)
        self.assertEqual(4 * u.years, hdd.lifespan.value)
        self.assertEqual(0 * u.W, hdd.idle_power.value)
        self.assertEqual(1 * u.TB, hdd.storage_capacity.value)
        self.assertEqual(0 * u.TB, hdd.base_storage_need.value)

    def test_hdd_classmethod_with_kwargs(self):
        """Test HDD factory method with custom parameters."""
        hdd = EdgeStorage.hdd(
            name="Custom HDD",
            storage_capacity=SourceValue(4 * u.TB),
            idle_power=SourceValue(2 * u.W)
        )
        self.assertEqual("Custom HDD", hdd.name)
        self.assertEqual(4 * u.TB, hdd.storage_capacity.value)
        self.assertEqual(2 * u.W, hdd.idle_power.value)
        # Other values should remain as defaults
        self.assertEqual(20 * u.kg / u.TB, hdd.carbon_footprint_fabrication_per_storage_capacity.value)

    def test_archetypes(self):
        """Test archetypes method returns both factory methods."""
        archetypes = EdgeStorage.archetypes()
        self.assertEqual(2, len(archetypes))
        self.assertIn(EdgeStorage.ssd, archetypes)
        self.assertIn(EdgeStorage.hdd, archetypes)

    def test_edge_device_property_no_containers(self):
        """Test edge_device property when no containers are set."""
        self.assertIsNone(self.edge_storage.edge_device)

    def test_edge_device_property_single_container(self):
        """Test edge_device property with single container."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Mock Device"
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        self.assertEqual(mock_device, self.edge_storage.edge_device)
        set_modeling_obj_containers(self.edge_storage, [])

    def test_edge_device_property_multiple_containers_raises_error(self):
        """Test edge_device property raises error with multiple containers."""
        mock_device_1 = MagicMock(spec=EdgeDevice)
        mock_device_1.name = "Device 1"
        mock_device_2 = MagicMock(spec=EdgeDevice)
        mock_device_2.name = "Device 2"
        
        set_modeling_obj_containers(self.edge_storage, [mock_device_1, mock_device_2])
        
        with self.assertRaises(PermissionError) as context:
            _ = self.edge_storage.edge_device
        
        expected_message = ("An EdgeStorage object can only be associated with one EdgeDevice object but "
                          "Test EdgeStorage is associated with")
        self.assertIn(expected_message, str(context.exception))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_edge_processes_property_no_device(self):
        """Test edge_processes property when no device is set."""
        self.assertEqual([], self.edge_storage.edge_processes)

    def test_edge_processes_property_with_device(self):
        """Test edge_processes property delegates to device."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_processes = [MagicMock(spec=RecurrentEdgeProcess), MagicMock(spec=RecurrentEdgeProcess)]
        mock_device.edge_processes = mock_processes
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        self.assertEqual(mock_processes, self.edge_storage.edge_processes)
        set_modeling_obj_containers(self.edge_storage, [])

    def test_edge_usage_patterns_property_no_device(self):
        """Test edge_usage_patterns property when no device is set."""
        self.assertEqual([], self.edge_storage.edge_usage_patterns)

    def test_edge_usage_patterns_property_with_device(self):
        """Test edge_usage_patterns property delegates to device."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_device.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        self.assertEqual([mock_pattern_1, mock_pattern_2], self.edge_storage.edge_usage_patterns)
        set_modeling_obj_containers(self.edge_storage, [])

    def test_power_usage_effectiveness_property_no_device(self):
        """Test power_usage_effectiveness property when no device is set."""
        result = self.edge_storage.power_usage_effectiveness
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_power_usage_effectiveness_property_with_device(self):
        """Test power_usage_effectiveness property delegates to device."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_pue = SourceValue(1.4 * u.dimensionless)
        mock_device.power_usage_effectiveness = mock_pue
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        self.assertEqual(mock_pue, self.edge_storage.power_usage_effectiveness)
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_carbon_footprint_fabrication(self):
        """Test update_carbon_footprint_fabrication calculation."""
        with patch.object(self.edge_storage, "carbon_footprint_fabrication_per_storage_capacity",
                         SourceValue(100 * u.kg / u.TB)), \
             patch.object(self.edge_storage, "storage_capacity",
                         SourceValue(2 * u.TB)):
            
            self.edge_storage.update_carbon_footprint_fabrication()
            
            expected_value = 100 * 2  # 200 kg
            self.assertAlmostEqual(
                expected_value, self.edge_storage.carbon_footprint_fabrication.value.magnitude, places=5)
            self.assertEqual(u.kg, self.edge_storage.carbon_footprint_fabrication.value.units)
            self.assertEqual("Carbon footprint of Test EdgeStorage",
                             self.edge_storage.carbon_footprint_fabrication.label)

    def test_update_power(self):
        """Test update_power calculation."""
        with patch.object(self.edge_storage, "power_per_storage_capacity",
                          SourceValue(2.0 * u.W / u.TB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(3 * u.TB)):
            
            self.edge_storage.update_power()
            
            expected_value = 2.0 * 3  # 6.0 W
            self.assertAlmostEqual(expected_value, self.edge_storage.power.value.magnitude, places=5)
            self.assertEqual(u.W, self.edge_storage.power.value.units)
            self.assertEqual("Power of Test EdgeStorage", self.edge_storage.power.label)

    def test_update_unitary_storage_delta_per_usage_pattern(self):
        """Test update_unitary_storage_delta_per_usage_pattern aggregates all patterns."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2.name = "Pattern 2"
        mock_device.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        with patch.object(EdgeStorage, "update_dict_element_in_unitary_storage_delta_per_usage_pattern") as mock_update:
            self.edge_storage.update_unitary_storage_delta_per_usage_pattern()
            
            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(mock_pattern_1)
            mock_update.assert_any_call(mock_pattern_2)
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_unitary_storage_delta_per_usage_pattern_empty(self):
        """Test update_dict_element_in_unitary_storage_delta_per_usage_pattern with no processes."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.edge_processes = []
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        self.edge_storage.update_dict_element_in_unitary_storage_delta_per_usage_pattern(mock_pattern)
        
        result = self.edge_storage.unitary_storage_delta_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)
        self.assertIn("Hourly storage delta for Test EdgeStorage in Test Pattern", result.label)
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_unitary_storage_delta_per_usage_pattern_with_processes(self):
        """Test update_dict_element_in_unitary_storage_delta_per_usage_pattern with processes."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        
        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)
        
        storage_need_1 = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.GB)
        storage_need_2 = create_source_hourly_values_from_list([2, 1, 4], pint_unit=u.GB)
        
        mock_process_1.unitary_hourly_storage_need_per_usage_pattern = {mock_pattern: storage_need_1}
        mock_process_2.unitary_hourly_storage_need_per_usage_pattern = {mock_pattern: storage_need_2}
        
        mock_device.edge_processes = [mock_process_1, mock_process_2]
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        self.edge_storage.update_dict_element_in_unitary_storage_delta_per_usage_pattern(mock_pattern)
        
        expected_values = [3, 3, 7]  # Sum of both processes
        result = self.edge_storage.unitary_storage_delta_per_usage_pattern[mock_pattern]
        self.assertEqual(expected_values, result.value_as_float_list)
        self.assertEqual(u.GB, result.unit)
        self.assertIn("Hourly storage delta for Test EdgeStorage in Test Pattern", result.label)
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_empty_delta(self):
        """Test update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern with empty delta."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test pattern id"
        
        empty_delta = EmptyExplainableObject()
        self.edge_storage.unitary_storage_delta_per_usage_pattern = {mock_pattern: empty_delta}
        
        self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(mock_pattern)
        
        result = self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)
        self.assertIn(empty_delta, result.direct_ancestors_with_id)

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_with_data(self):
        """Test update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern with real data."""
        # Create mock edge device and usage journey
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.usage_span = SourceValue(3 * u.hour)
        mock_device.edge_usage_journey = mock_journey
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test pattern id"
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        # Create storage delta data (5 hours of data, but usage span is only 3 hours)
        storage_delta = create_source_hourly_values_from_list([10, 5, -3, 2, 1], pint_unit=u.GB)
        self.edge_storage.unitary_storage_delta_per_usage_pattern = {mock_pattern: storage_delta}
        
        # Set base storage need and storage capacity
        with patch.object(self.edge_storage, "base_storage_need", SourceValue(20 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB)):
            
            self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(mock_pattern)
            
            # Expected: [20+10, 20+10+5, 20+10+5-3] = [30, 35, 32]
            expected_values = [30, 35, 32]
            result = self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[mock_pattern]
            self.assertEqual(expected_values, result.value_as_float_list)
            self.assertEqual(u.GB, result.unit)
            self.assertIn("Cumulative storage need for Test EdgeStorage in Test Pattern", result.label)
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_cumulative_unitary_storage_need_negative_cumulative_error(self):
        """Test update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern raises error on negative cumulative storage."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.usage_span = SourceValue(3 * u.hour)
        mock_device.edge_usage_journey = mock_journey
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test Pattern id"
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        # Create storage delta that will result in negative cumulative
        storage_delta = create_source_hourly_values_from_list([10, -20, 5], pint_unit=u.GB)
        self.edge_storage.unitary_storage_delta_per_usage_pattern = {mock_pattern: storage_delta}
        
        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB)):
            
            with self.assertRaises(NegativeCumulativeStorageNeedError) as context:
                self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(mock_pattern)
            
            self.assertEqual(self.edge_storage, context.exception.storage_obj)
            self.assertIn("negative cumulative storage need detected", str(context.exception))
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_cumulative_unitary_storage_need_insufficient_capacity_error(self):
        """Test update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern raises error when capacity exceeded."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.usage_span = SourceValue(2 * u.hour)
        mock_device.edge_usage_journey = mock_journey
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test pattern id"
        
        set_modeling_obj_containers(self.edge_storage, [mock_device])
        
        # Create storage delta that will exceed capacity
        storage_delta = create_source_hourly_values_from_list([40, 60], pint_unit=u.GB)
        self.edge_storage.unitary_storage_delta_per_usage_pattern = {mock_pattern: storage_delta}
        
        with patch.object(self.edge_storage, "base_storage_need", SourceValue(10 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(50 * u.GB)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(mock_pattern)
            
            self.assertEqual("storage capacity", context.exception.capacity_type)
            self.assertEqual(self.edge_storage, context.exception.overloaded_object)
            self.assertEqual(self.edge_storage.storage_capacity, context.exception.available_capacity)
            # Maximum required storage is 10 + 40 + 60 = 110 GB
            self.assertEqual(110 * u.GB, context.exception.requested_capacity.value)
            self.assertIn("Test EdgeStorage cumulative storage need for Test Pattern", context.exception.requested_capacity.label)
        
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_unitary_power_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_power_per_usage_pattern calculation."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test pattern id"
        
        storage_delta = create_source_hourly_values_from_list([0, 500, -250], pint_unit=u.GB)
        self.edge_storage.unitary_storage_delta_per_usage_pattern = {mock_pattern: storage_delta}
        
        with patch.object(self.edge_storage, "storage_capacity", SourceValue(1 * u.TB)), \
             patch.object(self.edge_storage, "idle_power", SourceValue(5 * u.W)), \
             patch.object(self.edge_storage, "power", SourceValue(25 * u.W)), \
             patch.object(EdgeStorage, "power_usage_effectiveness", new_callable=PropertyMock) as mock_pue:
            mock_pue.return_value = SourceValue(1.2 * u.dimensionless)
            self.edge_storage.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)
            
            # Activity levels: [0/1000, 500/1000, 250/1000] = [0, 0.5, 0.25]
            # Power: [5 + (25-5)*0, 5 + (25-5)*0.5, 5 + (25-5)*0.25] = [5, 15, 10]
            # With PUE: [5*1.2, 15*1.2, 10*1.2] = [6, 18, 12]
            expected_values = [6, 18, 12]
            result = self.edge_storage.unitary_power_per_usage_pattern[mock_pattern]
            self.assertTrue(np.allclose(expected_values, result.value_as_float_list))
            self.assertEqual(u.W, result.unit)
            self.assertIn("Hourly power for Test EdgeStorage in Test Pattern", result.label)

    def test_negative_cumulative_storage_need_error_message(self):
        """Test NegativeCumulativeStorageNeedError message formatting."""
        cumulative_quantity = np.array([-5, -10, -2]) * u.GB
        error = NegativeCumulativeStorageNeedError(self.edge_storage, cumulative_quantity)
        
        message = str(error)
        self.assertIn("Test EdgeStorage", message)
        self.assertIn("negative cumulative storage need detected", message)
        self.assertIn("-10 GB", message)  # Should show minimum value
        self.assertIn("base_storage_need", message)


if __name__ == "__main__":
    unittest.main()