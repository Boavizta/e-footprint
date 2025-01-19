import math
import numbers
from copy import copy
from datetime import datetime

import pandas as pd
import pint_pandas
import pytz
from pint import Quantity, Unit
import numpy as np
import matplotlib.pyplot as plt

from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, Source)
from efootprint.constants.units import u
from efootprint.utils.plot_baseline_and_simulation_dfs import plot_baseline_and_simulation_dfs


class EmptyExplainableObject(ExplainableObject):
    def __init__(self, label="no value", left_parent: ExplainableObject = None, right_parent: ExplainableObject = None,
                 operator: str = None):
        super().__init__(
            value=None, label=label, left_parent=left_parent, right_parent=right_parent, operator=operator)
        self.value = self

    def to(self, unit):
        return self

    def check(self, str_unit):
        return True

    def ceil(self):
        return EmptyExplainableObject(left_parent=self, operator="ceil")

    def max(self):
        return EmptyExplainableObject(left_parent=self, operator="max")

    def abs(self):
        return EmptyExplainableObject(left_parent=self, operator="abs")

    def sum(self):
        return EmptyExplainableObject(left_parent=self, operator="sum")

    def copy(self):
        return EmptyExplainableObject()

    def generate_explainable_object_with_logical_dependency(self, explainable_condition: ExplainableObject):
        return EmptyExplainableObject(
            label=self.label, left_parent=self, right_parent=explainable_condition, operator="logically dependent on")

    @property
    def iloc(self):
        return [EmptyExplainableObject(left_parent=self, operator="iloc")]

    @property
    def magnitude(self):
        return 0

    def __copy__(self):
        return EmptyExplainableObject(label=self.label)

    def __eq__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return True
        elif isinstance(other, ExplainableObject):
            return other.__eq__(self)
        elif other == 0:
            return True

        return False

    def __add__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="+")
        if isinstance(other, ExplainableObject):
            return other.__add__(self)
        elif other == 0:
            return self
        else:
            raise ValueError

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="-")
        else:
            raise ValueError

    def __mul__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        if isinstance(other, ExplainableQuantity) or isinstance(other, ExplainableHourlyQuantities):
            return other.__mul__(self)
        elif other == 0:
            return self
        else:
            raise ValueError

    def __rmul__(self, other):
        return self.__mul__(other)

    def __str__(self):
        return "no value"

    def __deepcopy__(self, memo):
        return EmptyExplainableObject(label=self.label)

    def np_compared_with(self, compared_object, comparator):
        if isinstance(compared_object, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=compared_object,
                                          operator=f"{comparator} compared with")
        elif isinstance(compared_object, ExplainableHourlyQuantities):
            return compared_object.np_compared_with(self, comparator)
        else:
            raise ValueError(f"Can only compare with another EmptyExplainableObject or ExplainableHourlyQuantities,"
                             f" not {type(compared_object)}")

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {"label": self.label, "value": None}

        if with_calculated_attributes_data:
            output_dict["id"] = self.id
            output_dict["direct_ancestors_with_id"] = [elt.id for elt in self.direct_ancestors_with_id]
            output_dict["direct_children_with_id"] = [elt.id for elt in self.direct_children_with_id]

        return output_dict

    def plot(self, figsize=(10, 4), filepath=None, plt_show=False, xlims=None, cumsum=False):
        assert self.simulation_twin is not None, "Cannot plot EmptyExplainableObject if simulation twin is None"
        simulated_values_df = self.simulation_twin.value
        assert not isinstance(simulated_values_df, EmptyExplainableObject), \
            "Cannot plot EmptyExplainableObject if simulation twin is EmptyExplainableObject"

        baseline_df = pd.DataFrame(
            {"value": pint_pandas.PintArray(
                np.zeros(len(simulated_values_df.index)),
                dtype=simulated_values_df.dtypes.value.units)},
            index=simulated_values_df.index)

        if cumsum:
            simulated_values_df = simulated_values_df.cumsum()

        ax = plot_baseline_and_simulation_dfs(baseline_df, simulated_values_df, figsize, xlims)

        if self.label:
            if not cumsum:
                ax.set_title(self.label)
            else:
                ax.set_title("Cumulative " + self.label[:1].lower() + self.label[1:])

        if filepath is not None:
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            plt.show()



class ExplainableQuantity(ExplainableObject):
    def __init__(
            self, value: Quantity, label: str = None, left_parent: ExplainableObject = None,
            right_parent: ExplainableObject = None, operator: str = None, source: Source = None):
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
        elif isinstance(other, EmptyExplainableObject):
            return self.value > 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __lt__(self, other):
        if isinstance(other, ExplainableQuantity):
            return self.value < other.value
        elif isinstance(other, EmptyExplainableObject):
            return self.value < 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __eq__(self, other):
        if isinstance(other, ExplainableQuantity):
            return self.value == other.value
        elif isinstance(other, EmptyExplainableObject):
            return self.value == 0
        else:
            raise ValueError(f"Can only compare with another ExplainableQuantity, not {type(other)}")

    def __add__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            # summing with sum() adds an implicit 0 as starting value
            return ExplainableQuantity(self.value, left_parent=self)
        elif isinstance(other, EmptyExplainableObject):
            return ExplainableQuantity(self.value, left_parent=self)
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value + other.value, "", self, other, "+")
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __sub__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableQuantity(self.value, left_parent=self)
        elif isinstance(other, EmptyExplainableObject):
            return ExplainableQuantity(self.value, left_parent=self)
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value - other.value, "", self, other, "-")
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __mul__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return 0
        elif isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value * other.value, "", self, other, "*")
        elif isinstance(other, ExplainableHourlyQuantities):
            return other.__mul__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __truediv__(self, other):
        if isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(self.value / other.value, "", self, other, "/")
        elif isinstance(other, ExplainableHourlyQuantities):
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
        elif isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=other, right_parent=self, operator="/")
        elif isinstance(other, ExplainableQuantity):
            return ExplainableQuantity(other.value / self.value, "", other, self, "/")
        elif isinstance(other, ExplainableHourlyQuantities):
            return other.__truediv__(self)
        else:
            raise ValueError(f"Can only make operation with another ExplainableQuantity, not with {type(other)}")

    def __round__(self, round_level):
        self.value = round(self.value, round_level)
        return self

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {
            "label": self.label, "value": float(self.value.magnitude), "unit": str(self.value.units)}

        if self.source is not None:
            output_dict["source"] = {"name": self.source.name, "link": self.source.link}

        if with_calculated_attributes_data:
            output_dict["id"] = self.id
            output_dict["direct_ancestors_with_id"] = [elt.id for elt in self.direct_ancestors_with_id]
            output_dict["direct_children_with_id"] = [elt.id for elt in self.direct_children_with_id]

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


class ExplainableHourlyQuantities(ExplainableObject):
    def __init__(
            self, value: pd.DataFrame, label: str = None, left_parent: ExplainableObject = None,
            right_parent: ExplainableObject = None, operator: str = None, source: Source = None):
        if not isinstance(value, pd.DataFrame):
            raise ValueError(f"ExplainableHourlyQuantities values must be pandas DataFrames, got {type(value)}")
        if value.columns != ["value"]:
            raise ValueError(
                f"ExplainableHourlyQuantities values must have only one column named value, got {value.columns}")
        if not isinstance(value.dtypes.iloc[0], pint_pandas.pint_array.PintType):
            raise ValueError(f"The pd DataFrame value of an ExplainableHourlyQuantities object must be typed with Pint,"
                             f" got {type(value.dtypes.iloc[0])} dtype")
        super().__init__(value, label, left_parent, right_parent, operator, source)

    def to(self, unit_to_convert_to: Unit, rounding=6):
        self.value["value"] = self.value["value"].pint.to(unit_to_convert_to)
        if rounding is not None:
            self.round(rounding)

        return self

    def round(self, rounding_nb):
        self.value["value"] = pint_pandas.PintArray(
            np.round(self.value["value"].values._data, rounding_nb), dtype=self.unit)

        return self

    def return_shifted_hourly_quantities(self, shift_duration: ExplainableQuantity):
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
        utc_tz = pytz.timezone('UTC')
        current_time = datetime.now()
        time_diff = (utc_tz.utcoffset(current_time) - local_timezone.value.utcoffset(current_time))
        time_diff_in_hours = int(time_diff.total_seconds() / 3600)

        return ExplainableHourlyQuantities(
            self.value.copy().shift(time_diff_in_hours, freq="h"),
            left_parent=self, right_parent=local_timezone, operator="converted to UTC from")

    def sum(self):
        return ExplainableQuantity(self.value["value"].sum(), left_parent=self, operator="sum")

    def mean(self):
        return ExplainableQuantity(self.value["value"].mean(), left_parent=self, operator="mean")

    def max(self):
        return ExplainableQuantity(self.value["value"].max(), left_parent=self, operator="max")

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

        if isinstance(compared_object, EmptyExplainableObject):
            compared_values = np.full(len(self.value), fill_value=0)
            right_parent = None
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
        elif isinstance(other, EmptyExplainableObject):
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
            return ExplainableHourlyQuantities(self.value, left_parent=self)
        elif isinstance(other, EmptyExplainableObject):
            return ExplainableHourlyQuantities(self.value, left_parent=self)
        elif isinstance(other, ExplainableHourlyQuantities):
            df_sum = self.value.add(other.value, fill_value=0 * self.unit)
            return ExplainableHourlyQuantities(df_sum, "", self, other, "+")
        else:
            raise ValueError(f"Can only make operation with another ExplainableHourlyUsage, not with {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, numbers.Number) and other == 0:
            return ExplainableHourlyQuantities(self.value, left_parent=self)
        elif isinstance(other, EmptyExplainableObject):
            return ExplainableHourlyQuantities(self.value, left_parent=self)
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
        elif isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="*")
        elif isinstance(other, ExplainableQuantity) or isinstance(other, ExplainableHourlyQuantities):
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
        elif isinstance(other, ExplainableQuantity):
            return ExplainableHourlyQuantities(self.value / other.value, "", self, other, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity, "
                f"not with {type(other)}")

    def __rtruediv__(self, other):
        if isinstance(other, ExplainableHourlyQuantities):
            raise NotImplementedError
        elif isinstance(other, ExplainableQuantity):
            return ExplainableHourlyQuantities(other.value / self.value, "", other, self, "/")
        else:
            raise ValueError(
                f"Can only make operation with another ExplainableHourlyUsage or ExplainableQuantity,"
                f" not with {type(other)}")

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {
            "label": self.label,
            "values": list(map(lambda x: round(float(x), 2), self.value["value"].values._data)),
            "unit": str(self.value.dtypes.iloc[0].units),
            "start_date": self.value.index[0].strftime("%Y-%m-%d %H:%M:%S")
        }

        if self.source is not None:
            output_dict["source"] = {"name": self.source.name, "link": self.source.link}

        if with_calculated_attributes_data:
            output_dict["id"] = self.id
            output_dict["direct_ancestors_with_id"] = [elt.id for elt in self.direct_ancestors_with_id]
            output_dict["direct_children_with_id"] = [elt.id for elt in self.direct_children_with_id]

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

        return f"{nb_of_values} values from {self.value.index.min().to_timestamp()} " \
               f"to {self.value.index.max().to_timestamp()} in {compact_unit}:\n    {str_rounded_values}"

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
            if isinstance(simulated_values_df, EmptyExplainableObject):
                period_index = pd.period_range(start=self.simulation.simulation_date_as_hourly_freq,
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
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            plt.show()
