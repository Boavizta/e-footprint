from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.storage_defaults import default_ssd
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.servers.autoscaling import Autoscaling
from efootprint.core.hardware.servers.on_premise import OnPremise
from efootprint.core.hardware.servers.serverless import Serverless

BLOOM_PAPER_SOURCE = Source("Estimating the Carbon Footprint of BLOOM", "https://arxiv.org/abs/2211.05100")
CPU_CORE_PER_GPU = SourceValue(1 * u.core, label="1 CPU core / GPU")


def generative_ai_gpu_server_builder(
        base_efootprint_class, average_carbon_intensity, fixed_nb_of_instances=None, 
        gpu_power=None, gpu_idle_power=None, nb_gpus_per_instance=None, ram_per_gpu=None, 
        carbon_footprint_fabrication_server_without_gpu=None, carbon_footprint_fabrication_one_gpu=None):
    assert base_efootprint_class in [Autoscaling, OnPremise, Serverless], \
        f"Invalid base efootprint class {base_efootprint_class}"

    if gpu_power is None:
        gpu_power = SourceValue(400 * u.W, BLOOM_PAPER_SOURCE, "GPU Power")
    if gpu_idle_power is None:
        gpu_idle_power = SourceValue(50 * u.W, BLOOM_PAPER_SOURCE, "GPU idle power")
    if nb_gpus_per_instance is None:
        nb_gpus_per_instance = SourceValue(4 * u.dimensionless, Sources.USER_DATA, label="Number of GPUs")
    if ram_per_gpu is None:
        ram_per_gpu = SourceValue(80 * u.GB, BLOOM_PAPER_SOURCE, label="RAM per GPU")
    if carbon_footprint_fabrication_server_without_gpu is None:
        carbon_footprint_fabrication_server_without_gpu = SourceValue(
            2500 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint without GPU")
    if carbon_footprint_fabrication_one_gpu is None:
        carbon_footprint_fabrication_one_gpu = SourceValue(150 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint one GPU")

    kwargs = {}
    if base_efootprint_class == OnPremise:
        assert fixed_nb_of_instances is not None, "Fixed number of instances must be provided for OnPremise server"
        kwargs["fixed_nb_of_instances"] = fixed_nb_of_instances

    return base_efootprint_class(
        "GPU server",
        carbon_footprint_fabrication=(
                carbon_footprint_fabrication_server_without_gpu + nb_gpus_per_instance 
                * carbon_footprint_fabrication_one_gpu
            ).set_label("default"),
        power=(gpu_power * nb_gpus_per_instance).set_label("default"),
        lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
        idle_power=(gpu_idle_power * nb_gpus_per_instance).set_label("default"),
        ram=(ram_per_gpu * nb_gpus_per_instance).set_label("default"),
        cpu_cores=(nb_gpus_per_instance * CPU_CORE_PER_GPU).set_label("default"),
        power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
        average_carbon_intensity=average_carbon_intensity,
        server_utilization_rate=SourceValue(1 * u.dimensionless, Sources.HYPOTHESIS),
        base_cpu_consumption=SourceValue(0 * u.core, Sources.HYPOTHESIS),
        base_ram_consumption=SourceValue(0 * u.GB, Sources.HYPOTHESIS),
        storage=default_ssd(
            data_storage_duration=SourceValue(5 * u.year, Sources.HYPOTHESIS),
            data_replication_factor=SourceValue(2 * u.dimensionless, Sources.HYPOTHESIS),
            base_storage_need=SourceValue(200 * u.GB, Sources.HYPOTHESIS)),
        **kwargs
        )
