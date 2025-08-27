from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerBase, ServerTypes


class Server(ServerBase):
    def _abc_marker(self):
        pass  # silent override

    default_values =  {
            "server_type": ServerTypes.autoscaling(),
            "carbon_footprint_fabrication": SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(300 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "idle_power": SourceValue(50 * u.W),
            "ram": SourceValue(128 * u.GB),
            "compute": SourceValue(24 * u.cpu_core),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless),
            "average_carbon_intensity": SourceValue(400 * u.g / u.kWh),
            "utilization_rate": SourceValue(0.9 * u.dimensionless),
            "base_ram_consumption": SourceValue(0 * u.GB),
            "base_compute_consumption": SourceValue(0 * u.cpu_core),
            "fixed_nb_of_instances": EmptyExplainableObject()
        }

    def __init__(self, name: str, server_type: ExplainableObject, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity, average_carbon_intensity: ExplainableQuantity,
                 utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication, power, lifespan, idle_power, ram, compute,
            power_usage_effectiveness, average_carbon_intensity, utilization_rate, base_ram_consumption,
            base_compute_consumption, storage, fixed_nb_of_instances)
