"""Update-time safety for newly linked objects.

Guard slots (validation and capacity checks living outside the footprint cone) are re-pulled when an
invalidation wave voids them — but a slot that has never been computed has no dependency edges, so
no wave can reach it. These tests pin the complementary mechanism: linking a new object into a live
system pulls all its guard slots at update time, so invalid new links are rejected and rolled back
exactly like invalid input edits (spec: update-time safety preserved), for both gap shapes — a
never-read validation slot under the default eager set, and a capacity guard under an empty eager
set (where no footprint pull would reach it either).
"""
from unittest import TestCase

from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from tests.integration_tests.integration_simple_edge_system_base_class import (
    IntegrationTestSimpleEdgeSystemBaseClass)
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


class TestNewlyLinkedObjectGuardSlots(TestCase):
    def test_linking_device_with_invalid_lifespan_raises_and_rolls_back(self):
        """Test that linking a new EdgeDevice whose lifespan is shorter than the usage journey's
        usage span is rejected at update time, even though lifespan_validation (a never-read
        validation slot, outside the footprint cone) has never been computed on the new device."""
        system, _ = IntegrationTestSimpleEdgeSystemBaseClass.generate_simple_edge_system()
        device_need = next(
            obj for obj in system.all_linked_objects if obj.class_as_simple_str == "RecurrentEdgeDeviceNeed")
        old_device = device_need.edge_device
        new_device = EdgeDevice.from_defaults(
            "short-lived device", lifespan=SourceValue(1 * u.hour),
            components=[
                EdgeRAMComponent.from_defaults("new device ram"),
                EdgeCPUComponent.from_defaults(
                    "new device cpu", base_compute_consumption=SourceValue(0.1 * u.cpu_core))])

        with self.assertRaises(InsufficientCapacityError):
            device_need.edge_device = new_device

        self.assertEqual(old_device.id, device_need.edge_device.id)

    def test_linking_over_subscribed_server_with_empty_eager_set_raises_and_rolls_back(self):
        """Test that relinking a job to a new over-subscribed server is rejected at update time under
        eager_outputs=(), where no footprint pull would otherwise compute the new server's capacity
        guard (available_ram_per_instance has never been computed, so no wave can void it)."""
        system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
        job = next(obj for obj in system.all_linked_objects if obj.class_as_simple_str == "Job")
        old_server = job.server
        over_subscribed_server = Server.from_defaults(
            "over-subscribed server", storage=Storage.from_defaults("new server storage"),
            ram=SourceValue(1 * u.GB_ram), base_ram_consumption=SourceValue(10 * u.GB_ram))

        with self.assertRaises(InsufficientCapacityError):
            ModelingUpdate([[job.server, over_subscribed_server]], eager_outputs=())

        self.assertEqual(old_server.id, job.server.id)
