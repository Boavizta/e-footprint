import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeRAMComponent(TestCase):
    def setUp(self):
        self.ram_component = EdgeRAMComponent(
            name="Test RAM",
            carbon_footprint_fabrication_per_unit=SourceValue(10 * u.kg),
            power_per_unit=SourceValue(0 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power_per_unit=SourceValue(0 * u.W),
            ram_per_unit=SourceValue(16 * u.GB_ram),
            base_ram_consumption=SourceValue(2 * u.GB_ram)
        )
        self.ram_component.trigger_modeling_updates = False
        self.ram_component.update_carbon_footprint_fabrication()
        self.ram_component.update_power()
        self.ram_component.update_idle_power()
        self.ram_component.update_ram()

    def test_init(self):
        """Test EdgeRAMComponent initialization."""
        self.assertEqual("Test RAM", self.ram_component.name)
        self.assertEqual(10 * u.kg, self.ram_component.carbon_footprint_fabrication_per_unit.value)
        self.assertEqual(10 * u.kg, self.ram_component.carbon_footprint_fabrication.value)
        self.assertEqual(0 * u.W, self.ram_component.power_per_unit.value)
        self.assertEqual(0 * u.W, self.ram_component.power.value)
        self.assertEqual(5 * u.year, self.ram_component.lifespan.value)
        self.assertEqual(1 * u.dimensionless, self.ram_component.nb_of_units.value)
        self.assertEqual(16 * u.GB_ram, self.ram_component.ram_per_unit.value)
        self.assertEqual(16 * u.GB_ram, self.ram_component.ram.value)
        self.assertEqual(2 * u.GB_ram, self.ram_component.base_ram_consumption.value)

    def test_update_available_ram_per_instance(self):
        """Test update_available_ram_per_instance calculation."""
        self.ram_component.update_available_ram_per_instance()

        # available = ram - base_ram_consumption = 16 - 2 = 14 GB
        expected_value = 14
        self.assertAlmostEqual(
            expected_value, self.ram_component.available_ram_per_instance.value.magnitude, places=5)
        self.assertEqual(u.GB_ram, self.ram_component.available_ram_per_instance.value.units)
        self.assertIn("Available RAM per Test RAM instance",
                     self.ram_component.available_ram_per_instance.label)

    def test_update_available_ram_per_instance_with_nb_of_units(self):
        """Test update_available_ram_per_instance multiplies RAM by nb_of_units."""
        self.ram_component.nb_of_units = SourceValue(3 * u.dimensionless)
        self.ram_component.update_ram()

        self.ram_component.update_available_ram_per_instance()

        self.assertAlmostEqual(46, self.ram_component.available_ram_per_instance.value.magnitude, places=5)

    def test_update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern_with_nb_of_units(self):
        """Test RAM need stays expressed at component-pack level with multiple RAM units."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern distributed")

        mock_need = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need.unitary_hourly_need_per_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([3, 6, 12], pint_unit=u.GB_ram)
        }
        mock_need.edge_usage_patterns = [mock_pattern]
        set_modeling_obj_containers(self.ram_component, [mock_need])
        self.ram_component.nb_of_units = SourceValue(3 * u.dimensionless)
        self.ram_component.update_ram()

        self.ram_component.update_available_ram_per_instance()
        self.ram_component.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(mock_pattern)

        result = self.ram_component.unitary_hourly_ram_need_per_usage_pattern[mock_pattern]
        self.assertEqual([3, 6, 12], result.value_as_float_list)

    def test_update_available_ram_per_instance_insufficient_capacity(self):
        """Test update_available_ram_per_instance raises error when capacity is insufficient."""
        self.ram_component.base_ram_consumption = SourceValue(20 * u.GB_ram)

        with self.assertRaises(InsufficientCapacityError) as context:
            self.ram_component.update_available_ram_per_instance()

        self.assertEqual("RAM", context.exception.capacity_type)
        self.assertEqual(self.ram_component, context.exception.overloaded_object)

    def test_update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern calculation."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        mock_need_1 = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need_2 = MagicMock(spec=RecurrentEdgeComponentNeed)

        ram_need_1 = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.GB_ram)
        ram_need_2 = create_source_hourly_values_from_list([2, 1, 4], pint_unit=u.GB_ram)

        mock_need_1.unitary_hourly_need_per_usage_pattern = {mock_pattern: ram_need_1}
        mock_need_2.unitary_hourly_need_per_usage_pattern = {mock_pattern: ram_need_2}
        mock_need_1.edge_usage_patterns = [mock_pattern]
        mock_need_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.ram_component, [mock_need_1, mock_need_2])

        self.ram_component.update_available_ram_per_instance()
        self.ram_component.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(mock_pattern)

        expected_values = [3, 3, 7]  # Sum of both needs
        result = self.ram_component.unitary_hourly_ram_need_per_usage_pattern[mock_pattern]
        self.assertEqual(expected_values, result.value_as_float_list)
        self.assertEqual(u.GB_ram, result.unit)
        self.assertIn("Hourly RAM need for Test Pattern", result.label)

    def test_update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern_insufficient_capacity(self):
        """Test update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern raises error when capacity is exceeded."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        mock_need = MagicMock(spec=RecurrentEdgeComponentNeed)
        ram_need = create_source_hourly_values_from_list([1, 2, 20], pint_unit=u.GB_ram)  # Peak of 20 GB
        mock_need.unitary_hourly_need_per_usage_pattern = {mock_pattern: ram_need}
        mock_need.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.ram_component, [mock_need])

        self.ram_component.update_available_ram_per_instance()

        with self.assertRaises(InsufficientCapacityError) as context:
            self.ram_component.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(mock_pattern)

        self.assertEqual("RAM", context.exception.capacity_type)
        self.assertEqual(self.ram_component, context.exception.overloaded_object)


if __name__ == "__main__":
    unittest.main()
