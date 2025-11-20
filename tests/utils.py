from typing import List
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.system import System


def set_modeling_obj_containers(efootprint_obj: ModelingObject, mod_obj_containers_to_set: List):
    mock_contextual_containers = []
    for mod_obj_container in mod_obj_containers_to_set:
        mock_contextual_container = MagicMock()
        mock_contextual_container.modeling_obj_container = mod_obj_container
        mock_contextual_containers.append(mock_contextual_container)

    efootprint_obj.contextual_modeling_obj_containers = mock_contextual_containers

def get_canonical_class_index(obj: ModelingObject):
    from efootprint.all_classes_in_order import CANONICAL_COMPUTATION_ORDER
    index = 0
    for efootprint_class in CANONICAL_COMPUTATION_ORDER:
        if isinstance(obj, efootprint_class):
            return index
        index += 1
    raise ValueError(f"Class of object {obj} not found in CANONICAL_COMPUTATION_ORDER.")

def check_all_calculus_graph_dependencies_consistencies(system: System):
    for obj in system.all_linked_objects:
        # Exclude hidden component classes
        if obj.class_as_simple_str in [
            "EdgeComputerRAMComponent", "EdgeComputerCPUComponent", "EdgeApplianceComponent"]:
            continue
        for attr in obj.calculated_attributes:
            calculated_attr_value = getattr(obj, attr)
            if isinstance(calculated_attr_value, dict):
                calculated_attr_value = list(calculated_attr_value.values())[0]
            obj_canonical_index = get_canonical_class_index(obj)
            for ancestor in calculated_attr_value.direct_ancestors_with_id:
                ancestor_obj = ancestor.modeling_obj_container
                ancestor_canonical_index = get_canonical_class_index(ancestor_obj)
                if ancestor_canonical_index > obj_canonical_index:
                    raise ValueError(
                        f"Inconsistent calculus graph dependency found: object {obj.name} of class "
                        f"{obj.class_as_simple_str} (canonical index {obj_canonical_index}) has a calculated "
                        f"attribute '{attr}' depending on ancestor object {ancestor_obj.name} of class "
                        f"{ancestor_obj.class_as_simple_str} (canonical index {ancestor_canonical_index})."
                    )
