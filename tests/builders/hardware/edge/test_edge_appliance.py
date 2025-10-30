import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from tests.utils import set_modeling_obj_containers


class TestEdgeAppliance(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.edge_device = EdgeAppliance(
            "test edge appliance",
            carbon_footprint_fabrication=SourceValue(100 * u.kg),
            power=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power=SourceValue(5 * u.W))

    def test_init(self):
        """Test EdgeAppliance initialization."""
        self.assertEqual("test edge appliance", self.edge_device.name)
        self.assertEqual(100 * u.kg, self.edge_device.carbon_footprint_fabrication.value)
        self.assertEqual(50 * u.W, self.edge_device.power.value)
        self.assertEqual(5 * u.year, self.edge_device.lifespan.value)
        self.assertEqual(5 * u.W, self.edge_device.idle_power.value)
        self.assertIsInstance(self.edge_device.unitary_hourly_workload_per_usage_pattern, ExplainableObjectDict)

    def test_recurrent_needs_property(self):
        """Test recurrent_needs property returns modeling_obj_containers."""
        mock_workload1 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload2 = MagicMock(spec=RecurrentEdgeWorkload)

        set_modeling_obj_containers(self.edge_device, [mock_workload1, mock_workload2])

        self.assertEqual({mock_workload1, mock_workload2}, set(self.edge_device.recurrent_needs))

    def test_edge_usage_patterns_property(self):
        """Test edge_usage_patterns property aggregates patterns from workloads."""
        mock_pattern1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern1.id = "pattern1"
        mock_pattern2.id = "pattern2"

        mock_workload1 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload2 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload1.edge_usage_patterns = [mock_pattern1]
        mock_workload2.edge_usage_patterns = [mock_pattern2]

        set_modeling_obj_containers(self.edge_device, [mock_workload1, mock_workload2])

        patterns = self.edge_device.edge_usage_patterns
        self.assertEqual(2, len(patterns))
        self.assertIn(mock_pattern1, patterns)
        self.assertIn(mock_pattern2, patterns)


if __name__ == "__main__":
    unittest.main()