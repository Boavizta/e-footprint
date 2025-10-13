from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.hardware.edge_computer import EdgeComputer

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, edge_processes: List[RecurrentEdgeProcess], edge_computer: EdgeComputer,
                 usage_span: ExplainableQuantity):
        super().__init__(name)
        self.assert_usage_span_is_inferior_to_edge_computer_lifespan(usage_span, edge_computer)
        self.edge_processes = edge_processes
        self.edge_computer = edge_computer
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

    @staticmethod
    def assert_usage_span_is_inferior_to_edge_computer_lifespan(usage_span: ExplainableQuantity, edge_computer: EdgeComputer):
        if usage_span > edge_computer.lifespan:
            raise InsufficientCapacityError(edge_computer, "lifespan", edge_computer.lifespan, usage_span)

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[RecurrentEdgeProcess]:
        if self.edge_usage_patterns:
            return self.edge_usage_patterns
        return self.edge_processes + [self.edge_computer]

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "usage_span":
            self.assert_usage_span_is_inferior_to_edge_computer_lifespan(input_value, self.edge_computer)
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)
