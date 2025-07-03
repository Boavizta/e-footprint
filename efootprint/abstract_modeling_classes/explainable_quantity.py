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
        value = {key: d[key] for key in ["value", "unit"]}
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        return cls(value, label=d["label"], source=source)

    def __init__(
            self, value: Quantity | dict, label: str = None, left_parent: ExplainableObject = None,
            right_parent: ExplainableObject = None, operator: str = None, source: Source = None):
        from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
        self._ExplainableHourlyQuantities = ExplainableHourlyQuantities
        self._EmptyExplainableObject = EmptyExplainableObject
        self.json_value_data = None
        if isinstance(value, Quantity):
            if not isinstance(value.magnitude, float):
                value = float(value.magnitude) * value.units
            super().__init__(value, label, left_parent, right_parent, operator, source)
        elif isinstance(value, dict):
            self.json_value_data = value
            super().__init__(None, label, left_parent, right_parent, operator, source)
        else:
            raise ValueError(f"Variable 'value' of type {type(value)} isn’t a Quantity or a dict")

    @property
    def value(self):
        if self._value is None and self.json_value_data is not None:
            self._value = Quantity(
                float(self.json_value_data["value"]), get_unit(self.json_value_data["unit"]))

        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.json_value_data = None

    @value.deleter
    def value(self):
        self._value = None
        self.json_value_data = None

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
            converted_other_value = other.value.to(self.value.units)
            return np.allclose(
                np.asarray(self.magnitude), np.asarray(converted_other_value.magnitude), rtol=1e-4, atol=1e-6)
        elif isinstance(other, self._EmptyExplainableObject):
            return self.value == 0

        return False

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
        if self.json_value_data is not None:
            output_dict = self.json_value_data
        else:
            output_dict = {"value": float(self.value.magnitude), "unit": str(self.value.units)}

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
        return ExplainableQuantity(copy(self.value), label=copy(self.label), source=copy(self.source))
