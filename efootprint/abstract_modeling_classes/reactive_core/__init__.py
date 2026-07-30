"""Stable import facade for the reactive engine.

Implementation lives in three package modules with one-way dependencies:

- graph: slots, compute frames, dependency recording, and invalidation;
- computed_slots: computed descriptors and their class registries;
- reverse_relationships: declarative reverse links and their reactive hooks.

Existing callers continue to import from this package so the split does not leak through the model.
"""

from .graph import (
    CircularDependencyError,
    ReactiveSlot,
    _compute_stack,
    _node_slot,
    collect_invalidated_slots,
    computation_in_progress,
    instance_slot_registry,
    invalidate,
    invalidate_node_if_exists,
    peek_instance_slot_registry,
    record_calculus_dependency,
    record_calculus_edges_from_ancestry,
    record_calculus_edges_from_value_structure,
    record_read_of_node,
    record_structural_dependency,
    slot_of_attached_value,
    suppress_dependency_recording,
)
from .computed_slots import (
    ComputationPurpose,
    add_computed_attribute,
    computation_slots_for_purpose,
    computed_attribute,
    computed_dict,
    computed_structure,
    computed_structures,
    computed_slots,
    prune_stale_computed_dict_keys,
    removed_computed_attribute,
    serialized_slots,
)
from .reverse_relationships import (
    CONTAINERS_NODE_NAME,
    ReverseCollection,
    ReverseLink,
    bump_reverse_nodes,
    reverse_slots,
)
