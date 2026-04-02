import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeDevice(TestCase):
    def setUp(self):
        self.mock_component_1 = create_mod_obj_mock(EdgeComponent, "Component 1")
        self.mock_component_2 = create_mod_obj_mock(EdgeComponent, "Component 2")

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
        self.assertIsInstance(self.edge_device.structure_fabrication_footprint_per_usage_pattern, ExplainableObjectDict)
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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")

        mock_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_need.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_device, [mock_need])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_device.edge_usage_patterns))

    def test_edge_usage_patterns_property_multiple_needs_with_deduplication(self):
        """Test edge_usage_patterns property deduplicates patterns across needs."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")
        mock_pattern_3 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 3")

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
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern", edge_usage_journey=mock_journey)
        mock_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.concurrent)
        }

        self.mock_component_1.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_structure_fabrication_footprint_per_usage_pattern(mock_pattern)
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
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern", edge_usage_journey=mock_journey)
        mock_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.concurrent)
        }

        component_1_footprint = create_source_hourly_values_from_list([5, 5], pint_unit=u.kg)
        component_2_footprint = create_source_hourly_values_from_list([8, 8], pint_unit=u.kg)

        self.mock_component_1.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_footprint
        })
        self.mock_component_2.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_2_footprint
        })

        self.edge_device.update_dict_element_in_structure_fabrication_footprint_per_usage_pattern(mock_pattern)
        self.edge_device.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(mock_pattern)

        # Structure footprint: 10 * (100 / 5) / (365.25 * 24) kg
        # Total: structure + 5 kg + 8 kg
        structure_footprint = 10 * (100 / 5) / (365.25 * 24)
        expected_footprint = [structure_footprint + 5 + 8, structure_footprint + 5 + 8]

        result = self.edge_device.instances_fabrication_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude, rtol=1e-5))

    def test_update_dict_element_in_instances_energy_per_usage_pattern_no_components(self):
        """Test energy calculation with no component contributions."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        self.mock_component_1.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_instances_energy_per_usage_pattern(mock_pattern)

        result = self.edge_device.instances_energy_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_update_dict_element_in_instances_energy_per_usage_pattern_with_components(self):
        """Test energy calculation with component contributions."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        component_1_energy = create_source_hourly_values_from_list([100, 200], pint_unit=u.Wh)
        component_2_energy = create_source_hourly_values_from_list([50, 100], pint_unit=u.Wh)

        self.mock_component_1.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_energy
        })
        self.mock_component_2.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_2_energy
        })

        self.edge_device.update_dict_element_in_instances_energy_per_usage_pattern(mock_pattern)

        # Total energy: [100, 200] + [50, 100] = [150, 300]
        expected_energy = [150, 300]

        result = self.edge_device.instances_energy_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_energy, result.value.to(u.Wh).magnitude))
        self.assertIn("Test Device", result.label)

    def test_update_dict_element_in_fabrication_footprint_breakdown_by_source(self):
        """Test per-component fabrication breakdown splits structure equally across components."""
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)
        self.mock_component_2.fabrication_footprint_per_edge_device = SourceValue(10 * u.kg)
        self.edge_device.instances_fabrication_footprint = SourceValue(20 * u.kg)

        self.edge_device.fabrication_footprint_breakdown_by_source = ExplainableObjectDict()
        self.edge_device.update_dict_element_in_fabrication_footprint_breakdown_by_source(self.mock_component_1)

        breakdown = self.edge_device.fabrication_footprint_breakdown_by_source
        self.assertEqual(7, breakdown[self.mock_component_1].value.to(u.kg).magnitude)
        self.assertIn("Test Device", breakdown[self.mock_component_1].label)
        self.assertIn("Component 1", breakdown[self.mock_component_1].label)

    def test_update_fabrication_footprint_breakdown_by_source(self):
        """Test fabrication breakdown updates every component contribution."""
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)
        self.mock_component_2.fabrication_footprint_per_edge_device = SourceValue(10 * u.kg)
        self.edge_device.instances_fabrication_footprint = SourceValue(20 * u.kg)

        self.edge_device.update_fabrication_footprint_breakdown_by_source()

        breakdown = self.edge_device.fabrication_footprint_breakdown_by_source
        self.assertEqual({self.mock_component_1, self.mock_component_2}, set(breakdown))
        self.assertEqual(7, breakdown[self.mock_component_1].value.to(u.kg).magnitude)
        self.assertEqual(13, breakdown[self.mock_component_2].value.to(u.kg).magnitude)

    def test_update_fabrication_footprint_breakdown_by_source_without_components(self):
        """Test fabrication breakdown stays empty when the edge device has no components."""
        edge_device = EdgeDevice(
            name="Empty Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(5 * u.year)
        )
        edge_device.trigger_modeling_updates = False
        edge_device.instances_fabrication_footprint = SourceValue(20 * u.kg)

        edge_device.update_fabrication_footprint_breakdown_by_source()

        self.assertEqual({}, edge_device.fabrication_footprint_breakdown_by_source)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern_no_components(self):
        """Test energy footprint calculation with no component contributions."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        self.mock_component_1.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_2.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_energy_footprint_per_usage_pattern(mock_pattern)

        result = self.edge_device.energy_footprint_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern_with_components(self):
        """Test energy footprint calculation with component contributions."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        component_1_footprint = create_source_hourly_values_from_list([1, 2], pint_unit=u.kg)
        component_2_footprint = create_source_hourly_values_from_list([0.5, 1], pint_unit=u.kg)

        self.mock_component_1.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            mock_pattern: component_1_footprint
        })
        self.mock_component_2.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_fabrication_impact_repartition_weights_distributes_component_impact_across_component_needs(
            self, mock_component_needs):
        """Test edge device distributes component fabrication impact across its own recurrent needs."""
        pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")
        self.mock_component_1.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([4, 4], pint_unit=u.kg),
            pattern_2: create_source_hourly_values_from_list([4, 4], pint_unit=u.kg),
        })
        self.mock_component_1.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([16, 16], pint_unit=u.cpu_core * u.concurrent),
            pattern_2: create_source_hourly_values_from_list([16, 16], pint_unit=u.cpu_core * u.concurrent),
        })
        self.edge_device.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([0, 0], pint_unit=u.kg),
            pattern_2: create_source_hourly_values_from_list([0, 0], pint_unit=u.kg),
        })

        component_need_1 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 1", edge_component=self.mock_component_1)
        component_need_2 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 2", edge_component=self.mock_component_1)
        component_need_1.edge_usage_patterns = [pattern_1, pattern_2]
        component_need_2.edge_usage_patterns = [pattern_1, pattern_2]
        component_need_1.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
            pattern_2: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        component_need_2.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([6, 6], pint_unit=u.cpu_core * u.concurrent),
            pattern_2: create_source_hourly_values_from_list([6, 6], pint_unit=u.cpu_core * u.concurrent),
        })
        mock_component_needs.return_value = [component_need_1, component_need_2]

        self.edge_device.update_fabrication_impact_repartition_weights()

        self.assertTrue(np.allclose([5, 5], self.edge_device.fabrication_impact_repartition_weights[component_need_1].magnitude))
        self.assertTrue(np.allclose([3, 3], self.edge_device.fabrication_impact_repartition_weights[component_need_2].magnitude))

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_fabrication_impact_repartition_weights_evenly_distributes_structure_across_components(
            self, mock_component_needs):
        """Test edge device fabrication repartition gives each component an equal structure share before need splits."""
        pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        self.mock_component_1.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([4, 4], pint_unit=u.kg),
        })
        self.mock_component_2.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([8, 8], pint_unit=u.kg),
        })
        self.mock_component_1.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        self.mock_component_2.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        self.edge_device.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([6, 6], pint_unit=u.kg),
        })

        component_need_1 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 1", edge_component=self.mock_component_1)
        component_need_2 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 2", edge_component=self.mock_component_1)
        component_need_3 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 3", edge_component=self.mock_component_2)
        component_need_1.edge_usage_patterns = [pattern]
        component_need_2.edge_usage_patterns = [pattern]
        component_need_3.edge_usage_patterns = [pattern]
        component_need_1.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([6, 6], pint_unit=u.cpu_core * u.concurrent),
        })
        component_need_2.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([4, 4], pint_unit=u.cpu_core * u.concurrent),
        })
        component_need_3.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        mock_component_needs.return_value = [component_need_1, component_need_2, component_need_3]

        self.edge_device.update_fabrication_impact_repartition_weights()

        self.assertTrue(
            np.allclose([4.2, 4.2], self.edge_device.fabrication_impact_repartition_weights[component_need_1].magnitude)
        )
        self.assertTrue(
            np.allclose([2.8, 2.8], self.edge_device.fabrication_impact_repartition_weights[component_need_2].magnitude)
        )
        self.assertTrue(
            np.allclose([11, 11], self.edge_device.fabrication_impact_repartition_weights[component_need_3].magnitude)
        )

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_usage_impact_repartition_weights_uses_usage_pattern_energy_impact(
            self, mock_component_needs):
        """Test edge device usage repartition reflects per-pattern energy impact and intra-component need shares."""
        pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")
        self.mock_component_1.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([2, 2], pint_unit=u.kg),
        })
        self.mock_component_2.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict({
            pattern_2: create_source_hourly_values_from_list([6, 6], pint_unit=u.kg),
        })
        self.mock_component_1.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        self.mock_component_2.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_2: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })

        component_need_1 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 1", edge_component=self.mock_component_1)
        component_need_2 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 2", edge_component=self.mock_component_1)
        component_need_3 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed, name="Component need 3", edge_component=self.mock_component_2)
        component_need_1.edge_usage_patterns = [pattern_1]
        component_need_2.edge_usage_patterns = [pattern_1]
        component_need_3.edge_usage_patterns = [pattern_2]
        component_need_1.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([6, 6], pint_unit=u.cpu_core * u.concurrent),
        })
        component_need_2.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_1: create_source_hourly_values_from_list([4, 4], pint_unit=u.cpu_core * u.concurrent),
        })
        component_need_3.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict({
            pattern_2: create_source_hourly_values_from_list([10, 10], pint_unit=u.cpu_core * u.concurrent),
        })
        mock_component_needs.return_value = [component_need_1, component_need_2, component_need_3]

        self.edge_device.update_usage_impact_repartition_weights()

        self.assertTrue(np.allclose([1.2, 1.2], self.edge_device.usage_impact_repartition_weights[component_need_1].magnitude))
        self.assertTrue(np.allclose([0.8, 0.8], self.edge_device.usage_impact_repartition_weights[component_need_2].magnitude))
        self.assertTrue(np.allclose([6, 6], self.edge_device.usage_impact_repartition_weights[component_need_3].magnitude))

    def test_footprint_breakdown_by_source_distributes_computed_structure_across_components_and_keeps_energy(self):
        """Test footprint_breakdown_by_source conserves computed device fabrication and keeps energy unchanged."""
        self.edge_device.instances_fabrication_footprint = SourceValue(110 * u.kg)
        self.edge_device.energy_footprint = SourceValue(6 * u.kg)
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)
        self.mock_component_2.fabrication_footprint_per_edge_device = SourceValue(6 * u.kg)
        self.mock_component_1.energy_footprint_per_edge_device = SourceValue(1 * u.kg)
        self.mock_component_2.energy_footprint_per_edge_device = SourceValue(5 * u.kg)
        self.edge_device.update_fabrication_footprint_breakdown_by_source()

        breakdown = self.edge_device.footprint_breakdown_by_source

        self.assertEqual(54, breakdown[LifeCyclePhases.MANUFACTURING][self.mock_component_1].magnitude)
        self.assertEqual(56, breakdown[LifeCyclePhases.MANUFACTURING][self.mock_component_2].magnitude)
        self.assertEqual(
            110,
            sum(breakdown[LifeCyclePhases.MANUFACTURING].values(), start=EmptyExplainableObject()).magnitude,
        )
        self.assertNotIn(self.edge_device, breakdown[LifeCyclePhases.MANUFACTURING])
        self.assertEqual(1, breakdown[LifeCyclePhases.USAGE][self.mock_component_1].magnitude)
        self.assertEqual(5, breakdown[LifeCyclePhases.USAGE][self.mock_component_2].magnitude)

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_component_needs_edge_device_validation_all_components_valid(
            self, mock_recurrent_edge_component_needs):
        """Test validation passes when all component needs belong to the same device."""
        mock_component_1 = MagicMock(spec=EdgeComponent)
        mock_component_1.name = "Component 1"
        mock_component_1.edge_device = self.edge_device

        mock_component_2 = MagicMock(spec=EdgeComponent)
        mock_component_2.name = "Component 2"
        mock_component_2.edge_device = self.edge_device

        mock_component_need_1 = MagicMock()
        mock_component_need_2 = MagicMock()
        mock_component_need_1.edge_component = mock_component_1
        mock_component_need_2.edge_component = mock_component_2
        mock_recurrent_edge_component_needs.return_value = [mock_component_need_1, mock_component_need_2]

        self.edge_device.update_component_needs_edge_device_validation()

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_component_needs_edge_device_validation_component_device_is_none(
            self, mock_recurrent_edge_component_needs):
        """Test validation passes when component's edge_device is None."""
        mock_component = MagicMock(spec=EdgeComponent)
        mock_component.name = "Component"
        mock_component.edge_device = None

        mock_component_need_1 = MagicMock()
        mock_component_need_2 = MagicMock()
        mock_component_need_1.edge_component = mock_component
        mock_component_need_2.edge_component = mock_component
        mock_recurrent_edge_component_needs.return_value = [mock_component_need_1, mock_component_need_2]

        self.edge_device.update_component_needs_edge_device_validation()

    @patch("efootprint.core.hardware.edge.edge_device.EdgeDevice.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_component_needs_edge_device_validation_mismatched_device(self, mock_recurrent_edge_component_needs):
        """Test validation raises error when component belongs to different device."""
        mock_component_need_1 = MagicMock()
        mock_component_need_2 = MagicMock()

        mock_other_device = MagicMock(spec=EdgeDevice)
        mock_other_device.name = "Other Device"
        mock_other_device.id = "other_device_id"
        mock_component = MagicMock(spec=EdgeComponent)
        mock_component.name = "Component 1"
        mock_component.edge_device = mock_other_device
        mock_component_need_1.edge_component = mock_component

        mock_component_2 = MagicMock(spec=EdgeComponent)
        mock_component_2.name = "Component 2"
        mock_component_2.edge_device = self.edge_device
        mock_component_need_2.edge_component = mock_component_2

        mock_recurrent_edge_component_needs.return_value = [mock_component_need_1, mock_component_need_2]

        with self.assertRaises(ValueError) as context:
            self.edge_device.update_component_needs_edge_device_validation()

    def test_changing_to_usage_span_superior_to_edge_device_lifespan_raises_error(self):
        edge_device = EdgeDevice(
            name="Test Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(2 * u.year)
        )
        edge_need = RecurrentEdgeDeviceNeed("Empty need", edge_device=edge_device, recurrent_edge_component_needs=[])
        edge_function = EdgeFunction("Mock Function", recurrent_edge_device_needs=[edge_need],
                                     recurrent_server_needs=[])

        usage_span = SourceValue(1 * u.year)
        euj = EdgeUsageJourney("test euj", edge_functions=[edge_function], usage_span=usage_span)
        edge_device.compute_calculated_attributes()

        with self.assertRaises(InsufficientCapacityError):
            euj.usage_span = SourceValue(3 * u.year)


class TestEdgeDeviceFindGroupMethods(TestCase):

    def setUp(self):
        self.device = EdgeDevice(
            name="Test Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(5 * u.year),
        )
        self.device.trigger_modeling_updates = False

    def _make_group(self, name):
        from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
        g = EdgeDeviceGroup(name)
        g.trigger_modeling_updates = False
        return g

    def test_find_parent_groups_returns_empty_when_no_groups(self):
        self.assertEqual([], self.device._find_parent_groups())

    def test_find_parent_groups_returns_group_when_device_is_in_it(self):
        from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
        group = self._make_group("Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_parent_groups()
        self.assertEqual([group], result)

    def test_find_parent_groups_returns_multiple_groups(self):
        group_a = self._make_group("Group A")
        group_b = self._make_group("Group B")
        group_a.edge_device_counts[self.device] = SourceValue(2 * u.dimensionless)
        group_b.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        result = self.device._find_parent_groups()
        self.assertIn(group_a, result)
        self.assertIn(group_b, result)
        self.assertEqual(2, len(result))

    def test_find_root_groups_returns_empty_when_no_groups(self):
        self.assertEqual([], self.device._find_root_groups())

    def test_find_root_groups_returns_root_for_flat_hierarchy(self):
        group = self._make_group("Root Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_root_groups()
        self.assertEqual([group], result)

    def test_find_root_groups_traverses_nested_hierarchy(self):
        from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
        root = self._make_group("Root")
        sub = self._make_group("Sub")
        root.sub_group_counts[sub] = SourceValue(2 * u.dimensionless)
        sub.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_root_groups()
        self.assertEqual([root], result)

    def test_find_root_groups_deduplicates_root_in_diamond_hierarchy(self):
        root = self._make_group("Root")
        left = self._make_group("Left")
        right = self._make_group("Right")
        root.sub_group_counts[left] = SourceValue(1 * u.dimensionless)
        root.sub_group_counts[right] = SourceValue(1 * u.dimensionless)
        left.edge_device_counts[self.device] = SourceValue(1 * u.dimensionless)
        right.edge_device_counts[self.device] = SourceValue(1 * u.dimensionless)
        result = self.device._find_root_groups()
        self.assertEqual([root], result)


class TestEdgeDeviceUpdateTotalNbOfUnits(TestCase):

    def setUp(self):
        self.device = EdgeDevice(
            name="Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(5 * u.year),
        )
        self.device.trigger_modeling_updates = False

    def _make_group(self, name):
        from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
        g = EdgeDeviceGroup(name)
        g.trigger_modeling_updates = False
        return g

    def test_no_groups_gives_total_of_one(self):
        self.device.update_total_nb_of_units_per_ensemble()
        self.assertAlmostEqual(1.0, self.device.total_nb_of_units_per_ensemble.value.magnitude)

    def test_no_groups_label_mentions_no_group(self):
        self.device.update_total_nb_of_units_per_ensemble()
        label = self.device.total_nb_of_units_per_ensemble.label
        self.assertIn("no group", label.lower())

    def test_with_one_group_of_four(self):
        group = self._make_group("Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        group.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units_per_ensemble()
        self.assertAlmostEqual(4.0, self.device.total_nb_of_units_per_ensemble.value.magnitude)

    def test_with_nested_groups_multiplies_counts(self):
        root = self._make_group("Root")
        sub = self._make_group("Sub")
        root.sub_group_counts[sub] = SourceValue(3 * u.dimensionless)
        sub.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        root.update_effective_nb_of_units_within_root()
        sub.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units_per_ensemble()
        self.assertAlmostEqual(12.0, self.device.total_nb_of_units_per_ensemble.value.magnitude)

    def test_with_two_independent_root_groups_sums_contributions(self):
        group_a = self._make_group("Group A")
        group_b = self._make_group("Group B")
        group_a.edge_device_counts[self.device] = SourceValue(2 * u.dimensionless)
        group_b.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        group_a.update_effective_nb_of_units_within_root()
        group_b.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units_per_ensemble()
        self.assertAlmostEqual(5.0, self.device.total_nb_of_units_per_ensemble.value.magnitude)

    def test_total_nb_is_dimensionless(self):
        group = self._make_group("Group")
        group.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        group.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units_per_ensemble()
        self.assertTrue(self.device.total_nb_of_units_per_ensemble.value.check("[]"))


if __name__ == "__main__":
    unittest.main()
