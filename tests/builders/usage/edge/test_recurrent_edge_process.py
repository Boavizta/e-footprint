import unittest
from copy import copy
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_weekly_pattern import (
    ExplainableRecurrentQuantitiesFromWeeklyPattern)
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.constants.units import u


class TestRecurrentEdgeProcess(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ram_component = MagicMock(spec=EdgeRAMComponent)
        self.mock_ram_component.name = "Mock RAM Component"
        self.mock_ram_component.compatible_root_units = [u.bit_ram]
        self.mock_ram_component.edge_device = None

        self.mock_cpu_component = MagicMock(spec=EdgeCPUComponent)
        self.mock_cpu_component.name = "Mock CPU Component"
        self.mock_cpu_component.compatible_root_units = [u.cpu_core]
        self.mock_cpu_component.edge_device = None

        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.mock_storage.name = "Mock Storage"
        self.mock_storage.compatible_root_units = [u.bit_ram]
        self.mock_storage.edge_device = None

        self.mock_edge_computer = MagicMock(spec=EdgeComputer)
        self.mock_edge_computer.id = "mock_computer"
        self.mock_edge_computer.name = "Mock Computer"
        self.mock_edge_computer.ram_component = self.mock_ram_component
        self.mock_edge_computer.cpu_component = self.mock_cpu_component
        self.mock_edge_computer.storage = self.mock_storage

        self.recurrent_compute_needed = SourceRecurrentValues(
            Quantity(np.array([2.5] * 168, dtype=np.float32), u.cpu_core))
        self.recurrent_ram_needed = SourceRecurrentValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB_ram))
        self.recurrent_storage_needed = SourceRecurrentValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB))

        self.edge_process = RecurrentEdgeProcess(
            "test edge process",
            edge_device=self.mock_edge_computer,
            recurrent_compute_needed=self.recurrent_compute_needed,
            recurrent_ram_needed=self.recurrent_ram_needed,
            recurrent_storage_needed=self.recurrent_storage_needed)

    def test_init(self):
        """Test RecurrentEdgeProcess initialization."""
        self.assertEqual("test edge process", self.edge_process.name)
        self.assertEqual(self.mock_edge_computer, self.edge_process.edge_device)
        self.assertIs(self.recurrent_compute_needed, self.edge_process.recurrent_compute_needed)
        self.assertIs(self.recurrent_ram_needed, self.edge_process.recurrent_ram_needed)
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
        self.assertIsInstance(self.edge_process.unitary_hourly_compute_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_process.unitary_hourly_ram_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_process.unitary_hourly_storage_need_per_usage_pattern, ExplainableObjectDict)
        # Verify that storage need is a RecurrentEdgeStorageNeed instance
        self.assertIsInstance(self.edge_process.storage_need, RecurrentEdgeStorageNeed)

    def test_unitary_hourly_storage_need_per_usage_pattern_delegates_to_storage_need(self):
        """Test that unitary_hourly_storage_need_per_usage_pattern delegates to the storage need."""
        # Verify that the property returns the storage need's unitary_hourly_need_per_usage_pattern
        result = self.edge_process.unitary_hourly_storage_need_per_usage_pattern
        expected = self.edge_process.storage_need.unitary_hourly_need_per_usage_pattern

        self.assertIs(result, expected)

    def test_from_defaults_class_method(self):
        """Test RecurrentEdgeProcess can be created using from_defaults class method."""
        edge_process_from_defaults = RecurrentEdgeProcess.from_defaults(
            "default process", edge_device=self.mock_edge_computer)

        self.assertEqual("default process", edge_process_from_defaults.name)
        self.assertEqual(self.mock_edge_computer, edge_process_from_defaults.edge_device)
        self.assertIsInstance(edge_process_from_defaults.recurrent_compute_needed, SourceRecurrentValues)
        self.assertIsInstance(edge_process_from_defaults.recurrent_ram_needed, SourceRecurrentValues)
        self.assertEqual(
            edge_process_from_defaults.recurrent_compute_needed.unit, u.cpu_core)
        self.assertEqual(
            edge_process_from_defaults.recurrent_ram_needed.unit, u.GB_ram)

    def test_modeling_update_swaps_constant_and_weekly_recurrent_builders(self):
        """Test sibling recurrent builders can replace each other under the declared base-class annotation."""
        constant = ExplainableRecurrentQuantitiesFromConstant({
            "constant_value": 2, "constant_unit": "cpu_core"})
        process = RecurrentEdgeProcess(
            "builder swap process", edge_device=self.mock_edge_computer,
            recurrent_compute_needed=constant,
            recurrent_ram_needed=copy(self.recurrent_ram_needed),
            recurrent_storage_needed=copy(self.recurrent_storage_needed))
        weekly = ExplainableRecurrentQuantitiesFromWeeklyPattern({
            "unit": "cpu_core",
            "profiles": [{"name": "all week", "days": list(range(7)), "baseline": 3, "ranges": []}],
        })

        update = ModelingUpdate([[process.recurrent_compute_needed, weekly]])

        self.assertIs(weekly, process.recurrent_compute_needed)
        update.rollback()
        self.assertIs(constant, process.recurrent_compute_needed)
        ModelingUpdate([[process.recurrent_compute_needed, weekly]])
        replacement_constant = ExplainableRecurrentQuantitiesFromConstant({
            "constant_value": 4, "constant_unit": "cpu_core"})
        ModelingUpdate([[process.recurrent_compute_needed, replacement_constant]])
        self.assertIs(replacement_constant, process.recurrent_compute_needed)

    def test_modeling_update_rejects_incompatible_batch_before_applying_valid_sibling_swap(self):
        """Test incompatible declared input types leave every change in a mixed update unapplied."""
        original_compute = self.edge_process.recurrent_compute_needed
        original_ram = self.edge_process.recurrent_ram_needed
        weekly = ExplainableRecurrentQuantitiesFromWeeklyPattern({
            "unit": "cpu_core",
            "profiles": [{"name": "all week", "days": list(range(7)), "baseline": 3, "ranges": []}],
        })
        incompatible_ram = ExplainableQuantity(2 * u.GB_ram, label="not recurrent")

        with self.assertRaises(TypeError):
            ModelingUpdate([
                [original_compute, weekly],
                [original_ram, incompatible_ram],
            ])

        self.assertIs(original_compute, self.edge_process.recurrent_compute_needed)
        self.assertIs(original_ram, self.edge_process.recurrent_ram_needed)


if __name__ == "__main__":
    unittest.main()
