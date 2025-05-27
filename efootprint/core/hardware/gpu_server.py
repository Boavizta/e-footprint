from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerBase, ServerTypes

BLOOM_PAPER_SOURCE = Source("Estimating the Carbon Footprint of BLOOM", "https://arxiv.org/abs/2211.05100")


class GPUServer(ServerBase):
    @classmethod
    def default_values(cls):
        return {
            "server_type": ServerTypes.serverless(),
            "gpu_power": SourceValue(400 * u.W / u.gpu, BLOOM_PAPER_SOURCE, "GPU Power"),
            "gpu_idle_power": SourceValue(50 * u.W / u.gpu, BLOOM_PAPER_SOURCE, "GPU idle power"),
            "ram_per_gpu": SourceValue(80 * u.GB / u.gpu, BLOOM_PAPER_SOURCE, label="RAM per GPU"),
            "carbon_footprint_fabrication_per_gpu": SourceValue(
                150 * u.kg / u.gpu, BLOOM_PAPER_SOURCE, "Carbon footprint one GPU"),
            "average_carbon_intensity": SourceValue(100 * u.g / u.kWh),
            "carbon_footprint_fabrication_without_gpu": SourceValue(
            2500 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint without GPU"),
            "compute": SourceValue(4 * u.gpu),
            "lifespan": SourceValue(6 * u.year),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless),
            "server_utilization_rate": SourceValue(1 * u.dimensionless),
            "base_compute_consumption": SourceValue(0 * u.gpu),
            "base_ram_consumption": SourceValue(0 * u.GB),
            "fixed_nb_of_instances": EmptyExplainableObject()
            }
    
    def __init__(self, name: str, server_type: ExplainableObject,  gpu_power: ExplainableQuantity,
                 gpu_idle_power: ExplainableQuantity, ram_per_gpu: ExplainableQuantity,
                 carbon_footprint_fabrication_per_gpu: ExplainableQuantity,
                 average_carbon_intensity: ExplainableQuantity, compute: ExplainableQuantity,
                 carbon_footprint_fabrication_without_gpu: ExplainableQuantity, lifespan: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity, server_utilization_rate: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, base_ram_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power=SourceValue(0 * u.W), ram=SourceValue(0 * u.GB),
            compute=compute, power_usage_effectiveness=power_usage_effectiveness,
            average_carbon_intensity=average_carbon_intensity, server_utilization_rate=server_utilization_rate,
            base_compute_consumption=base_compute_consumption, base_ram_consumption=base_ram_consumption,
            storage=storage, fixed_nb_of_instances=fixed_nb_of_instances)
        self.gpu_power = gpu_power.set_label(f"{self.name} GPU power")
        self.gpu_idle_power = gpu_idle_power.set_label(f"{self.name} GPU idle power")
        self.ram_per_gpu = ram_per_gpu.set_label(f"{self.name} RAM per GPU")
        self.carbon_footprint_fabrication_without_gpu = carbon_footprint_fabrication_without_gpu.set_label(
            f"{self.name} carbon footprint without GPU")
        self.carbon_footprint_fabrication_per_gpu = carbon_footprint_fabrication_per_gpu.set_label(
            f"{self.name} carbon footprint one GPU")

    @property
    def calculated_attributes(self):
        return ["carbon_footprint_fabrication", "power", "idle_power", "ram"] + super().calculated_attributes

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (self.carbon_footprint_fabrication_without_gpu
                + self.compute * self.carbon_footprint_fabrication_per_gpu
                ).set_label(f"{self.name} carbon footprint fabrication")

    def update_power(self):
        self.power = (self.gpu_power * self.compute).set_label(f"{self.name} power")

    def update_idle_power(self):
        self.idle_power = (self.gpu_idle_power * self.compute).set_label(f"{self.name} idle power")

    def update_ram(self):
        self.ram = (self.ram_per_gpu * self.compute).set_label(f"{self.name} RAM")
