from typing import List, TYPE_CHECKING

import numpy as np
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
    from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed


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
    compatible_root_units = [u.bit_stored]
    default_values = {
        "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB_stored),
        "lifespan": SourceValue(6 * u.years),
        "nb_of_units": SourceValue(1 * u.dimensionless),
        "storage_capacity_per_unit": SourceValue(1 * u.TB_stored),
        "base_storage_need": SourceValue(30 * u.GB_stored),
    }

    @classmethod
    def ssd(cls, name="Default SSD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                160 * u.kg / u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years),
            "storage_capacity_per_unit": SourceValue(1 * u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB_stored),
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years),
            "storage_capacity_per_unit": SourceValue(1 * u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB_stored),
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.ssd, cls.hdd]

    def __init__(self, name: str, storage_capacity_per_unit: ExplainableQuantity,
                 carbon_footprint_fabrication_per_storage_capacity: ExplainableQuantity,
                 base_storage_need: ExplainableQuantity, lifespan: ExplainableQuantity,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(
            name, carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg), power_per_unit=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power_per_unit=SourceValue(0 * u.W), nb_of_units=nb_of_units)
        del self.power
        del self.idle_power
        self.carbon_footprint_fabrication_per_storage_capacity = (
            carbon_footprint_fabrication_per_storage_capacity.set_label(
                f"Fabrication carbon footprint per unit of {self.name} per storage capacity"))
        self.storage_capacity_per_unit = storage_capacity_per_unit.set_label(
            f"Storage capacity per unit of {self.name}")
        self.storage_capacity = EmptyExplainableObject()
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")
        self.cumulative_unitary_storage_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def recurrent_edge_storage_needs(self) -> List["RecurrentEdgeStorageNeed"]:
        from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
        recurrent_edge_storage_needs = [
            container for container in self.modeling_obj_containers if isinstance(container, RecurrentEdgeStorageNeed)
        ]
        invalid_component_needs = [
            need for need in self.recurrent_edge_component_needs if need not in recurrent_edge_storage_needs
        ]
        if invalid_component_needs:
            raise ValueError(
                f"EdgeStorage object {self.name} has recurrent component needs that are not "
                f"RecurrentEdgeStorageNeed objects: "
                f"{[need.name for need in invalid_component_needs]}. "
                f"Please check your model structure.")
        return recurrent_edge_storage_needs

    @property
    def calculated_attributes(self):
        return ["storage_capacity", "cumulative_unitary_storage_need_per_usage_pattern"] + [
            attr for attr in super().calculated_attributes
            if attr not in ["power", "idle_power"]
        ]

    def update_storage_capacity(self):
        self.storage_capacity = (self.storage_capacity_per_unit * self.nb_of_units).set_label(
            f"Storage capacity of {self.name}")

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (
            self.carbon_footprint_fabrication_per_storage_capacity
            * self.storage_capacity
        ).set_label(f"Carbon footprint of {self.name}")

    def update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(self, usage_pattern):
        total = sum(
            [
                recurrent_need.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern]
                for recurrent_need in self.recurrent_edge_storage_needs
                if usage_pattern in recurrent_need.cumulative_unitary_storage_need_per_usage_pattern
            ],
            start=EmptyExplainableObject(),
        )
        if not isinstance(total, EmptyExplainableObject):
            total = total + self.base_storage_need
            if np.min(total.magnitude) < 0:
                raise NegativeCumulativeStorageNeedError(self, total)

            if np.max(total.value) > self.storage_capacity.value:
                raise InsufficientCapacityError(
                    self, "storage capacity", self.storage_capacity,
                    ExplainableQuantity(total.value.max(), label=f"{self.name} cumulative storage need"))
        self.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern] = total.set_label(
            f"{self.name} cumulative storage need for {usage_pattern.name}"
        ).generate_explainable_object_with_logical_dependency(self.storage_capacity)

    def update_cumulative_unitary_storage_need_per_usage_pattern(self):
        self.cumulative_unitary_storage_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.unitary_power_per_usage_pattern[usage_pattern] = EmptyExplainableObject()
