from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import align_temporally_quantity_arrays
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.all_classes_in_order import OBJECT_CATEGORIES
from efootprint.constants.units import u
from efootprint.utils.plot_baseline_and_simulation_data import get_time_axis
from efootprint.utils.tools import get_init_signature_params

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
    """Two systems' hourly footprint aligned on one calendar axis, plus their cumulative sums (kg).

    Carries both the combined totals (``values_a``/``values_b``) and the per-phase split
    (``usage_*``/``fabrication_*``) on the *same* axis, so ``usage + fabrication == values`` hour-by-hour
    for each system. The per-phase split lets a consumer bucket usage and fabrication exactly per period
    (e.g. per year) rather than approximating with a single full-period ratio.
    """
    start_date: datetime
    values_a: np.ndarray
    values_b: np.ndarray
    usage_a: np.ndarray
    usage_b: np.ndarray
    fabrication_a: np.ndarray
    fabrication_b: np.ndarray

    @property
    def hours(self) -> np.ndarray:
        return get_time_axis(self.start_date, len(self.values_a))

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


def _count_value_str(explainable_quantity: ExplainableQuantity) -> str:
    """A weighted-dict count as a bare magnitude ("3", "2.5"), dropping the dimensionless unit and a
    trailing ".0" — these counts are how many times a key occurs, not a physical quantity."""
    magnitude = float(explainable_quantity.value.magnitude)
    return str(int(magnitude)) if magnitude.is_integer() else str(magnitude)


def _constructor_input_values(obj: ModelingObject) -> Dict[str, object]:
    """The object's declared constructor inputs, keyed by attribute name — the SSOT for "what the user
    provided", mirroring ``copy_with`` and ``is_structural_input_dict_attribute``. Calculated and infra
    attributes (``id``, cached properties, …) are excluded by construction: they are not ``__init__``
    parameters, so no skip-list of computed attributes is needed.

    Reads the signature off ``efootprint_class`` rather than ``type(obj)`` because linked objects arrive
    wrapped in ``ContextualModelingObjectAttribute`` proxies; ``efootprint_class`` (and attribute access)
    transparently resolve to the wrapped modeling object, exactly as the object-level pairing relies on."""
    return {name: getattr(obj, name) for name in get_init_signature_params(obj.efootprint_class)
            if name not in ("self", "name") and hasattr(obj, name)}


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
        assert len(values_a) == len(values_b)
        total_timeseries_length = len(values_a)

        # The per-phase series ride on the same axis as the totals (same common start, same length), so
        # usage + fabrication reconstructs the total hour-by-hour for each system.
        usage_a = self._aligned_phase_series(self.system_a, "energy", start_date, total_timeseries_length)
        usage_b = self._aligned_phase_series(self.system_b, "energy", start_date, total_timeseries_length)
        fabrication_a = self._aligned_phase_series(
            self.system_a, "fabrication", start_date, total_timeseries_length)
        fabrication_b = self._aligned_phase_series(
            self.system_b, "fabrication", start_date, total_timeseries_length)

        return TimeSeries(
            start_date=start_date, values_a=values_a, values_b=values_b,
            usage_a=usage_a, usage_b=usage_b, fabrication_a=fabrication_a, fabrication_b=fabrication_b)

    @staticmethod
    def _aligned_phase_series(system, phase: str, axis_start: datetime, axis_length: int) -> np.ndarray:
        """One system's combined hourly footprint for ``phase`` (kg), placed onto the shared axis.

        Sums the per-category hourly footprints for the phase exactly as ``System.update_total_footprint``
        builds the total, then positions the system's own window inside the shared ``[axis_start, +length]``
        axis (zero outside it) — so usage + fabrication equals the aligned total per hour.
        """
        per_category = (system.total_energy_footprints if phase == "energy"
                        else system.total_fabrication_footprints)
        phase_total = sum(per_category.values(), start=EmptyExplainableObject())

        aligned = np.zeros(axis_length, dtype=np.float32)
        if isinstance(phase_total, EmptyExplainableObject):
            return aligned
        magnitude = phase_total.to(u.kg).value.magnitude.astype(np.float32)
        offset = int((phase_total.start_date - axis_start).total_seconds() // 3600)
        aligned[offset:offset + len(magnitude)] = magnitude
        return aligned

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
        """The object's scalar/array ``ExplainableObject`` inputs, keyed by attribute name."""
        return {name: value for name, value in _constructor_input_values(obj).items()
                if isinstance(value, ExplainableObject)}

    @staticmethod
    def _dict_input_attributes(obj: ModelingObject) -> Dict[str, ExplainableObjectDict]:
        """The object's dict-relationship inputs (e.g. ``UsageJourney.uj_steps``): per-key dimensionless
        counts (weights) that the scalar ``_input_attributes`` walk skips, since an ``ExplainableObjectDict``
        is not an ``ExplainableObject``."""
        return {name: value for name, value in _constructor_input_values(obj).items()
                if isinstance(value, ExplainableObjectDict)}

    @staticmethod
    def _list_input_attributes(obj: ModelingObject) -> Dict[str, list]:
        """The object's list-relationship inputs (e.g. ``System.usage_patterns``, ``UsagePattern.devices``):
        ordered links to other ``ModelingObject``s, diffed by membership. Non-``ModelingObject`` lists (none
        exist today) are excluded — they have no identity to pair on."""
        return {name: value for name, value in _constructor_input_values(obj).items()
                if isinstance(value, list) and all(isinstance(elt, ModelingObject) for elt in value)}

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

        dicts_a = self._dict_input_attributes(obj_a)
        dicts_b = self._dict_input_attributes(obj_b)
        for attribute in dicts_a.keys() & dicts_b.keys():
            diffs.extend(self._diff_dict_input(obj_a, obj_b, attribute, dicts_a[attribute], dicts_b[attribute]))

        lists_a = self._list_input_attributes(obj_a)
        lists_b = self._list_input_attributes(obj_b)
        for attribute in lists_a.keys() & lists_b.keys():
            diffs.extend(self._diff_list_input(obj_a, obj_b, attribute, lists_a[attribute], lists_b[attribute]))

        return diffs

    def _diff_dict_input(self, obj_a, obj_b, attribute, dict_a, dict_b) -> List[AttributeDiff]:
        """Diff one dict-relationship input key by key: a changed count (the key in both, weight differs),
        an added key (only in B → absent/count row), or a removed key (only in A → count/absent row).

        Keys are ``ModelingObject``s matched id-first then (name, type) — the same identity philosophy as
        the object-level pairing — so renaming a key in B still pairs it. The attribute label is the dict's
        ``weight_labels`` metadata plus the key's name, so each row reads as e.g. "Times per journey (step
        name)" with the counts as the two values."""
        weight_label = obj_a.weight_labels.get(attribute, attribute)
        keys_b_by_id = {key.id: key for key in dict_b if isinstance(key, ModelingObject)}
        keys_b_by_name_type = {(key.name, key.efootprint_class): key for key in dict_b
                               if isinstance(key, ModelingObject)}

        diffs = []
        matched_b_ids = set()
        for key_a in dict_a:
            key_b = (keys_b_by_id.get(getattr(key_a, "id", None))
                     or keys_b_by_name_type.get((getattr(key_a, "name", None), getattr(key_a, "efootprint_class", None))))
            count_a = _count_value_str(dict_a[key_a])
            if key_b is None:  # removed: key present only in A
                diffs.append(self._dict_attribute_diff(obj_a, obj_b, weight_label, key_a, count_a, None))
                continue
            matched_b_ids.add(id(key_b))
            count_b = _count_value_str(dict_b[key_b])
            if count_a != count_b:
                diffs.append(self._dict_attribute_diff(obj_a, obj_b, weight_label, key_a, count_a, count_b))

        for key_b in dict_b:  # added: keys present only in B
            if id(key_b) not in matched_b_ids:
                diffs.append(self._dict_attribute_diff(
                    obj_a, obj_b, weight_label, key_b, None, _count_value_str(dict_b[key_b])))

        return diffs

    @staticmethod
    def _dict_attribute_diff(obj_a, obj_b, weight_label, key, count_a, count_b) -> AttributeDiff:
        key_name = getattr(key, "name", str(key))
        return AttributeDiff(
            object_class=obj_a.class_as_simple_str, object_name_a=obj_a.name, object_name_b=obj_b.name,
            attribute=f"{weight_label} ({key_name})",
            value_a=count_a, value_b=count_b,
            source_a=None, source_b=None, confidence_a=None, confidence_b=None)

    def _diff_list_input(self, obj_a, obj_b, attribute, list_a, list_b) -> List[AttributeDiff]:
        """Diff one list-relationship input by membership: a link present in only one model surfaces as a
        present/absent row ("present" on the side that has it, ``None`` on the other). Links present in both
        are unchanged here — each is paired and diffed in its own right at the object level. Elements are
        ``ModelingObject``s paired id-first then (name, type), the same identity philosophy as the dict and
        object-level pairing, so renaming a link in B still pairs it."""
        elements_b_by_id = {elt.id: elt for elt in list_b}
        elements_b_by_name_type = {(elt.name, elt.efootprint_class): elt for elt in list_b}

        diffs = []
        matched_b_ids = set()
        for elt_a in list_a:
            elt_b = elements_b_by_id.get(elt_a.id) or elements_b_by_name_type.get((elt_a.name, elt_a.efootprint_class))
            if elt_b is None:  # removed: present only in A
                diffs.append(self._list_attribute_diff(obj_a, obj_b, attribute, elt_a, present_a=True))
            else:
                matched_b_ids.add(id(elt_b))

        for elt_b in list_b:  # added: present only in B
            if id(elt_b) not in matched_b_ids:
                diffs.append(self._list_attribute_diff(obj_a, obj_b, attribute, elt_b, present_a=False))

        return diffs

    @staticmethod
    def _list_attribute_diff(obj_a, obj_b, attribute, element, present_a) -> AttributeDiff:
        return AttributeDiff(
            object_class=obj_a.class_as_simple_str, object_name_a=obj_a.name, object_name_b=obj_b.name,
            attribute=f"{attribute} ({element.name})",
            value_a="present" if present_a else None, value_b=None if present_a else "present",
            source_a=None, source_b=None, confidence_a=None, confidence_b=None)

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
