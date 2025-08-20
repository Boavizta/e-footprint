from typing import TYPE_CHECKING

from pint import Unit, Quantity
import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, Source)
from efootprint.constants.units import u, get_unit
from efootprint.logger import logger

if TYPE_CHECKING:
    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
    from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


@ExplainableObject.register_subclass(lambda d: "recurring_values" in d and "unit" in d)
class ExplainableRecurringQuantities(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        value = Quantity(np.array(d["recurring_values"], dtype=np.float32), get_unit(d["unit"]))

        return cls(value, label=d["label"], source=source)

    def __init__(
            self, value: Quantity | dict, label: str = None,
            left_parent: ExplainableObject = None, right_parent: ExplainableObject = None, operator: str = None,
            source: Source = None):
        from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
        self._ExplainableQuantity = ExplainableQuantity
        self._EmptyExplainableObject = EmptyExplainableObject
        if isinstance(value, Quantity):
            if value.magnitude.dtype != np.float32:
                logger.info(
                    f"converting value {label} to float32. This is surprising, a casting to np.float32 is probably "
                    f"missing somewhere.")
                value = value.magnitude.astype(np.float32, copy=False) * value.units
            super().__init__(value, label, left_parent, right_parent, operator, source)
        else:
            raise ValueError(
                f"ExplainableRecurringQuantities values must be Pint Quantities of numpy arrays, got {type(value)}"
            )

    def to(self, unit_to_convert_to: Unit):
        self.value = self.value.to(unit_to_convert_to)

        return self

    def generate_explainable_object_with_logical_dependency(self, explainable_condition: "ExplainableObject"):
        return self.__class__(
            value=self.value, label=self.label, left_parent=self,
            right_parent=explainable_condition, operator="logically dependent on")

    def __round__(self, round_level):
        return ExplainableRecurringQuantities(
            np.round(self.value, round_level).astype(np.float32, copy=False), label=self.label,
            left_parent=self, operator=f"rounded to {round_level} decimals", source=self.source
        )

    def round(self, round_level):
        self.value = np.round(self.value, round_level).astype(np.float32, copy=False)

        return self

    @property
    def unit(self):
        return self.value.units

    @property
    def magnitude(self):
        return self.value.magnitude

    @property
    def value_as_float_list(self):
        return self.magnitude.tolist()

    def copy(self):
        return ExplainableRecurringQuantities(
            self.value.copy(), label=self.label, left_parent=self, operator="duplicate")

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {
                "recurring_values": self.magnitude,
                "unit": str(self.unit),
            }

        output_dict.update(super().to_json(with_calculated_attributes_data))

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        def _round_series_values(input_series: np.array):
            return [str(round(hourly_value.magnitude, 2)) for hourly_value in input_series]

        compact_unit = "{:~}".format(self.unit)
        if self.unit == u.dimensionless:
            compact_unit = "dimensionless"

        nb_of_values = len(self.value)
        if nb_of_values < 30:
            rounded_values = _round_series_values(self.value)
            str_rounded_values = "[" + ", ".join(rounded_values) + "]"
        else:
            first_vals = _round_series_values(self.value[:10])
            last_vals = _round_series_values(self.value[-10:])
            str_rounded_values = "first 10 vals [" + ", ".join(first_vals) \
                                 + "],\n    last 10 vals [" + ", ".join(last_vals) + "]"

        return f"{nb_of_values} values in {compact_unit}:\n    {str_rounded_values}"
