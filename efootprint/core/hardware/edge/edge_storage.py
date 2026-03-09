from typing import List, TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.constants.sources import Sources
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed


class NegativeCumulativeStorageNeedError(Exception):
    def __init__(self, storage_obj: "EdgeStorage", cumulative_quantity: ExplainableHourlyQuantities):
        self.storage_obj = storage_obj
        self.cumulative_quantity = cumulative_quantity

        message = (
            f"In EdgeStorage object {self.storage_obj.name}, negative cumulative storage need detected: "
            f"{np.min(cumulative_quantity.value):~P}. Please check your processes "
            f"or increase the base_storage_need value, currently set to {self.storage_obj.base_storage_need.value}")
        super().__init__(message)


class EdgeStorage(EdgeComponent):
    compatible_root_units = [u.bit]
    default_values = {
        "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB),
        "lifespan": SourceValue(6 * u.years),
        "storage_capacity": SourceValue(1 * u.TB),
        "base_storage_need": SourceValue(30 * u.GB),
    }

    @classmethod
    def ssd(cls, name="Default SSD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB),
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB),
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.ssd, cls.hdd]

    def __init__(self, name: str, storage_capacity: ExplainableQuantity,
                 carbon_footprint_fabrication_per_storage_capacity: ExplainableQuantity,
                 base_storage_need: ExplainableQuantity, lifespan: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power=SourceValue(0 * u.W))
        self.carbon_footprint_fabrication_per_storage_capacity = (carbon_footprint_fabrication_per_storage_capacity
            .set_label(f"Fabrication carbon footprint of {self.name} per storage capacity"))
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity of {self.name}")
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")
        self.cumulative_unitary_storage_need_per_recurrent_need = ExplainableObjectDict()
        self.full_cumulative_storage_need = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return ([
            "carbon_footprint_fabrication", "cumulative_unitary_storage_need_per_recurrent_need",
            "full_cumulative_storage_need"]
                + [elt for elt in super().calculated_attributes if elt != "impact_repartition_weights"])

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (
            self.carbon_footprint_fabrication_per_storage_capacity * self.storage_capacity).set_label(
            f"Carbon footprint of {self.name}")

    def update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need(
            self, recurrent_need: "RecurrentEdgeComponentNeed"):
        recurrent_need_storage_rate = sum(
            [recurrent_need.unitary_hourly_need_per_usage_pattern[eup] for eup in recurrent_need.edge_usage_patterns],
            start=EmptyExplainableObject())

        if isinstance(recurrent_need_storage_rate, EmptyExplainableObject):
            self.cumulative_unitary_storage_need_per_recurrent_need[recurrent_need] = EmptyExplainableObject(
                left_parent=recurrent_need_storage_rate,
                label=f"Cumulative storage for {recurrent_need.name} in {self.name}")
            return

        rate_array = np.copy(recurrent_need_storage_rate.value.magnitude)
        rate_units = recurrent_need_storage_rate.value.units
        cumulative_quantity = Quantity(np.cumsum(rate_array, dtype=np.float32), rate_units)
        self.cumulative_unitary_storage_need_per_recurrent_need[recurrent_need] = ExplainableHourlyQuantities(
            cumulative_quantity, start_date=recurrent_need_storage_rate.start_date,
            label=f"Cumulative storage for {recurrent_need.name} in {self.name}",
            left_parent=recurrent_need_storage_rate, operator="cumulative sum")

    def update_cumulative_unitary_storage_need_per_recurrent_need(self):
        self.cumulative_unitary_storage_need_per_recurrent_need = ExplainableObjectDict()
        for recurrent_need in self.recurrent_edge_component_needs:
            self.update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need(recurrent_need)

    def update_full_cumulative_storage_need(self):
        total = sum(self.cumulative_unitary_storage_need_per_recurrent_need.values(), start=EmptyExplainableObject())
        if not isinstance(total, EmptyExplainableObject):
            total = total + self.base_storage_need
            if np.min(total.magnitude) < 0:
                raise NegativeCumulativeStorageNeedError(self, total)

            if np.max(total.value) > self.storage_capacity.value:
                raise InsufficientCapacityError(
                    self, "storage capacity", self.storage_capacity,
                    ExplainableQuantity(total.value.max(), label=f"{self.name} cumulative storage need"))

        self.full_cumulative_storage_need = (
            total.set_label(f"{self.name} cumulative storage need")
            .generate_explainable_object_with_logical_dependency(self.storage_capacity))

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.unitary_power_per_usage_pattern[usage_pattern] = EmptyExplainableObject()

    @property
    def impact_repartition_weights(self):
        return self.cumulative_unitary_storage_need_per_recurrent_need
