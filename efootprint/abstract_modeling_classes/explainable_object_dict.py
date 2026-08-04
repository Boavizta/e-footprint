from collections import Counter

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectDictKey
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.reactive_core import (
    bump_reverse_nodes, computation_in_progress, record_calculus_dependency, record_read_of_node,
    record_structural_dependency)

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


def validate_weight(key, weight):
    key_name = getattr(key, "name", key)
    if not isinstance(weight, ExplainableQuantity):
        raise ValueError(
            f"Weight for {key_name} must be an ExplainableQuantity, received {type(weight)}")
    if not weight.value.check("[]"):
        raise ValueError(f"Weight for {key_name} should be dimensionless but has units {weight.value.units}")
    if weight.value.magnitude < 0:
        raise ValueError(f"Weight for {key_name} should be non-negative but is {weight.value.magnitude}")


def to_weighted_explainable_object_dict(input_value, weight_label: str = None) -> "WeightedExplainableObjectDict":
    """Normalize constructor sugar into a WeightedExplainableObjectDict of dimensionless, non-negative weights.

    Accepts None (empty dict), a list of keys (each entry weighs 1, duplicates accumulating), or a dict whose
    values are either ExplainableQuantities (passed through) or plain numbers (wrapped as
    SourceValue(n * u.dimensionless), so they carry Sources.HYPOTHESIS provenance like any hand-declared input).
    Number wrapping happens only at this constructor boundary; the weight invariant itself is enforced by
    WeightedExplainableObjectDict.__setitem__ on every set, construction included.
    """
    from efootprint.abstract_modeling_classes.source_objects import SourceValue
    from efootprint.constants.units import u

    if input_value is None:
        items = []
    elif isinstance(input_value, list):
        items = Counter(input_value).items()
    elif isinstance(input_value, dict):
        items = input_value.items()
    else:
        raise ValueError(
            f"Weighted dict inputs must be None, a list of keys or a dict, received {type(input_value)}")

    output_dict = WeightedExplainableObjectDict()
    for key, value in items:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = SourceValue(value * u.dimensionless)
            if weight_label is not None:
                value.set_label(weight_label)
        output_dict[key] = value

    return output_dict


class ExplainableObjectDict(ObjectLinkedToModelingObjBase, dict):
    """Dict that can be linked to a ModelingObject. Uses ObjectLinkedToModelingObjBase (not slotted).

    Doubles as the live facade of a computed dict attribute: reads pull the per-key sub-slots (and the
    key-set node for whole-dict reads) so the view is always fresh, and writes route through the slot
    attach path. Input dicts keep their trigger-based update flow."""

    def __init__(self, input_dict=None):
        super().__init__()
        self.trigger_modeling_updates = False
        if input_dict is not None:
            for key, value in input_dict.items():
                self._set_entry_passively(key, value)

    def _computed_binding(self):
        """(owner, descriptor) when this dict is the facade of a computed dict attribute, else None."""
        return self.__dict__.get("_computed_facade_of")

    def _record_read(self):
        binding = self._computed_binding()
        if binding is not None:
            if computation_in_progress():
                owner, descriptor = binding
                record_structural_dependency(descriptor.slot(owner))
        elif self.modeling_obj_container is not None:
            record_read_of_node(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def _sync_keys_if_computed(self):
        binding = self._computed_binding()
        if binding is not None:
            owner, descriptor = binding
            descriptor.slot(owner).pull()

    def _sync_all_if_computed(self):
        """Key-set sync plus a pull of every sub-slot: a cached key-set node says nothing about the
        freshness of individual values, whose slots are invalidated independently."""
        binding = self._computed_binding()
        if binding is not None:
            owner, descriptor = binding
            descriptor.slot(owner).pull()
            for key in list(dict.keys(self)):
                descriptor.sub_slot(owner, key).pull()

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        previous_modeling_obj_container = self.modeling_obj_container
        previous_attr_name = self.attr_name_in_mod_obj_container
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)
        for value in dict.values(self):
            value.set_modeling_obj_container(new_parent_modeling_object, attr_name)
        if new_parent_modeling_object is None:
            for key in dict.keys(self):
                self._remove_self_from_key_containers(key)
                self._remove_self_from_key_contextual_containers(
                    key, modeling_obj_container=previous_modeling_obj_container, attr_name=previous_attr_name)
        else:
            for key in dict.keys(self):
                self._add_self_to_key_containers(key)
                self._add_self_to_key_contextual_containers(key)
        # Linking or unlinking a populated relationship dict changes its keys' reverse relationships
        # (which containers hold them), exactly like a single-link container-field transition.
        if previous_modeling_obj_container is not new_parent_modeling_object:
            for key in dict.keys(self):
                if isinstance(key, ModelingObject):
                    bump_reverse_nodes(key, previous_modeling_obj_container)
                    bump_reverse_nodes(key, new_parent_modeling_object)

    @property
    def all_ancestors_with_id(self):
        all_ancestors_with_id = []

        for value in self.values():
            all_ancestor_ids = [ancestor.id for ancestor in all_ancestors_with_id]
            for ancestor in value.all_ancestors_with_id:
                if ancestor.id not in all_ancestor_ids:
                    all_ancestors_with_id.append(ancestor)

        return all_ancestors_with_id

    def update(self, __m=None, **kwargs):
        entries = []
        if __m is not None:
            entries.extend(__m.items() if hasattr(__m, 'items') else __m)
        entries.extend(kwargs.items())
        if not entries:
            return

        binding = self._computed_binding()
        if binding is not None or not self.trigger_modeling_updates:
            for key, value in entries:
                self[key] = value
            return

        new_dict = self._copy_passively()
        for key, value in entries:
            new_dict._set_entry_passively(key, value)
        from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
        ModelingUpdate([[self, new_dict]])

    def _validate_entry_value(self, key, value):
        if not isinstance(value, (ExplainableObject, EmptyExplainableObject)):
            raise ValueError(
                f"ExplainableObjectDicts only accept ExplainableObjects or EmptyExplainableObject as values, "
                f"received {type(value)}")

    def _copy_passively(self, entries=None):
        copied_dict = type(self)()
        for key, value in (dict.items(self) if entries is None else entries):
            copied_dict._set_entry_passively(key, value)
        copied_dict.trigger_modeling_updates = self.trigger_modeling_updates
        return copied_dict

    def _set_entry_passively(self, key, value):
        """Store one entry with the container bookkeeping but no engine involvement — used by the
        computed-dict slot machinery and by input-dict storage."""
        self._validate_entry_value(key, value)
        key_is_new = not dict.__contains__(self, key)
        if dict.__contains__(self, key) and self.modeling_obj_container is not None:
            previous_value = dict.__getitem__(self, key)
            if previous_value is not value:
                previous_value.set_modeling_obj_container(None, None)
        dict.__setitem__(self, key, value)
        if self.modeling_obj_container is not None:
            value.set_modeling_obj_container(
                new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)
        self._add_self_to_key_containers(key)
        self._add_self_to_key_contextual_containers(key)
        if key_is_new and self.is_structural_input_dict and isinstance(key, ModelingObject):
            bump_reverse_nodes(key, self.modeling_obj_container)

    def _drop_entry_passively(self, key):
        """Remove one entry with the container bookkeeping but no engine involvement."""
        was_structural = self.is_structural_input_dict and isinstance(key, ModelingObject)
        modeling_obj_container = self.modeling_obj_container
        if self.modeling_obj_container is not None:
            dict.__getitem__(self, key).set_modeling_obj_container(None, None)
        dict.__delitem__(self, key)
        self._remove_self_from_key_containers(key)
        self._remove_self_from_key_contextual_containers(key)
        if was_structural:
            bump_reverse_nodes(key, modeling_obj_container)

    def __setitem__(self, key, value: ExplainableObject):
        self._validate_entry_value(key, value)

        binding = self._computed_binding()
        if binding is not None:
            owner, descriptor = binding
            descriptor.attach_element_cached_value(owner, key, value)
            return

        if self.trigger_modeling_updates:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            if key in self:
                # Value update on existing key: the value node's dependents trace downstream
                ModelingUpdate([[self[key], value]])
            else:
                # Structural change: new key — full dict replacement so the key set is diffed
                new_dict = self._copy_passively()
                new_dict._set_entry_passively(key, value)
                ModelingUpdate([[self, new_dict]])
            return

        self._set_entry_passively(key, value)

    def __delitem__(self, key):
        binding = self._computed_binding()
        if binding is not None:
            owner, descriptor = binding
            from efootprint.abstract_modeling_classes.reactive_core import instance_slot_registry
            popped_slot = instance_slot_registry(owner).pop((descriptor.attr_name, key))
            popped_slot.guard = False
            self._drop_entry_passively(key)
            return

        if self.trigger_modeling_updates:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            new_dict = self._copy_passively(
                (k, v) for k, v in dict.items(self) if k != key)
            ModelingUpdate([[self, new_dict]])
            return

        self._drop_entry_passively(key)

    def __getitem__(self, key):
        binding = self._computed_binding()
        if binding is not None:
            owner, descriptor = binding
            from efootprint.abstract_modeling_classes.reactive_core import (
                instance_slot_registry, suppress_dependency_recording)
            sub_slot = instance_slot_registry(owner).get((descriptor.attr_name, key))
            if sub_slot is None:
                # No sub-slot yet: only members of the key collection may compute lazily — indexing
                # a foreign key must raise, not run the getter on it (and never insert it into the
                # facade). Membership is read without recording so the reader keeps depending on the
                # key's value only, never on the key set (a sibling key's change must not invalidate
                # it); the key collections are relationship reads, so nothing computes here.
                with suppress_dependency_recording():
                    if key not in getattr(owner, descriptor.keys):
                        raise KeyError(key)
                sub_slot = descriptor.sub_slot(owner, key)
            if computation_in_progress():
                # Indexing one key depends on that key's value, not on the key set: a sibling key's
                # change never invalidates this reader.
                record_calculus_dependency(sub_slot)
            return sub_slot.pull()
        self._record_read()
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def keys(self):
        self._record_read()
        self._sync_keys_if_computed()
        return dict.keys(self)

    def values(self):
        self._record_read()
        self._sync_all_if_computed()
        return dict.values(self)

    def items(self):
        self._record_read()
        self._sync_all_if_computed()
        return dict.items(self)

    def __iter__(self):
        self._record_read()
        self._sync_keys_if_computed()
        return dict.__iter__(self)

    def __len__(self):
        self._record_read()
        self._sync_keys_if_computed()
        return dict.__len__(self)

    def __contains__(self, key):
        self._record_read()
        self._sync_keys_if_computed()
        return dict.__contains__(self, key)

    def pop(self, key, *args):
        if key in self:
            value = self[key]
            self.__delitem__(key)
            return value
        if len(args) > 1:
            raise TypeError(f"pop expected at most 2 arguments, got {len(args) + 1}")
        if args:
            return args[0]
        raise KeyError(key)

    def popitem(self):
        if not dict.__len__(self):
            raise KeyError("popitem(): dictionary is empty")
        key = next(reversed(dict.keys(self)))
        value = dict.__getitem__(self, key)
        self.__delitem__(key)
        return key, value

    def clear(self):
        if not dict.__len__(self):
            return
        binding = self._computed_binding()
        if binding is not None:
            for key in list(dict.keys(self)):
                self.__delitem__(key)
            return
        if self.trigger_modeling_updates:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            ModelingUpdate([[self, self._copy_passively(())]])
            return
        for key in list(dict.keys(self)):
            self._drop_entry_passively(key)

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __copy__(self):
        return self._copy_passively()

    def copy(self):
        return self._copy_passively()

    def __ior__(self, other):
        self.update(other)
        return self

    def _add_self_to_key_containers(self, key):
        if (self.modeling_obj_container is not None and isinstance(key, ModelingObject)
                and id(self) not in [id(elt) for elt in key.explainable_object_dicts_containers]):
            key.explainable_object_dicts_containers.append(self)

    def _remove_self_from_key_containers(self, key):
        if not isinstance(key, ModelingObject):
            return
        key.explainable_object_dicts_containers = [elt for elt in key.explainable_object_dicts_containers
                                                   if id(elt) != id(self)]

    @property
    def is_structural_input_dict(self):
        return (
            self.modeling_obj_container is not None
            and self.modeling_obj_container.is_structural_input_dict_attribute(
                self.attr_name_in_mod_obj_container, self)
        )

    def _add_self_to_key_contextual_containers(self, key):
        if not self.is_structural_input_dict or not isinstance(key, ModelingObject):
            return
        if any(
                isinstance(container, ContextualModelingObjectDictKey)
                and container.modeling_obj_container is self.modeling_obj_container
                and container.attr_name_in_mod_obj_container == self.attr_name_in_mod_obj_container
                and container.dict_container is self
                for container in key.contextual_modeling_obj_containers
        ):
            return
        ContextualModelingObjectDictKey(key, self.modeling_obj_container, self.attr_name_in_mod_obj_container, self)

    def _remove_self_from_key_contextual_containers(self, key, modeling_obj_container=None, attr_name=None):
        if not isinstance(key, ModelingObject):
            return
        modeling_obj_container = modeling_obj_container or self.modeling_obj_container
        attr_name = attr_name or self.attr_name_in_mod_obj_container
        key.contextual_modeling_obj_containers = [
            container for container in key.contextual_modeling_obj_containers
            if not (
                isinstance(container, ContextualModelingObjectDictKey)
                and container.modeling_obj_container is modeling_obj_container
                and container.attr_name_in_mod_obj_container == attr_name
                and container.dict_container is self
            )
        ]

    def to_json(self, with_formula=False):
        output_dict = {}

        # Raw dict reads: serialization peeks the current entries and must never pull sub-slots.
        for key, value in dict.items(self):
            if isinstance(key, ModelingObject):
                output_dict[key.id] = value.to_json(with_formula)
            elif isinstance(key, str):
                output_dict[key] = value.to_json(with_formula)
            else:
                raise ValueError(f"Key {key} is not a ModelingObject or a string")

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        if len(self) == 0:
            return "{}"

        return_str = "{\n"

        for key, value in self.items():
            if isinstance(key, ModelingObject):
                return_str += f"{key.class_as_simple_str} {key.name} ({key.id}): {value}, \n"
            elif isinstance(key, str):
                return_str += f"{key}: {value}, \n"
            else:
                return_str += f"{key}: {value}, \n"

        return_str = return_str + "}"

        return return_str


class WeightedExplainableObjectDict(ExplainableObjectDict):
    """ExplainableObjectDict of dimensionless, non-negative weights. validate_weight runs on every __setitem__,
    so the invariant holds at construction and across later mutations alike."""

    def _validate_entry_value(self, key, value):
        super()._validate_entry_value(key, value)
        validate_weight(key, value)
