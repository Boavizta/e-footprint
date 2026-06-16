from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import align_temporally_quantity_arrays
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.all_classes_in_order import OBJECT_CATEGORIES
from efootprint.constants.units import u

PHASES = ("energy", "fabrication")


@dataclass(frozen=True)
class Delta:
    """Absolute and relative change from ``before`` to ``after``, both in kg."""
    before: float
    after: float

    @property
    def absolute(self) -> float:
        return self.after - self.before

    @property
    def relative(self) -> Optional[float]:
        """Fractional change (``after / before - 1``); ``None`` when there is no baseline to divide by."""
        if self.before == 0:
            return None
        return self.absolute / self.before


@dataclass(frozen=True)
class DecompositionRow:
    """One (category, phase) cell of the breakdown, holding its delta (each system's kg total is on the ``Delta``)."""
    category: str
    phase: str
    delta: Delta


@dataclass(frozen=True)
class AttributeDiff:
    """A single input attribute that differs between the paired objects."""
    object_class: str
    object_name_a: str
    object_name_b: str
    attribute: str
    value_a: Optional[str]
    value_b: Optional[str]
    source_a: Optional[str]
    source_b: Optional[str]
    confidence_a: Optional[str]
    confidence_b: Optional[str]


@dataclass(frozen=True)
class UnmatchedObject:
    object_class: str
    object_name: str
    object_id: str


@dataclass(frozen=True)
class InputDiff:
    """The structural difference between two systems' inputs."""
    changed: List[AttributeDiff]
    only_in_a: List[UnmatchedObject]
    only_in_b: List[UnmatchedObject]


@dataclass(frozen=True)
class TimeSeries:
    """Two systems' hourly footprint aligned on one calendar axis, plus their cumulative sums (kg)."""
    start_date: datetime
    values_a: np.ndarray
    values_b: np.ndarray

    @property
    def hours(self) -> List[datetime]:
        return [self.start_date + timedelta(hours=i) for i in range(len(self.values_a))]

    @property
    def cumulative_a(self) -> np.ndarray:
        return np.cumsum(self.values_a)

    @property
    def cumulative_b(self) -> np.ndarray:
        return np.cumsum(self.values_b)


def _kg(explainable_quantity: ExplainableQuantity) -> float:
    return float(explainable_quantity.to(u.kg).magnitude)


def _attribute_value_str(explainable_object: ExplainableObject) -> Optional[str]:
    value = getattr(explainable_object, "value", None)
    if value is None:
        return None
    # Scalars read straight off the value (e.g. "300.0 watt"). Array-valued inputs (hourly / recurrent
    # quantities) render via their wrapper's compact __str__ ("<N> values in <unit>: [first 10 / last 10]")
    # rather than dumping the full numpy array.
    if isinstance(explainable_object, ExplainableQuantity):
        return str(value)
    return str(explainable_object)


class SystemComparison:
    """Domain-truth comparison of two e-footprint {class:System}s.

    Computes the headline footprint totals and their delta, the per-(category, phase) decomposition that sums
    to that headline delta by construction (the categories are the library SSOT ``OBJECT_CATEGORIES``), the two
    systems' footprint time-series aligned on a shared calendar axis with cumulative sums, and the input diff
    (objects paired by id first, then by (name, type)). No new modeling logic, no attribution claims — every
    number is read from the systems' own already-computed totals.
    """

    def __init__(self, system_a, system_b):
        self.system_a = system_a
        self.system_b = system_b

    @property
    def total_a(self) -> float:
        return _kg(self.system_a.total_footprint.sum())

    @property
    def total_b(self) -> float:
        return _kg(self.system_b.total_footprint.sum())

    @property
    def total_delta(self) -> Delta:
        return Delta(before=self.total_a, after=self.total_b)

    @property
    def decomposition(self) -> List[DecompositionRow]:
        sums_a = {
            "energy": self.system_a.total_energy_footprint_sum_over_period,
            "fabrication": self.system_a.total_fabrication_footprint_sum_over_period}
        sums_b = {
            "energy": self.system_b.total_energy_footprint_sum_over_period,
            "fabrication": self.system_b.total_fabrication_footprint_sum_over_period}

        rows = []
        for category in OBJECT_CATEGORIES:
            for phase in PHASES:
                before = _kg(sums_a[phase][category])
                after = _kg(sums_b[phase][category])
                rows.append(DecompositionRow(category=category, phase=phase, delta=Delta(before, after)))

        return rows

    @property
    def time_series(self) -> TimeSeries:
        footprint_a = self.system_a.total_footprint
        footprint_b = self.system_b.total_footprint
        values_a, values_b, start_date = align_temporally_quantity_arrays(
            footprint_a.value, footprint_a.start_date, footprint_b.value, footprint_b.start_date)

        return TimeSeries(start_date=start_date, values_a=values_a, values_b=values_b)

    @property
    def input_diff(self) -> InputDiff:
        objects_a = self.system_a.all_linked_objects
        objects_b = self.system_b.all_linked_objects

        by_id_b = {obj.id: obj for obj in objects_b}
        by_name_type_b = {(obj.name, obj.efootprint_class): obj for obj in objects_b}

        matched_b_ids = set()
        changed = []
        only_in_a = []

        for obj_a in objects_a:
            obj_b = by_id_b.get(obj_a.id) or by_name_type_b.get((obj_a.name, obj_a.efootprint_class))
            if obj_b is None:
                only_in_a.append(UnmatchedObject(obj_a.class_as_simple_str, obj_a.name, obj_a.id))
                continue
            matched_b_ids.add(obj_b.id)
            changed.extend(self._diff_inputs(obj_a, obj_b))

        only_in_b = [UnmatchedObject(obj_b.class_as_simple_str, obj_b.name, obj_b.id)
                     for obj_b in objects_b if obj_b.id not in matched_b_ids]

        return InputDiff(changed=changed, only_in_a=only_in_a, only_in_b=only_in_b)

    @staticmethod
    def _input_attributes(obj: ModelingObject) -> Dict[str, ExplainableObject]:
        skip = set(obj.calculated_attributes) | set(obj.attributes_that_shouldnt_trigger_update_logic)
        return {key: value for key, value in obj.__dict__.items()
                if key not in skip and isinstance(value, ExplainableObject)}

    def _diff_inputs(self, obj_a: ModelingObject, obj_b: ModelingObject) -> List[AttributeDiff]:
        inputs_a = self._input_attributes(obj_a)
        inputs_b = self._input_attributes(obj_b)

        diffs = []
        for attribute in inputs_a.keys() & inputs_b.keys():
            value_a, value_b = inputs_a[attribute], inputs_b[attribute]
            if value_a == value_b:
                continue
            diffs.append(AttributeDiff(
                object_class=obj_a.class_as_simple_str, object_name_a=obj_a.name, object_name_b=obj_b.name,
                attribute=attribute,
                value_a=_attribute_value_str(value_a), value_b=_attribute_value_str(value_b),
                source_a=getattr(getattr(value_a, "source", None), "name", None),
                source_b=getattr(getattr(value_b, "source", None), "name", None),
                confidence_a=getattr(value_a, "confidence", None),
                confidence_b=getattr(value_b, "confidence", None)))

        return diffs

    def plot_emissions_over_time(self, filepath=None, figsize=(10, 5), plt_show=False):
        return _plot_paired_series(
            self.time_series, "Hourly carbon footprint", self.system_a.name, self.system_b.name,
            cumulative=False, filepath=filepath, figsize=figsize, plt_show=plt_show)

    def plot_cumulative_emissions(self, filepath=None, figsize=(10, 5), plt_show=False):
        return _plot_paired_series(
            self.time_series, "Cumulative carbon footprint", self.system_a.name, self.system_b.name,
            cumulative=True, filepath=filepath, figsize=figsize, plt_show=plt_show)

    def plot_decomposition(self, filepath=None, figsize=(10, 6), plt_show=False):
        return _plot_decomposition(
            self.decomposition, self.system_a.name, self.system_b.name,
            filepath=filepath, figsize=figsize, plt_show=plt_show)


def _matplotlib_pyplot(plt_show):
    import os
    import matplotlib
    if not plt_show and os.environ.get("MPLBACKEND") is None:
        matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    return plt


def _plot_paired_series(time_series, title, label_a, label_b, cumulative, filepath, figsize, plt_show):
    plt = _matplotlib_pyplot(plt_show)
    fig, ax = plt.subplots(figsize=figsize)
    hours = time_series.hours
    if cumulative:
        series_a, series_b = time_series.cumulative_a, time_series.cumulative_b
    else:
        series_a, series_b = time_series.values_a, time_series.values_b
    ax.plot(hours, series_a, label=label_a, color="#6372f2")
    ax.plot(hours, series_b, label=label_b, color="#de5f46")
    ax.set_title(title)
    ax.set_ylabel("kg CO2")
    ax.legend()

    if filepath is not None:
        fig.savefig(filepath, bbox_inches="tight")
    if plt_show:
        plt.show()

    return fig, ax


def _plot_decomposition(decomposition, label_a, label_b, filepath, figsize, plt_show):
    plt = _matplotlib_pyplot(plt_show)
    fig, ax = plt.subplots(figsize=figsize)
    rows = [row for row in decomposition if row.delta.absolute != 0]
    labels = [f"{row.category} ({row.phase})" for row in rows]
    deltas = [row.delta.absolute for row in rows]
    colors = ["#de5f46" if d > 0 else "#6372f2" for d in deltas]
    ax.barh(labels, deltas, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(f"Footprint difference by category and phase ({label_b} − {label_a})")
    ax.set_xlabel("kg CO2 difference")

    if filepath is not None:
        fig.savefig(filepath, bbox_inches="tight")
    if plt_show:
        plt.show()

    return fig, ax
