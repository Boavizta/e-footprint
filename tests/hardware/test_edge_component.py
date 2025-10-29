import unittest
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_component import EdgeComponent
from efootprint.core.hardware.edge_device import EdgeDevice


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

    def test_device_carbon_footprint_fabrication_intensity_share_no_device(self):
        """Test device_carbon_footprint_fabrication_intensity_share returns EmptyExplainableObject when no device."""
        result = self.component.device_carbon_footprint_fabrication_intensity_share
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_device_carbon_footprint_fabrication_intensity_share(self):
        """Test device_carbon_footprint_fabrication_intensity_share calculation."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"

        # Component intensity: 20 kg / 5 year = 4 kg/year
        # Device total intensity: 10 kg/year
        # Share: 4/10 = 0.4
        mock_device.total_carbon_footprint_fabrication_intensity = SourceValue(10 * u.kg / u.year)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.device_carbon_footprint_fabrication_intensity_share

            expected_share = 0.4
            self.assertAlmostEqual(expected_share, result.value.magnitude, places=5)
            self.assertEqual(u.dimensionless, result.value.units)
            self.assertIn("Test Component carbon footprint fabrication intensity share of Test Device", result.label)

    def test_device_carbon_footprint_fabrication_intensity_share_zero_total(self):
        """Test device_carbon_footprint_fabrication_intensity_share returns EmptyExplainableObject when device total is zero."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_carbon_footprint_fabrication_intensity = SourceValue(0 * u.kg / u.year)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.device_carbon_footprint_fabrication_intensity_share
            self.assertIsInstance(result, EmptyExplainableObject)

    def test_device_power_share_no_device(self):
        """Test device_power_share returns EmptyExplainableObject when no device."""
        result = self.component.device_power_share
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_device_power_share(self):
        """Test device_power_share calculation."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"

        # Component power: 50 W
        # Device total power: 200 W
        # Share: 50/200 = 0.25
        mock_device.total_component_power = SourceValue(200 * u.W)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.device_power_share

            expected_share = 0.25
            self.assertAlmostEqual(expected_share, result.value.magnitude, places=5)
            self.assertEqual(u.dimensionless, result.value.units)
            self.assertIn("Test Component power share of Test Device", result.label)

    def test_device_power_share_zero_total(self):
        """Test device_power_share returns EmptyExplainableObject when device total power is zero."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_component_power = SourceValue(0 * u.W)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.device_power_share
            self.assertIsInstance(result, EmptyExplainableObject)

    def test_instances_fabrication_footprint_no_device(self):
        """Test instances_fabrication_footprint returns EmptyExplainableObject when no device."""
        result = self.component.instances_fabrication_footprint
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_instances_fabrication_footprint(self):
        """Test instances_fabrication_footprint calculation."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_carbon_footprint_fabrication_intensity = SourceValue(10 * u.kg / u.year)
        mock_device.instances_fabrication_footprint = SourceValue(100 * u.kg)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.instances_fabrication_footprint

            # Component intensity: 20 kg / 5 year = 4 kg/year
            # Share: 4/10 = 0.4
            # Component footprint: 100 kg * 0.4 = 40 kg
            expected_footprint = 40
            self.assertAlmostEqual(expected_footprint, result.value.to(u.kg).magnitude, places=5)
            self.assertIn("Test Component instances fabrication footprint", result.label)

    def test_instances_fabrication_footprint_empty_device_footprint(self):
        """Test instances_fabrication_footprint returns EmptyExplainableObject when device footprint is empty."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_carbon_footprint_fabrication_intensity = SourceValue(10 * u.kg / u.year)
        mock_device.instances_fabrication_footprint = EmptyExplainableObject()

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.instances_fabrication_footprint
            self.assertIsInstance(result, EmptyExplainableObject)

    def test_instances_energy_no_device(self):
        """Test instances_energy returns EmptyExplainableObject when no device."""
        result = self.component.instances_energy
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_instances_energy(self):
        """Test instances_energy calculation."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_component_power = SourceValue(200 * u.W)
        mock_device.instances_energy = SourceValue(1000 * u.Wh)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.instances_energy

            # Component power: 50 W
            # Share: 50/200 = 0.25
            # Component energy: 1000 Wh * 0.25 = 250 Wh
            expected_energy = 250
            self.assertAlmostEqual(expected_energy, result.value.to(u.Wh).magnitude, places=5)
            self.assertIn("Test Component instances energy", result.label)

    def test_instances_energy_empty_device_energy(self):
        """Test instances_energy returns EmptyExplainableObject when device energy is empty."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_component_power = SourceValue(200 * u.W)
        mock_device.instances_energy = EmptyExplainableObject()

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.instances_energy
            self.assertIsInstance(result, EmptyExplainableObject)

    def test_energy_footprint_no_device(self):
        """Test energy_footprint returns EmptyExplainableObject when no device."""
        result = self.component.energy_footprint
        self.assertIsInstance(result, EmptyExplainableObject)

    def test_energy_footprint(self):
        """Test energy_footprint calculation."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_component_power = SourceValue(200 * u.W)
        mock_device.energy_footprint = SourceValue(50 * u.kg)

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.energy_footprint

            # Component power: 50 W
            # Share: 50/200 = 0.25
            # Component energy footprint: 50 kg * 0.25 = 12.5 kg
            expected_footprint = 12.5
            self.assertAlmostEqual(expected_footprint, result.value.to(u.kg).magnitude, places=5)
            self.assertIn("Test Component energy footprint", result.label)

    def test_energy_footprint_empty_device_footprint(self):
        """Test energy_footprint returns EmptyExplainableObject when device energy footprint is empty."""
        mock_device = MagicMock(spec=EdgeDevice)
        mock_device.name = "Test Device"
        mock_device.total_component_power = SourceValue(200 * u.W)
        mock_device.energy_footprint = EmptyExplainableObject()

        with patch.object(type(self.component), 'edge_device', new_callable=PropertyMock, return_value=mock_device):
            result = self.component.energy_footprint
            self.assertIsInstance(result, EmptyExplainableObject)


if __name__ == "__main__":
    unittest.main()
