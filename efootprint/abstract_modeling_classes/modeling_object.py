import uuid
from abc import ABCMeta
from copy import copy
from types import UnionType
from typing import Annotated, Any, ForwardRef, List, Literal, Type, Union, get_origin, get_args, TYPE_CHECKING
import os

from IPython.display import HTML

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.logger import logger
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.reactive_core import (
    CONTAINERS_NODE_NAME, collect_invalidated_slots, computed_attribute, computed_slots, instance_slot_registry,
    computed_structure, computed_structures, invalidate, prune_stale_computed_dict_keys, record_read_of_node,
    serialized_slots)
from efootprint.utils.graph_tools import WIDTH, HEIGHT, add_unique_id_to_mynetwork
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE
from efootprint.utils.tools import get_init_signature_params, get_init_type_hints
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict


_CONSTRUCTING = object()
_HYDRATING = object()
_LIVE = object()


def pull_slots_system_wide(systems: list):
    """Explicitly materialize every computed slot of every object linked to the given systems."""
    objs_to_pull = []
    for system in dict.fromkeys(systems):
        objs_to_pull += [system] + system.all_linked_objects
    for mod_obj in dict.fromkeys(objs_to_pull):
        mod_obj.pull_computed_attributes()


def pull_guard_slots(invalidated_slots):
    """Recompute the validation slots a write invalidated: guard slots exist to reject invalid
    states, so they must run at update time even though nothing downstream reads them."""
    guard_slots = [slot for slot in invalidated_slots if slot.guard and slot.getter is not None]
    for slot in sorted(guard_slots, key=lambda slot: slot.name):
        slot.pull()


def invalidate_slots_system_wide(systems: list):
    """Void every slot of every object linked to the given systems. Used when a model whose values
    were attached at load time (dependency edges only partially rebuilt) receives a relationship
    change: the full recompute that follows re-records every edge."""
    slots = []
    for system in dict.fromkeys(systems):
        for mod_obj in dict.fromkeys([system] + system.all_linked_objects):
            slots += list(instance_slot_registry(mod_obj).values())
    invalidate(*slots)


def get_instance_attributes(obj, target_class):
    return {attr_name: attr_value for attr_name, attr_value in obj.__dict__.items()
            if isinstance(attr_value, target_class)}


def get_canonical_class_for_cls(modeling_object_class: type) -> type:
    from efootprint.all_classes_in_order import CANONICAL_CLASSES

    for canonical_class in CANONICAL_CLASSES:
        if issubclass(modeling_object_class, canonical_class):
            return canonical_class
    return modeling_object_class


class AfterInitMeta(type):
    def __call__(cls, *args, **kwargs):
        instance = super(AfterInitMeta, cls).__call__(*args, **kwargs)
        instance.after_init()
        instance._mark_live()

        return instance

    @property
    def canonical_class(cls):
        return get_canonical_class_for_cls(cls)


class ABCAfterInitMeta(AfterInitMeta, ABCMeta):
    def __instancecheck__(cls, instance):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute
        # Allow an instance of ContextualModelingObjectAttribute to be considered as an instance of ModelingObject
        if isinstance(instance, ContextualModelingObjectAttribute):
            return AfterInitMeta.__instancecheck__(cls, instance._value)

        return AfterInitMeta.__instancecheck__(cls, instance)


class ModelingObject(metaclass=ABCAfterInitMeta):
    classes_outside_init_params_needed_for_generating_from_json = []
    _use_name_as_id: bool = False

    @classmethod
    def from_json_dict(cls, object_json_dict: dict, flat_obj_dict: dict, attach_stored_computed_values=True,
                       sources_dict: dict | None = None):
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        from efootprint.abstract_modeling_classes.explainable_object_base_class import explainable_object_from_json
        new_obj = cls.__new__(cls)
        new_obj.__dict__["_lifecycle_state"] = _HYDRATING
        new_obj.__dict__["contextual_modeling_obj_containers"] = []
        new_obj.__dict__["explainable_object_dicts_containers"] = []
        explainable_object_dicts_to_create_after_objects_creation = {}
        declared_computed_slots = computed_slots(cls)
        declared_computed_structures = computed_structures(cls)
        for attr_key, attr_value in object_json_dict.items():
            if attr_key in declared_computed_structures:
                # Serialize-flagged computed structures hold raw JSON-native values (list rows like the
                # impact-repartition matrix, plain dicts like the edge-device breakdown summary),
                # attached as-is when trusted. Checked before the generic dict branches: a dict-valued
                # structure is neither an explainable value nor a deferred input ExplainableObjectDict.
                if attach_stored_computed_values:
                    declared_computed_structures[attr_key].attach_cached_value(
                        new_obj, tuple(attr_value) if isinstance(attr_value, list) else attr_value)
            elif isinstance(attr_value, dict) and "label" in attr_value:
                if attr_key in declared_computed_slots and not attach_stored_computed_values:
                    # Values computed by another library version are not trusted as caches: the
                    # loader demotes them to a comparison baseline and the slot recomputes on read.
                    continue
                new_value = explainable_object_from_json(attr_value, sources_dict)
                if attr_key in declared_computed_slots:
                    declared_computed_slots[attr_key].attach_cached_value(new_obj, new_value)
                else:
                    new_obj.__setattr__(attr_key, new_value, check_input_validity=False)
                # Calculus graph data is added after setting as new_obj attribute to not interfere
                # with set_modeling_obj_container logic
                new_value.initialize_calculus_graph_data_from_json(attr_value, flat_obj_dict, sources_dict)
            elif isinstance(attr_value, dict) and "label" not in attr_value:
                explainable_object_dicts_to_create_after_objects_creation[(new_obj, attr_key)] = attr_value
            elif isinstance(attr_value, str) and attr_key not in ("id", "name") and attr_value in flat_obj_dict:
                # A scalar string attribute is treated as a reference when it matches an existing object id.
                # `name` is always a plain label, never a reference: excluding it prevents an object whose name
                # equals another object's id (e.g. a second "France" country alongside the catalog one keyed
                # "France") from having its name silently resolved into that object.
                new_obj.__setattr__(attr_key, flat_obj_dict[attr_value], check_input_validity=False)
            elif isinstance(attr_value, list):
                new_obj.__setattr__(
                    attr_key, [flat_obj_dict[elt] for elt in attr_value], check_input_validity=False)
            else:
                new_obj.__setattr__(attr_key, attr_value)

        # Initialize input ExplainableObjectDicts that were deferred to empty, so they exist before after_init
        for (obj, attr_key) in list(explainable_object_dicts_to_create_after_objects_creation.keys()):
            if obj is new_obj and attr_key not in new_obj.calculated_attributes:
                if getattr(new_obj, attr_key, None) is None:
                    new_obj.__setattr__(attr_key, ExplainableObjectDict(), check_input_validity=False)

        return new_obj, explainable_object_dicts_to_create_after_objects_creation

    default_values = {}

    # Static labels for weighted dict relationship attributes, keyed by attr name. Single source of truth
    # for the wording consumers (e.g. the web interface) must use when building weight entries themselves.
    weight_labels = {}

    list_values =  {}

    conditional_list_values =  {}

    @classmethod
    def attributes_with_depending_values(cls):
        output_dict = {}
        for dependent_attribute, dependent_attribute_dependencies in cls.conditional_list_values.items():
            if dependent_attribute not in output_dict:
                output_dict[dependent_attribute_dependencies["depends_on"]] = [dependent_attribute]
            else:
                output_dict[dependent_attribute_dependencies["depends_on"]].append(dependent_attribute)

        return output_dict

    @classmethod
    def from_defaults(cls, name, **kwargs):
        from copy import deepcopy
        output_kwargs = deepcopy(cls.default_values)
        output_kwargs.update(kwargs)

        return cls(name, **output_kwargs)

    def copy_with(self, name: str | None = None, **overrides):
        """
        Create a new instance of this class by reusing the current initialization inputs.

        Args:
            name: Optional name for the copy. Defaults to "<current name> copy".
            **overrides: Replacement values for constructor arguments. Inputs whose annotations are
                ModelingObjects or Lists must always be provided explicitly.

        Returns:
            A new ModelingObject instance.
        """
        overrides = dict(overrides)
        init_params = get_init_signature_params(type(self))
        allowed_kwargs = {param for param in init_params if param not in ("self", "name")}
        unexpected_kwargs = set(overrides) - allowed_kwargs
        if unexpected_kwargs:
            raise TypeError(
                f"Unexpected overrides for {type(self).__name__}.copy_with: {sorted(unexpected_kwargs)}")

        constructor_kwargs = {}

        for param_name, param in init_params.items():
            if param_name in ("self", "name"):
                continue

            if param_name in overrides:
                value = overrides.pop(param_name)
            else:
                if hasattr(self, param_name):
                    value = getattr(self, param_name)
                elif param.default is not param.empty:
                    value = param.default
                else:
                    raise AttributeError(
                        f"{type(self).__name__}.{param_name} is missing on {self.name} and no override was provided.")

                if self._value_requires_manual_override(value):
                    annotation_str = getattr(param.annotation, "__name__", str(param.annotation))
                    raise ValueError(
                        f"{type(self).__name__}.copy_with requires explicit '{param_name}' because it is annotated "
                        f"as {annotation_str}.")

            constructor_kwargs[param_name] = self._prepare_value_for_copy(value)

        if overrides:
            raise TypeError(
                f"Some overrides could not be consumed when copying {type(self).__name__}: {sorted(overrides.keys())}")

        new_name = name or f"{self.name} copy"
        return type(self)(new_name, **constructor_kwargs)

    @staticmethod
    def _prepare_value_for_copy(value):
        if isinstance(value, ObjectLinkedToModelingObjBase):
            return copy(value)

        return value

    @staticmethod
    def _value_requires_manual_override(value):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

        if isinstance(value, list):
            return True

        if isinstance(value, ExplainableObjectDict):
            return True

        if isinstance(value, ContextualModelingObjectAttribute):
            return True

        return isinstance(value, ModelingObject)

    @classmethod
    def archetypes(cls):
        return []

    @classmethod
    def attributes_that_can_have_negative_values(cls):
        return []

    def __init__(self, name):
        self.__dict__["_lifecycle_state"] = _CONSTRUCTING
        self.name = name
        self.id = css_escape(name) if ModelingObject._use_name_as_id else str(uuid.uuid4())[:12]
        self.contextual_modeling_obj_containers = []
        self.explainable_object_dicts_containers = []

    @property
    def readable_id(self):
        return f"id-{self.id}-{css_escape(self.name)}"

    @property
    def efootprint_class(self):
        return type(self)

    @staticmethod
    def _unwrap_contextual_input_value(input_value):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute

        return input_value._value if isinstance(input_value, ContextualModelingObjectAttribute) else input_value

    @classmethod
    def _input_value_matches_annotation(cls, input_value, annotation):
        input_value = cls._unwrap_contextual_input_value(input_value)
        if annotation is Any:
            return True
        if isinstance(annotation, (str, ForwardRef)):
            raise TypeError(f"Unresolved input annotation {annotation!r}")

        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin in (Union, UnionType):
            return any(cls._input_value_matches_annotation(input_value, option) for option in args)
        if origin is Annotated:
            return cls._input_value_matches_annotation(input_value, args[0])
        if origin is Literal:
            return input_value in args
        if origin in (list, List):
            return isinstance(input_value, list) and (not args or all(
                cls._input_value_matches_annotation(item, args[0]) for item in input_value
            ))
        if origin is dict:
            return isinstance(input_value, dict) and (not args or all(
                cls._input_value_matches_annotation(key, args[0])
                and cls._input_value_matches_annotation(value, args[1])
                for key, value in input_value.items()
            ))
        if isinstance(origin, type) and issubclass(origin, dict):
            if not isinstance(input_value, dict):
                return False
            from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
            if issubclass(origin, ExplainableObjectDict):
                return (not isinstance(input_value, ExplainableObjectDict) or isinstance(input_value, origin)) and (
                    not args or all(cls._input_value_matches_annotation(key, args[0]) for key in input_value)
                )
            if len(args) == 2:
                return all(
                    cls._input_value_matches_annotation(key, args[0])
                    and cls._input_value_matches_annotation(value, args[1])
                    for key, value in input_value.items()
                )
            return True
        if origin is not None:
            if not isinstance(origin, type):
                raise TypeError(f"Unsupported input annotation {annotation!r}")
            return isinstance(input_value, origin)
        if not isinstance(annotation, type):
            raise TypeError(f"Unsupported input annotation {annotation!r}")
        if issubclass(annotation, dict):
            return isinstance(input_value, dict)
        return isinstance(input_value, annotation)

    @classmethod
    def _replacement_matches_annotation(cls, input_value, annotation, replaced_value):
        if replaced_value is None:
            return cls._input_value_matches_annotation(input_value, annotation)

        if replaced_value.dict_container is not None:
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin in (Union, UnionType):
                return any(cls._replacement_matches_annotation(input_value, option, replaced_value) for option in args)
            from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
            dict_class = origin if isinstance(origin, type) else annotation
            if isinstance(dict_class, type) and issubclass(dict_class, ExplainableObjectDict):
                from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
                return cls._input_value_matches_annotation(input_value, ExplainableObject)
            if origin is dict and len(args) == 2:
                return cls._input_value_matches_annotation(input_value, args[1])
            return False

        if replaced_value.list_container is not None:
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin in (Union, UnionType):
                return any(cls._replacement_matches_annotation(input_value, option, replaced_value) for option in args)
            if origin in (list, List) and args:
                return cls._input_value_matches_annotation(input_value, args[0])
            return False

        return cls._input_value_matches_annotation(input_value, annotation)

    def check_input_value_type_positivity_and_unit(self, name, input_value, replaced_value=None):
        init_sig_params = get_init_signature_params(type(self))
        if name in init_sig_params:
            annotation = get_init_type_hints(type(self)).get(name)
            if annotation is None:
                raise TypeError(f"{type(self).__name__}.__init__ input '{name}' has no resolvable type annotation")
            if (not isinstance(input_value, EmptyExplainableObject)
                    and not self._replacement_matches_annotation(input_value, annotation, replaced_value)):
                origin = get_origin(annotation)
                args = get_args(annotation)
                if origin in (list, List) and args and isinstance(input_value, list):
                    expected_name = getattr(args[0], "__name__", str(args[0]))
                    raise TypeError(f"All elements in '{name}' must be instances of {expected_name}, "
                                    f"got {[type(item) for item in input_value]}")
                raise TypeError(f"In {self.name}, attribute {name} should be of type {annotation} "
                                f"but is of type {type(self._unwrap_contextual_input_value(input_value))}")
            if isinstance(annotation, type) and issubclass(annotation, ExplainableQuantity):
                default_value = self.default_values[name]
                if (not isinstance(input_value, EmptyExplainableObject)
                        and input_value.value.dimensionality != default_value.value.dimensionality):
                    raise ValueError(
                        f"Value {input_value} for attribute {name} is not homogeneous to "
                        f"{default_value.value.units} ({default_value.value.dimensionality})")
                if input_value.magnitude < 0 and name not in self.attributes_that_can_have_negative_values():
                    raise ValueError(
                        f"Value {input_value} for attribute {name} should be positive but is negative")

    def check_belonging_to_authorized_values(self, name, input_value, attributes_with_depending_values):
        if name in self.list_values:
            if input_value not in self.list_values[name]:
                raise ValueError(
                    f"Value {input_value} for attribute {name} is not in the list of possible values: "
                    f"{[elt.value for elt in self.list_values[name]]}")

        if name in self.conditional_list_values:
            conditional_attr_name = self.conditional_list_values[name]['depends_on']
            # depends_on may be a dotted path (e.g. "external_api.model_name") to reach an attribute on a related object
            conditional_value = self
            for part in conditional_attr_name.split("."):
                conditional_value = getattr(conditional_value, part, None)
                if conditional_value is None:
                    break
            if conditional_value is None:
                raise ValueError(f"Value for attribute {conditional_attr_name} is not set but required for checking "
                                 f"validity of {name}")
            if (conditional_value in self.conditional_list_values[name]["conditional_list_values"]
                    and input_value not in
                    self.conditional_list_values[name]["conditional_list_values"][conditional_value]):
                raise ValueError(
                    f"Value {input_value} for attribute {name} is not in the list of possible values for "
                    f"{conditional_attr_name} {conditional_value}: "
                    f"{self.conditional_list_values[name]['conditional_list_values'][conditional_value]}")

        if name in attributes_with_depending_values:
            for dependent_attribute in attributes_with_depending_values[name]:
                dependent_attribute_value = getattr(self, dependent_attribute, None)
                if (dependent_attribute_value is not None
                        and input_value
                        in self.conditional_list_values[dependent_attribute]["conditional_list_values"]
                        and dependent_attribute_value not in
                        self.conditional_list_values[dependent_attribute]["conditional_list_values"][input_value]):
                    raise ValueError(
                        f"Setting {name} as {input_value} is not possible because {dependent_attribute_value}"
                        f" is not in the list of possible values for {dependent_attribute} "
                        f"when {name} is {input_value}."
                        f"\nYou might want to use the ModelingUpdate object to be able to change both inputs "
                        f"at the same time."
                        f"\nList of possible values for {input_value}:"
                        f"\n{self.conditional_list_values[dependent_attribute]['conditional_list_values'][input_value]}"
                    )

    @property
    def modeling_obj_containers(self):
        record_read_of_node(self, CONTAINERS_NODE_NAME)
        return list(dict.fromkeys(
            [contextual_mod_obj_container.modeling_obj_container
             for contextual_mod_obj_container in self.contextual_modeling_obj_containers
             if contextual_mod_obj_container.modeling_obj_container is not None]))

    @classmethod
    def is_subclass_of(cls, base_class_name: str) -> bool:
        """Check if this class inherits from base_class_name or any of its subclasses.

        Args:
            base_class_name: The name of the base class to check against

        Returns:
            True if this object's class or any of its parent classes has the given name
        """
        for parent_cls in cls.__mro__:
            if parent_cls.__name__ == base_class_name:
                return True
        return False

    def add_to_contextual_modeling_obj_containers(self, contextual_mod_obj_container):
        self.contextual_modeling_obj_containers.append(contextual_mod_obj_container)

    def is_structural_input_dict_attribute(self, attr_name: str, attr_value=None) -> bool:
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

        if attr_name in self.calculated_attributes:
            return False

        init_sig_params = get_init_signature_params(type(self))
        if attr_name not in init_sig_params:
            return False

        if attr_value is None:
            attr_value = getattr(self, attr_name, None)

        return isinstance(attr_value, ExplainableObjectDict)

    @property
    def calculated_attributes(self) -> List[str]:
        """Names of this object's computed attributes, from the class computed-slot registry."""
        return list(computed_slots(type(self)))

    @property
    def validation_attributes(self) -> List[str]:
        return [attr for attr in self.calculated_attributes if attr.endswith("_validation")]

    @property
    def calculated_attributes_without_validations(self) -> List[str]:
        return [attr for attr in self.calculated_attributes if not attr.endswith("_validation")]

    @property
    def systems(self) -> List:
        return list(dict.fromkeys(sum([mod_obj.systems for mod_obj in self.modeling_obj_containers], start=[])))

    def pull_computed_attributes(self):
        """Read every computed attribute, computing and caching any void slot (whole-dict reads pull
        their per-key sub-slots too)."""
        for attr_name in self.calculated_attributes:
            getattr(self, attr_name)

    def pull_guard_attributes(self):
        """Materialize every declared guard on this object, without warming ordinary outputs."""
        for attr_name, descriptor in computed_slots(type(self)).items():
            if descriptor.guard:
                getattr(self, attr_name)

    def after_init(self):
        """Run subclass construction hooks before the metaclass makes the instance live."""

    @property
    def _is_live(self):
        return self.__dict__.get("_lifecycle_state") is _LIVE

    def _mark_live(self):
        """Finish construction or hydration exactly once; live instances cannot return to passive mode."""
        lifecycle_state = self.__dict__.get("_lifecycle_state")
        if lifecycle_state is _LIVE:
            return
        if lifecycle_state not in (_CONSTRUCTING, _HYDRATING):
            raise RuntimeError(f"Cannot make an uninitialized {type(self).__name__} live.")
        self.__dict__["_lifecycle_state"] = _LIVE

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute

        if isinstance(other, ContextualModelingObjectAttribute):
            return self.id == other._value.id
        elif isinstance(other, ModelingObject):
            return self.id == other.id

        return False

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return ["name", "id", "contextual_modeling_obj_containers",
                "explainable_object_dicts_containers"]

    def _set_input_passively(self, name, input_value, check_input_validity=True):
        """Attach one framework-owned input without starting a transaction.

        Construction, hydration, and focused test pinning use this boundary. Ordinary writes to a
        live object always go through ``ModelingUpdate``.
        """
        if isinstance(getattr(type(self), name, None), (computed_attribute, computed_structure)):
            raise AttributeError(f"{name} is a computed attribute and cannot be attached as an input.")
        current_attr = getattr(self, name, None)
        if check_input_validity:
            self.check_input_value_type_positivity_and_unit(name, input_value)
            self.check_belonging_to_authorized_values(name, input_value, self.attributes_with_depending_values())
        value_to_set = input_value
        if isinstance(value_to_set, ModelingObject):
            from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
                ContextualModelingObjectAttribute
            value_to_set = ContextualModelingObjectAttribute(value_to_set)
        elif type(value_to_set) == list:
            from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
            value_to_set = ListLinkedToModelingObj(value_to_set)
        elif type(value_to_set) == dict:
            value_to_set = current_attr.__class__(value_to_set)
        assert isinstance(value_to_set, ObjectLinkedToModelingObjBase) or value_to_set is None, (
            f"input {name} of value {value_to_set} should be an ObjectLinkedToModelingObjBase or None but is of "
            f"type {type(value_to_set)}")
        if isinstance(current_attr, ObjectLinkedToModelingObjBase):
            current_attr.set_modeling_obj_container(None, None)
        if isinstance(value_to_set, ObjectLinkedToModelingObjBase):
            value_to_set.set_modeling_obj_container(self, name)
        super().__setattr__(name, value_to_set)
        return value_to_set

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name in self.attributes_that_shouldnt_trigger_update_logic:
            super().__setattr__(name, input_value)
            return
        computed_descriptor = getattr(type(self), name, None)
        if isinstance(computed_descriptor, (computed_attribute, computed_structure)):
            facade_binding = getattr(input_value, "__dict__", {}).get("_computed_facade_of")
            if facade_binding is not None and facade_binding[0] is self and facade_binding[1] is computed_descriptor:
                return
            # Computed values only enter their slot by computation or by the descriptor's explicit
            # attach_cached_value (the load path and the test pinning path): a plain assignment would
            # either silently vanish or leave dependents cached against the unpinned value.
            raise AttributeError(
                f"{name} is a computed attribute of {type(self).__name__} and cannot be assigned: change the "
                f"inputs it derives from instead. Tests can pin a value with tests.utils.patch_attribute / "
                f"attach_attribute or the descriptor's attach_cached_value.")
        if not self._is_live:
            self._set_input_passively(name, input_value, check_input_validity=check_input_validity)
        else:
            current_attr = getattr(self, name, None)
            if input_value is current_attr:
                return
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            logger.debug(f"Updating {name} in {self.name}")
            ModelingUpdate([[current_attr, input_value]])

    @property
    def contextual_mod_obj_attributes(self) -> List["ContextualModelingObjectAttribute"]:
        """The ContextualModelingObjectAttributes this object owns, directly or inside a list.

        These are the links self_delete severs one by one. Dict-held children are absent by design: an
        ExplainableObjectDict owns its keys’ backward links and severs them all at once when unlinked.
        """
        from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
        output_list = list(get_instance_attributes(self, ModelingObject).values())
        for attr_value in get_instance_attributes(self, ListLinkedToModelingObj).values():
            output_list += list(attr_value)

        return output_list

    @property
    def mod_obj_attributes(self) -> List["ModelingObject"]:
        """Every ModelingObject this object references: direct attributes, list items and structural dict keys.

        Structural dict keys (a UsageJourneyStep’s jobs, a UsageJourney’s uj_steps) are the ModelingObjects
        themselves rather than their ContextualModelingObjectDictKeys, so that consumers walking the object
        graph see one object per child. Calculated dicts keyed by modeling objects (e.g. a Job’s
        hourly_occurrences_per_usage_pattern) are results, not references, and are left out.
        """
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        output_list = self.contextual_mod_obj_attributes
        for attr_value in get_instance_attributes(self, ExplainableObjectDict).values():
            if attr_value.is_structural_input_dict:
                output_list += [key for key in attr_value if isinstance(key, ModelingObject)]

        return output_list

    def object_relationship_graph_to_file(
            self, filename=None, classes_to_ignore=USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE, width=WIDTH, height=HEIGHT,
            notebook=False):
        object_relationships_graph = build_object_relationships_graph(
            self, classes_to_ignore=classes_to_ignore, width=width, height=height, notebook=notebook)

        if filename is None:
            filename = os.path.join(".", f"{self.name} object relationship graph.html")
        object_relationships_graph.show(filename, notebook=notebook)

        add_unique_id_to_mynetwork(filename)

        if notebook:
            return HTML(filename)

    def self_delete(self):
        logger.warning(
            f"Deleting {self.name}, removing backward links pointing to it in "
            f"{','.join([mod_obj.name for mod_obj in self.mod_obj_attributes])}")
        if self.modeling_obj_containers:
            raise PermissionError(
                f"You can’t delete {self.name} because "
                f"{','.join([mod_obj.name for mod_obj in self.modeling_obj_containers])} have it as attribute.")

        # Drop this object's computed values so ancestor children links and container bookkeeping on
        # surviving objects don't accumulate dead values.
        for slot in list(instance_slot_registry(self).values()):
            slot._drop_value()
        for facade in self.__dict__.get("_computed_dict_facades", {}).values():
            facade.set_modeling_obj_container(None, None)

        # The unlinks below bump the reverse nodes of every object this one points to, invalidating
        # their dependent slots.
        with collect_invalidated_slots() as invalidated_slots:
            for contextual_attr in self.contextual_mod_obj_attributes:
                contextual_attr.set_modeling_obj_container(None, None)
            # ObjectLinkedToModelingObjBase also covers ExplainableObjectDicts, whose unlinking removes the
            # backward links their keys hold to self (e.g. a deleted UsageJourneyStep's jobs).
            for attr_value in get_instance_attributes(self, ObjectLinkedToModelingObjBase).values():
                    attr_value.set_modeling_obj_container(None, None)

        if self._is_live:
            prune_stale_computed_dict_keys(invalidated_slots)
            pull_guard_slots(invalidated_slots)

        del self

    def to_json(self, save_computed_state=True) -> dict:
        output_dict = {}

        for key, value in self.__dict__.items():
            if key in ["name", "id", "short_name", "impact_url"]:
                output_dict[key] = value
            if key.startswith("_") or key in self.attributes_that_shouldnt_trigger_update_logic:
                continue
            elif value is None or isinstance(value, str):
                output_dict[key] = value
            elif isinstance(value, ModelingObject):
                output_dict[key] = value.id
            elif getattr(value, "to_json", None) is not None:
                output_dict[key] = value.to_json()
            else:
                raise ValueError(f"Attribute {key} of {self.name} {type(value)}) is not handled in to_json")

        if save_computed_state:
            # Serialize-flagged slots persist their cached value (peek, never pull: saving a model
            # must not compute it — a void flagged slot is simply absent and recomputes on read).
            # Explainable values carry their formula; raw computed structures (e.g. the impact-repartition
            # matrix rows) must be JSON-native.
            for attr_name, descriptor in serialized_slots(type(self)).items():
                value = descriptor.peek(self)
                if value is None:
                    continue
                if getattr(value, "to_json", None) is not None:
                    output_dict[attr_name] = value.to_json(with_formula=True)
                elif isinstance(value, dict):
                    output_dict[attr_name] = value
                else:
                    output_dict[attr_name] = list(value)

        return output_dict

    @property
    def class_as_simple_str(self):
        return type(self).__name__

    @property
    def canonical_class(self):
        return type(self).canonical_class

    def __repr__(self):
        return str(self)

    def __str__(self):
        output_str = ""

        def key_value_to_str(input_key, input_value):
            key_value_str = ""

            if type(input_value) in (str, int) or input_value is None:
                key_value_str = f"{input_key}: {input_value}\n"
            elif isinstance(input_value, list):
                if len(input_value) == 0:
                    key_value_str = f"{input_key}: {input_value}\n"
                else:
                    if type(input_value[0]) == str:
                        key_value_str = f"{input_key}: {input_value}"
                    elif isinstance(input_value[0], ModelingObject):
                        str_value = "[" + ", ".join([elt.id for elt in input_value]) + "]"
                        key_value_str = f"{input_key}: {str_value}\n"
            elif isinstance(input_value, ModelingObject):
                key_value_str = f"{input_key}: {input_value.id}\n"
            elif isinstance(input_value, ObjectLinkedToModelingObjBase):
                key_value_str = f"{input_key}: {input_value}\n"

            return key_value_str

        output_str += f"{self.class_as_simple_str} {self.id}\n \nname: {self.name}\n"

        for key, attr_value in self.__dict__.items():
            if key.startswith("_") or key in self.attributes_that_shouldnt_trigger_update_logic:
                continue
            output_str += key_value_to_str(key, attr_value)

        declared_computed_slots = computed_slots(type(self))
        if len(declared_computed_slots) > 0:
            output_str += " \ncalculated_attributes:\n"
            for key, descriptor in declared_computed_slots.items():
                # peek, never pull: printing an object must not trigger computations.
                output_str += "  " + key_value_to_str(key, descriptor.peek(self))

        return output_str

    @property
    def attribute_update_entanglements(self):
        # Used to generate new changes that depend on a change in certain attributes
        # Used in RecurrentEdgeProcess class for generating entanglements so that whenever device is updated,
        # component needs are updated too.
        return {}

    @property
    def nb_of_occurrences_per_container(self) -> dict["ModelingObject", ExplainableQuantity]:
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

        record_read_of_node(self, CONTAINERS_NODE_NAME)
        output_dict = {}
        for contextual_mod_obj_container in self.contextual_modeling_obj_containers:
            if contextual_mod_obj_container.modeling_obj_container is None:
                continue
            if contextual_mod_obj_container.modeling_obj_container not in output_dict:
                output_dict[contextual_mod_obj_container.modeling_obj_container] = 1
            else:
                output_dict[contextual_mod_obj_container.modeling_obj_container] += 1

        return ExplainableObjectDict({key: ExplainableQuantity(
            value * u.dimensionless, label=f"Number of occurrences of {self.name} in {key.name}")
            for key, value in output_dict.items()})
