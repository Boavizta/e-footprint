from typing import List, TYPE_CHECKING, Optional

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.usage.edge_process import EdgeProcess
from efootprint.core.hardware.edge_device import EdgeDevice

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.system import System


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(6 * u.year, Sources.HYPOTHESIS)
    }

    def __init__(self, name: str, edge_processes: List[EdgeProcess], edge_device: EdgeDevice,
                 usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_processes = edge_processes
        self.edge_device = edge_device
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

    @property
    def edge_usage_pattern(self) -> Optional["EdgeUsagePattern"]:
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"EdgeUsageJourney object can only be associated with one EdgeUsagePattern object but {self.name} "
                    f"is associated with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def systems(self) -> List["System"]:
        return self.edge_usage_pattern.systems

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[EdgeProcess]:
        if self.edge_usage_pattern:
            return [self.edge_usage_pattern]
        return self.edge_processes
