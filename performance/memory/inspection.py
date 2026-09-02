"""Peek-only measurements of materialized reactive state."""

from efootprint.abstract_modeling_classes.reactive_core import (
    computed_structures,
    peek_instance_slot_registry,
)
from efootprint.core.system import System


def _underlying(obj):
    return getattr(obj, "_value", obj)


def linked_objects(system: System) -> tuple:
    """Return each underlying linked object once, including the system."""
    objects = [_underlying(system), *(_underlying(obj) for obj in system.all_linked_objects)]
    return tuple(dict.fromkeys(objects))


def cached_sub_slot_count(system: System, attribute_name: str) -> int:
    """Count cached computed-dictionary entries without creating slots or pulling values."""
    count = 0
    for obj in linked_objects(system):
        for key, slot in peek_instance_slot_registry(obj).items():
            if isinstance(key, tuple) and key[0] == attribute_name and slot.has_cached_value:
                count += 1
    return count


def materialized_state(system: System) -> dict[str, int | None]:
    """Report observable cache dimensions without changing the model."""
    objects = linked_objects(system)
    registries = [peek_instance_slot_registry(obj) for obj in objects]
    matrix = computed_structures(System)["impact_repartition_matrix"].peek(system)
    transient_cached = 0
    for obj in objects:
        registry = peek_instance_slot_registry(obj)
        for name, descriptor in computed_structures(obj.efootprint_class).items():
            slot = registry.get(name)
            if descriptor.transient and slot is not None and slot.has_cached_value:
                transient_cached += 1
    return {
        "modeling_objects": len(objects),
        "reactive_slots": sum(len(registry) for registry in registries),
        "cached_reactive_slots": sum(slot.has_cached_value for registry in registries for slot in registry.values()),
        "web_step_coordinate_slots": cached_sub_slot_count(system, "hourly_avg_occurrences_per_usage_coordinate"),
        "job_occurrence_coordinate_slots": cached_sub_slot_count(system, "hourly_avg_occurrences_per_coordinate"),
        "job_transfer_coordinate_slots": cached_sub_slot_count(system, "hourly_data_transferred_per_coordinate"),
        "edge_component_hourly_slots": cached_sub_slot_count(system, "unitary_hourly_need_per_usage_pattern"),
        "edge_server_hourly_slots": cached_sub_slot_count(system, "unitary_hourly_volume_per_usage_pattern"),
        "attribution_matrix_rows": None if matrix is None else len(matrix),
        "cached_transient_structures": transient_cached,
    }
