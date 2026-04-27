from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerBase, ServerTypes


class Server(ServerBase):
    """A physical or virtual machine with CPU and RAM that runs jobs as part of a digital service. Resource use is computed from the jobs it hosts and rolled up into an hourly energy and fabrication footprint."""

    def _abc_marker(self):
        pass  # silent override

    disambiguation = (
        "Use {class:Server} for CPU-bound workloads with manually defined hardware specifications. "
        "Use {class:GPUServer} for GPU-bound workloads such as model training or inference. "
        "Use {class:BoaviztaCloudServer} for cloud instances whose hardware specifications and "
        "fabrication footprint should be looked up automatically from Boavizta reference data.")

    pitfalls = (
        "{param:Server.fixed_nb_of_instances} only applies when {param:Server.server_type} is on-premise. "
        "Setting it on an autoscaling or serverless server has no effect; setting it too low on an on-premise "
        "server raises an error when peak demand exceeds capacity.")

    interactions = (
        "Construct {class:Server} with all required quantities, then attach {class:Job}s by passing the server "
        "to each job's constructor. The server is wired into the system through the jobs that reference it.")

    param_descriptions = {
        "server_type": (
            "Provisioning model of the server, which decides how many instances are attributed in each hour. "
            "Autoscaling rounds the hourly demand up to a whole number of instances, so an instance is billed "
            "even when it is only partially loaded. Serverless attributes only the fractional instance-hours "
            "actually used. On-premise holds a fixed number of physical instances over the whole modeling "
            "period (capacity sized to peak demand, or to {param:Server.fixed_nb_of_instances} if set)."),
        "carbon_footprint_fabrication": (
            "Embodied carbon emitted to manufacture one server instance. Amortised over the lifespan when "
            "computing the hourly fabrication footprint."),
        "power": (
            "Electrical power drawn by one fully-loaded instance, before applying datacenter overhead."),
        "lifespan": (
            "Expected time before the server is replaced. Embodied carbon is amortised over this duration."),
        "idle_power": (
            "Electrical power drawn by one instance that is on but not running any jobs."),
        "ram": (
            "Total memory available on one instance. Combined with {param:Server.utilization_rate} to obtain "
            "the memory usable by jobs."),
        "compute": (
            "Total compute capacity available on one instance, expressed in CPU cores."),
        "power_usage_effectiveness": (
            "Datacenter overhead multiplier applied to instance power to account for cooling, lighting, and "
            "other site-wide energy use."),
        "average_carbon_intensity": (
            "Average grid carbon intensity at the location where the server runs, used to convert energy "
            "consumption into carbon emissions."),
        "utilization_rate": (
            "Fraction of an instance's RAM and compute that is considered usable by jobs after operating-system "
            "and headroom overhead."),
        "base_ram_consumption": (
            "RAM consumed per instance independently of jobs, for the operating system, agents, and idle services."),
        "base_compute_consumption": (
            "Compute consumed per instance independently of jobs."),
        "storage": (
            "Backing {class:Storage} attached to the server. Storage emissions are reported separately from "
            "the server's own footprint."),
        "fixed_nb_of_instances": (
            "On-premise only: number of physical machines deployed. Used to detect when traffic exceeds "
            "capacity. Leave empty for autoscaling and serverless server types."),
    }

    default_values =  {
            "server_type": ServerTypes.autoscaling(),
            "carbon_footprint_fabrication": SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(300 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "idle_power": SourceValue(50 * u.W),
            "ram": SourceValue(128 * u.GB_ram),
            "compute": SourceValue(24 * u.cpu_core),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless),
            "average_carbon_intensity": SourceValue(400 * u.g / u.kWh),
            "utilization_rate": SourceValue(0.9 * u.dimensionless),
            "base_ram_consumption": SourceValue(0 * u.GB_ram),
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
