from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_appliance_component import EdgeApplianceComponent

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload


class EdgeAppliance(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):

        # Appliance component gets power and idle_power
        appliance_component = EdgeApplianceComponent(
            name=f"{name} appliance",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=power,
            lifespan=lifespan,
            idle_power=idle_power)

        # All fabrication footprint goes to structure
        super().__init__(
            name=name,
            structure_fabrication_carbon_footprint=carbon_footprint_fabrication,
            components=[appliance_component],
            lifespan=lifespan)

        self._appliance_component = appliance_component

    @property
    def appliance_component(self) -> EdgeApplianceComponent:
        return self._appliance_component

    @property
    def edge_workloads(self) -> List["RecurrentEdgeWorkload"]:
        return self.modeling_obj_containers

    @property
    def unitary_hourly_workload_per_usage_pattern(self):
        return self._appliance_component.unitary_hourly_workload_per_usage_pattern