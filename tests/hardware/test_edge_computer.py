import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestEdgeComputer(TestCase):
    def setUp(self):
        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.edge_computer = EdgeComputer(
            name="Test EdgeComputer",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            power_usage_effectiveness=SourceValue(1.0 * u.dimensionless),
            utilization_rate=SourceValue(0.8 * u.dimensionless),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=self.mock_storage
        )
        self.edge_computer.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeComputer initialization."""
        self.assertEqual("Test EdgeComputer", self.edge_computer.name)
        self.assertEqual(60 * u.kg, self.edge_computer.carbon_footprint_fabrication.value)
        self.assertEqual(30 * u.W, self.edge_computer.power.value)
        self.assertEqual(8 * u.year, self.edge_computer.lifespan.value)
        self.assertEqual(5 * u.W, self.edge_computer.idle_power.value)
        self.assertEqual(8 * u.GB, self.edge_computer.ram.value)
        self.assertEqual(4 * u.cpu_core, self.edge_computer.compute.value)
        self.assertEqual(1.0 * u.dimensionless, self.edge_computer.power_usage_effectiveness.value)
        self.assertEqual(0.8 * u.dimensionless, self.edge_computer.utilization_rate.value)
        self.assertEqual(1 * u.GB, self.edge_computer.base_ram_consumption.value)
        self.assertEqual(0.1 * u.cpu_core, self.edge_computer.base_compute_consumption.value)
        self.assertEqual(self.mock_storage, self.edge_computer.storage)

    def test_init_removes_raw_nb_of_instances(self):
        """Test that raw_nb_of_instances is removed during initialization."""
        self.assertFalse(hasattr(self.edge_computer, "raw_nb_of_instances"))

    def test_init_sets_empty_explainable_objects(self):
        """Test that initialization sets proper empty explainable objects."""
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        self.assertIsInstance(self.edge_computer.available_compute_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_computer.available_ram_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_computer.unitary_hourly_compute_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_computer.unitary_hourly_ram_need_per_usage_pattern, ExplainableObjectDict)

    def test_labels_are_set_correctly(self):
        """Test that all attributes have correct labels."""
        self.assertIn("Idle power of Test EdgeComputer", self.edge_computer.idle_power.label)
        self.assertIn("RAM of Test EdgeComputer", self.edge_computer.ram.label)
        self.assertIn("Compute of Test EdgeComputer", self.edge_computer.compute.label)
        self.assertIn("PUE of Test EdgeComputer", self.edge_computer.power_usage_effectiveness.label)
        self.assertIn("Test EdgeComputer utilization rate", self.edge_computer.utilization_rate.label)
        self.assertIn("Base RAM consumption of Test EdgeComputer", self.edge_computer.base_ram_consumption.label)
        self.assertIn("Base compute consumption of Test EdgeComputer", self.edge_computer.base_compute_consumption.label)

    def test_edge_processes_property_no_containers(self):
        """Test edge_processes property when no containers are set."""
        self.assertEqual([], self.edge_computer.edge_processes)

    def test_edge_processes_property_with_containers(self):
        """Test edge_processes property returns modeling_obj_containers."""
        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)

        set_modeling_obj_containers(self.edge_computer, [mock_process_1, mock_process_2])

        self.assertEqual({mock_process_1, mock_process_2}, set(self.edge_computer.edge_processes))
        set_modeling_obj_containers(self.edge_computer, [])

    def test_edge_usage_journeys_property_no_processes(self):
        """Test edge_usage_journeys property when no processes are set."""
        self.assertEqual([], self.edge_computer.edge_usage_journeys)

    def test_edge_usage_journeys_property_with_process(self):
        """Test edge_usage_journeys property aggregates from processes."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)

        mock_process = MagicMock(spec=RecurrentEdgeProcess)
        mock_process.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        set_modeling_obj_containers(self.edge_computer, [mock_process])

        self.assertEqual({mock_journey_1, mock_journey_2}, set(self.edge_computer.edge_usage_journeys))
        set_modeling_obj_containers(self.edge_computer, [])

    def test_edge_usage_journeys_property_with_multiple_processes(self):
        """Test edge_usage_journeys property deduplicates across processes."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_3 = MagicMock(spec=EdgeUsageJourney)

        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2.edge_usage_journeys = [mock_journey_2, mock_journey_3]

        set_modeling_obj_containers(self.edge_computer, [mock_process_1, mock_process_2])

        journeys = self.edge_computer.edge_usage_journeys
        self.assertEqual(3, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)
        self.assertIn(mock_journey_3, journeys)
        set_modeling_obj_containers(self.edge_computer, [])

    def test_edge_usage_patterns_property_no_processes(self):
        """Test edge_usage_patterns property when no processes are set."""
        self.assertEqual([], self.edge_computer.edge_usage_patterns)

    def test_edge_usage_patterns_property_with_process(self):
        """Test edge_usage_patterns property aggregates from processes."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)

        mock_process = MagicMock(spec=RecurrentEdgeProcess)
        mock_process.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_computer, [mock_process])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_computer.edge_usage_patterns))
        set_modeling_obj_containers(self.edge_computer, [])

    def test_edge_usage_patterns_property_with_multiple_processes(self):
        """Test edge_usage_patterns property deduplicates patterns across processes."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_3 = MagicMock(spec=EdgeUsagePattern)

        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_1.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2.edge_usage_patterns = [mock_pattern_2, mock_pattern_3]

        set_modeling_obj_containers(self.edge_computer, [mock_process_1, mock_process_2])

        patterns = self.edge_computer.edge_usage_patterns
        self.assertEqual(3, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)
        self.assertIn(mock_pattern_3, patterns)
        set_modeling_obj_containers(self.edge_computer, [])

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that storage is returned as dependent object."""
        dependent_objects = self.edge_computer.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_storage], dependent_objects)


    def test_update_available_ram_per_instance(self):
        """Test update_available_ram_per_instance calculation."""
        with patch.object(self.edge_computer, "ram", SourceValue(16 * u.GB_ram)), \
             patch.object(self.edge_computer, "utilization_rate", SourceValue(0.8 * u.dimensionless)), \
             patch.object(self.edge_computer, "base_ram_consumption", SourceValue(2 * u.GB)):
            
            self.edge_computer.update_available_ram_per_instance()
            
            expected_value = 16 * 0.8 - 2  # 10.8 GB
            self.assertAlmostEqual(
                expected_value, self.edge_computer.available_ram_per_instance.value.magnitude, places=5)
            self.assertEqual(u.GB_ram, self.edge_computer.available_ram_per_instance.value.units)
            self.assertEqual("Available RAM per Test EdgeComputer instance",
                             self.edge_computer.available_ram_per_instance.label)

    def test_update_available_ram_per_instance_insufficient_capacity(self):
        """Test update_available_ram_per_instance raises error when capacity is insufficient."""
        with patch.object(self.edge_computer, "ram", SourceValue(8 * u.GB_ram)), \
             patch.object(self.edge_computer, "utilization_rate", SourceValue(0.5 * u.dimensionless)), \
             patch.object(self.edge_computer, "base_ram_consumption", SourceValue(5 * u.GB)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_computer.update_available_ram_per_instance()
            
            self.assertEqual("RAM", context.exception.capacity_type)
            self.assertEqual(self.edge_computer, context.exception.overloaded_object)

    def test_update_available_compute_per_instance(self):
        """Test update_available_compute_per_instance calculation."""
        with patch.object(self.edge_computer, "compute", SourceValue(8 * u.cpu_core)), \
             patch.object(self.edge_computer, "utilization_rate", SourceValue(0.75 * u.dimensionless)), \
             patch.object(self.edge_computer, "base_compute_consumption", SourceValue(1 * u.cpu_core)):
            
            self.edge_computer.update_available_compute_per_instance()
            
            expected_value = 8 * 0.75 - 1  # 5.0 cpu_core
            self.assertAlmostEqual(
                expected_value, self.edge_computer.available_compute_per_instance.value.magnitude, places=5)
            self.assertEqual(u.cpu_core, self.edge_computer.available_compute_per_instance.value.units)
            self.assertEqual("Available compute per Test EdgeComputer instance",
                             self.edge_computer.available_compute_per_instance.label)

    def test_update_available_compute_per_instance_insufficient_capacity(self):
        """Test update_available_compute_per_instance raises error when capacity is insufficient."""
        with patch.object(self.edge_computer, "compute", SourceValue(4 * u.cpu_core)), \
             patch.object(self.edge_computer, "utilization_rate", SourceValue(0.5 * u.dimensionless)), \
             patch.object(self.edge_computer, "base_compute_consumption", SourceValue(3 * u.cpu_core)):
            
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_computer.update_available_compute_per_instance()
            
            self.assertEqual("compute", context.exception.capacity_type)
            self.assertEqual(self.edge_computer, context.exception.overloaded_object)

    def test_update_unitary_hourly_ram_need_per_usage_pattern(self):
        """Test update_unitary_hourly_ram_need_per_usage_pattern aggregates all patterns."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2.name = "Pattern 2"

        mock_process = MagicMock(spec=RecurrentEdgeProcess)
        mock_process.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_computer, [mock_process])

        with patch.object(
                EdgeComputer, "update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern") as mock_update:
            self.edge_computer.update_unitary_hourly_ram_need_per_usage_pattern()

            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(mock_pattern_1)
            mock_update.assert_any_call(mock_pattern_2)

        set_modeling_obj_containers(self.edge_computer, [])

    def test_update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern calculation."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)

        ram_need_1 = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.GB_ram)
        ram_need_2 = create_source_hourly_values_from_list([2, 1, 4], pint_unit=u.GB_ram)

        mock_process_1.unitary_hourly_ram_need_per_usage_pattern = {mock_pattern: ram_need_1}
        mock_process_2.unitary_hourly_ram_need_per_usage_pattern = {mock_pattern: ram_need_2}
        mock_process_1.edge_usage_patterns = [mock_pattern]
        mock_process_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.edge_computer, [mock_process_1, mock_process_2])

        with patch.object(self.edge_computer, "available_ram_per_instance", SourceValue(10 * u.GB)):
            self.edge_computer.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(mock_pattern)

            expected_values = [3, 3, 7]  # Sum of both processes
            result = self.edge_computer.unitary_hourly_ram_need_per_usage_pattern[mock_pattern]
            self.assertEqual(expected_values, result.value_as_float_list)
            self.assertEqual(u.GB_ram, result.unit)
            self.assertIn("Test EdgeComputer hourly RAM need for Test Pattern", result.label)

        set_modeling_obj_containers(self.edge_computer, [])

    def test_update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern_insufficient_capacity(self):
        """Test update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern raises error when capacity is exceeded."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_process = MagicMock(spec=RecurrentEdgeProcess)
        ram_need = create_source_hourly_values_from_list([1, 2, 15], pint_unit=u.GB_ram)  # Peak of 15 GB
        mock_process.unitary_hourly_ram_need_per_usage_pattern = {mock_pattern: ram_need}
        mock_process.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.edge_computer, [mock_process])

        with patch.object(self.edge_computer, "available_ram_per_instance", SourceValue(10 * u.GB)):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_computer.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(mock_pattern)

            self.assertEqual("RAM", context.exception.capacity_type)
            self.assertEqual(self.edge_computer, context.exception.overloaded_object)

        set_modeling_obj_containers(self.edge_computer, [])

    def test_update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern calculation."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        mock_process_2 = MagicMock(spec=RecurrentEdgeProcess)

        compute_need_1 = create_source_hourly_values_from_list([0.5, 1.0, 1.5], pint_unit=u.cpu_core)
        compute_need_2 = create_source_hourly_values_from_list([1.0, 0.5, 2.0], pint_unit=u.cpu_core)

        mock_process_1.unitary_hourly_compute_need_per_usage_pattern = {mock_pattern: compute_need_1}
        mock_process_2.unitary_hourly_compute_need_per_usage_pattern = {mock_pattern: compute_need_2}
        mock_process_1.edge_usage_patterns = [mock_pattern]
        mock_process_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.edge_computer, [mock_process_1, mock_process_2])

        with patch.object(self.edge_computer, "available_compute_per_instance", SourceValue(5 * u.cpu_core)):
            self.edge_computer.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(mock_pattern)

            expected_values = [1.5, 1.5, 3.5]  # Sum of both processes
            result = self.edge_computer.unitary_hourly_compute_need_per_usage_pattern[mock_pattern]
            self.assertEqual(expected_values, result.value_as_float_list)
            self.assertEqual(u.cpu_core, result.unit)
            self.assertIn("Test EdgeComputer hourly compute need for Test Pattern", result.label)

        set_modeling_obj_containers(self.edge_computer, [])

    def test_update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern_insufficient_capacity(self):
        """Test update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern raises error when capacity is exceeded."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_process = MagicMock(spec=RecurrentEdgeProcess)
        compute_need = create_source_hourly_values_from_list([0.5, 1.0, 8.0], pint_unit=u.cpu_core)  # Peak of 8.0 cpu_core
        mock_process.unitary_hourly_compute_need_per_usage_pattern = {mock_pattern: compute_need}
        mock_process.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.edge_computer, [mock_process])

        with patch.object(self.edge_computer, "available_compute_per_instance", SourceValue(5 * u.cpu_core)):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.edge_computer.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(mock_pattern)

            self.assertEqual("compute", context.exception.capacity_type)
            self.assertEqual(self.edge_computer, context.exception.overloaded_object)

        set_modeling_obj_containers(self.edge_computer, [])

    def test_update_dict_element_in_unitary_power_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_power_per_usage_pattern calculation."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test pattern id"
        
        compute_need = create_source_hourly_values_from_list([0, 2, 4], pint_unit=u.cpu_core)
        self.edge_computer.unitary_hourly_compute_need_per_usage_pattern = {mock_pattern: compute_need}
        
        with patch.object(self.edge_computer, "base_compute_consumption", SourceValue(0 * u.cpu_core)), \
             patch.object(self.edge_computer, "compute", SourceValue(4 * u.cpu_core)), \
             patch.object(self.edge_computer, "idle_power", SourceValue(10 * u.W)), \
             patch.object(self.edge_computer, "power", SourceValue(50 * u.W)), \
             patch.object(self.edge_computer, "power_usage_effectiveness", SourceValue(1.2 * u.dimensionless)):
            
            self.edge_computer.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)
            
            # Workload ratios: [0/4, 2/4, 4/4] = [0, 0.5, 1]
            # Power: [10 + (50-10)*0, 10 + (50-10)*0.5, 10 + (50-10)*1] = [10, 30, 50]
            # With PUE: [10*1.2, 30*1.2, 50*1.2] = [12, 36, 60]
            expected_values = [12, 36, 60]
            result = self.edge_computer.unitary_power_per_usage_pattern[mock_pattern]
            self.assertTrue(np.allclose(expected_values, result.value_as_float_list))
            self.assertEqual(u.W, result.unit)
            self.assertIn("Test EdgeComputer unitary power for Test Pattern", result.label)


if __name__ == "__main__":
    unittest.main()