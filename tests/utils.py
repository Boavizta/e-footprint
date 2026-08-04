from contextlib import contextmanager
from typing import List
from unittest.mock import MagicMock, patch as mock_patch

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.system import System


@contextmanager
def patch_attribute(target, attr_name: str, new_value):
    """Pin an attribute for the duration of a with-block. For computed attributes the value is
    attached to the reactive slot without computing (mock.patch.object would compute the current
    value on entry just to snapshot it); anything else falls back to mock.patch.object."""
    from efootprint.abstract_modeling_classes.reactive_core import (
        computed_slots, computed_attribute, computed_structure, computed_structures)

    descriptor = None
    if not isinstance(target, type):
        target_class = getattr(target, "efootprint_class", type(target))
        if isinstance(target_class, type):
            descriptor = computed_slots(target_class).get(attr_name) or computed_structures(target_class).get(attr_name)
    if not isinstance(descriptor, (computed_attribute, computed_structure)):
        if isinstance(target, ModelingObject):
            original_value = getattr(target, attr_name, None)
            target._set_input_passively(attr_name, new_value, check_input_validity=False)
            try:
                yield new_value
            finally:
                target._set_input_passively(attr_name, original_value, check_input_validity=False)
            return
        with mock_patch.object(target, attr_name, new_value):
            yield new_value
        return
    slot = descriptor.slot(target)
    had_value = slot.has_cached_value
    original_value = slot._value if had_value else None
    descriptor.attach_cached_value(target, new_value)
    try:
        yield new_value
    finally:
        slot._drop_value()
        if had_value:
            descriptor.attach_cached_value(target, original_value)


def _slot_descriptor(efootprint_class, attr_name: str):
    from efootprint.abstract_modeling_classes.reactive_core import computed_slots, computed_structures

    descriptor = computed_slots(efootprint_class).get(attr_name) or computed_structures(efootprint_class).get(attr_name)
    if descriptor is None:
        raise KeyError(f"{attr_name} is neither a computed attribute nor a computed structure of "
                       f"{efootprint_class.__name__}")
    return descriptor


def attach_attribute(mod_obj, attr_name: str, value, key=None):
    """Pin a computed attribute or computed structure (or one key of a computed dict) through the
    descriptor's attach path — the test replacement for plain assignment, which raises on computed
    names."""
    descriptor = _slot_descriptor(mod_obj.efootprint_class, attr_name)
    if key is not None:
        descriptor.attach_element_cached_value(mod_obj, key, value)
    else:
        descriptor.attach_cached_value(mod_obj, value)
    return value


def attach_input(mod_obj, attr_name: str, value, check_input_validity=True):
    """Pin one input without launching a transaction, for focused computed-getter test setup."""
    return mod_obj._set_input_passively(attr_name, value, check_input_validity=check_input_validity)


def recompute_attribute(mod_obj, attr_name: str, key=None):
    """Force a fresh computation of a computed attribute or computed structure (or one key of a computed
    dict) and return the new value — the unit-test replacement for the former update_<attr> calls, for
    tests that change raw inputs in place and want the recomputation to run now."""
    from efootprint.abstract_modeling_classes.reactive_core import invalidate, instance_slot_registry

    descriptor = _slot_descriptor(mod_obj.efootprint_class, attr_name)
    if key is not None:
        slot = descriptor.sub_slot(mod_obj, key)
        invalidate(slot)
        return slot.pull()
    slot = descriptor.slot(mod_obj)
    slots_to_invalidate = [slot] + [
        sub_slot for registry_key, sub_slot in instance_slot_registry(mod_obj).items()
        if isinstance(registry_key, tuple) and registry_key[0] == attr_name]
    invalidate(*slots_to_invalidate)
    return slot.pull()


def set_modeling_obj_containers(efootprint_obj: ModelingObject, mod_obj_containers_to_set: List):
    mock_contextual_containers = []
    for mod_obj_container in mod_obj_containers_to_set:
        mock_contextual_container = MagicMock()
        mock_contextual_container.modeling_obj_container = mod_obj_container
        mock_contextual_containers.append(mock_contextual_container)

    efootprint_obj.contextual_modeling_obj_containers = mock_contextual_containers


def create_mod_obj_mock(efootprint_class, name: str = None, **kwargs):
    mock_obj = MagicMock(spec=efootprint_class)
    mock_obj.name = name if name else "Mock " + efootprint_class.__name__
    mock_obj.id = mock_obj.name.replace(" ", "-").lower()
    mock_obj.efootprint_class = efootprint_class
    mock_obj.canonical_class = efootprint_class.canonical_class
    mock_obj.contextual_modeling_obj_containers = []
    mock_obj.explainable_object_dicts_containers = []
    for key, value in kwargs.items():
        setattr(mock_obj, key, value)
    return mock_obj

def get_canonical_class_index(obj: ModelingObject):
    """Index of the object's canonical family in a low-to-high dependency-level ordering, used by
    check_all_calculus_graph_dependencies_consistencies to assert that calculated attributes only
    depend on same-or-lower-level calculated ancestors."""
    from efootprint.core.country import Country
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep
    from efootprint.core.hardware.device import Device
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.core.hardware.edge.edge_component import EdgeComponent
    from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
    from efootprint.core.hardware.edge.edge_device import EdgeDevice
    from efootprint.builders.services.service_base_class import Service
    from efootprint.core.usage.job import JobBase
    from efootprint.core.hardware.network import Network
    from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
    from efootprint.core.hardware.server_base import ServerBase
    from efootprint.core.hardware.storage import Storage
    from efootprint.core.system import System

    dependency_level_order = [
        Country, UsagePattern, UsageJourney, UsageJourneyStep, Device,
        EdgeUsagePattern, EdgeUsageJourney, EdgeFunction,
        RecurrentEdgeDeviceNeed, RecurrentServerNeed, RecurrentEdgeComponentNeed, EdgeComponent,
        EdgeDeviceGroup, EdgeDevice, Service, JobBase, Network, ExternalAPI, ServerBase, ExternalAPIServer,
        Storage, System]
    for index, efootprint_class in enumerate(dependency_level_order):
        if isinstance(obj, efootprint_class):
            return index
    raise ValueError(f"Class of object {obj} not found in the dependency-level ordering.")

def check_all_calculus_graph_dependencies_consistencies(system: System):
    for obj in system.all_linked_objects:
        # Exclude hidden component classes
        if obj.class_as_simple_str in [
            "EdgeComputerRAMComponent", "EdgeComputerCPUComponent", "EdgeApplianceComponent"]:
            continue
        for attr in obj.calculated_attributes:
            calculated_attr_value = getattr(obj, attr)
            if isinstance(calculated_attr_value, dict):
                if len(calculated_attr_value) == 0:
                    continue
                calculated_attr_value = list(calculated_attr_value.values())[0]
            obj_canonical_index = get_canonical_class_index(obj)
            for ancestor in calculated_attr_value.direct_ancestors_with_id:
                ancestor_obj = ancestor.modeling_obj_container
                ancestor_canonical_index = get_canonical_class_index(ancestor_obj)
                if (ancestor_canonical_index > obj_canonical_index
                        and ancestor.attr_name_in_mod_obj_container in ancestor_obj.calculated_attributes):
                    raise ValueError(
                        f"Inconsistent calculus graph dependency found: object {obj.name} of class "
                        f"{obj.class_as_simple_str} (canonical index {obj_canonical_index}) has a calculated "
                        f"attribute '{attr}' depending on calculated ancestor object {ancestor_obj.name} of class "
                        f"{ancestor_obj.class_as_simple_str} (canonical index {ancestor_canonical_index})."
                    )
