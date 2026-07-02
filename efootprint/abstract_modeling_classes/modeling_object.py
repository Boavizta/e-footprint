import uuid
import weakref
from abc import ABCMeta
from copy import copy
from functools import cache, cached_property
from typing import List, Type, get_origin, get_args, TYPE_CHECKING
import os

from IPython.display import HTML

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.logger import logger
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.reactive_core import (
    CONTAINERS_NODE_NAME, collect_invalidated_slots, computed_slots, instance_slot_registry, invalidate,
    record_read_of_node)
from efootprint.utils.graph_tools import WIDTH, HEIGHT, add_unique_id_to_mynetwork
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE
from efootprint.utils.tools import get_init_signature_params
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict


@cache
def class_cached_property_names(cls: type) -> tuple:
    """Names of every functools.cached_property in the class MRO, memoized per class.

    Codebase invariant: every cached property on a ModelingObject is a flushable read-time projection
    (the lazy attribution layer) — never model state — so the wholesale flush may pop them all.
    """
    return tuple(dict.fromkeys(
        name for klass in cls.__mro__ for name, attr in vars(klass).items() if isinstance(attr, cached_property)))


def flush_cached_properties_system_wide(mod_objs: list):
    """Flat, system-wide flush of every cached property: the given objects plus every object linked to their
    systems. Runs after every ModelingUpdate and after the initial build, keeping lazy read-time projections
    (attribution memos and the like) consistent with the recomputed calculated-attribute graph."""
    objs_to_flush = list(mod_objs)
    for system in dict.fromkeys(sum([mod_obj.systems for mod_obj in mod_objs], start=[])):
        objs_to_flush += system.all_linked_objects + [system]
    for mod_obj in dict.fromkeys(objs_to_flush):
        mod_obj.flush_cached_properties()


def pull_slots_system_wide(systems: list):
    """Pull every computed slot of every object linked to the given systems (plus the systems
    themselves). This is the transitional eager set: after every update, every slot is cached, keeping
    serialization and error-surfacing behavior identical to the eager engine's."""
    objs_to_pull = []
    for system in dict.fromkeys(systems):
        objs_to_pull += [system] + system.all_linked_objects
    for mod_obj in dict.fromkeys(objs_to_pull):
        mod_obj.pull_computed_attributes()


def pull_invalidated_slots(invalidated_slots):
    """Recompute the slots a write invalidated, key-set nodes first: their sync discards the
    sub-slots of keys that left the key set, which must not be recomputed (their getters may
    legitimately no longer apply)."""
    for slot in sorted(invalidated_slots, key=lambda slot: (slot.pull_precedence, slot.name)):
        if slot.getter is not None and not slot.discarded:
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


_incomplete_edge_systems = weakref.WeakSet()


def mark_system_edges_incomplete(system):
    """Flag a system loaded with stored values: its calculus edges are rebuilt from the serialized
    ancestry but structural edges only exist once getters have run, so the first relationship change
    must void everything for the recompute to re-record the full edge set."""
    system.__dict__["_computed_edges_incomplete"] = True
    _incomplete_edge_systems.add(system)


def wipe_slots_of_incomplete_edge_systems(mod_objs: list):
    """Called by the relationship write hook: when any of the given objects belongs to a system whose
    structural edges are incomplete, void every slot of that system (once — the flag clears)."""
    if not _incomplete_edge_systems:
        return
    flagged_systems = []
    for mod_obj in mod_objs:
        if mod_obj is None:
            continue
        try:
            mod_obj_systems = list(mod_obj.systems)
        except (AttributeError, TypeError):
            # The hook fires inside container transitions: one side may be mid-construction (e.g. a
            # service whose server link is being stored) or a test double, unable to resolve its
            # systems. The other side of the transition resolves them.
            continue
        for system in mod_obj_systems:
            if isinstance(system, ModelingObject) and system.__dict__.pop("_computed_edges_incomplete", False):
                flagged_systems.append(system)
                _incomplete_edge_systems.discard(system)
    if flagged_systems:
        invalidate_slots_system_wide(flagged_systems)


def get_instance_attributes(obj, target_class):
    return {attr_name: attr_value for attr_name, attr_value in obj.__dict__.items()
            if isinstance(attr_value, target_class)}


def check_type_homogeneity_within_list_or_set(input_list_or_set):
    type_set = [type(value) for value in input_list_or_set]
    base_type = type(type_set[0])

    if not all(isinstance(item, base_type) for item in type_set):
        raise ValueError(
            f"There shouldn't be objects of different types within the same list, found {type_set}")
    else:
        return type_set.pop()


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
    def from_json_dict(cls, object_json_dict: dict, flat_obj_dict: dict, set_trigger_modeling_updates_to_true=False,
                       is_loaded_from_system_with_calculated_attributes=False, sources_dict: dict | None = None):
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        from efootprint.abstract_modeling_classes.explainable_object_base_class import explainable_object_from_json
        new_obj = cls.__new__(cls)
        new_obj.__dict__["contextual_modeling_obj_containers"] = []
        new_obj.__dict__["explainable_object_dicts_containers"] = []
        new_obj.trigger_modeling_updates = False
        explainable_object_dicts_to_create_after_objects_creation = {}
        declared_computed_slots = computed_slots(cls)
        for attr_key, attr_value in object_json_dict.items():
            if isinstance(attr_value, dict) and "label" in attr_value:
                if attr_key in declared_computed_slots and not is_loaded_from_system_with_calculated_attributes:
                    # A now-computed attribute stored by an older version (when it was an input, or a
                    # legacy placeholder): the stored value is stale by definition — the slot computes.
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

        if set_trigger_modeling_updates_to_true:
            new_obj.trigger_modeling_updates = True

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
        self.__dict__["_under_construction"] = True
        self.trigger_modeling_updates = False
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

    def check_input_value_type_positivity_and_unit(self, name, input_value):
        init_sig_params = get_init_signature_params(type(self))
        if name in init_sig_params:
            annotation = init_sig_params[name].annotation
            if get_origin(annotation):
                if get_origin(annotation) in (list, List):
                    inner_type = get_args(annotation)[0]
                    if not all(isinstance(item, inner_type) for item in input_value):
                        raise TypeError(f"All elements in '{name}' must be instances of {inner_type.__name__}, "
                                         f"got {[type(item) for item in input_value]}")
            elif not isinstance(input_value, annotation) and not isinstance(input_value, EmptyExplainableObject):
                raise TypeError(f"In {self.name}, attribute {name} should be of type {annotation} "
                                      f"but is of type {type(input_value)}")
            elif issubclass(annotation, ExplainableQuantity):
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

    def flush_cached_properties(self):
        """Pop every materialized cached property (auto-discovered from the class MRO) so the next read
        recomputes from the fresh calculated-attribute graph."""
        for cached_property_name in class_cached_property_names(type(self)):
            self.__dict__.pop(cached_property_name, None)

    @cached_property
    def render_cache(self) -> dict:
        """Scratch store for lazy, query-time memos (e.g. the attribution layer's atom lists and fold
        results). Being itself a cached property, it is wiped wholesale by flush_cached_properties and is
        never serialized."""
        return {}

    def after_init(self):
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        self.__dict__["_under_construction"] = False
        self.trigger_modeling_updates = True
        for attr_name, attr_value in self.__dict__.items():
            if (isinstance(attr_value, ExplainableObjectDict)
                    and attr_name not in self.calculated_attributes):
                attr_value.trigger_modeling_updates = True

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
        return ["name", "id", "trigger_modeling_updates", "contextual_modeling_obj_containers",
                "explainable_object_dicts_containers"] + list(class_cached_property_names(type(self)))

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name in self.attributes_that_shouldnt_trigger_update_logic:
            super().__setattr__(name, input_value)
            return
        declared_computed_slots = computed_slots(type(self))
        if name in declared_computed_slots:
            if not self.__dict__.get("_under_construction", False):
                # Computed storage lives in the reactive slot, never in the instance dict. Direct
                # assignment attaches a cached value without computing (the manual pinning path).
                declared_computed_slots[name].attach_cached_value(self, input_value)
            # Constructor-time writes are dropped: they are legacy dummy values for attributes a
            # subclass computes (e.g. a parent constructor storing a zero the subclass derives from
            # other inputs); the slot computes the real value on pull. The load path attaches stored
            # values through the descriptor directly, never through __setattr__.
            return
        if not self.trigger_modeling_updates:
            current_attr = getattr(self, name, None)
            if check_input_validity:
                self.check_input_value_type_positivity_and_unit(name, input_value)
                self.check_belonging_to_authorized_values(name, input_value, self.attributes_with_depending_values())
            value_to_set = input_value
            if isinstance(value_to_set, ModelingObject):
                from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
                    ContextualModelingObjectAttribute
                # The container is set below through set_modeling_obj_container so the reverse-node
                # bump of the container-field transition fires.
                value_to_set = ContextualModelingObjectAttribute(value_to_set)
            elif type(value_to_set) == list:
                from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
                value_to_set = ListLinkedToModelingObj(value_to_set)
            elif type(value_to_set) == dict:
                value_to_set = current_attr.__class__(value_to_set)
            assert isinstance(value_to_set, ObjectLinkedToModelingObjBase) or value_to_set is None, \
                    f"input {name} of value {value_to_set} should be an ObjectLinkedToModelingObjBase or None but is of type {type(value_to_set)}"
            if isinstance(current_attr, ObjectLinkedToModelingObjBase):
                current_attr.set_modeling_obj_container(None, None)
            if isinstance(value_to_set, ObjectLinkedToModelingObjBase):
                value_to_set.set_modeling_obj_container(self, name)
            # attribute setting must be done after setting modeling_obj_container because if system has been loaded
            # with calculated attributes from json, the calculation graph must be loaded before the attribute setting.
            super().__setattr__(name, value_to_set)
        else:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            logger.debug(f"Updating {name} in {self.name}")
            ModelingUpdate([[getattr(self, name, None), input_value]])

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

        # Capture the systems the neighbours belong to before unlinking makes them unreachable.
        systems = list(dict.fromkeys(sum([mod_obj.systems for mod_obj in self.mod_obj_attributes], start=[])))

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

        if self.trigger_modeling_updates and systems:
            pull_slots_system_wide(systems)
            pull_invalidated_slots(invalidated_slots)
            flush_cached_properties_system_wide(systems)

        del self

    def to_json(self, save_calculated_attributes=False) -> dict:
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
                output_dict[key] = value.to_json(save_calculated_attributes)
            else:
                raise ValueError(f"Attribute {key} of {self.name} {type(value)}) is not handled in to_json")

        if save_calculated_attributes:
            for attr_name in self.calculated_attributes:
                output_dict[attr_name] = getattr(self, attr_name).to_json(save_calculated_attributes)

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
