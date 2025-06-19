import math
import numbers
import base64
from copy import copy
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytz
from pint import Unit, Quantity
import numpy as np
import zstandard as zstd
import ciso8601

from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, Source)
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.constants.units import u, get_unit
from efootprint.logger import logger
from efootprint.utils.plot_baseline_and_simulation_data import plot_baseline_and_simulation_data, prepare_data

if TYPE_CHECKING:
    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
    from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


def align_temporally_quantity_arrays(
        first_quantity: Quantity, first_start_date: datetime, second_quantity: Quantity, second_start_date: datetime):
    if first_quantity.units != second_quantity.units:
        second_quantity = second_quantity.to(first_quantity.units)

    first_quantity_array = first_quantity.magnitude.astype(np.float32)
    second_quantity_array = second_quantity.magnitude.astype(np.float32)

    # Align by start_date
    end1 = first_start_date + timedelta(hours=len(first_quantity_array))
    end2 = second_start_date + timedelta(hours=len(second_quantity_array))

    # Compute common start and end
    common_start = min(first_start_date, second_start_date)
    common_end = max(end1, end2)
    total_len = int((common_end - common_start).total_seconds() // 3600)

    # Create aligned zero arrays
    aligned_first_array = np.zeros(total_len, dtype=np.float32)
    aligned_second_array = np.zeros(total_len, dtype=np.float32)

    # Compute insertion positions
    offset_first_quantity = int((first_start_date - common_start).total_seconds() // 3600)
    offset_second_quantity = int((second_start_date - common_start).total_seconds() // 3600)

    aligned_first_array[offset_first_quantity:offset_first_quantity + len(first_quantity_array)] = first_quantity_array
    aligned_second_array[offset_second_quantity:offset_second_quantity + len(second_quantity_array)] = (
        second_quantity_array)

    return aligned_first_array, aligned_second_array, common_start


@ExplainableObject.register_subclass(lambda d: ("values" in d or "compressed_values" in d) and "unit" in d)
class ExplainableHourlyQuantities(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        if "values" in d:
            value = Quantity(np.array(d["values"], dtype=np.float32), get_unit(d["unit"]))
        elif "compressed_values" in d:
            # start_date and timezone are included to facilitate json dumping if object doesn’t rehydrate
            value = {k: d[k] for k in ["compressed_values", "unit", "start_date", "timezone"]}
        else:
            raise ValueError("Invalid hourly quantity format")
        start_date = ciso8601.parse_datetime(d["start_date"])
        if d.get("timezone", None) is not None:
            start_date = pytz.timezone(d["timezone"]).localize(start_date)

        return cls(value, start_date=start_date, label=d["label"], source=source)

    def __init__(
            self, value: Quantity | dict, start_date: datetime, label: str = None,
            left_parent: ExplainableObject = None, right_parent: ExplainableObject = None, operator: str = None,
            source: Source = None):
        from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
        self._ExplainableQuantity = ExplainableQuantity
        self._EmptyExplainableObject = EmptyExplainableObject
        self.start_date = start_date
        self.json_compressed_value_data = None
        if isinstance(value, Quantity):
            if value.magnitude.dtype != np.float32:
                logger.info(
                    f"converting value {label} to float32. This is surprising, a casting to np.float32 is proably "
                    f"missing somewhere.")
                value = value.magnitude.astype(np.float32, copy=False) * value.units
            super().__init__(value, label, left_parent, right_parent, operator, source)
        elif isinstance(value, dict):
            self.json_compressed_value_data = value
            super().__init__(None, label, left_parent, right_parent, operator, source)
        else:
            raise ValueError(
                f"ExplainableHourlyQuantities values must be Pint Quantities of numpy arrays or dict, got {type(value)}"
            )

    @property
    def value(self):
        if self._value is None and self.json_compressed_value_data is not None:
            decompressed_values = self.decompress_values(self.json_compressed_value_data["compressed_values"])
            self._value = Quantity(decompressed_values, get_unit(self.json_compressed_value_data["unit"]))

        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.json_compressed_value_data = None

    @value.deleter
    def value(self):
        self._value = None
        self.json_compressed_value_data = None

    def to(self, unit_to_convert_to: Unit):
        self.value = self.value.to(unit_to_convert_to)

        return self

    def generate_explainable_object_with_logical_dependency(self, explainable_condition: "ExplainableObject"):
        return self.__class__(
            value=self.value, start_date=self.start_date, label=self.label, left_parent=self,
            right_parent=explainable_condition, operator="logically dependent on")

    def __round__(self, round_level):
        return ExplainableHourlyQuantities(
            np.round(self.value, round_level).astype(np.float32, copy=False), start_date=self.start_date, label=self.label,
            left_parent=self, operator=f"rounded to {round_level} decimals", source=self.source
        )

    def round(self, round_level):
        self.value = np.round(self.value, round_level).astype(np.float32, copy=False)

        return self

    def return_shifted_hourly_quantities(self, shift_duration: "ExplainableQuantity"):
        shift_hours = math.floor(shift_duration.to(u.hour).magnitude)

        return ExplainableHourlyQuantities(
            copy(self.value),  # Use copy to avoid modifying the original value
            start_date=self.start_date + timedelta(hours=shift_hours),
            label=f"{self.label} shifted by {shift_hours}h" if self.label else None,
            left_parent=self,
            right_parent=shift_duration,
            operator="shifted by"
        )

    @property
    def unit(self):
        return self.value.units

    @property
    def magnitude(self):
        return self.value.magnitude

    @property
    def value_as_float_list(self):
        return self.magnitude.tolist()

    def convert_to_utc(self, local_timezone: ExplainableTimezone):
        if self.start_date.tzinfo is None:
            localized_dt = local_timezone.value.localize(self.start_date)
        else:
            localized_dt = self.start_date

        return ExplainableHourlyQuantities(
            self.value, start_date=localized_dt.astimezone(pytz.utc),
            left_parent=self, right_parent=local_timezone, operator="converted to UTC from")

    def sum(self):
        return self._ExplainableQuantity(np.sum(self.value, dtype=np.float32), left_parent=self, operator="sum")

    def mean(self):
        return self._ExplainableQuantity(np.mean(self.value, dtype=np.float32), left_parent=self, operator="mean")

    def max(self):
        return self._ExplainableQuantity(np.max(self.value), left_parent=self, operator="max")

    def min(self):
        return self._ExplainableQuantity(np.min(self.value), left_parent=self, operator="min")

    def abs(self):
        return ExplainableHourlyQuantities(
            np.abs(self.value), start_date=self.start_date, left_parent=self, operator="abs")

    def ceil(self):
        return ExplainableHourlyQuantities(
            np.ceil(self.value), start_date=self.start_date, left_parent=self, operator="ceil")

    def __neg__(self):
        return ExplainableHourlyQuantities(-self.value, start_date=self.start_date, left_parent=self, operator="negate")

    def np_compared_with(self, compared_object, comparator):
        if isinstance(compared_object, self._EmptyExplainableObject):
            compared_values = np.full(len(self.value), fill_value=np.float32(0))
            right_parent = compared_object
        elif isinstance(compared_object, ExplainableHourlyQuantities):
            compared_values = compared_object.value
            right_parent = compared_object
            assert self.start_date == compared_object.start_date, \
                f"Cannot compare ExplainableHourlyQuantities with different start dates: " \
                f"{self.start_date} and {compared_object.start_date}"
        else:
            raise ValueError(f"Can only compare ExplainableHourlyQuantities with ExplainableHourlyQuantities or "
                             f"EmptyExplainableObjects, not {type(compared_object)}")

        if comparator == "max":
            result_comparison_np = np.maximum(self.value, compared_values)
        elif comparator == "min":
            result_comparison_np = np.minimum(self.value, compared_values)
        else:
            raise ValueError(f"Comparator {comparator} not implemented in np_compared_with method")

        return ExplainableHourlyQuantities(
            Quantity(result_comparison_np, self.unit),
            start_date=self.start_date,
            label=f"{self.label} compared with {compared_object.label}",
            left_parent=self,
            right_parent=right_parent,
            operator=f"{comparator} compared with"
        )

    def copy(self):
        return ExplainableHourlyQuantities(
            self.value.copy(), copy(self.start_date), label=self.label, left_parent=self, operator="duplicate")

    def __eq__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return False
        elif isinstance(other, self._EmptyExplainableObject):
            return False
        if isinstance(other, ExplainableHourlyQuantities):
            aligned_first_array, aligned_second_array, common_start = align_temporally_quantity_arrays(
                self.value, self.start_date, other.value, other.start_date)

            return np.allclose(aligned_first_array, aligned_second_array, rtol=1e-06, atol=1e-06)

        return False

    def __len__(self):
        return len(self.value)

    def __add__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableHourlyQuantities(
                self.value, start_date=self.start_date, label=self.label,
                left_parent=self, operator=""
            )
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableHourlyQuantities(
                self.value, start_date=self.start_date, label=self.label,
                left_parent=self, right_parent=other, operator="+"
            )
        elif isinstance(other, ExplainableHourlyQuantities):
            aligned_self, aligned_other, common_start = align_temporally_quantity_arrays(
                self.value, self.start_date, other.value, other.start_date)
            result_array = aligned_self + aligned_other

            return ExplainableHourlyQuantities(
                Quantity(result_array, self.unit), start_date=common_start, label=None,
                left_parent=self, right_parent=other, operator="+")
        else:
            raise ValueError(f"Can only add another ExplainableHourlyQuantities or scalar 0, not {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableHourlyQuantities(
                self.value, start_date=self.start_date, label=self.label,
                left_parent=self, operator=""
            )
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableHourlyQuantities(
                self.value, start_date=self.start_date, label=self.label,
                left_parent=self, right_parent=other, operator="-"
            )
        elif isinstance(other, ExplainableHourlyQuantities):
            aligned_self, aligned_other, common_start = align_temporally_quantity_arrays(
                self.value, self.start_date, other.value, other.start_date)
            result_array = aligned_self - aligned_other

            return ExplainableHourlyQuantities(
                Quantity(result_array, self.unit), start_date=common_start, label=None,
                left_parent=self, right_parent=other, operator="-")
        else:
            raise ValueError(f"Can only subtract another ExplainableHourlyQuantities or scalar 0, not {type(other)}")

    def __rsub__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            return other.__sub__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableHourlyUsage, not with {type(other)}")

    def __mul__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return 0
        elif isinstance(other, self._EmptyExplainableObject):
            return self._EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        elif isinstance(other, self._ExplainableQuantity):
            other_magnitude_to_multiply = other.magnitude
            if not isinstance(other_magnitude_to_multiply, np.float32):
                other_magnitude_to_multiply = np.float32(other_magnitude_to_multiply)
            result_magnitude = self.value.magnitude * other_magnitude_to_multiply
            result_quantity = Quantity(result_magnitude, self.unit * other.value.units)
            return ExplainableHourlyQuantities(
                result_quantity, self.start_date, "", self, other, "*")
        elif isinstance(other, ExplainableHourlyQuantities):
            aligned_self, aligned_other, common_start = align_temporally_quantity_arrays(
                self.value, self.start_date, other.value, other.start_date)
            result_array = aligned_self * aligned_other

            return ExplainableHourlyQuantities(
                Quantity(result_array, self.unit), start_date=common_start, label=None,
                left_parent=self, right_parent=other, operator="*")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity, "
                f"not with {type(other)}")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            raise NotImplementedError
        elif isinstance(other, self._ExplainableQuantity):
            other_value_to_divide = other.value
            if not isinstance(other_value_to_divide.magnitude, np.float32):
                other_value_to_divide = np.float32(other_value_to_divide.magnitude) * other_value_to_divide.units
            return ExplainableHourlyQuantities(self.value / other_value_to_divide, self.start_date,"", self, other, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity, "
                f"not with {type(other)}")

    def __rtruediv__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            raise NotImplementedError
        elif isinstance(other, self._ExplainableQuantity):
            other_value_to_divide = other.value
            if not isinstance(other_value_to_divide.magnitude, np.float32):
                other_value_to_divide = np.float32(other_value_to_divide.magnitude) * other_value_to_divide.units
            return ExplainableHourlyQuantities(other_value_to_divide / self.value, self.start_date,"", other, self, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity,"
                f" not with {type(other)}")

    @staticmethod
    def compress_values(values: np.ndarray) -> str:
        if values.dtype != np.float32:
            values = values.astype(np.float32, copy=False)
        cctx = zstd.ZstdCompressor(level=0)
        compressed = cctx.compress(values.tobytes())
        return base64.b64encode(compressed).decode("utf-8")

    @staticmethod
    def decompress_values(compressed_str: str) -> np.ndarray:
        compressed = base64.b64decode(compressed_str)
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        return np.frombuffer(decompressed, dtype=np.float32)

    def to_json(self, with_calculated_attributes_data=False):
        if self.json_compressed_value_data is not None:
            output_dict = self.json_compressed_value_data
        else:
            output_dict = {
                    "compressed_values": self.compress_values(self.magnitude),
                    "unit": str(self.unit),
                    "start_date": self.start_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": str(self.start_date.tzinfo) if self.start_date.tzinfo is not None else None,
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

        return f"{nb_of_values} values from {self.start_date} " \
               f"to {self.start_date + timedelta(hours=len(self.value))} in {compact_unit}:\n    {str_rounded_values}"

    def plot(self, figsize=(10, 4), filepath=None, plt_show=False, xlims=None, cumsum=False):
        import matplotlib.pyplot as plt

        if self.baseline_twin is None and self.simulation_twin is None:
            baseline_q = self.value
            baseline_start = self.start_date
            simulated_q = None
        elif self.baseline_twin is not None and self.simulation_twin is None:
            baseline_q = self.baseline_twin.value
            baseline_start = self.baseline_twin.start_date
            simulated_q = self.value
            simulated_start = self.start_date
        elif self.simulation_twin is not None and self.baseline_twin is None:
            baseline_q = self.value
            baseline_start = self.start_date
            simulated_q = self.simulation_twin.value
            simulated_start = self.simulation_twin.start_date
        else:
            raise ValueError("Both baseline and simulation twins are not None, this should not happen")

        time_baseline, baseline_q = prepare_data(baseline_q, baseline_start, cumsum)

        if simulated_q is not None:
            if isinstance(simulated_q, self._EmptyExplainableObject):
                sim_len = len(baseline_q.magnitude)
                simulated_q = Quantity(np.zeros(sim_len), baseline_q.units)
                simulated_start = self.simulation.simulation_date

            time_sim, simulated_q = prepare_data(simulated_q, simulated_start, cumsum)

            # Align simulation start offset with baseline in cumsum mode
            if cumsum:
                baseline_interp_index = np.where(time_baseline == time_sim[0])[0]
                if baseline_interp_index.size > 0:
                    simulated_q += baseline_q[baseline_interp_index[0]]
        else:
            time_sim = None

        # Plotting
        fig, ax = plot_baseline_and_simulation_data(baseline_q, time_baseline, simulated_q, time_sim, figsize, xlims)

        if self.label:
            title = self.label if not cumsum else "Cumulative " + self.label[0].lower() + self.label[1:]
            ax.set_title(title)
        if xlims is not None:
            ax.set_xlim(xlims)

        fig.autofmt_xdate()
        if filepath:
            plt.savefig(filepath, bbox_inches='tight')
        if plt_show:
            plt.show()
