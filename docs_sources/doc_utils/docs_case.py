from time import time

import numpy as np
from pint import Quantity

from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

start = time()

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job, GPUJob
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.system import System
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_random_source_hourly_values, create_hourly_usage_from_frequency
from efootprint.logger import logger
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")


storage = Storage(
    "storage",
    carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB, source=None),
    power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, source=None),
    lifespan=SourceValue(6 * u.years, source=None),
    idle_power=SourceValue(0 * u.W, source=None),
    storage_capacity=SourceValue(1 * u.TB, source=None),
    data_replication_factor=SourceValue(3 * u.dimensionless, source=None),
    data_storage_duration=SourceValue(2 * u.year, source=None),
    base_storage_need=SourceValue(0 * u.TB, source=None)
)

autoscaling_server = Server(
    "server",
    server_type=ServerTypes.autoscaling(),
    carbon_footprint_fabrication=SourceValue(600 * u.kg, source=None),
    power=SourceValue(300 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power=SourceValue(50 * u.W, source=None),
    ram=SourceValue(128 * u.GB_ram, source=None),
    compute=SourceValue(24 * u.cpu_core, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    base_ram_consumption=SourceValue(300 * u.MB_ram, source=None),
    base_compute_consumption=SourceValue(2 * u.cpu_core, source=None),
    storage=storage
)

serverless_server = BoaviztaCloudServer.from_defaults(
    "serverless cloud functions",
    server_type=ServerTypes.serverless(),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    storage=Storage.ssd()
)

on_premise_gpu_server = GPUServer.from_defaults(
    "on premise GPU server",
    server_type=ServerTypes.on_premise(),
    lifespan=SourceValue(6 * u.year, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    storage=Storage.ssd()
)

video_streaming = VideoStreaming.from_defaults("Video streaming service", server=autoscaling_server)
web_application = WebApplication.from_defaults("Web application service", server=serverless_server)
genai_model = GenAIModel.from_defaults("Generative AI model", server=on_premise_gpu_server)

video_streaming_job = VideoStreamingJob.from_defaults(
    "Video streaming job", service=video_streaming, video_duration=SourceValue(20 * u.min))
web_application_job = WebApplicationJob.from_defaults("Web application job", service=web_application)
genai_model_job = GenAIJob.from_defaults("Generative AI model job", service=genai_model)
manually_written_job = Job.from_defaults("Manually defined job", server=autoscaling_server)
custom_gpu_job = GPUJob.from_defaults("Manually defined GPU job", server=on_premise_gpu_server)

streaming_step = UsageJourneyStep(
    "20 min streaming",
    user_time_spent=SourceValue(20 * u.min, source=None),
    jobs=[web_application_job, genai_model_job, video_streaming_job, manually_written_job, custom_gpu_job]
    )

usage_journey = UsageJourney("user journey", uj_steps=[streaming_step])

network = Network(
        "network",
        bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))
random_hourly_usage_journey_starts = create_random_source_hourly_values(timespan=3 * u.year)
random_hourly_usage_journey_starts.source = None
usage_pattern = UsagePattern(
    "usage pattern",
    usage_journey=usage_journey,
    devices=[
        Device(name="device on which the user journey is made",
                 carbon_footprint_fabrication=SourceValue(156 * u.kg, source=None),
                 power=SourceValue(50 * u.W, source=None),
                 lifespan=SourceValue(6 * u.year, source=None),
                 fraction_of_usage_time=SourceValue(7 * u.hour / u.day, source=None))],
    network=network,
    country=country_generator(
            "devices country", "its 3 letter shortname, for example FRA", SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
    hourly_usage_journey_starts=random_hourly_usage_journey_starts)

edge_storage = EdgeStorage(
    "edge SSD storage",
    carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB, source=None),
    power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, source=None),
    lifespan=SourceValue(6 * u.years, source=None),
    idle_power=SourceValue(0.1 * u.W, source=None),
    storage_capacity=SourceValue(256 * u.GB, source=None),
    base_storage_need=SourceValue(10 * u.GB, source=None),
)

edge_computer = EdgeComputer(
    "edge computer",
    carbon_footprint_fabrication=SourceValue(60 * u.kg, source=None),
    power=SourceValue(30 * u.W, source=None),
    lifespan=SourceValue(8 * u.year, source=None),
    idle_power=SourceValue(5 * u.W, source=None),
    ram=SourceValue(16 * u.GB_ram, source=None),
    compute=SourceValue(8 * u.cpu_core, source=None),
    base_ram_consumption=SourceValue(1 * u.GB_ram, source=None),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core, source=None),
    storage=edge_storage
)

edge_process = RecurrentEdgeProcess(
    "edge process",
    edge_device=edge_computer,
    recurrent_compute_needed=SourceRecurrentValues(
        Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core), source=None),
    recurrent_ram_needed=SourceRecurrentValues(
        Quantity(np.array([2] * 168, dtype=np.float32), u.GB_ram), source=None),
    recurrent_storage_needed=SourceRecurrentValues(
        Quantity(np.array([200] * 168, dtype=np.float32), u.kB), source=None)
)

edge_appliance = EdgeAppliance(
    "edge appliance",
    carbon_footprint_fabrication=SourceValue(60 * u.kg, source=None),
    power=SourceValue(30 * u.W, source=None),
    lifespan=SourceValue(8 * u.year, source=None),
    idle_power=SourceValue(5 * u.W, source=None)
)

edge_workload = RecurrentEdgeWorkload(
    "edge workload",
    edge_device=edge_appliance,
    recurrent_workload=SourceRecurrentValues(
        Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent), source=None)
)

ram_component = EdgeRAMComponent(
    "edge RAM component",
    carbon_footprint_fabrication=SourceValue(20 * u.kg, source=None),
    power=SourceValue(10 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power=SourceValue(2 * u.W, source=None),
    ram=SourceValue(8 * u.GB_ram, source=None),
    base_ram_consumption=SourceValue(1 * u.GB_ram, source=None)
)

cpu_component = EdgeCPUComponent(
    "edge CPU component",
    carbon_footprint_fabrication=SourceValue(20 * u.kg, source=None),
    power=SourceValue(15 * u.W, source=None),
    lifespan=SourceValue(6 * u.year, source=None),
    idle_power=SourceValue(3 * u.W, source=None),
    compute=SourceValue(4 * u.cpu_core, source=None),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core, source=None)
)

edge_device = EdgeDevice(
    "custom edge device",
    structure_carbon_footprint_fabrication=SourceValue(50 * u.kg, source=None),
    components=[ram_component, cpu_component],
    lifespan=SourceValue(6 * u.year, source=None)
)

ram_need = RecurrentEdgeComponentNeed(
    "RAM need",
    edge_component=ram_component,
    recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB_ram), source=None)
)
cpu_need = RecurrentEdgeComponentNeed(
    "CPU need",
    edge_component=cpu_component,
    recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core), source=None)
)
edge_device_need = RecurrentEdgeDeviceNeed(
    "custom edge device need",
    edge_device=edge_device,
    recurrent_edge_component_needs=[ram_need, cpu_need]
)

edge_function = EdgeFunction(
    "edge function",
    recurrent_edge_device_needs=[edge_process, edge_workload, edge_device_need]
)

edge_usage_journey = EdgeUsageJourney(
    "edge usage journey",
    edge_functions=[edge_function],
    usage_span=SourceValue(6 * u.year, source=None)
)

edge_usage_pattern = EdgeUsagePattern(
    "Default edge usage pattern",
    edge_usage_journey=edge_usage_journey,
    country=country_generator(
            "devices country", "its 3 letter shortname, for example FRA",
        SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
    hourly_edge_usage_journey_starts=create_hourly_usage_from_frequency(
        timespan=6 * u.year, input_volume=1000, frequency='weekly',
        active_days=[0, 1, 2, 3, 4, 5], hours=[8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19])
        )

system = System("system", usage_patterns=[usage_pattern], edge_usage_patterns=[edge_usage_pattern])

logger.info(f"computation took {round((time() - start), 3)} seconds")
