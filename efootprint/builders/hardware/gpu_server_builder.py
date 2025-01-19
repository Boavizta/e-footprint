from typing import List, Type

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object_generator import ModelingObjectGenerator
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.storage_defaults import default_ssd
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server

BLOOM_PAPER_SOURCE = Source("Estimating the Carbon Footprint of BLOOM", "https://arxiv.org/abs/2211.05100")


class GPUServerBuilder(ModelingObjectGenerator):
    _default_values = {
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
    
    def __init__(self, name: str, gpu_power=None, gpu_idle_power=None, ram_per_gpu=None,
                 carbon_footprint_fabrication_one_gpu=None):
        super().__init__(name)
        self.gpu_power = (gpu_power or self.default_value("gpu_power")).set_label("GPU power")
        self.gpu_idle_power = (gpu_idle_power or self.default_value("gpu_idle_power")).set_label("GPU idle power")
        self.ram_per_gpu = (ram_per_gpu or self.default_value("ram_per_gpu")).set_label("RAM per GPU")
        self.carbon_footprint_fabrication_one_gpu = (carbon_footprint_fabrication_one_gpu or self.default_value(
            "carbon_footprint_fabrication_one_gpu")).set_label("Carbon footprint one GPU")
        self.nb_of_cpu_cores_per_gpu = SourceValue(1 * u.core, label="1 CPU core / GPU")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[Type["ModelingObject"]]:
        return []

    @property
    def systems(self) -> List:
        return []

    def generate_gpu_server(
            self, name, base_efootprint_class_str: str, average_carbon_intensity: SourceValue,
            nb_gpus_per_instance: SourceValue, fixed_nb_of_instances=None,
            carbon_footprint_fabrication_server_without_gpu=None, lifespan=None, power_usage_effectiveness=None,
            server_utilization_rate=None, base_cpu_consumption=None, base_ram_consumption=None,
            data_storage_duration=None, data_replication_factor=None, base_storage_need=None):
        base_efootprint_class = {
            "Autoscaling": Autoscaling, "OnPremise": OnPremise, "Serverless": Serverless
        }[base_efootprint_class_str]

        kwargs = {}
        if base_efootprint_class_str != "OnPremise":
            assert fixed_nb_of_instances is None, \
                "Fixed number of instances can’t be provided for non on-premise servers"
        else:
            kwargs["fixed_nb_of_instances"] = fixed_nb_of_instances

        return base_efootprint_class(
            name,
            carbon_footprint_fabrication=(
                (carbon_footprint_fabrication_server_without_gpu 
                 or self.default_value("carbon_footprint_fabrication_server_without_gpu"))
                + nb_gpus_per_instance * self.carbon_footprint_fabrication_one_gpu
                ).set_label("default"),
            power=(self.gpu_power * nb_gpus_per_instance).set_label("default"),
            lifespan=lifespan or self.default_value("lifespan"),
            idle_power=(self.gpu_idle_power * nb_gpus_per_instance).set_label("default"),
            ram=(self.ram_per_gpu * nb_gpus_per_instance).set_label("default"),
            cpu_cores=((nb_gpus_per_instance or self.default_value("nb_gpus_per_instance")
                        ) * self.nb_of_cpu_cores_per_gpu).set_label("default"),
            power_usage_effectiveness=power_usage_effectiveness or self.default_value("power_usage_effectiveness"),
            average_carbon_intensity=average_carbon_intensity,
            server_utilization_rate=server_utilization_rate or self.default_value("server_utilization_rate"),
            base_cpu_consumption=base_cpu_consumption or self.default_value("base_cpu_consumption"),
            base_ram_consumption=base_ram_consumption or self.default_value("base_ram_consumption"),
            storage=default_ssd(
                data_storage_duration=data_storage_duration or self.default_value("data_storage_duration"),
                data_replication_factor=data_replication_factor or self.default_value("data_replication_factor"),
                base_storage_need=base_storage_need or self.default_value("base_storage_need")),
            **kwargs
            )
