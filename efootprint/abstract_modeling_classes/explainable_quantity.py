import numbers
from copy import copy

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.constants.units import get_unit


@ExplainableObject.register_subclass(lambda d: "value" in d and "unit" in d)
class ExplainableQuantity(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        value = Quantity(d["value"], get_unit(d["unit"]))
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        return cls(value, label=d["label"], source=source)

    def __init__(
            self, value: Quantity, label: str = None, left_parent: ExplainableObject = None,
            right_parent: ExplainableObject = None, operator: str = None, source: Source = None):
        from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
        self._ExplainableHourlyQuantities = ExplainableHourlyQuantities
        self._EmptyExplainableObject = EmptyExplainableObject
        if not isinstance(value, Quantity):
            raise ValueError(
                f"Variable 'value' of type {type(value)} does not correspond to the appropriate 'Quantity' type, "
                "it is indeed mandatory to define a unit"
            )
        super().__init__(value, label, left_parent, right_parent, operator, source)

    def to(self, unit_to_convert_to):
        self.value = self.value.to(unit_to_convert_to)

        return self

    @property
    def magnitude(self):
        return self.value.magnitude

    def compare_with_and_return_max(self, other):
        if isinstance(other, ExplainableQuantity):
            if self.value >= other.value:
                return ExplainableQuantity(self.value, left_parent=self, right_parent=other, operator="max")
            else:
                return ExplainableQuantity(other.value, left_parent=self, right_parent=other, operator="max")
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def ceil(self):
        self.value = np.ceil(self.value)
        return self

    def copy(self):
        return ExplainableQuantity(copy(self.value), label=self.label, left_parent=self, operator="duplicate")

    def __gt__(self, other):
        if isinstance(other, ExplainableQuantity):
            return self.value > other.value
        elif isinstance(other, self._EmptyExplainableObject):
            return self.value > 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __lt__(self, other):
        if isinstance(other, ExplainableQuantity):
            return self.value < other.value
        elif isinstance(other, self._EmptyExplainableObject):
            return self.value < 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __eq__(self, other):
        if isinstance(other, ExplainableQuantity):
            return self.value == other.value
        elif isinstance(other, self._EmptyExplainableObject):
            return self.value == 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __add__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            # summing with sum() adds an implicit 0 as starting value
            return ExplainableQuantity(self.value, left_parent=self, operator="")
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableQuantity(self.value, left_parent=self, right_parent=other, operator="+")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value + other.value, "", self, other, "+")
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __sub__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableQuantity(self.value, left_parent=self, operator="")
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableQuantity(self.value, left_parent=self, right_parent=other, operator="-")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value - other.value, "", self, other, "-")
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __mul__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return 0
        elif isinstance(other, self._EmptyExplainableObject):
            return self._EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value * other.value, "", self, other, "*")
        elif isinstance(other, self._ExplainableHourlyQuantities):
            return other.__mul__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __truediv__(self, other):
        if isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value / other.value, "", self, other, "/")
        elif isinstance(other, self._ExplainableHourlyQuantities):
            return other.__rtruediv__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        if isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(other.value - self.value, "", other, self, "-")
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __rtruediv__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return 0
        elif isinstance(other, self._EmptyExplainableObject):
            return self._EmptyExplainableObject(left_parent=other, right_parent=self, operator="/")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(other.value / self.value, "", other, self, "/")
        elif isinstance(other, self._ExplainableHourlyQuantities):
            return other.__truediv__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __round__(self, round_level):
        return ExplainableQuantity(
            round(self.value, round_level), label=self.label, left_parent=self,
            operator=f"rounded to {round_level} decimals", source=self.source)

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {
            "value": float(self.value.magnitude), "unit": str(self.value.units)}

        output_dict.update(super().to_json(with_calculated_attributes_data))

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        if isinstance(self.value, Quantity):
            return f"{round(self.value, 2)}"
        else:
            return str(self.value)

    def __copy__(self):
        return ExplainableQuantity(
            self.value, label=self.label, source=self.source, left_parent=self, operator="duplicate")
