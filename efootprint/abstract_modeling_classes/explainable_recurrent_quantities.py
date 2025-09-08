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
    from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
    from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone


@ExplainableObject.register_subclass(lambda d: "recurring_values" in d and "unit" in d)
class ExplainableRecurrentQuantities(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        value = Quantity(np.array(eval(d["recurring_values"]), dtype=np.float32), get_unit(d["unit"]))

        return cls(value, label=d["label"], source=source)

    def __init__(
            self, value: Quantity, label: str = None,
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
                f"ExplainableRecurrentQuantities values must be Pint Quantities of numpy arrays, got {type(value)}"
            )

    def __eq__(self, other):
        if isinstance(other, ExplainableRecurrentQuantities):
            return np.allclose(self.value, other.value, rtol=1e-06, atol=1e-06)
        return False

    def __add__(self, other):
        if isinstance(other, (int, float)) and other == 0:
            return ExplainableRecurrentQuantities(self.value, label=self.label, left_parent=self, operator="")
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableRecurrentQuantities(
                self.value, label=self.label, left_parent=self, right_parent=other, operator="+")
        elif isinstance(other, ExplainableRecurrentQuantities):
            if len(self.value) != len(other.value):
                raise ValueError(f"Cannot add ExplainableRecurrentQuantities with different lengths: "
                                 f"{len(self.value)} vs {len(other.value)}")
            return ExplainableRecurrentQuantities(
                self.value + other.value, label=None, left_parent=self, right_parent=other, operator="+")
        elif isinstance(other, self._ExplainableQuantity):
            return ExplainableRecurrentQuantities(
                self.value + other.value, label=None, left_parent=self, right_parent=other, operator="+")
        else:
            raise ValueError(f"Can only add another ExplainableRecurrentQuantities, ExplainableQuantity, scalar 0, "
                             f"or EmptyExplainableObject, not {type(other)}")

    def to(self, unit_to_convert_to: Unit):
        self.value = self.value.to(unit_to_convert_to)

        return self

    def generate_explainable_object_with_logical_dependency(self, explainable_condition: "ExplainableObject"):
        return self.__class__(
            value=self.value, label=self.label, left_parent=self,
            right_parent=explainable_condition, operator="logically dependent on")

    def __round__(self, round_level):
        return ExplainableRecurrentQuantities(
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
        return ExplainableRecurrentQuantities(
            self.value.copy(), label=self.label, left_parent=self, operator="duplicate")

    def generate_hourly_quantities_over_timespan(
            self, timespan_hourly_quantities: "ExplainableHourlyQuantities", 
            local_timezone: "ExplainableTimezone"):
        """
        Generate an ExplainableHourlyQuantities over the timespan of the input ExplainableHourlyQuantities.
        
        The recurring values represent a canonical local timezone week (7 * 24 = 168 values).
        The timespan_hourly_quantities start_date is expressed in the local timezone but its start_date is not timezone aware.
        The method aligns the canonical week pattern with the local timespan and outputs in UTC.
        
        Args:
            timespan_hourly_quantities: ExplainableHourlyQuantities that defines the timespan and start date (local timezone)
            local_timezone: ExplainableTimezone that defines the local timezone
            
        Returns:
            ExplainableHourlyQuantities with values generated from the recurring pattern (UTC)
        """
        from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities

        # Validate canonical week length
        if len(self.value) != 168:
            raise ValueError(
                f"ExplainableRecurrentQuantities must have exactly 168 values (7*24 hours), got {len(self.value)}"
            )

        if timespan_hourly_quantities.start_date.tzinfo is None:
            start_date_local = local_timezone.value.localize(timespan_hourly_quantities.start_date)
        else:
            start_date_local = timespan_hourly_quantities.start_date.astimezone(local_timezone.value)
        timespan_length = len(timespan_hourly_quantities.value)
        start_offset_in_local_week = start_date_local.weekday() * 24 + start_date_local.hour

        # Vectorized index mapping into canonical local week (168 hours)
        indices = (start_offset_in_local_week + np.arange(timespan_length)) % 168

        # Vectorized extraction of values
        week_values = self.value.magnitude  # is numpy array
        output_values = np.take(week_values, indices)

        result_quantity = Quantity(output_values.astype(np.float32), self.unit)

        local_timezone_expanded = ExplainableHourlyQuantities(
            result_quantity,
            start_date=start_date_local,
            left_parent=self,
            right_parent=timespan_hourly_quantities,
            operator="expanded over timespan",
        )

        return local_timezone_expanded.convert_to_utc(local_timezone).set_label(
            f"{self.label} expanded over {timespan_hourly_quantities.label} timespan (UTC)" if self.label else None,
        )

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {
                "recurring_values": str(self.magnitude.tolist()),
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
