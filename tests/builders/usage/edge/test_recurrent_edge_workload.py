import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.usage.edge.recurrent_edge_component_need import WorkloadOutOfBoundsError
from efootprint.constants.units import u


class TestRecurrentEdgeWorkload(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_appliance_component = MagicMock(spec=EdgeWorkloadComponent)
        self.mock_appliance_component.name = "Mock Appliance Component"
        self.mock_appliance_component.compatible_root_units = [u.concurrent]
        self.mock_appliance_component.edge_device = None

        self.mock_edge_device = MagicMock(spec=EdgeAppliance)
        self.mock_edge_device.id = "mock_hardware"
        self.mock_edge_device.name = "Mock Hardware"
        self.mock_edge_device.appliance_component = self.mock_appliance_component

        self.recurrent_workload = SourceRecurrentValues(
            Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent))

        self.edge_workload = RecurrentEdgeWorkload(
            "test edge workload",
            edge_device=self.mock_edge_device,
            recurrent_workload=self.recurrent_workload)

    def test_init(self):
        """Test RecurrentEdgeWorkload initialization."""
        self.assertEqual("test edge workload", self.edge_workload.name)
        self.assertEqual(self.mock_edge_device, self.edge_workload.edge_device)
        self.assertIs(self.recurrent_workload, self.edge_workload.recurrent_workload)
        self.assertIsInstance(self.edge_workload.unitary_hourly_workload_per_usage_pattern, ExplainableObjectDict)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test modeling_objects_whose_attributes_depend_directly_on_me returns recurrent_edge_component_needs."""
        dependent_objects = self.edge_workload.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual(self.edge_workload.recurrent_edge_component_needs, dependent_objects)


if __name__ == "__main__":
    unittest.main()