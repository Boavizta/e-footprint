import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.hardware.edge_storage import EdgeStorage


class TestEdgeComputer(TestCase):
    def setUp(self):
        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.mock_storage.edge_usage_patterns = []
        self.mock_storage.id = "mock_storage_id"
        self.edge_computer = EdgeComputer(
            name="Test EdgeComputer",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=self.mock_storage
        )
        self.edge_computer.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeComputer initialization and property delegation."""
        self.assertEqual("Test EdgeComputer", self.edge_computer.name)
        # structure_fabrication_carbon_footprint is defined at EdgeDevice level
        self.assertIn("Structure fabrication carbon footprint",
                      self.edge_computer.structure_fabrication_carbon_footprint.label)
        self.assertEqual(60 * u.kg, self.edge_computer.structure_fabrication_carbon_footprint.value)

        # Properties delegate to components
        self.assertEqual(30 * u.W, self.edge_computer.power.value)
        self.assertEqual(8 * u.year, self.edge_computer.lifespan.value)
        self.assertEqual(5 * u.W, self.edge_computer.idle_power.value)
        self.assertEqual(8 * u.GB_ram, self.edge_computer.ram.value)
        self.assertEqual(4 * u.cpu_core, self.edge_computer.compute.value)
        self.assertEqual(1 * u.GB_ram, self.edge_computer.base_ram_consumption.value)
        self.assertEqual(0.1 * u.cpu_core, self.edge_computer.base_compute_consumption.value)
        self.assertEqual(self.mock_storage, self.edge_computer.storage)

        # Components should be created
        self.assertIsNotNone(self.edge_computer.ram_component)
        self.assertIsNotNone(self.edge_computer.cpu_component)

        # Verify components are in EdgeDevice.components list
        self.assertEqual(3, len(self.edge_computer.components))
        self.assertIn(self.edge_computer.ram_component, self.edge_computer.components)
        self.assertIn(self.edge_computer.cpu_component, self.edge_computer.components)
        self.assertIn(self.edge_computer.storage, self.edge_computer.components)

    def test_init_removes_raw_nb_of_instances(self):
        """Test that raw_nb_of_instances is removed during initialization."""
        self.assertFalse(hasattr(self.edge_computer, "raw_nb_of_instances"))

    def test_init_sets_empty_explainable_objects(self):
        """Test that initialization sets proper empty explainable objects."""
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        self.assertIsInstance(self.edge_computer.available_compute_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_computer.available_ram_per_instance, EmptyExplainableObject)
        self.assertIsInstance(self.edge_computer.unitary_hourly_compute_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_computer.unitary_hourly_ram_need_per_usage_pattern, ExplainableObjectDict)

    def test_labels_are_set_correctly(self):
        """Test that all attributes have correct labels."""
        self.assertIn("Idle power of Test EdgeComputer", self.edge_computer.idle_power.label)
        self.assertIn("RAM of Test EdgeComputer", self.edge_computer.ram.label)
        self.assertIn("Compute of Test EdgeComputer", self.edge_computer.compute.label)
        self.assertIn("Base RAM consumption of Test EdgeComputer", self.edge_computer.base_ram_consumption.label)
        self.assertIn("Base compute consumption of Test EdgeComputer", self.edge_computer.base_compute_consumption.label)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that components are returned as dependent objects."""
        dependent_objects = self.edge_computer.modeling_objects_whose_attributes_depend_directly_on_me
        # EdgeComputer has 3 components: RAM, CPU, and Storage
        self.assertEqual(3, len(dependent_objects))
        self.assertIn(self.edge_computer.ram_component, dependent_objects)
        self.assertIn(self.edge_computer.cpu_component, dependent_objects)
        self.assertIn(self.edge_computer.storage, dependent_objects)

    def test_unitary_power_per_usage_pattern_property(self):
        """Test unitary_power_per_usage_pattern is delegated to EdgeDevice."""
        # This is now calculated at the EdgeDevice level by aggregating component powers
        # EdgeComputer just provides a pass-through
        self.assertIsNotNone(self.edge_computer.unitary_power_per_usage_pattern)

    def test_lifespan_propagates_to_components(self):
        """Test that updating lifespan propagates copies to RAM and CPU components."""
        new_lifespan = SourceValue(10 * u.year)
        from efootprint.logger import logger
        logger.info("setting new lifespan to %s", new_lifespan)
        self.edge_computer.lifespan = new_lifespan

        # EdgeComputer's lifespan should be updated
        logger.info("checking edge computer lifespan: %s", self.edge_computer.lifespan)
        self.assertEqual(10 * u.year, self.edge_computer.lifespan.value)

        # Components should have copies with the same value but different objects
        self.assertEqual(10 * u.year, self.edge_computer.ram_component.lifespan.value)
        self.assertEqual(10 * u.year, self.edge_computer.cpu_component.lifespan.value)

        # They should be different objects (copies, not references)
        self.assertIsNot(self.edge_computer.lifespan, self.edge_computer.ram_component.lifespan)
        self.assertIsNot(self.edge_computer.lifespan, self.edge_computer.cpu_component.lifespan)


if __name__ == "__main__":
    unittest.main()