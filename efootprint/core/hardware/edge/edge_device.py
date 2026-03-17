from typing import List, TYPE_CHECKING

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.hardware.edge.edge_storage import EdgeStorage


class EdgeDevice(ModelingObject):
    default_values = {
        "structure_carbon_footprint_fabrication": SourceValue(50 * u.kg),
        "lifespan": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, structure_carbon_footprint_fabrication: ExplainableQuantity,
                 components: List[EdgeComponent], lifespan: ExplainableQuantity):
        super().__init__(name)
        self.lifespan = lifespan.set_label(f"Lifespan of {self.name}")
        self.structure_carbon_footprint_fabrication = structure_carbon_footprint_fabrication.set_label(
            f"Structure fabrication carbon footprint of {self.name}")
        self.components = components

        self.lifespan_validation = EmptyExplainableObject()
        self.component_needs_edge_device_validation = EmptyExplainableObject()
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def calculated_attributes(self):
        return (["lifespan_validation", "component_needs_edge_device_validation",
                "instances_fabrication_footprint_per_usage_pattern",
                "instances_energy_per_usage_pattern", "energy_footprint_per_usage_pattern",
                "instances_fabrication_footprint", "instances_energy", "energy_footprint"]
                + super().calculated_attributes)

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
        return [elt for elt in self.modeling_obj_containers if isinstance(elt, RecurrentEdgeDeviceNeed)]

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
        return [elt for elt in self.modeling_obj_containers if isinstance(elt, RecurrentServerNeed)]

    @property
    def recurrent_needs(self) -> List["RecurrentEdgeDeviceNeed | RecurrentServerNeed"]:
        return self.modeling_obj_containers

    @property
    def recurrent_edge_component_needs(self) -> List["RecurrentEdgeComponentNeed"]:
        return list(dict.fromkeys(sum(
            [need.recurrent_edge_component_needs for need in self.recurrent_edge_device_needs], start=[])))

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(dict.fromkeys(sum([need.edge_usage_journeys for need in self.recurrent_needs], start=[])))

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return list(dict.fromkeys(sum([need.edge_functions for need in self.recurrent_needs], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([need.edge_usage_patterns for need in self.recurrent_needs], start=[])))

    def _filter_component_by_type(self, component_type: type) -> List[EdgeComponent]:
        components_of_type = []
        for component in self.components:
            if isinstance(component, component_type):
                components_of_type.append(component)

        return components_of_type

    @property
    def storages(self) -> List["EdgeStorage"]:
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage
        return self._filter_component_by_type(EdgeStorage)

    @property
    def cpus(self):
        from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
        return self._filter_component_by_type(EdgeCPUComponent)

    def update_lifespan_validation(self):
        result = EmptyExplainableObject().generate_explainable_object_with_logical_dependency(self.lifespan)
        for edge_usage_journey in self.edge_usage_journeys:
            if self.lifespan < edge_usage_journey.usage_span:
                raise InsufficientCapacityError(self, "lifespan", self.lifespan, edge_usage_journey.usage_span)
            result = result.generate_explainable_object_with_logical_dependency(edge_usage_journey.usage_span)
        self.lifespan_validation = result

    def update_component_needs_edge_device_validation(self):
        """Validate that all component needs point to components of this edge_device."""
        for component_need in self.recurrent_edge_component_needs:
            component_device = component_need.edge_component.edge_device
            if component_device is not None and component_device != self:
                raise ValueError(
                    f"RecurrentEdgeComponentNeed '{component_need.name}' points to component "
                    f"'{component_need.edge_component.name}' belonging to EdgeDevice '{component_device.name}', "
                    f"but RecurrentEdgeDeviceNeed '{self.name}' is linked to EdgeDevice '{self.name}'. "
                    f"All component needs must belong to the same edge device.")

        self.component_needs_edge_device_validation = EmptyExplainableObject()

    def update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        # Sum fabrication footprints from all components plus device structure
        structure_fabrication_intensity = self.structure_carbon_footprint_fabrication / self.lifespan
        nb_instances = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
            usage_pattern]

        structure_footprint = (
            nb_instances * structure_fabrication_intensity * ExplainableQuantity(1 * u.hour, "one hour"))

        total_footprint = structure_footprint
        for component in self.components:
            if usage_pattern in component.instances_fabrication_footprint_per_usage_pattern:
                total_footprint += component.instances_fabrication_footprint_per_usage_pattern[usage_pattern]

        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = total_footprint.to(
            u.kg).set_label(f"Hourly {self.name} instances fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    def update_dict_element_in_instances_energy_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # Sum energy from all components
        total_energy = EmptyExplainableObject()
        for component in self.components:
            if usage_pattern in component.instances_energy_per_usage_pattern:
                total_energy += component.instances_energy_per_usage_pattern[usage_pattern]

        self.instances_energy_per_usage_pattern[usage_pattern] = total_energy.set_label(
            f"Hourly energy consumed by {self.name} instances for {usage_pattern.name}")

    def update_instances_energy_per_usage_pattern(self):
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_energy_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_footprint_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # Sum energy footprint from all components
        total_energy_footprint = EmptyExplainableObject()
        for component in self.components:
            if usage_pattern in component.energy_footprint_per_usage_pattern:
                total_energy_footprint += component.energy_footprint_per_usage_pattern[usage_pattern]

        self.energy_footprint_per_usage_pattern[usage_pattern] = total_energy_footprint.set_label(
            f"{self.name} energy footprint for {usage_pattern.name}").to(u.kg)

    def update_energy_footprint_per_usage_pattern(self):
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_footprint_per_usage_pattern(usage_pattern)

    def update_instances_energy(self):
        instances_energy = sum(
            self.instances_energy_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_energy = instances_energy.set_label(
            f"{self.name} total energy consumed across usage patterns")

    def update_energy_footprint(self):
        energy_footprint = sum(
            self.energy_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.energy_footprint = energy_footprint.set_label(
            f"{self.name} total energy footprint across usage patterns")

    def update_instances_fabrication_footprint(self):
        instances_fabrication_footprint = sum(
            self.instances_fabrication_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"{self.name} total fabrication footprint across usage patterns")

    @property
    def fabrication_footprint_breakdown_by_source(self) -> ExplainableObjectDict:
        breakdown = ExplainableObjectDict()
        if not self.components:
            return breakdown

        component_fabrication_total = sum(
            (component.instances_fabrication_footprint for component in self.components),
            start=EmptyExplainableObject(),
        )
        structure_fabrication_total = self.instances_fabrication_footprint - component_fabrication_total
        equal_structure_share = structure_fabrication_total / ExplainableQuantity(
            len(self.components) * u.dimensionless, label=f"Number of components in {self.name}")
        for component in self.components:
            breakdown[component] = component.instances_fabrication_footprint + equal_structure_share
        return breakdown

    @property
    def energy_footprint_breakdown_by_source(self) -> ExplainableObjectDict:
        return ExplainableObjectDict({
            component: component.energy_footprint
            for component in self.components
        })

    @property
    def footprint_breakdown_by_source(self) -> dict[LifeCyclePhases, ExplainableObjectDict]:
        return {
            LifeCyclePhases.MANUFACTURING: self.fabrication_footprint_breakdown_by_source,
            LifeCyclePhases.USAGE: self.energy_footprint_breakdown_by_source,
        }

    def update_dict_element_in_impact_repartition_weights(self, source_obj):
        from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

        if not isinstance(source_obj, RecurrentEdgeComponentNeed):
            raise TypeError(f"Unsupported edge device impact repartition source: {type(source_obj)}")

        component = source_obj.edge_component
        component_need_demand = source_obj.total_hourly_need_across_usage_patterns
        sibling_need_demand = sum(
            [recurrent_component_need.total_hourly_need_across_usage_patterns
             for recurrent_component_need in self.recurrent_edge_component_needs
             if recurrent_component_need.edge_component == component],
            start=EmptyExplainableObject())
        if isinstance(sibling_need_demand, EmptyExplainableObject) or sibling_need_demand.sum().magnitude == 0:
            weight = EmptyExplainableObject()
        else:
            component_total_impact = component.instances_fabrication_footprint + component.energy_footprint
            weight = component_total_impact * (component_need_demand / sibling_need_demand)
            if isinstance(weight, ExplainableHourlyQuantities):
                nan_values_mask = np.isnan(weight.magnitude)
                weight.magnitude[nan_values_mask] = 0

        self.impact_repartition_weights[source_obj] = weight.set_label(
            f"{source_obj.name} weight in {self.name} impact repartition")

    def update_impact_repartition_weights(self):
        self.impact_repartition_weights = ExplainableObjectDict()
        for recurrent_component_need in self.recurrent_edge_component_needs:
            self.update_dict_element_in_impact_repartition_weights(recurrent_component_need)
