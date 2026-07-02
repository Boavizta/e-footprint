from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class HardwareBase(ModelingObject):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    param_descriptions = {
        "carbon_footprint_fabrication": (
            "Embodied carbon emitted to manufacture one unit of the hardware. Amortised over the lifespan "
            "when computing the hourly fabrication footprint."),
        "power": (
            "Electrical power drawn by one fully-loaded unit, before applying any datacenter overhead."),
        "lifespan": (
            "Expected time before the hardware is replaced. Embodied carbon is amortised over this duration."),
        "fraction_of_usage_time": (
            "Fraction of the modeling period during which the hardware is in active use."),
    }

    # carbon_footprint_fabrication and power are None (and not stored) for subclasses that compute
    # them from other inputs (e.g. Storage, the Boavizta and GPU server builders) — assigning a
    # computed name raises.
    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity = None,
                 power: ExplainableQuantity = None, lifespan: ExplainableQuantity = None,
                 fraction_of_usage_time: ExplainableQuantity = None):
        super().__init__(name)
        if carbon_footprint_fabrication is not None:
            self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
                f"Carbon footprint fabrication")
        if power is not None:
            self.power = power.set_label(f"Power")
        self.lifespan = lifespan.set_label(f"Lifespan")
        self.fraction_of_usage_time = fraction_of_usage_time.set_label("Fraction of usage time")



class InsufficientCapacityError(Exception):
    def __init__(
            self, overloaded_object: HardwareBase, capacity_type: str,
            available_capacity: ExplainableQuantity|EmptyExplainableObject,
            requested_capacity: ExplainableQuantity|EmptyExplainableObject):
        self.overloaded_object = overloaded_object
        self.capacity_type = capacity_type
        self.available_capacity = available_capacity
        self.requested_capacity = requested_capacity

        message = (f"{self.overloaded_object.name} has available {capacity_type} capacity of "
                   f"{available_capacity.value} but is asked for {requested_capacity.value}")
        super().__init__(message)
