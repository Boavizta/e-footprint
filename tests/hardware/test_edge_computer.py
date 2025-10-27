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
        self.assertEqual(8 * u.GB_ram, self.edge_computer.ram.value)
        self.assertEqual(4 * u.cpu_core, self.edge_computer.compute.value)
        self.assertEqual(1 * u.GB_ram, self.edge_computer.base_ram_consumption.value)
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
        """Test that components are returned as dependent objects."""
        dependent_objects = self.edge_computer.modeling_objects_whose_attributes_depend_directly_on_me
        # EdgeComputer has 3 components: RAM, CPU, and Storage
        self.assertEqual(3, len(dependent_objects))
        self.assertIn(self.edge_computer.ram_component, dependent_objects)
        self.assertIn(self.edge_computer.cpu_component, dependent_objects)
        self.assertIn(self.mock_storage, dependent_objects)

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