import math
import numbers
import base64
import array
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd
import pint_pandas
from pint import Unit
import numpy as np
import zstandard as zstd

from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, Source)
from efootprint.constants.units import u
from efootprint.utils.plot_baseline_and_simulation_dfs import plot_baseline_and_simulation_dfs

if TYPE_CHECKING:
    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity


@ExplainableObject.register_subclass(lambda d: ("values" in d or "compressed_values" in d) and "unit" in d)
class ExplainableHourlyQuantities(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        if "values" in d:
            from efootprint.builders.time_builders import create_hourly_usage_df_from_list
            df = create_hourly_usage_df_from_list(
                d["values"],
                pint_unit=u(d["unit"]),
                start_date=datetime.strptime(d["start_date"], "%Y-%m-%d %H:%M:%S"),
                timezone=d.get("timezone", None)
            )
            return cls(df, label=d["label"], source=source)
        elif "compressed_values" in d:
            subset = {k: d[k] for k in ["compressed_values", "unit", "start_date", "timezone"]}
            return cls(subset, label=d["label"], source=source)
        raise ValueError("Invalid hourly quantity format")

    def __init__(
            self, value: pd.DataFrame | dict, label: str = None, left_parent: ExplainableObject = None,
            right_parent: ExplainableObject = None, operator: str = None, source: Source = None):
        from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
        self._ExplainableQuantity = ExplainableQuantity
        self._EmptyExplainableObject = EmptyExplainableObject
        if isinstance(value, pd.DataFrame):
            if value.columns != ["value"]:
                raise ValueError(
                    f"ExplainableHourlyQuantities values must have only one column named value, "
                    f"got {value.columns}")
            if not isinstance(value.dtypes.iloc[0], pint_pandas.pint_array.PintType):
                raise ValueError(f"The pd DataFrame value of an ExplainableHourlyQuantities object must be typed with "
                                 f"Pint, got {type(value.dtypes.iloc[0])} dtype")

            super().__init__(value, label, left_parent, right_parent, operator, source)
        elif isinstance(value, dict):
            self.json_compressed_value_data = value
            super().__init__(None, label, left_parent, right_parent, operator, source)
        else:
            raise ValueError(
                f"ExplainableHourlyQuantities values must be pandas DataFrames or dict, got {type(value)}")

    @property
    def value(self):
        if self._value is None and self.json_compressed_value_data is not None:
            from efootprint.builders.time_builders import create_hourly_usage_df_from_list
            self._value = create_hourly_usage_df_from_list(
                self.decompress_values(self.json_compressed_value_data["compressed_values"]),
                pint_unit=u(self.json_compressed_value_data["unit"]),
                start_date=datetime.strptime(self.json_compressed_value_data["start_date"], "%Y-%m-%d %H:%M:%S"),
                timezone=self.json_compressed_value_data.get("timezone", None)
            )

        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value

    @value.deleter
    def value(self):
        self._value = None
        self.json_compressed_value_data = None

    def to(self, unit_to_convert_to: Unit):
        self.value["value"] = self.value["value"].pint.to(unit_to_convert_to)

        return self

    def __round__(self, round_level):
        return ExplainableHourlyQuantities(
            pd.DataFrame(
                {"value": pint_pandas.PintArray(
                    np.round(self.value["value"].values._data, round_level), dtype=self.unit)},
                index=self.value.index),
            label=self.label, left_parent=self, operator=f"rounded to {round_level} decimals", source=self.source
        )

    def round(self, round_level):
        self.value["value"] = pint_pandas.PintArray(
            np.round(self.value["value"].values._data, round_level), dtype=self.unit)

        return self

    def return_shifted_hourly_quantities(self, shift_duration: "ExplainableQuantity"):
        shift_duration_in_hours =  math.floor(shift_duration.to(u.hour).magnitude)

        return ExplainableHourlyQuantities(
            self.value.shift(shift_duration_in_hours, freq="h"), left_parent=self, right_parent=shift_duration,
            operator=f"shifted by")

    @property
    def unit(self):
        return self.value.dtypes.iloc[0].units

    @property
    def value_as_float_list(self):
        return [float(elt) for elt in self.value["value"].values._data]

    def convert_to_utc(self, local_timezone):
        utc_localized_df = self.value.tz_localize(local_timezone.value, nonexistent="shift_forward",
                                   ambiguous=np.full(len(self.value), fill_value=True)).tz_convert('UTC')
        duplicate_datetimes_due_to_dst = utc_localized_df.index.duplicated(keep=False)

        duplicates_df = utc_localized_df[duplicate_datetimes_due_to_dst]
        if not duplicates_df.empty:
            non_duplicates_df = utc_localized_df[~duplicate_datetimes_due_to_dst]
            # Sum values for duplicate indices
            fused_duplicates = duplicates_df.groupby(duplicates_df.index).sum()
            # Combine the summed duplicates with the non-duplicates
            deduplicated_localized_df = pd.concat([non_duplicates_df, fused_duplicates]).sort_index()
        else:
            deduplicated_localized_df = utc_localized_df

        return ExplainableHourlyQuantities(
            deduplicated_localized_df,
            left_parent=self, right_parent=local_timezone, operator="converted to UTC from")

    def sum(self):
        return self._ExplainableQuantity(self.value["value"].sum(), left_parent=self, operator="sum")

    def mean(self):
        return self._ExplainableQuantity(self.value["value"].mean(), left_parent=self, operator="mean")

    def max(self):
        return self._ExplainableQuantity(self.value["value"].max(), left_parent=self, operator="max")

    def abs(self):
        return ExplainableHourlyQuantities(
            pd.DataFrame(
                {"value": pint_pandas.PintArray(np.abs(self.value["value"].values.data), dtype=self.unit)},
                index=self.value.index),
            left_parent=self, operator="abs")

    def ceil(self):
        return ExplainableHourlyQuantities(
            pd.DataFrame(
                {"value": pint_pandas.PintArray(np.ceil(self.value["value"].values.data), dtype=self.unit)},
                index=self.value.index),
            left_parent=self, operator="ceil")

    def __neg__(self):
        negated_df = pd.DataFrame(
            {"value": pint_pandas.PintArray(-self.value["value"].values.data, dtype=self.unit)},
            index=self.value.index)
        return ExplainableHourlyQuantities(negated_df, left_parent=self, operator="negate")

    def np_compared_with(self, compared_object, comparator):
        if comparator not in ["max", "min"]:
            raise ValueError(f"Comparator {comparator} not implemented in np_compared_with method")

        if isinstance(compared_object, self._EmptyExplainableObject):
            compared_values = np.full(len(self.value), fill_value=0)
            right_parent = compared_object
        elif isinstance(compared_object, ExplainableHourlyQuantities):
            compared_values = compared_object.value["value"].values.data.to_numpy()
            right_parent = compared_object
        else:
            raise ValueError(f"Can only compare ExplainableHourlyQuantities with ExplainableHourlyQuantities or "
                             f"EmptyExplainableObjects, not {type(compared_object)}")

        self_values = self.value["value"].values.data.to_numpy()

        if comparator == "max":
            result_comparison_np = np.maximum(self_values, compared_values)
        elif comparator == "min":
            result_comparison_np = np.minimum(self_values, compared_values)
        result_comparison_df = pd.DataFrame(
            {"value": pint_pandas.PintArray(result_comparison_np, dtype=self.unit)},
            index=self.value.index
        )

        return ExplainableHourlyQuantities(
            result_comparison_df,
            f"{self.label} compared with {compared_object.label}",
            left_parent=self,
            right_parent=right_parent,
            operator=f"{comparator} compared with"
        )

    def copy(self):
        return ExplainableHourlyQuantities(self.value.copy(), label=self.label, left_parent=self, operator="duplicate")

    def __eq__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return False
        elif isinstance(other, self._EmptyExplainableObject):
            return False
        if isinstance(other, ExplainableHourlyQuantities):
            if len(self.value) != len(other.value):
                raise ValueError(
                    f"Can only compare ExplainableHourlyUsages with values of same length. Here we are trying to "
                    f"compare {self.value} and {other.value}.")

            return self.value.equals(other.value)
        else:
            raise ValueError(f"Can only compare with another ExplainableHourlyUsage, not {type(other)}")

    def __len__(self):
        return len(self.value)

    def __add__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            # summing with sum() adds an implicit 0 as starting value
            return ExplainableHourlyQuantities(self.value, left_parent=self, operator="")
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableHourlyQuantities(self.value, left_parent=self, right_parent=other, operator="+")
        elif isinstance(other, ExplainableHourlyQuantities):
            df_sum = self.value.add(other.value, fill_value=0 * self.unit)
            return ExplainableHourlyQuantities(df_sum, "", self, other, "+")
        else:
            raise ValueError(f"Can only make operation with another ExplainableHourlyUsage, not with {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableHourlyQuantities(self.value, left_parent=self, operator="")
        elif isinstance(other, self._EmptyExplainableObject):
            return ExplainableHourlyQuantities(self.value, left_parent=self, right_parent=other, operator="-")
        elif isinstance(other, ExplainableHourlyQuantities):
            return ExplainableHourlyQuantities(self.value - other.value, "", self, other, "-")
        else:
            raise ValueError(f"Can only make operation with another ExplainableHourlyUsage, not with {type(other)}")

    def __rsub__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            return ExplainableHourlyQuantities(other.value - self.value, "", other, self, "-")
        else:
            raise ValueError(f"Can only make operation with another ExplainableHourlyUsage, not with {type(other)}")

    def __mul__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return 0
        elif isinstance(other, self._EmptyExplainableObject):
            return self._EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        elif isinstance(other, self._ExplainableQuantity) or isinstance(other, ExplainableHourlyQuantities):
            return ExplainableHourlyQuantities(self.value.mul(other.value, fill_value=0), "", self, other, "*")
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
            return ExplainableHourlyQuantities(self.value / other.value, "", self, other, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity, "
                f"not with {type(other)}")

    def __rtruediv__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            raise NotImplementedError
        elif isinstance(other, self._ExplainableQuantity):
            return ExplainableHourlyQuantities(other.value / self.value, "", other, self, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity,"
                f" not with {type(other)}")

    @staticmethod
    def compress_values(values):
        arr = array.array("d", values)  # "d" is double-precision float
        cctx = zstd.ZstdCompressor(level=1)
        compressed = cctx.compress(arr.tobytes())
        return base64.b64encode(compressed).decode("utf-8")

    @staticmethod
    def decompress_values(compressed_str):
        """Decompress a base64-encoded, zstd-compressed array of doubles."""
        compressed = base64.b64decode(compressed_str)
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        arr = array.array("d")
        arr.frombytes(decompressed)
        return arr.tolist()

    def to_json(self, with_calculated_attributes_data=False):
        if self._value is not None:
            output_dict = {
                    "compressed_values": self.compress_values(self.value["value"].values._data.tolist()),
                    "unit": str(self.value.dtypes.iloc[0].units),
                    "start_date": self.value.index[0].strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": str(self.value.index.tz) if self.value.index.tz is not None else None,
                }
        else:
            output_dict = self.json_compressed_value_data
        output_dict.update(super().to_json(with_calculated_attributes_data))

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        def _round_series_values(input_series):
            return [str(round(hourly_value.magnitude, 2)) for hourly_value in input_series.tolist()]

        compact_unit = "{:~}".format(self.unit)
        if self.unit == u.dimensionless:
            compact_unit = "dimensionless"

        nb_of_values = len(self.value)
        if nb_of_values < 30:
            rounded_values = _round_series_values(self.value["value"])
            str_rounded_values = "[" + ", ".join(rounded_values) + "]"
        else:
            first_vals = _round_series_values(self.value["value"].iloc[:10])
            last_vals = _round_series_values(self.value["value"].iloc[-10:])
            str_rounded_values = "first 10 vals [" + ", ".join(first_vals) \
                                 + "],\n    last 10 vals [" + ", ".join(last_vals) + "]"

        return f"{nb_of_values} values from {self.value.index.min()} " \
               f"to {self.value.index.max()} in {compact_unit}:\n    {str_rounded_values}"

    def plot(self, figsize=(10, 4), filepath=None, plt_show=False, xlims=None, cumsum=False):
        if self.baseline_twin is None and self.simulation_twin is None:
            baseline_df = self.value
            simulated_values_df = None
        elif self.baseline_twin is not None and self.simulation_twin is None:
            baseline_df = self.baseline_twin.value
            simulated_values_df = self.value
        elif self.simulation_twin is not None and self.baseline_twin is None:
            baseline_df = self.value
            simulated_values_df = self.simulation_twin.value
        else:
            raise ValueError("Both baseline and simulation twins are not None, this should not happen")

        if cumsum:
            baseline_df = baseline_df.cumsum()

        if simulated_values_df is not None:
            if isinstance(simulated_values_df, self._EmptyExplainableObject):
                period_index = pd.date_range(start=self.simulation.simulation_date,
                                             end=self.value.index.max(), freq='h')
                simulated_values_df = pd.DataFrame(
                    {"value": pint_pandas.PintArray(
                        np.zeros(len(period_index)), dtype=self.unit)}, index=period_index)
            if cumsum:
                simulated_values_df = simulated_values_df.cumsum()
                simulated_values_df["value"] += baseline_df["value"].at[simulated_values_df.index[0]]

        ax = plot_baseline_and_simulation_dfs(baseline_df, simulated_values_df, figsize, xlims)

        if self.label:
            if not cumsum:
                ax.set_title(self.label)
            else:
                ax.set_title("Cumulative " + self.label[:1].lower() + self.label[1:])

        if filepath is not None:
            import matplotlib.pyplot as plt
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            import matplotlib.pyplot as plt
            plt.show()
