import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.attribution import atoms_of
from efootprint.core.country import Country
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.network import Network
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from tests.core.attribution.conservation import (
    assert_hourly_quantities_equal, assert_source_atoms_conserve, sum_atom_values)
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeDevice(TestCase):
    def setUp(self):
        self.mock_component_1 = create_mod_obj_mock(EdgeComponent, "Component 1")
        self.mock_component_2 = create_mod_obj_mock(EdgeComponent, "Component 2")
        # Zero-footprint components skip the deployment booking of unused components, keeping these unit
        # tests focused on the structure + used-component paths.
        self.mock_component_1.carbon_footprint_fabrication_from_inputs = SourceValue(0 * u.kg)
        self.mock_component_2.carbon_footprint_fabrication_from_inputs = SourceValue(0 * u.kg)

        self.edge_device = EdgeDevice(
            name="Test Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[self.mock_component_1, self.mock_component_2],
            lifespan=SourceValue(5 * u.year)
        )
        self.edge_device.trigger_modeling_updates = False
        self.edge_device.total_nb_of_units = ExplainableQuantity(1 * u.dimensionless, "one device")

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
        self.assertIn("Hourly", result.label)
        self.assertIn("instances fabrication footprint", result.label)
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

    def test_update_dict_element_in_instances_fabrication_footprint_per_usage_pattern_unused_component(self):
        """Test that a component with no needs at the pattern is booked as part of the chassis: its embodied
        carbon amortizes with the deployment, from input attributes."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern", edge_usage_journey=mock_journey)
        mock_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 10], pint_unit=u.concurrent)
        }

        self.mock_component_1.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.mock_component_1.carbon_footprint_fabrication_from_inputs = SourceValue(50 * u.kg)
        self.mock_component_1.lifespan = SourceValue(5 * u.year)
        self.mock_component_2.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()

        self.edge_device.update_dict_element_in_structure_fabrication_footprint_per_usage_pattern(mock_pattern)
        self.edge_device.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(mock_pattern)

        # Structure: 10 * (100 / 5) / (365.25 * 24); unused component 1: 10 * (50 / 5) / (365.25 * 24)
        hourly = 10 / (365.25 * 24)
        expected_footprint = [hourly * (100 / 5 + 50 / 5)] * 2

        result = self.edge_device.instances_fabrication_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude, rtol=1e-5))

    def test_unused_component_fabrication_raises_on_uncomputed_lifespan(self):
        """Test that booking an unused component whose lifespan was never computed fails loudly."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        self.mock_component_1.carbon_footprint_fabrication_from_inputs = SourceValue(50 * u.kg)
        self.mock_component_1.lifespan = EmptyExplainableObject()

        with self.assertRaises(ValueError) as context:
            self.edge_device.unused_component_fabrication_per_edge_device(self.mock_component_1, mock_pattern)
        self.assertIn("lifespan", str(context.exception))

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

    def test_update_dict_element_in_fabrication_footprint_breakdown_by_source(self):
        """Test per-component fabrication breakdown scales by total_nb_of_units and splits structure equally."""
        self.edge_device.total_nb_of_units = ExplainableQuantity(2 * u.dimensionless, "two devices")
        pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        self.edge_device.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            pattern: SourceValue(10 * u.kg)})
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)

        self.edge_device.fabrication_footprint_breakdown_by_source = ExplainableObjectDict()
        self.edge_device.update_dict_element_in_fabrication_footprint_breakdown_by_source(self.mock_component_1)

        breakdown = self.edge_device.fabrication_footprint_breakdown_by_source
        # Expected: total_nb_of_units * per_device + structure_total / nb_components = 2*4 + 10/2 = 13
        self.assertEqual(13, breakdown[self.mock_component_1].value.to(u.kg).magnitude)
        self.assertIn("Fabrication footprint attributed to", breakdown[self.mock_component_1].label)
        self.assertIn("Component 1", breakdown[self.mock_component_1].label)

    def test_update_fabrication_footprint_breakdown_by_source(self):
        """Test fabrication breakdown updates every component contribution and scales by total_nb_of_units."""
        self.edge_device.total_nb_of_units = ExplainableQuantity(3 * u.dimensionless, "three devices")
        pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        self.edge_device.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            pattern: SourceValue(12 * u.kg)})
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)
        self.mock_component_2.fabrication_footprint_per_edge_device = SourceValue(10 * u.kg)

        self.edge_device.update_fabrication_footprint_breakdown_by_source()

        breakdown = self.edge_device.fabrication_footprint_breakdown_by_source
        self.assertEqual({self.mock_component_1, self.mock_component_2}, set(breakdown))
        # c_1: 3*4 + 12/2 = 18; c_2: 3*10 + 12/2 = 36
        self.assertEqual(18, breakdown[self.mock_component_1].value.to(u.kg).magnitude)
        self.assertEqual(36, breakdown[self.mock_component_2].value.to(u.kg).magnitude)

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
        self.assertIn("Energy footprint", result.label)
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
        self.assertIn("Total energy consumed", result.label)

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
        self.assertIn("Total energy footprint", result.label)

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
        self.assertIn("Total fabrication footprint", result.label)

    def test_footprint_breakdown_by_source_distributes_computed_structure_across_components_and_keeps_energy(self):
        """Test footprint_breakdown_by_source scales by total_nb_of_units for both fabrication and energy."""
        self.edge_device.total_nb_of_units = ExplainableQuantity(2 * u.dimensionless, "two devices")
        pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        self.edge_device.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            pattern: SourceValue(100 * u.kg)})
        self.mock_component_1.fabrication_footprint_per_edge_device = SourceValue(4 * u.kg)
        self.mock_component_2.fabrication_footprint_per_edge_device = SourceValue(6 * u.kg)
        self.mock_component_1.energy_footprint_per_edge_device = SourceValue(1 * u.kg)
        self.mock_component_2.energy_footprint_per_edge_device = SourceValue(5 * u.kg)
        self.edge_device.update_fabrication_footprint_breakdown_by_source()

        breakdown = self.edge_device.footprint_breakdown_by_source

        # c_1: 2*4 + 100/2 = 58; c_2: 2*6 + 100/2 = 62; total = 120 = 2*(100/2 + 10) scaled.
        self.assertEqual(58, breakdown[LifeCyclePhases.MANUFACTURING][self.mock_component_1].magnitude)
        self.assertEqual(62, breakdown[LifeCyclePhases.MANUFACTURING][self.mock_component_2].magnitude)
        self.assertEqual(
            120,
            sum(breakdown[LifeCyclePhases.MANUFACTURING].values(), start=EmptyExplainableObject()).magnitude,
        )
        self.assertNotIn(self.edge_device, breakdown[LifeCyclePhases.MANUFACTURING])
        # Energy: 2 * component.energy_footprint_per_edge_device
        self.assertEqual(2, breakdown[LifeCyclePhases.USAGE][self.mock_component_1].magnitude)
        self.assertEqual(10, breakdown[LifeCyclePhases.USAGE][self.mock_component_2].magnitude)

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



def _make_edge_device_group(name):
    """Module-level helper: create an EdgeDeviceGroup with trigger disabled."""
    from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
    g = EdgeDeviceGroup(name)
    g.trigger_modeling_updates = False
    return g


class TestEdgeDeviceFindGroupMethods(TestCase):

    def setUp(self):
        self.device = EdgeDevice(
            name="Test Device",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(5 * u.year),
        )
        self.device.trigger_modeling_updates = False

    def test_find_parent_groups_returns_empty_when_no_groups(self):
        self.assertEqual([], self.device._find_parent_groups())

    def test_find_parent_groups_returns_group_when_device_is_in_it(self):
        group = _make_edge_device_group("Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_parent_groups()
        self.assertEqual([group], result)

    def test_find_parent_groups_returns_multiple_groups(self):
        group_a = _make_edge_device_group("Group A")
        group_b = _make_edge_device_group("Group B")
        group_a.edge_device_counts[self.device] = SourceValue(2 * u.dimensionless)
        group_b.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        result = self.device._find_parent_groups()
        self.assertIn(group_a, result)
        self.assertIn(group_b, result)
        self.assertEqual(2, len(result))

    def test_find_root_groups_returns_empty_when_no_groups(self):
        self.assertEqual([], self.device._find_root_groups())

    def test_find_root_groups_returns_root_for_flat_hierarchy(self):
        group = _make_edge_device_group("Root Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_root_groups()
        self.assertEqual([group], result)

    def test_find_root_groups_traverses_nested_hierarchy(self):
        root = _make_edge_device_group("Root")
        sub = _make_edge_device_group("Sub")
        root.sub_group_counts[sub] = SourceValue(2 * u.dimensionless)
        sub.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        result = self.device._find_root_groups()
        self.assertEqual([root], result)

    def test_find_root_groups_deduplicates_root_in_diamond_hierarchy(self):
        root = _make_edge_device_group("Root")
        left = _make_edge_device_group("Left")
        right = _make_edge_device_group("Right")
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

    def test_no_groups_gives_total_of_one(self):
        self.device.update_total_nb_of_units()
        self.assertAlmostEqual(1.0, self.device.total_nb_of_units.value.magnitude)

    def test_no_groups_label_mentions_no_group(self):
        self.device.update_total_nb_of_units()
        label = self.device.total_nb_of_units.label
        self.assertIn("no group", label.lower())

    def test_with_one_group_of_four(self):
        group = _make_edge_device_group("Group")
        group.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        group.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units()
        self.assertAlmostEqual(4.0, self.device.total_nb_of_units.value.magnitude)

    def test_with_nested_groups_multiplies_counts(self):
        root = _make_edge_device_group("Root")
        sub = _make_edge_device_group("Sub")
        root.sub_group_counts[sub] = SourceValue(3 * u.dimensionless)
        sub.edge_device_counts[self.device] = SourceValue(4 * u.dimensionless)
        root.update_effective_nb_of_units_within_root()
        sub.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units()
        self.assertAlmostEqual(12.0, self.device.total_nb_of_units.value.magnitude)

    def test_with_two_independent_root_groups_sums_contributions(self):
        group_a = _make_edge_device_group("Group A")
        group_b = _make_edge_device_group("Group B")
        group_a.edge_device_counts[self.device] = SourceValue(2 * u.dimensionless)
        group_b.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        group_a.update_effective_nb_of_units_within_root()
        group_b.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units()
        self.assertAlmostEqual(5.0, self.device.total_nb_of_units.value.magnitude)

    def test_total_nb_is_dimensionless(self):
        group = _make_edge_device_group("Group")
        group.edge_device_counts[self.device] = SourceValue(3 * u.dimensionless)
        group.update_effective_nb_of_units_within_root()
        self.device.update_total_nb_of_units()
        self.assertTrue(self.device.total_nb_of_units.value.check("[]"))


class TestEdgeDeviceSelfDelete(TestCase):

    def test_self_delete_raises_when_device_is_referenced_by_group(self):
        """Test self_delete raises when an edge device group references the device."""
        device = EdgeDevice(
            name="Device blocked by group deletion",
            structure_carbon_footprint_fabrication=SourceValue(100 * u.kg),
            components=[],
            lifespan=SourceValue(5 * u.year),
        )
        group = EdgeDeviceGroup("Group blocking device deletion")
        group.edge_device_counts[device] = SourceValue(3 * u.dimensionless)

        with self.assertRaises(PermissionError) as context:
            device.self_delete()

        self.assertIn("Group blocking device deletion", str(context.exception))


class TestEdgeDeviceAttributionAtoms(TestCase):
    """EdgeDevice atom builder on a real multi-pattern, multi-country model exercising the three
    attribution-revamp fixes (equal-share zero-demand fallback, held-volume storage weight, equal-share idle
    floor) plus within-journey reuse and chassis consistency with the breakdown-by-source axis."""

    @classmethod
    def setUpClass(cls):
        cls.cpu = EdgeCPUComponent(
            "edge atoms cpu", carbon_footprint_fabrication_per_unit=SourceValue(20 * u.kg),
            power_per_unit=SourceValue(15 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(3 * u.W), compute_per_unit=SourceValue(4 * u.cpu_core),
            base_compute_consumption=SourceValue(0.4 * u.cpu_core))
        cls.ram = EdgeRAMComponent(
            "edge atoms ram", carbon_footprint_fabrication_per_unit=SourceValue(40 * u.kg),
            power_per_unit=SourceValue(8 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(2 * u.W), ram_per_unit=SourceValue(8 * u.GB_ram),
            base_ram_consumption=SourceValue(1 * u.GB_ram))
        cls.workload_component = EdgeWorkloadComponent(
            "edge atoms workload component", carbon_footprint_fabrication_per_unit=SourceValue(100 * u.kg),
            power_per_unit=SourceValue(50 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(5 * u.W))
        cls.storage = EdgeStorage(
            "edge atoms storage", storage_capacity_per_unit=SourceValue(1 * u.TB_stored),
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored),
            base_storage_need=SourceValue(30 * u.GB_stored), lifespan=SourceValue(6 * u.year))
        cls.device = EdgeDevice(
            "edge atoms device", structure_carbon_footprint_fabrication=SourceValue(60 * u.kg),
            components=[cls.cpu, cls.ram, cls.workload_component, cls.storage], lifespan=SourceValue(6 * u.year))

        cls.cpu_active_need = RecurrentEdgeComponentNeed(
            "edge atoms active cpu need", edge_component=cls.cpu,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1, 0] * 84, dtype=np.float32), u.cpu_core)))
        cls.cpu_idle_need = RecurrentEdgeComponentNeed(
            "edge atoms idle cpu need", edge_component=cls.cpu,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.cpu_core)))
        cls.ram_need = RecurrentEdgeComponentNeed(
            "edge atoms ram need", edge_component=cls.ram,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([2] * 168, dtype=np.float32), u.GB_ram)))
        cls.workload_need = RecurrentEdgeComponentNeed(
            "edge atoms workload need", edge_component=cls.workload_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0.3] * 168, dtype=np.float32), u.concurrent)))
        cls.storage_write_need = RecurrentEdgeStorageNeed(
            "edge atoms write storage need", edge_component=cls.storage,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB_stored)))
        cls.storage_cycle_need = RecurrentEdgeStorageNeed(
            "edge atoms cycle storage need", edge_component=cls.storage,
            recurrent_need=SourceRecurrentValues(
                Quantity(np.array([2] * 84 + [-2] * 84, dtype=np.float32), u.GB_stored)))

        cls.main_bundle = RecurrentEdgeDeviceNeed(
            "edge atoms main bundle", edge_device=cls.device,
            recurrent_edge_component_needs=[
                cls.cpu_active_need, cls.cpu_idle_need, cls.ram_need, cls.workload_need, cls.storage_write_need,
                cls.storage_cycle_need])
        cls.reuse_bundle = RecurrentEdgeDeviceNeed(
            "edge atoms reuse bundle", edge_device=cls.device,
            recurrent_edge_component_needs=[cls.cpu_active_need])
        cls.edge_function = EdgeFunction(
            "edge atoms function", recurrent_edge_device_needs=[cls.main_bundle, cls.reuse_bundle],
            recurrent_server_needs=[])
        cls.journey = EdgeUsageJourney(
            "edge atoms journey", edge_functions=[cls.edge_function], usage_span=SourceValue(168 * u.hour))

        network = Network("edge atoms network", SourceValue(0.05 * u.kWh / u.GB))
        start_date = datetime(2025, 1, 6)  # a Monday, so weekly patterns align with the series grid
        cls.low_ci_up = EdgeUsagePattern(
            "edge atoms low ci pattern", cls.journey, network,
            Country("edge atoms low ci country", "EAL", SourceValue(50 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([1, 0, 2], start_date))
        cls.high_ci_up = EdgeUsagePattern(
            "edge atoms high ci pattern", cls.journey, network,
            Country("edge atoms high ci country", "EAH", SourceValue(500 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([2, 1], start_date))
        cls.system = System("edge atoms system", [], edge_usage_patterns=[cls.low_ci_up, cls.high_ci_up])

    def test_edge_device_atoms_conserve_both_phases(self):
        """Test that Σ atoms recovers the eager phase totals on a multi-pattern, multi-country model."""
        assert_source_atoms_conserve(self, self.device)

    def test_edge_device_atoms_conserve_per_usage_pattern(self):
        """Test that Σ atoms over a pattern recovers dev(up) — the eager per-pattern dicts, both phases."""
        for usage_pattern in (self.low_ci_up, self.high_ci_up):
            usage_atoms = [a for a in atoms_of(self.device, LifeCyclePhases.USAGE) if a.up == usage_pattern]
            assert_hourly_quantities_equal(
                self, self.device.energy_footprint_per_usage_pattern[usage_pattern], sum_atom_values(usage_atoms))
            fabrication_atoms = [
                a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING) if a.up == usage_pattern]
            assert_hourly_quantities_equal(
                self, self.device.instances_fabrication_footprint_per_usage_pattern[usage_pattern],
                sum_atom_values(fabrication_atoms))

    def test_within_journey_reuse_splits_by_occurrence_ratios(self):
        """Test that a need reused in two bundles of one journey yields one atom per slot, each carrying half
        of its atom_value (the occurrence ratios sum to 1)."""
        for phase in LifeCyclePhases:
            reused_atoms = [
                a for a in atoms_of(self.device, phase)
                if a.recn == self.cpu_active_need and a.up == self.low_ci_up]
            self.assertEqual({self.main_bundle.id, self.reuse_bundle.id}, {a.redn.id for a in reused_atoms})
            atom_value = self.device.atom_value(self.cpu_active_need, self.low_ci_up, phase)
            half = ExplainableQuantity(0.5 * u.dimensionless, "half")
            for atom in reused_atoms:
                assert_hourly_quantities_equal(self, atom_value * half, atom.value)
            assert_hourly_quantities_equal(self, atom_value, sum_atom_values(reused_atoms))

    def test_equal_share_idle_floor_at_partial_demand_hours(self):
        """Test that the idle/base energy floor is split equally between the CPU's two needs at every hour —
        including the hours where only the active need has demand, which a single demand weight mis-splits."""
        up = self.low_ci_up
        nb_journeys = self.journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[up]
        floor = (nb_journeys * self.cpu.unitary_power_at_zero_recurrent_need
                 * ExplainableQuantity(1 * u.hour, "one hour") * up.country.average_carbon_intensity).to(u.kg)
        half = ExplainableQuantity(0.5 * u.dimensionless, "half")
        idle_atoms = [
            a for a in atoms_of(self.device, LifeCyclePhases.USAGE)
            if a.recn == self.cpu_idle_need and a.up == up]
        self.assertEqual(1, len(idle_atoms))
        assert_hourly_quantities_equal(self, floor * half, idle_atoms[0].value)
        # The active need carries the whole dynamic marginal on top of its half floor.
        cpu_energy = self.cpu.energy_footprint_per_edge_device_per_usage_pattern[up]
        active_atoms = [
            a for a in atoms_of(self.device, LifeCyclePhases.USAGE)
            if a.recn == self.cpu_active_need and a.up == up]
        assert_hourly_quantities_equal(self, floor * half + (cpu_energy - floor), sum_atom_values(active_atoms))

    def test_zero_demand_hours_fall_back_to_equal_fabrication_share(self):
        """Test that at hours where no need loads the CPU, its fabrication footprint is split equally between
        its needs instead of being dropped (the fallback-0 bug) or double-booked (the fallback-1 bug)."""
        up = self.low_ci_up
        demand = self.cpu_active_need.unitary_hourly_need_per_usage_pattern[up]
        zero_demand_mask = demand.magnitude == 0
        self.assertTrue(zero_demand_mask.any() and (~zero_demand_mask).any())
        idle_fab = sum_atom_values([
            a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING)
            if a.recn == self.cpu_idle_need and a.up == up]).to(u.kg)
        active_fab = sum_atom_values([
            a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING)
            if a.recn == self.cpu_active_need and a.up == up]).to(u.kg)
        np.testing.assert_allclose(
            idle_fab.magnitude[zero_demand_mask], active_fab.magnitude[zero_demand_mask], rtol=1e-5)
        self.assertGreater(idle_fab.magnitude[zero_demand_mask].max(), 0)
        np.testing.assert_allclose(idle_fab.magnitude[~zero_demand_mask], 0, atol=1e-9)

    def test_held_volume_weight_stays_correct_across_delete_hours(self):
        """Test that storage fabrication splits by each need's cumulative held volume, staying within [0, 1]
        across the delete hours where the net write rate goes negative."""
        up = self.low_ci_up
        cumulative_write = self.storage_write_need.cumulative_unitary_storage_need_per_usage_pattern[up]
        cumulative_cycle = self.storage_cycle_need.cumulative_unitary_storage_need_per_usage_pattern[up]
        expected_cycle_share = (cumulative_cycle / (cumulative_write + cumulative_cycle)).to(u.dimensionless)
        cycle_fab = sum_atom_values([
            a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING)
            if a.recn == self.storage_cycle_need and a.up == up]).to(u.kg)
        write_fab = sum_atom_values([
            a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING)
            if a.recn == self.storage_write_need and a.up == up]).to(u.kg)
        delete_hours_mask = self.storage_cycle_need.unitary_hourly_need_per_usage_pattern[up].magnitude < 0
        self.assertTrue(delete_hours_mask.any())
        self.assertGreaterEqual(cycle_fab.magnitude.min(), -1e-6)  # float32 noise around zero held volume
        actual_cycle_share = cycle_fab.magnitude / (cycle_fab.magnitude + write_fab.magnitude)
        np.testing.assert_allclose(
            expected_cycle_share.magnitude[delete_hours_mask], actual_cycle_share[delete_hours_mask], rtol=1e-4)

    def test_chassis_consistency_between_atom_fold_and_breakdown_axis(self):
        """Test that folding the fabrication atoms by component recovers fabrication_footprint_breakdown_by_source
        — the chassis rides with each component as the same equal 1/nb_components share on both axes."""
        for component in self.device.components:
            component_atoms = [
                a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING)
                if a.recn.edge_component == component]
            assert_hourly_quantities_equal(
                self, self.device.fabrication_footprint_breakdown_by_source[component],
                sum_atom_values(component_atoms))

    def test_edge_device_atoms_enumerate_slots_with_edge_coordinates(self):
        """Test the slot enumeration: edge coordinates set, no web coordinates, single stream."""
        for atom in atoms_of(self.device, LifeCyclePhases.USAGE):
            self.assertIsNotNone(atom.recn)
            self.assertIsNotNone(atom.redn)
            self.assertIsNotNone(atom.ef)
            self.assertIsNone(atom.job)
            self.assertIsNone(atom.step)
            self.assertIsNone(atom.rsn)
            self.assertEqual("single", atom.stream)


class TestEdgeDeviceUnusedComponentsChassisPool(TestCase):
    """Chassis-pool rule: components unused at a pattern are part of the chassis — their
    embodied carbon is deployment-booked in the eager totals and attributed in an equal split across the
    pattern's carriers (component needs and RecurrentServerNeeds)."""

    @classmethod
    def setUpClass(cls):
        start_date = datetime(2025, 1, 6)  # a Monday, so weekly patterns align with the series grid

        # Scenario 1 — a RAM component with no needs on a device whose CPU is loaded.
        cls.cpu = EdgeCPUComponent(
            "pool cpu", carbon_footprint_fabrication_per_unit=SourceValue(20 * u.kg),
            power_per_unit=SourceValue(15 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(3 * u.W), compute_per_unit=SourceValue(4 * u.cpu_core),
            base_compute_consumption=SourceValue(0.4 * u.cpu_core))
        cls.ram = EdgeRAMComponent(
            "pool unused ram", carbon_footprint_fabrication_per_unit=SourceValue(40 * u.kg),
            power_per_unit=SourceValue(8 * u.W), lifespan=SourceValue(5 * u.year),
            idle_power_per_unit=SourceValue(2 * u.W), ram_per_unit=SourceValue(8 * u.GB_ram),
            base_ram_consumption=SourceValue(1 * u.GB_ram))
        cls.device = EdgeDevice(
            "pool device", structure_carbon_footprint_fabrication=SourceValue(60 * u.kg),
            components=[cls.cpu, cls.ram], lifespan=SourceValue(6 * u.year))
        cls.cpu_need = RecurrentEdgeComponentNeed(
            "pool cpu need", edge_component=cls.cpu,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))
        bundle = RecurrentEdgeDeviceNeed(
            "pool bundle", edge_device=cls.device, recurrent_edge_component_needs=[cls.cpu_need])
        function = EdgeFunction("pool function", recurrent_edge_device_needs=[bundle], recurrent_server_needs=[])
        journey = EdgeUsageJourney("pool journey", edge_functions=[function], usage_span=SourceValue(168 * u.hour))
        network = Network("pool network", SourceValue(0.05 * u.kWh / u.GB))
        cls.up = EdgeUsagePattern(
            "pool pattern", journey, network,
            Country("pool country", "PC", SourceValue(50 * u.g / u.kWh), ExplainableTimezone(pytz.utc, "UTC tz 1")),
            create_source_hourly_values_from_list([1, 1], start_date))

        # Scenario 2 — a second device reached at a second pattern only through a RecurrentServerNeed.
        cls.rsn_cpu = EdgeCPUComponent(
            "rsn cpu", carbon_footprint_fabrication_per_unit=SourceValue(20 * u.kg),
            power_per_unit=SourceValue(15 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(3 * u.W), compute_per_unit=SourceValue(4 * u.cpu_core),
            base_compute_consumption=SourceValue(0.4 * u.cpu_core))
        cls.rsn_device = EdgeDevice(
            "rsn device", structure_carbon_footprint_fabrication=SourceValue(60 * u.kg),
            components=[cls.rsn_cpu], lifespan=SourceValue(6 * u.year))
        rsn_cpu_need = RecurrentEdgeComponentNeed(
            "rsn cpu need", edge_component=cls.rsn_cpu,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))
        rsn_bundle = RecurrentEdgeDeviceNeed(
            "rsn bundle", edge_device=cls.rsn_device, recurrent_edge_component_needs=[rsn_cpu_need])
        used_function = EdgeFunction(
            "rsn used function", recurrent_edge_device_needs=[rsn_bundle], recurrent_server_needs=[])
        used_journey = EdgeUsageJourney(
            "rsn used journey", edge_functions=[used_function], usage_span=SourceValue(168 * u.hour))
        cls.used_up = EdgeUsagePattern(
            "rsn used pattern", used_journey, network,
            Country("rsn country 1", "RC1", SourceValue(50 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC tz 2")),
            create_source_hourly_values_from_list([1, 1], start_date))
        cls.rsn = RecurrentServerNeed(
            "rsn", edge_device=cls.rsn_device,
            recurrent_volume_per_edge_device=SourceRecurrentValues(
                Quantity(np.array([1.0] * 168, dtype=np.float32), u.occurrence)),
            jobs=[])
        cls.rsn_function = EdgeFunction(
            "rsn only function", recurrent_edge_device_needs=[], recurrent_server_needs=[cls.rsn])
        rsn_journey = EdgeUsageJourney(
            "rsn only journey", edge_functions=[cls.rsn_function], usage_span=SourceValue(168 * u.hour))
        cls.rsn_only_up = EdgeUsagePattern(
            "rsn only pattern", rsn_journey, network,
            Country("rsn country 2", "RC2", SourceValue(500 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC tz 3")),
            create_source_hourly_values_from_list([3, 3], start_date))

        cls.system = System("pool system", [], edge_usage_patterns=[cls.up, cls.used_up, cls.rsn_only_up])

    def test_unused_component_is_booked_in_eager_totals(self):
        """Test that the unused RAM's embodied carbon amortizes with the deployment in the eager per-pattern
        fabrication total, like the chassis."""
        unused_booking = self.device.unused_component_fabrication_per_edge_device(self.ram, self.up)
        self.assertGreater(unused_booking.magnitude.sum(), 0)
        expected = (self.device.structure_fabrication_footprint_per_usage_pattern[self.up]
                    + self.device.total_nb_of_units
                    * (self.cpu.fabrication_footprint_per_edge_device_per_usage_pattern[self.up] + unused_booking))
        assert_hourly_quantities_equal(
            self, expected.to(u.kg), self.device.instances_fabrication_footprint_per_usage_pattern[self.up])

    def test_unused_component_pool_is_carried_by_the_pattern_needs(self):
        """Test that the unused RAM's fabrication and chassis share land on the CPU need (the pattern's only
        carrier) and that the atoms conserve the eager totals."""
        assert_source_atoms_conserve(self, self.device)
        fabrication_atoms = list(atoms_of(self.device, LifeCyclePhases.MANUFACTURING))
        self.assertEqual({self.cpu_need.id}, {a.recn.id for a in fabrication_atoms})
        pool_share = self.device.fabrication_pool_share_per_carrier_and_pattern[self.up]
        half = ExplainableQuantity(0.5 * u.dimensionless, "half")
        expected_pool = (
            self.device.total_nb_of_units
            * self.device.unused_component_fabrication_per_edge_device(self.ram, self.up)
            + self.device.structure_fabrication_footprint_per_usage_pattern[self.up] * half)
        assert_hourly_quantities_equal(self, expected_pool.to(u.kg), pool_share)

    def test_unused_component_breakdown_entry_includes_deployment_booking(self):
        """Test that the breakdown-by-source axis shows the unused RAM carrying its deployment-booked
        fabrication plus its equal chassis share, and still sums to the device total."""
        unused_booking = self.device.unused_component_fabrication_per_edge_device(self.ram, self.up)
        half = ExplainableQuantity(0.5 * u.dimensionless, "half")
        expected_ram = (self.device.total_nb_of_units * unused_booking
                        + self.device.structure_fabrication_footprint_per_usage_pattern[self.up] * half)
        assert_hourly_quantities_equal(
            self, expected_ram.to(u.kg), self.device.fabrication_footprint_breakdown_by_source[self.ram])
        breakdown_total = sum(
            self.device.fabrication_footprint_breakdown_by_source.values(), start=EmptyExplainableObject())
        assert_hourly_quantities_equal(self, self.device.instances_fabrication_footprint, breakdown_total)

    def test_rsn_only_pattern_chassis_flows_through_the_server_need(self):
        """Test that at a pattern reaching the device only through a RecurrentServerNeed, the whole device
        fabrication (chassis + unused CPU) is carried by (rsn, ef) atoms and conserves the eager total."""
        assert_source_atoms_conserve(self, self.rsn_device)
        rsn_atoms = [a for a in atoms_of(self.rsn_device, LifeCyclePhases.MANUFACTURING)
                     if a.up == self.rsn_only_up]
        self.assertEqual(1, len(rsn_atoms))
        self.assertEqual(self.rsn.id, rsn_atoms[0].rsn.id)
        self.assertEqual(self.rsn_function.id, rsn_atoms[0].ef.id)
        self.assertIsNone(rsn_atoms[0].recn)
        assert_hourly_quantities_equal(
            self, self.rsn_device.instances_fabrication_footprint_per_usage_pattern[self.rsn_only_up],
            rsn_atoms[0].value)
        self.assertEqual(
            [], [a for a in atoms_of(self.rsn_device, LifeCyclePhases.USAGE) if a.up == self.rsn_only_up])
        self.assertIsInstance(
            self.rsn_device.energy_footprint_per_usage_pattern[self.rsn_only_up], EmptyExplainableObject)

    def test_deployed_pattern_without_carriers_raises(self):
        """Test that a pattern where the device books fabrication through an empty RecurrentEdgeDeviceNeed
        (no component needs, no server needs to carry it) fails loudly at attribution time."""
        cpu = EdgeCPUComponent(
            "carrierless cpu", carbon_footprint_fabrication_per_unit=SourceValue(20 * u.kg),
            power_per_unit=SourceValue(15 * u.W), lifespan=SourceValue(6 * u.year),
            idle_power_per_unit=SourceValue(3 * u.W), compute_per_unit=SourceValue(4 * u.cpu_core),
            base_compute_consumption=SourceValue(0.4 * u.cpu_core))
        device = EdgeDevice(
            "carrierless device", structure_carbon_footprint_fabrication=SourceValue(60 * u.kg),
            components=[cpu], lifespan=SourceValue(6 * u.year))
        cpu_need = RecurrentEdgeComponentNeed(
            "carrierless cpu need", edge_component=cpu,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))
        used_bundle = RecurrentEdgeDeviceNeed(
            "carrierless used bundle", edge_device=device, recurrent_edge_component_needs=[cpu_need])
        used_function = EdgeFunction(
            "carrierless used function", recurrent_edge_device_needs=[used_bundle], recurrent_server_needs=[])
        used_journey = EdgeUsageJourney(
            "carrierless used journey", edge_functions=[used_function], usage_span=SourceValue(168 * u.hour))
        empty_bundle = RecurrentEdgeDeviceNeed(
            "carrierless bundle", edge_device=device, recurrent_edge_component_needs=[])
        function = EdgeFunction(
            "carrierless function", recurrent_edge_device_needs=[empty_bundle], recurrent_server_needs=[])
        journey = EdgeUsageJourney(
            "carrierless journey", edge_functions=[function], usage_span=SourceValue(168 * u.hour))
        network = Network("carrierless network", SourceValue(0.05 * u.kWh / u.GB))
        used_pattern = EdgeUsagePattern(
            "carrierless used pattern", used_journey, network,
            Country("carrierless country 1", "CC1", SourceValue(50 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC tz 4")),
            create_source_hourly_values_from_list([1, 1], datetime(2025, 1, 6)))
        carrierless_pattern = EdgeUsagePattern(
            "carrierless pattern", journey, network,
            Country("carrierless country 2", "CC2", SourceValue(50 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC tz 5")),
            create_source_hourly_values_from_list([1, 1], datetime(2025, 1, 6)))
        System("carrierless system", [], edge_usage_patterns=[used_pattern, carrierless_pattern])

        self.assertIn(
            carrierless_pattern, device.structure_fabrication_footprint_per_usage_pattern)
        with self.assertRaises(ValueError) as context:
            list(atoms_of(device, LifeCyclePhases.MANUFACTURING))
        self.assertIn("no component needs and no", str(context.exception))


if __name__ == "__main__":
    unittest.main()
