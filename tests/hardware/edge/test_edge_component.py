import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class ConcreteEdgeComponent(EdgeComponent):
    """Concrete implementation of EdgeComponent for testing."""

    default_values = {
        "carbon_footprint_fabrication": SourceValue(20 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(10 * u.W),
    }

    def expected_need_units(self):
        return [u.cpu_core]

    def update_unitary_power_per_usage_pattern(self):
        pass


class TestEdgeComponent(TestCase):
    def setUp(self):
        self.component = ConcreteEdgeComponent(
            name="Test Component",
            carbon_footprint_fabrication=SourceValue(20 * u.kg),
            power=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power=SourceValue(10 * u.W)
        )
        self.component.trigger_modeling_updates = False

    def test_update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(self):
        """Test fabrication footprint calculation for a single pattern."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"
        mock_pattern.nb_edge_usage_journeys_in_parallel = SourceValue(10 * u.concurrent)

        self.component.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(mock_pattern)

        # Component intensity: 20 kg / 5 year = 4 kg/year
        # Per hour: 4 kg/year / (365.25 * 24) kg/hour
        # For 10 instances: 10 * (4 / 8766) kg
        expected_footprint = 10 * (20 / 5) / (365.25 * 24)

        result = self.component.instances_fabrication_footprint_per_usage_pattern[mock_pattern]
        self.assertAlmostEqual(expected_footprint, result.value.to(u.kg).magnitude, places=5)
        self.assertIn("Test Component", result.label)
        self.assertIn("Test Pattern", result.label)

    def test_update_dict_element_in_instances_energy_per_usage_pattern(self):
        """Test energy calculation for a single pattern."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"
        mock_pattern.nb_edge_usage_journeys_in_parallel = create_source_hourly_values_from_list([10, 20], pint_unit=u.concurrent)

        unitary_power = create_source_hourly_values_from_list([30, 40], pint_unit=u.W)
        self.component.unitary_power_per_usage_pattern = ExplainableObjectDict({mock_pattern: unitary_power})

        self.component.update_dict_element_in_instances_energy_per_usage_pattern(mock_pattern)

        # Energy = nb_instances * unitary_power * 1 hour = [10, 20] * [30, 40] W * 1 hour = [300, 800] Wh
        expected_energy = [300, 800]

        result = self.component.instances_energy_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_energy, result.value.to(u.Wh).magnitude))
        self.assertIn("Test Component", result.label)

    def test_update_dict_element_in_energy_footprint_per_usage_pattern(self):
        """Test energy footprint calculation for a single pattern."""
        mock_pattern = MagicMock()
        mock_pattern.name = "Test Pattern"
        mock_pattern.country.average_carbon_intensity = SourceValue(0.5 * u.kg / u.kWh)

        instances_energy = create_source_hourly_values_from_list([1000, 2000], pint_unit=u.Wh)
        self.component.instances_energy_per_usage_pattern = ExplainableObjectDict({mock_pattern: instances_energy})

        self.component.update_dict_element_in_energy_footprint_per_usage_pattern(mock_pattern)

        # Energy footprint = [1000, 2000] Wh * 0.5 kg/kWh = [0.5, 1.0] kg
        expected_footprint = [0.5, 1.0]

        result = self.component.energy_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))

    def test_update_instances_fabrication_footprint(self):
        """Test summing fabrication footprint across patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        footprint_1 = create_source_hourly_values_from_list([10, 20], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([5, 10], pint_unit=u.kg)
        self.component.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.component.update_instances_fabrication_footprint()

        # Sum: [10, 20] + [5, 10] = [15, 30]
        result = self.component.instances_fabrication_footprint
        self.assertTrue(np.allclose([15, 30], result.value.to(u.kg).magnitude))

    def test_update_instances_energy(self):
        """Test summing energy across patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        energy_1 = create_source_hourly_values_from_list([100, 200], pint_unit=u.Wh)
        energy_2 = create_source_hourly_values_from_list([50, 100], pint_unit=u.Wh)
        self.component.instances_energy_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: energy_1,
            mock_pattern_2: energy_2
        })

        self.component.update_instances_energy()

        # Sum: [100, 200] + [50, 100] = [150, 300]
        result = self.component.instances_energy
        self.assertTrue(np.allclose([150, 300], result.value.to(u.Wh).magnitude))

    def test_update_energy_footprint(self):
        """Test summing energy footprint across patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.id = "pattern_1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.id = "pattern_2"

        footprint_1 = create_source_hourly_values_from_list([1, 2], pint_unit=u.kg)
        footprint_2 = create_source_hourly_values_from_list([0.5, 1], pint_unit=u.kg)
        self.component.energy_footprint_per_usage_pattern = ExplainableObjectDict({
            mock_pattern_1: footprint_1,
            mock_pattern_2: footprint_2
        })

        self.component.update_energy_footprint()

        # Sum: [1, 2] + [0.5, 1] = [1.5, 3]
        result = self.component.energy_footprint
        self.assertTrue(np.allclose([1.5, 3], result.value.to(u.kg).magnitude))


if __name__ == "__main__":
    unittest.main()
