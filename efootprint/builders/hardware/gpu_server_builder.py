from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core import Storage
from efootprint.core.hardware.server import Server

BLOOM_PAPER_SOURCE = Source("Estimating the Carbon Footprint of BLOOM", "https://arxiv.org/abs/2211.05100")


class GPUServer(Server):
    @classmethod
    def default_values(cls):
        return {
                "gpu_power": SourceValue(400 * u.W, BLOOM_PAPER_SOURCE, "GPU Power"),
                "gpu_idle_power": SourceValue(50 * u.W, BLOOM_PAPER_SOURCE, "GPU idle power"),
                "ram_per_gpu": SourceValue(80 * u.GB, BLOOM_PAPER_SOURCE, label="RAM per GPU"),
                "carbon_footprint_fabrication_one_gpu": SourceValue(150 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint one GPU"),
                "carbon_footprint_fabrication_server_without_gpu": SourceValue(
                2500 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint without GPU"),
                "nb_gpus_per_instance": SourceValue(4 * u.dimensionless, Sources.HYPOTHESIS, label="Number of GPUs"),
                "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
                "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
                "server_utilization_rate": SourceValue(1 * u.dimensionless, Sources.HYPOTHESIS),
                "base_cpu_consumption": SourceValue(0 * u.core, Sources.HYPOTHESIS),
                "base_ram_consumption": SourceValue(0 * u.GB, Sources.HYPOTHESIS),
                "data_storage_duration": SourceValue(5 * u.year, Sources.HYPOTHESIS),
                "data_replication_factor": SourceValue(2 * u.dimensionless, Sources.HYPOTHESIS),
                "base_storage_need": SourceValue(200 * u.GB, Sources.HYPOTHESIS)
                }

    @classmethod
    def list_values(cls):
        return {"base_efootprint_class_str": ["Autoscaling", "OnPremise", "Serverless"]}

    @classmethod
    def conditional_list_values(cls):
        return {}
    
    def __init__(self, name: str, server_type: SourceObject,  gpu_power: SourceValue, gpu_idle_power: SourceValue, 
                 ram_per_gpu: SourceValue, carbon_footprint_fabrication_one_gpu: SourceValue,
                 average_carbon_intensity: SourceValue, nb_gpus_per_instance: SourceValue,
                 carbon_footprint_fabrication_without_gpu: SourceValue, lifespan: SourceValue,
                 power_usage_effectiveness: SourceValue, server_utilization_rate: SourceValue,
                 base_cpu_consumption: SourceValue, base_ram_consumption: SourceValue, storage: Storage,
                 fixed_nb_of_instances: SourceValue | EmptyExplainableObject = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power=SourceValue(0 * u.W), ram=SourceValue(0 * u.GB),
            cpu_cores=SourceValue(0 * u.core), power_usage_effectiveness=power_usage_effectiveness,
            average_carbon_intensity=average_carbon_intensity, server_utilization_rate=server_utilization_rate,
            base_cpu_consumption=base_cpu_consumption, base_ram_consumption=base_ram_consumption, storage=storage,
            fixed_nb_of_instances=fixed_nb_of_instances)
        self.gpu_power = gpu_power.set_label(f"{self.name} GPU power")
        self.gpu_idle_power = gpu_idle_power.set_label(f"{self.name} GPU idle power")
        self.ram_per_gpu = ram_per_gpu.set_label(f"{self.name} RAM per GPU")
        self.nb_gpus_per_instance = nb_gpus_per_instance.set_label(f"{self.name} number of GPUs")
        self.carbon_footprint_fabrication_without_gpu = carbon_footprint_fabrication_without_gpu.set_label(
            f"{self.name} carbon footprint without GPU")
        self.carbon_footprint_fabrication_one_gpu = carbon_footprint_fabrication_one_gpu.set_label(
            f"{self.name} carbon footprint one GPU")

    def calculated_attributes(self):
        return ["carbon_footprint_fabrication", "power", "idle_power", "ram", "cpu_cores"]

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (self.carbon_footprint_fabrication_without_gpu
                + self.nb_gpus_per_instance * self.carbon_footprint_fabrication_one_gpu
                ).set_label(f"{self.name} carbon footprint fabrication")

    def update_power(self):
        self.power = (self.gpu_power * self.nb_gpus_per_instance).set_label(f"{self.name} power")

    def update_idle_power(self):
        self.idle_power = (self.gpu_idle_power * self.nb_gpus_per_instance).set_label(f"{self.name} idle power")

    def update_ram(self):
        self.ram = (self.ram_per_gpu * self.nb_gpus_per_instance).set_label(f"{self.name} RAM")

    def update_cpu_cores(self):
        nb_of_cpu_cores_per_gpu = SourceValue(1 * u.core, label="1 CPU core / GPU")
        self.cpu_cores = (self.nb_gpus_per_instance * nb_of_cpu_cores_per_gpu).set_label(f"{self.name} CPU cores")
