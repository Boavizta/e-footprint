import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload, WorkloadOutOfBoundsError
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeWorkload(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_appliance_component = MagicMock(spec=EdgeWorkloadComponent)
        self.mock_appliance_component.name = "Mock Appliance Component"
        self.mock_appliance_component.expected_need_units.return_value = [u.concurrent, u.dimensionless]
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


    def test_workload_exceeds_upper_bound(self):
        """Test that workload values exceeding 1 raise WorkloadOutOfBoundsError."""
        invalid_workload = SourceRecurrentValues(
            Quantity(np.array([0.5, 1.2, 0.8] * 56, dtype=np.float32), u.concurrent))

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            RecurrentEdgeWorkload(
                "invalid edge workload",
                edge_device=self.mock_edge_device,
                recurrent_workload=invalid_workload)

        self.assertIn("values outside the valid range [0, 1]", str(context.exception))
        self.assertIn("1.200", str(context.exception))

    def test_workload_below_lower_bound(self):
        """Test that workload values below 0 raise WorkloadOutOfBoundsError."""
        invalid_workload = SourceRecurrentValues(
            Quantity(np.array([0.5, -0.2, 0.8] * 56, dtype=np.float32), u.concurrent))

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            RecurrentEdgeWorkload(
                "invalid edge workload",
                edge_device=self.mock_edge_device,
                recurrent_workload=invalid_workload)

        self.assertIn("values outside the valid range [0, 1]", str(context.exception))
        self.assertIn("-0.200", str(context.exception))

    def test_workload_at_boundaries(self):
        """Test that workload values exactly at 0 and 1 are valid."""
        valid_workload = SourceRecurrentValues(
            Quantity(np.array([0.0, 1.0, 0.5] * 56, dtype=np.float32), u.concurrent))

        edge_workload = RecurrentEdgeWorkload(
            "boundary edge workload",
            edge_device=self.mock_edge_device,
            recurrent_workload=valid_workload)

        self.assertEqual("boundary edge workload", edge_workload.name)
        self.assertEqual(self.mock_edge_device, edge_workload.edge_device)

    def test_workload_update_exceeds_bound(self):
        """Test that updating workload to invalid values raises WorkloadOutOfBoundsError."""
        invalid_workload = SourceRecurrentValues(
            Quantity(np.array([0.5, 1.5, 0.8] * 56, dtype=np.float32), u.concurrent))

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            self.edge_workload.recurrent_workload = invalid_workload

        self.assertIn("values outside the valid range [0, 1]", str(context.exception))


if __name__ == "__main__":
    unittest.main()