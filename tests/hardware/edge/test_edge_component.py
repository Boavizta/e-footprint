from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from tests.utils import create_mod_obj_mock


class ConcreteEdgeComponent(EdgeComponent):
    """Concrete implementation of EdgeComponent for testing."""
    compatible_root_units = [u.cpu_core]
    default_values = {
        "carbon_footprint_fabrication": SourceValue(20 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(10 * u.W),
    }

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
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Test Journey")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: SourceValue(10 * u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey

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
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Test Journey")
        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 20], pint_unit=u.concurrent)}
        mock_pattern.edge_usage_journey = mock_edge_usage_journey

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
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")
        mock_country = MagicMock()
        mock_country.average_carbon_intensity = SourceValue(0.5 * u.kg / u.kWh)
        mock_pattern.country = mock_country

        instances_energy = create_source_hourly_values_from_list([1000, 2000], pint_unit=u.Wh)
        self.component.instances_energy_per_usage_pattern = ExplainableObjectDict({mock_pattern: instances_energy})

        self.component.update_dict_element_in_energy_footprint_per_usage_pattern(mock_pattern)

        # Energy footprint = [1000, 2000] Wh * 0.5 kg/kWh = [0.5, 1.0] kg
        expected_footprint = [0.5, 1.0]

        result = self.component.energy_footprint_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_footprint, result.value.to(u.kg).magnitude))

    def test_update_instances_fabrication_footprint(self):
        """Test summing fabrication footprint across patterns."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2")

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

    @patch("efootprint.core.hardware.edge.edge_component.EdgeComponent.recurrent_edge_component_needs",
           new_callable=PropertyMock)
    def test_update_impact_repartition_weights_scales_component_needs_by_parallel_usage(self, mock_needs):
        """Test component weights aggregate hourly need times the number of parallel edge usage journeys."""
        usage_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        usage_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")
        usage_pattern_1.edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey 1")
        usage_pattern_2.edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey 2")
        usage_pattern_1.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([2, 2], pint_unit=u.concurrent)}
        usage_pattern_2.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            usage_pattern_2: create_source_hourly_values_from_list([4, 4], pint_unit=u.concurrent)}

        need_1 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed,
            name="Need 1",
            edge_usage_patterns=[usage_pattern_1, usage_pattern_2],
            unitary_hourly_need_per_usage_pattern={
                usage_pattern_1: create_source_hourly_values_from_list([1, 1], pint_unit=u.cpu_core),
                usage_pattern_2: create_source_hourly_values_from_list([2, 2], pint_unit=u.cpu_core),
            },
        )
        need_2 = create_mod_obj_mock(
            RecurrentEdgeComponentNeed,
            name="Need 2",
            edge_usage_patterns=[usage_pattern_1],
            unitary_hourly_need_per_usage_pattern={
                usage_pattern_1: create_source_hourly_values_from_list([3, 3], pint_unit=u.cpu_core)},
        )
        mock_needs.return_value = [need_1, need_2]

        self.component.update_impact_repartition_weights()

        self.assertTrue(np.allclose([10, 10], self.component.impact_repartition_weights[need_1].magnitude))
        self.assertTrue(np.allclose([6, 6], self.component.impact_repartition_weights[need_2].magnitude))
