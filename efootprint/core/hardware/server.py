from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerBase, ServerTypes


class Server(ServerBase):
    @classmethod
    def default_values(cls):
        return {
            "server_type": ServerTypes.autoscaling(),
            "carbon_footprint_fabrication": SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(300 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
            "idle_power": SourceValue(50 * u.W, Sources.HYPOTHESIS),
            "ram": SourceValue(128 * u.GB, Sources.HYPOTHESIS),
            "compute": SourceValue(24 * u.cpu_core, Sources.HYPOTHESIS),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            "average_carbon_intensity": SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            "server_utilization_rate": SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            "base_ram_consumption": SourceValue(0 * u.GB, Sources.HYPOTHESIS),
            "base_compute_consumption": SourceValue(0 * u.cpu_core, Sources.HYPOTHESIS),
            "fixed_nb_of_instances": EmptyExplainableObject()
        }

    def __init__(self, name: str, server_type: ExplainableObject, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity, average_carbon_intensity: ExplainableQuantity,
                 server_utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication, power, lifespan, idle_power, ram, compute,
            power_usage_effectiveness, average_carbon_intensity, server_utilization_rate, base_ram_consumption,
            base_compute_consumption, storage, fixed_nb_of_instances)
