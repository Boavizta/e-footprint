from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerBase, ServerTypes

BLOOM_PAPER_SOURCE = Source("Estimating the Carbon Footprint of BLOOM", "https://arxiv.org/abs/2211.05100")


class GPUServer(ServerBase):
    """A server whose compute capacity is expressed in GPUs rather than CPU cores, with separate fabrication and power figures for the GPUs and the rest of the chassis."""

    def _abc_marker(self):
        pass  # silent override

    disambiguation = (
        "Use {class:GPUServer} when {param:GPUServer.compute} is measured in GPUs. Hardware specifications are "
        "decomposed per-GPU so that varying the GPU count adjusts power, fabrication footprint, and available "
        "memory consistently. Use {class:Server} for CPU-bound workloads.")

    pitfalls = (
        "{class:GPUServer} can only host {class:GPUJob}s. Wiring a {class:Job} that has CPU-core compute units "
        "to a {class:GPUServer} fails when the model is computed.")

    param_descriptions = {
        "server_type": (
            "Provisioning model of the server. Same semantics as {param:Server.server_type}: autoscaling, "
            "serverless, or on-premise."),
        "gpu_power": (
            "Electrical power drawn by one fully-loaded GPU."),
        "gpu_idle_power": (
            "Electrical power drawn by a GPU that is on but not processing."),
        "ram_per_gpu": (
            "Memory available per GPU. Total instance RAM is derived by multiplying with the GPU count."),
        "carbon_footprint_fabrication_per_gpu": (
            "Embodied carbon emitted to manufacture one GPU."),
        "average_carbon_intensity": (
            "Average grid carbon intensity at the location where the server runs, used to convert energy "
            "consumption into carbon emissions."),
        "compute": (
            "Number of GPUs in one server instance."),
        "carbon_footprint_fabrication_without_gpu": (
            "Embodied carbon of one server chassis excluding GPUs (CPUs, motherboard, chassis)."),
        "lifespan": (
            "Expected time before the server is replaced. Embodied carbon is amortised over this duration."),
        "power_usage_effectiveness": (
            "Datacenter overhead multiplier applied to the server's power consumption to account for cooling "
            "and other site-wide energy use."),
        "utilization_rate": (
            "Fraction of available GPU and memory time considered usable after operating-system and headroom overhead."),
        "base_compute_consumption": (
            "GPU consumed per instance independently of jobs."),
        "base_ram_consumption": (
            "GPU memory consumed per instance independently of jobs."),
        "storage": (
            "Backing {class:Storage} attached to the server."),
        "fixed_nb_of_instances": (
            "On-premise only: number of physical servers deployed. Leave empty for autoscaling and serverless "
            "server types."),
    }

    default_values =  {
            "server_type": ServerTypes.serverless(),
            "gpu_power": SourceValue(400 * u.W / u.gpu, BLOOM_PAPER_SOURCE, "GPU Power"),
            "gpu_idle_power": SourceValue(50 * u.W / u.gpu, BLOOM_PAPER_SOURCE, "GPU idle power"),
            "ram_per_gpu": SourceValue(80 * u.GB_ram / u.gpu, BLOOM_PAPER_SOURCE, label="RAM per GPU"),
            "carbon_footprint_fabrication_per_gpu": SourceValue(
                150 * u.kg / u.gpu, BLOOM_PAPER_SOURCE, "Carbon footprint one GPU"),
            "average_carbon_intensity": SourceValue(400 * u.g / u.kWh),
            "carbon_footprint_fabrication_without_gpu": SourceValue(
            2500 * u.kg, BLOOM_PAPER_SOURCE, "Carbon footprint without GPU"),
            "compute": SourceValue(4 * u.gpu),
            "lifespan": SourceValue(6 * u.year),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless),
            "utilization_rate": SourceValue(1 * u.dimensionless),
            "base_compute_consumption": SourceValue(0 * u.gpu),
            "base_ram_consumption": SourceValue(0 * u.GB_ram),
            "fixed_nb_of_instances": EmptyExplainableObject()
            }
    
    def __init__(self, name: str, server_type: ExplainableObject,  gpu_power: ExplainableQuantity,
                 gpu_idle_power: ExplainableQuantity, ram_per_gpu: ExplainableQuantity,
                 carbon_footprint_fabrication_per_gpu: ExplainableQuantity,
                 average_carbon_intensity: ExplainableQuantity, compute: ExplainableQuantity,
                 carbon_footprint_fabrication_without_gpu: ExplainableQuantity, lifespan: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity, utilization_rate: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 storage: Storage, fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power=SourceValue(0 * u.W), ram=SourceValue(0 * u.GB_ram),
            compute=compute, power_usage_effectiveness=power_usage_effectiveness,
            average_carbon_intensity=average_carbon_intensity, utilization_rate=utilization_rate,
            base_compute_consumption=base_compute_consumption, base_ram_consumption=base_ram_consumption,
            storage=storage, fixed_nb_of_instances=fixed_nb_of_instances)
        self.gpu_power = gpu_power.set_label("GPU power")
        self.gpu_idle_power = gpu_idle_power.set_label("GPU idle power")
        self.ram_per_gpu = ram_per_gpu.set_label("RAM per GPU")
        self.carbon_footprint_fabrication_without_gpu = carbon_footprint_fabrication_without_gpu.set_label(
            "Carbon footprint without GPU")
        self.carbon_footprint_fabrication_per_gpu = carbon_footprint_fabrication_per_gpu.set_label(
            "Carbon footprint one GPU")

    @property
    def calculated_attributes(self):
        return ["carbon_footprint_fabrication", "power", "idle_power", "ram"] + super().calculated_attributes

    def update_carbon_footprint_fabrication(self):
        """Embodied carbon of one server instance, equal to the chassis fabrication footprint plus the per-GPU fabrication footprint times the GPU count."""
        self.carbon_footprint_fabrication = (self.carbon_footprint_fabrication_without_gpu
                + self.compute * self.carbon_footprint_fabrication_per_gpu
                ).set_label("Carbon footprint fabrication")

    def update_power(self):
        """Power drawn by one fully-loaded instance, equal to the per-GPU power times the GPU count."""
        self.power = (self.gpu_power * self.compute).set_label("Power")

    def update_idle_power(self):
        """Power drawn by one idle instance, equal to the per-GPU idle power times the GPU count."""
        self.idle_power = (self.gpu_idle_power * self.compute).set_label("Idle power")

    def update_ram(self):
        """Total memory of one instance, equal to per-GPU memory times the GPU count."""
        self.ram = (self.ram_per_gpu * self.compute).set_label("RAM").to(u.GB_ram)
