from typing import List
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


def set_modeling_obj_containers(efootprint_obj: ModelingObject, mod_obj_containers_to_set: List):
    mock_contextual_containers = []
    for mod_obj_container in mod_obj_containers_to_set:
        mock_contextual_container = MagicMock()
        mock_contextual_container.modeling_obj_container = mod_obj_container
        mock_contextual_containers.append(mock_contextual_container)

    efootprint_obj.contextual_modeling_obj_containers = mock_contextual_containers
