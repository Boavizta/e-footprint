from copy import copy

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.utils.plot_baseline_and_simulation_data import plot_baseline_and_simulation_data, prepare_data


@ExplainableObject.register_subclass(lambda d: "value" in d and d["value"] is None)
class EmptyExplainableObject(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        return cls(label=d["label"])

    def __init__(self, label="no value", left_parent: ExplainableObject = None, right_parent: ExplainableObject = None,
                 operator: str = None):
        from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
        from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
        self._ExplainableQuantity = ExplainableQuantity
        self._ExplainableHourlyQuantities = ExplainableHourlyQuantities
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
        return EmptyExplainableObject(left_parent=self, operator="copy")

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
        return EmptyExplainableObject(label=copy(self.label))

    def __eq__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return True
        elif isinstance(other, ExplainableObject):
            return other.__eq__(self)
        elif other == 0:
            return True

        return False

    def __round__(self, round_level):
        return EmptyExplainableObject(
            label=self.label, left_parent=self, operator=f"rounded to {round_level} decimals")

    def __add__(self, other):
        if isinstance(other, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=other, operator="+")
        if isinstance(other, ExplainableObject):
            return other.__add__(self)
        elif other == 0:
            return EmptyExplainableObject(left_parent=self, operator="+ 0")
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
        if isinstance(other, self._ExplainableQuantity) or isinstance(other, self._ExplainableHourlyQuantities):
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
        return EmptyExplainableObject(label=self.label, left_parent=self.left_parent, right_parent=self.right_parent,
                                      operator=self.operator)

    def np_compared_with(self, compared_object, comparator):
        if isinstance(compared_object, EmptyExplainableObject):
            return EmptyExplainableObject(left_parent=self, right_parent=compared_object,
                                          operator=f"{comparator} compared with")
        elif isinstance(compared_object, self._ExplainableHourlyQuantities):
            return compared_object.np_compared_with(self, comparator)
        else:
            raise ValueError(f"Can only compare with another EmptyExplainableObject or ExplainableHourlyQuantities,"
                             f" not {type(compared_object)}")

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {"value": None}
        output_dict.update(super().to_json(with_calculated_attributes_data))

        return output_dict

    def plot(self, figsize=(10, 4), filepath=None, plt_show=False, xlims=None, cumsum=False):
        import matplotlib.pyplot as plt

        assert self.simulation_twin is not None, \
            "Cannot plot EmptyExplainableObject if simulation twin is None"

        sim_obj = self.simulation_twin
        assert not isinstance(sim_obj, EmptyExplainableObject), \
            "Cannot plot EmptyExplainableObject if simulation twin is EmptyExplainableObject"

        time_sim, simulated_q = prepare_data(sim_obj.value, sim_obj.start_date, apply_cumsum=cumsum)
        unit = simulated_q.units

        # Create a baseline of zeros with the same time index and unit
        baseline_q = Quantity(np.zeros_like(simulated_q.magnitude, dtype=np.float32), unit)
        time_baseline = time_sim

        fig, ax = plot_baseline_and_simulation_data(
            baseline_q, time_baseline, simulated_q, time_sim, figsize=figsize, xlims=xlims)

        if self.label:
            title = self.label if not cumsum else f"Cumulative {self.label[0].lower()}{self.label[1:]}"
            ax.set_title(title)

        if filepath is not None:
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            plt.show()
