import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge_process import EdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestEdgeDevice(TestCase):
    def setUp(self):
        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.edge_device = EdgeDevice(
            name="Test EdgeDevice",
            carbon_footprint_fabrication=SourceValue(60 * u.kg, Sources.HYPOTHESIS),
            power=SourceValue(30 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(4 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(5 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(8 * u.GB, Sources.HYPOTHESIS),
            compute=SourceValue(4 * u.cpu_core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.0 * u.dimensionless, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.8 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(1 * u.GB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core, Sources.HYPOTHESIS),
            storage=self.mock_storage
        )
        self.edge_device.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeDevice initialization."""
        self.assertEqual("Test EdgeDevice", self.edge_device.name)
        self.assertEqual(60 * u.kg, self.edge_device.carbon_footprint_fabrication.value)
        self.assertEqual(30 * u.W, self.edge_device.power.value)
        self.assertEqual(4 * u.year, self.edge_device.lifespan.value)
        self.assertEqual(5 * u.W, self.edge_device.idle_power.value)
        self.assertEqual(8 * u.GB, self.edge_device.ram.value)
        self.assertEqual(4 * u.cpu_core, self.edge_device.compute.value)
        self.assertEqual(1.0 * u.dimensionless, self.edge_device.power_usage_effectiveness.value)
        self.assertEqual(0.8 * u.dimensionless, self.edge_device.server_utilization_rate.value)
        self.assertEqual(1 * u.GB, self.edge_device.base_ram_consumption.value)
        self.assertEqual(0.1 * u.cpu_core, self.edge_device.base_compute_consumption.value)
        self.assertEqual(self.mock_storage, self.edge_device.storage)

    def test_init_removes_raw_nb_of_instances(self):
        """Test that raw_nb_of_instances is removed during initialization."""
        self.assertFalse(hasattr(self.edge_device, "raw_nb_of_instances"))

    def test_init_sets_empty_explainable_objects(self):
        """Test that initialization sets proper empty explainable objects."""
        self.assertIsInstance(self.edge_device.available_compute_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.available_ram_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.unitary_hourly_compute_need_over_full_timespan, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.unitary_hourly_ram_need_over_full_timespan, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.unitary_power_over_full_timespan, EmptyExplainableObject)

    def test_labels_are_set_correctly(self):
        """Test that all attributes have correct labels."""
        self.assertIn("Idle power of Test EdgeDevice", self.edge_device.idle_power.label)
        self.assertIn("RAM of Test EdgeDevice", self.edge_device.ram.label)
        self.assertIn("Compute of Test EdgeDevice", self.edge_device.compute.label)
        self.assertIn("PUE of Test EdgeDevice", self.edge_device.power_usage_effectiveness.label)
        self.assertIn("Test EdgeDevice utilization rate", self.edge_device.server_utilization_rate.label)
        self.assertIn("Base RAM consumption of Test EdgeDevice", self.edge_device.base_ram_consumption.label)
        self.assertIn("Base compute consumption of Test EdgeDevice", self.edge_device.base_compute_consumption.label)

    def test_edge_usage_journey_property_no_containers(self):
        """Test edge_usage_journey property when no containers are set."""
        self.assertIsNone(self.edge_device.edge_usage_journey)

    def test_edge_usage_journey_property_single_container(self):
        """Test edge_usage_journey property with single container."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.name = "Mock Journey"
        set_modeling_obj_containers(self.edge_device, [mock_journey])
        self.assertEqual(mock_journey, self.edge_device.edge_usage_journey)
        set_modeling_obj_containers(self.edge_device, [])

    def test_edge_usage_journey_property_multiple_containers_raises_error(self):
        """Test edge_usage_journey property raises error with multiple containers."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.name = "Journey 1"
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.name = "Journey 2"
        
        set_modeling_obj_containers(self.edge_device, [mock_journey_1, mock_journey_2])
        
        with self.assertRaises(PermissionError) as context:
            _ = self.edge_device.edge_usage_journey
        
        expected_message = ("EdgeDevice object can only be associated with one EdgeUsageJourney object but "
                          "Test EdgeDevice is associated with")
        self.assertIn(expected_message, str(context.exception))
        set_modeling_obj_containers(self.edge_device, [])

    def test_edge_usage_pattern_property_no_journey(self):
        """Test edge_usage_pattern property when no journey is set."""
        self.assertIsNone(self.edge_device.edge_usage_pattern)

    def test_edge_usage_pattern_property_with_journey(self):
        """Test edge_usage_pattern property delegates to journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_journey.edge_usage_pattern = mock_pattern
        
        set_modeling_obj_containers(self.edge_device, [mock_journey])
        
        self.assertEqual(mock_pattern, self.edge_device.edge_usage_pattern)
        set_modeling_obj_containers(self.edge_device, [])

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that storage is returned as dependent object."""
        dependent_objects = self.edge_device.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_storage], dependent_objects)

    def test_edge_processes_property(self):
        """Test edge_processes property delegates to journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_processes = [MagicMock(spec=EdgeProcess), MagicMock(spec=EdgeProcess)]
        mock_journey.edge_processes = mock_processes
        
        set_modeling_obj_containers(self.edge_device, [mock_journey])
        
        self.assertEqual(mock_processes, self.edge_device.edge_processes)
        set_modeling_obj_containers(self.edge_device, [])

    def test_update_available_ram_per_instance(self):
        """Test update_available_ram_per_instance calculation."""
        with patch.object(self.edge_device, "ram", SourceValue(16 * u.GB)), \
             patch.object(self.edge_device, "server_utilization_rate", SourceValue(0.8 * u.dimensionless)), \
             patch.object(self.edge_device, "base_ram_consumption", SourceValue(2 * u.GB)):
            
            self.edge_device.update_available_ram_per_instance()
            
            expected_value = 16 * 0.8 - 2  # 10.8 GB
            self.assertAlmostEqual(
                expected_value, self.edge_device.available_ram_per_instance.value.magnitude, places=5)
            self.assertEqual(u.GB, self.edge_device.available_ram_per_instance.value.units)
            self.assertEqual("Available RAM per Test EdgeDevice instance",
                             self.edge_device.available_ram_per_instance.label)

    def test_update_available_ram_per_instance_insufficient_capacity(self):
        """Test update_available_ram_per_instance raises error when capacity is insufficient."""
        with patch.object(self.edge_device, "ram", SourceValue(8 * u.GB)), \
             patch.object(self.edge_device, "server_utilization_rate", SourceValue(0.5 * u.dimensionless)), \
             patch.object(self.edge_device, "base_ram_consumption", SourceValue(5 * u.GB)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_device.update_available_ram_per_instance()
            
            self.assertEqual("RAM", context.exception.capacity_type)
            self.assertEqual(self.edge_device, context.exception.overloaded_object)

    def test_update_available_compute_per_instance(self):
        """Test update_available_compute_per_instance calculation."""
        with patch.object(self.edge_device, "compute", SourceValue(8 * u.cpu_core)), \
             patch.object(self.edge_device, "server_utilization_rate", SourceValue(0.75 * u.dimensionless)), \
             patch.object(self.edge_device, "base_compute_consumption", SourceValue(1 * u.cpu_core)):
            
            self.edge_device.update_available_compute_per_instance()
            
            expected_value = 8 * 0.75 - 1  # 5.0 cpu_core
            self.assertAlmostEqual(
                expected_value, self.edge_device.available_compute_per_instance.value.magnitude, places=5)
            self.assertEqual(u.cpu_core, self.edge_device.available_compute_per_instance.value.units)
            self.assertEqual("Available compute per Test EdgeDevice instance",
                             self.edge_device.available_compute_per_instance.label)

    def test_update_available_compute_per_instance_insufficient_capacity(self):
        """Test update_available_compute_per_instance raises error when capacity is insufficient."""
        with patch.object(self.edge_device, "compute", SourceValue(4 * u.cpu_core)), \
             patch.object(self.edge_device, "server_utilization_rate", SourceValue(0.5 * u.dimensionless)), \
             patch.object(self.edge_device, "base_compute_consumption", SourceValue(3 * u.cpu_core)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_device.update_available_compute_per_instance()
            
            self.assertEqual("compute", context.exception.capacity_type)
            self.assertEqual(self.edge_device, context.exception.overloaded_object)

    @patch("efootprint.core.hardware.edge_device.EdgeDevice.edge_processes", new_callable=PropertyMock)
    def test_update_unitary_hourly_ram_need_over_full_timespan(self, mock_edge_processes):
        """Test update_unitary_hourly_ram_need_over_full_timespan calculation."""
        mock_process_1 = MagicMock(spec=EdgeProcess)
        mock_process_2 = MagicMock(spec=EdgeProcess)
        
        ram_need_1 = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.GB)
        ram_need_2 = create_source_hourly_values_from_list([2, 1, 4], pint_unit=u.GB)
        
        mock_process_1.unitary_hourly_ram_need_over_full_timespan = ram_need_1
        mock_process_2.unitary_hourly_ram_need_over_full_timespan = ram_need_2

        mock_edge_processes.return_value = [mock_process_1, mock_process_2]
        
        with patch.object(self.edge_device, "available_ram_per_instance", SourceValue(10 * u.GB)):
            self.edge_device.update_unitary_hourly_ram_need_over_full_timespan()
            
            expected_values = [3, 3, 7]  # Sum of both processes
            self.assertEqual(expected_values,
                             self.edge_device.unitary_hourly_ram_need_over_full_timespan.value_as_float_list)
            self.assertEqual(u.GB, self.edge_device.unitary_hourly_ram_need_over_full_timespan.unit)
            self.assertEqual("Test EdgeDevice hour by hour RAM need",
                             self.edge_device.unitary_hourly_ram_need_over_full_timespan.label)

    @patch("efootprint.core.hardware.edge_device.EdgeDevice.edge_processes", new_callable=PropertyMock)
    def test_update_unitary_hourly_ram_need_over_full_timespan_insufficient_capacity(self, mock_edge_processes):
        """Test update_unitary_hourly_ram_need_over_full_timespan raises error when capacity is exceeded."""
        mock_process = MagicMock(spec=EdgeProcess)
        ram_need = create_source_hourly_values_from_list([1, 2, 15], pint_unit=u.GB)  # Peak of 15 GB
        mock_process.unitary_hourly_ram_need_over_full_timespan = ram_need

        mock_edge_processes.return_value = [mock_process]
        
        with patch.object(self.edge_device, "available_ram_per_instance", SourceValue(10 * u.GB)):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_device.update_unitary_hourly_ram_need_over_full_timespan()
            
            self.assertEqual("RAM", context.exception.capacity_type)
            self.assertEqual(self.edge_device, context.exception.overloaded_object)

    @patch("efootprint.core.hardware.edge_device.EdgeDevice.edge_processes", new_callable=PropertyMock)
    def test_update_unitary_hourly_compute_need_over_full_timespan(self, mock_edge_processes):
        """Test update_unitary_hourly_compute_need_over_full_timespan calculation."""
        mock_process_1 = MagicMock(spec=EdgeProcess)
        mock_process_2 = MagicMock(spec=EdgeProcess)
        
        compute_need_1 = create_source_hourly_values_from_list([0.5, 1.0, 1.5], pint_unit=u.cpu_core)
        compute_need_2 = create_source_hourly_values_from_list([1.0, 0.5, 2.0], pint_unit=u.cpu_core)
        
        mock_process_1.unitary_hourly_compute_need_over_full_timespan = compute_need_1
        mock_process_2.unitary_hourly_compute_need_over_full_timespan = compute_need_2

        mock_edge_processes.return_value = [mock_process_1, mock_process_2]
        
        with patch.object(self.edge_device, "available_compute_per_instance", SourceValue(5 * u.cpu_core)):
            self.edge_device.update_unitary_hourly_compute_need_over_full_timespan()
            
            expected_values = [1.5, 1.5, 3.5]  # Sum of both processes
            self.assertEqual(expected_values,
                             self.edge_device.unitary_hourly_compute_need_over_full_timespan.value_as_float_list)
            self.assertEqual(u.cpu_core, self.edge_device.unitary_hourly_compute_need_over_full_timespan.unit)
            self.assertEqual("Test EdgeDevice hour by hour compute need",
                             self.edge_device.unitary_hourly_compute_need_over_full_timespan.label)

    @patch("efootprint.core.hardware.edge_device.EdgeDevice.edge_processes", new_callable=PropertyMock)
    def test_update_unitary_hourly_compute_need_over_full_timespan_insufficient_capacity(self, mock_edge_processes):
        """Test update_unitary_hourly_compute_need_over_full_timespan raises error when capacity is exceeded."""
        mock_process = MagicMock(spec=EdgeProcess)
        compute_need = create_source_hourly_values_from_list([0.5, 1.0, 8.0], pint_unit=u.cpu_core)  # Peak of 8.0 cpu_core
        mock_process.unitary_hourly_compute_need_over_full_timespan = compute_need

        mock_edge_processes.return_value = [mock_process]
        
        with patch.object(self.edge_device, "available_compute_per_instance", SourceValue(5 * u.cpu_core)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_device.update_unitary_hourly_compute_need_over_full_timespan()
            
            self.assertEqual("compute", context.exception.capacity_type)
            self.assertEqual(self.edge_device, context.exception.overloaded_object)

    def test_update_unitary_power_over_full_timespan(self):
        """Test update_unitary_power_over_full_timespan calculation."""
        compute_need = create_source_hourly_values_from_list([0, 2, 4], pint_unit=u.cpu_core)
        
        with patch.object(self.edge_device, "unitary_hourly_compute_need_over_full_timespan", compute_need), \
             patch.object(self.edge_device, "base_compute_consumption", SourceValue(0 * u.cpu_core)), \
             patch.object(self.edge_device, "compute", SourceValue(4 * u.cpu_core)), \
             patch.object(self.edge_device, "idle_power", SourceValue(10 * u.W)), \
             patch.object(self.edge_device, "power", SourceValue(50 * u.W)), \
             patch.object(self.edge_device, "power_usage_effectiveness", SourceValue(1.2 * u.dimensionless)):
            
            self.edge_device.update_unitary_power_over_full_timespan()
            
            # Workload ratios: [0/4, 2/4, 4/4] = [0, 0.5, 1]
            # Power: [10 + (50-10)*0, 10 + (50-10)*0.5, 10 + (50-10)*1] = [10, 30, 50]
            # With PUE: [10*1.2, 30*1.2, 50*1.2] = [12, 36, 60]
            expected_values = [12, 36, 60]
            self.assertTrue(np.allclose(expected_values,
                                        self.edge_device.unitary_power_over_full_timespan.value_as_float_list))
            self.assertEqual(u.W, self.edge_device.unitary_power_over_full_timespan.unit)
            self.assertEqual("Test EdgeDevice unitary power over full timespan.",
                             self.edge_device.unitary_power_over_full_timespan.label)


if __name__ == "__main__":
    unittest.main()