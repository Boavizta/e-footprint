import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from tests.utils import set_modeling_obj_containers


class TestEdgeDevice(TestCase):
    def setUp(self):
        self.mock_component_1 = MagicMock(spec=EdgeComponent)
        self.mock_component_1.name = "Component 1"
        self.mock_component_1.id = "component_1"

        self.mock_component_2 = MagicMock(spec=EdgeComponent)
        self.mock_component_2.name = "Component 2"
        self.mock_component_2.id = "component_2"

        self.edge_device = EdgeDevice(
            name="Test Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[self.mock_component_1, self.mock_component_2],
            lifespan=SourceValue(5 * u.year)
        )
        self.edge_device.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeDevice initialization."""
        self.assertEqual("Test Device", self.edge_device.name)
        self.assertEqual(100, self.edge_device.structure_carbon_footprint_fabrication.value.to(u.kg).magnitude)
        self.assertEqual(5, self.edge_device.lifespan.value.to(u.year).magnitude)
        self.assertEqual([self.mock_component_1, self.mock_component_2], self.edge_device.components)

        self.assertIsInstance(self.edge_device.instances_energy_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_device.energy_footprint_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_device.instances_fabrication_footprint_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_device.instances_fabrication_footprint, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.instances_energy, EmptyExplainableObject)
        self.assertIsInstance(self.edge_device.energy_footprint, EmptyExplainableObject)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that no objects depend directly on EdgeDevice."""
        self.assertEqual([], self.edge_device.modeling_objects_whose_attributes_depend_directly_on_me)

    def test_recurrent_needs_property(self):
        """Test recurrent_needs property returns modeling_obj_containers."""
        mock_need_1 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_2 = MagicMock(spec=RecurrentEdgeDeviceNeed)

        set_modeling_obj_containers(self.edge_device, [mock_need_1, mock_need_2])

        self.assertEqual({mock_need_1, mock_need_2}, set(self.edge_device.recurrent_needs))

    def test_edge_usage_journeys_property_no_needs(self):
        """Test edge_usage_journeys property when no needs are set."""
        self.assertEqual([], self.edge_device.edge_usage_journeys)

    def test_edge_usage_journeys_property_single_need(self):
        """Test edge_usage_journeys property with single need."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)

        mock_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        set_modeling_obj_containers(self.edge_device, [mock_need])

        self.assertEqual({mock_journey_1, mock_journey_2}, set(self.edge_device.edge_usage_journeys))

    def test_edge_usage_journeys_property_multiple_needs_with_deduplication(self):
        """Test edge_usage_journeys property deduplicates journeys across needs."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_3 = MagicMock(spec=EdgeUsageJourney)

        mock_need_1 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        mock_need_2 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_2.edge_usage_journeys = [mock_journey_2, mock_journey_3]

        set_modeling_obj_containers(self.edge_device, [mock_need_1, mock_need_2])

        journeys = self.edge_device.edge_usage_journeys
        self.assertEqual(3, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)
        self.assertIn(mock_journey_3, journeys)

    def test_edge_functions_property_no_needs(self):
        """Test edge_functions property when no needs are set."""
        self.assertEqual([], self.edge_device.edge_functions)

    def test_edge_functions_property_single_need(self):
        """Test edge_functions property with single need."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_2 = MagicMock(spec=EdgeFunction)

        mock_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need.edge_functions = [mock_function_1, mock_function_2]

        set_modeling_obj_containers(self.edge_device, [mock_need])

        self.assertEqual({mock_function_1, mock_function_2}, set(self.edge_device.edge_functions))

    def test_edge_functions_property_multiple_needs_with_deduplication(self):
        """Test edge_functions property deduplicates functions across needs."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_3 = MagicMock(spec=EdgeFunction)

        mock_need_1 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_1.edge_functions = [mock_function_1, mock_function_2]

        mock_need_2 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_2.edge_functions = [mock_function_2, mock_function_3]

        set_modeling_obj_containers(self.edge_device, [mock_need_1, mock_need_2])

        functions = self.edge_device.edge_functions
        self.assertEqual(3, len(functions))
        self.assertIn(mock_function_1, functions)
        self.assertIn(mock_function_2, functions)
        self.assertIn(mock_function_3, functions)

    def test_edge_usage_patterns_property_no_needs(self):
        """Test edge_usage_patterns property when no needs are set."""
        self.assertEqual([], self.edge_device.edge_usage_patterns)

    def test_edge_usage_patterns_property_single_need(self):
        """Test edge_usage_patterns property with single need."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)

        mock_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_device, [mock_need])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_device.edge_usage_patterns))

    def test_edge_usage_patterns_property_multiple_needs_with_deduplication(self):
        """Test edge_usage_patterns property deduplicates patterns across needs."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_3 = MagicMock(spec=EdgeUsagePattern)

        mock_need_1 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_1.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_need_2 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need_2.edge_usage_patterns = [mock_pattern_2, mock_pattern_3]

        set_modeling_obj_containers(self.edge_device, [mock_need_1, mock_need_2])

        patterns = self.edge_device.edge_usage_patterns
        self.assertEqual(3, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)
        self.assertIn(mock_pattern_3, patterns)

    def test_update_dict_element_in_instances_fabrication_footprint_per_usage_pattern_structure_only(self):
        """Test fabrication footprint calculation with structure only (no component footprints)."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"
        mock_pattern.nb_edge_usage_journeys_in_parallel = create_source_hourly_values_from_list(
            [10, 10], pint_unit=u.concurrent)

        self.mock_component_1.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(mock_pattern)

        # Structure intensity: 100 kg / 5 year = 20 kg/year
        # Per hour: 20 kg/year / (365.25 * 24) kg/hour
        # For 10 instances: 10 * (100 / 5) / (365.25 * 24) kg
        expected_footprint = [10 * (100 / 5) / (365.25 * 24), 10 * (100 / 5) / (365.25 * 24)]

        result = self.edge_device.instances_fabrication_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude, rtol=1e-5))
        self.assertIn("Test Device", result.label)
        self.assertIn("Test Pattern", result.label)

    def test_update_dict_element_in_instances_fabrication_footprint_per_usage_pattern_with_components(self):
        """Test fabrication footprint calculation with component contributions."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"
        mock_pattern.nb_edge_usage_journeys_in_parallel = create_source_hourly_values_from_list(
            [10, 10], pint_unit=u.concurrent)

        component_1_footprint = create_source_hourly_values_from_list([5, 5], pint_unit=u.kg)
        component_2_footprint = create_source_hourly_values_from_list([8, 8], pint_unit=u.kg)

        self.mock_component_1.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_footprint
        })
        self.mock_component_2.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_2_footprint
        })

        self.edge_device.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(mock_pattern)

        # Structure footprint: 10 * (100 / 5) / (365.25 * 24) kg
        # Total: structure + 5 kg + 8 kg
        structure_footprint = 10 * (100 / 5) / (365.25 * 24)
        expected_footprint = [structure_footprint + 5 + 8, structure_footprint + 5 + 8]

        result = self.edge_device.instances_fabrication_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude, rtol=1e-5))

    def test_update_dict_element_in_instances_energy_per_usage_pattern_no_components(self):
        """Test energy calculation with no component contributions."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        self.mock_component_1.instances_energy_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.instances_energy_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_instances_energy_per_usage_pattern(mock_pattern)

        result = self.edge_device.instances_energy_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_update_dict_element_in_instances_energy_per_usage_pattern_with_components(self):
        """Test energy calculation with component contributions."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        component_1_energy = create_source_hourly_values_from_list([100, 200], pint_unit=u.Wh)
        component_2_energy = create_source_hourly_values_from_list([50, 100], pint_unit=u.Wh)

        self.mock_component_1.instances_energy_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_energy
        })
        self.mock_component_2.instances_energy_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_2_energy
        })

        self.edge_device.update_dict_element_in_instances_energy_per_usage_pattern(mock_pattern)

        # Total energy: [100, 200] + [50, 100] = [150, 300]
        expected_energy = [150, 300]

        result = self.edge_device.instances_energy_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_energy, result.value.to(u.Wh).magnitude))
        self.assertIn("Test Device", result.label)
        self.assertIn("Test Pattern", result.label)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern_no_components(self):
        """Test energy footprint calculation with no component contributions."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        self.mock_component_1.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.energy_footprint_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_energy_footprint_per_usage_pattern(mock_pattern)

        result = self.edge_device.energy_footprint_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern_with_components(self):
        """Test energy footprint calculation with component contributions."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        component_1_footprint = create_source_hourly_values_from_list([1, 2], pint_unit=u.kg)
        component_2_footprint = create_source_hourly_values_from_list([0.5, 1], pint_unit=u.kg)

        self.mock_component_1.energy_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_footprint
        })
        self.mock_component_2.energy_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_2_footprint
        })

        self.edge_device.update_dict_element_in_energy_footprint_per_usage_pattern(mock_pattern)

        # Total energy footprint: [1, 2] + [0.5, 1] = [1.5, 3]
        expected_footprint = [1.5, 3]

        result = self.edge_device.energy_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))
        self.assertIn("Test Device", result.label)
        self.assertIn("Test Pattern", result.label)

    def test_update_instances_energy(self):
        """Test summing energy across all usage patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        energy_1 = create_source_hourly_values_from_list([100, 200], pint_unit=u.Wh)
        energy_2 = create_source_hourly_values_from_list([50, 100], pint_unit=u.Wh)
        self.edge_device.instances_energy_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: energy_1,
            mock_pattern_2: energy_2
        })

        self.edge_device.update_instances_energy()

        # Sum: [100, 200] + [50, 100] = [150, 300]
        expected_energy = [150, 300]
        result = self.edge_device.instances_energy
        self.assertTrue(np.allclose(expected_energy, result.value.to(u.Wh).magnitude))
        self.assertIn("Test Device", result.label)

    def test_update_energy_footprint(self):
        """Test summing energy footprint across all usage patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        footprint_1 = create_source_hourly_values_from_list([1, 2], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([0.5, 1], pint_unit=u.kg)
        self.edge_device.energy_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.edge_device.update_energy_footprint()

        # Sum: [1, 2] + [0.5, 1] = [1.5, 3]
        expected_footprint = [1.5, 3]
        result = self.edge_device.energy_footprint
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))
        self.assertIn("Test Device", result.label)

    def test_update_instances_fabrication_footprint(self):
        """Test summing fabrication footprint across all usage patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        footprint_1 = create_source_hourly_values_from_list([10, 20], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([5, 10], pint_unit=u.kg)
        self.edge_device.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.edge_device.update_instances_fabrication_footprint()

        # Sum: [10, 20] + [5, 10] = [15, 30]
        expected_footprint = [15, 30]
        result = self.edge_device.instances_fabrication_footprint
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))
        self.assertIn("Test Device", result.label)


if __name__ == "__main__":
    unittest.main()
