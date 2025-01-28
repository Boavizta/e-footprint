from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.hardware import Hardware
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_random_hourly_usage_df
from efootprint.logger import logger

from time import time

start = time()

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
    ram=SourceValue(128 * u.GB, source=None),
    compute=SourceValue(24 * u.cpu_core, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    server_utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    base_ram_consumption=SourceValue(300 * u.MB, source=None),
    base_compute_consumption=SourceValue(2 * u.cpu_core, source=None),
    storage=storage
)

serverless_server = BoaviztaCloudServer.from_defaults(
    "serverless cloud functions",
    server_type=ServerTypes.serverless(),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    server_utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
    storage=Storage.ssd()
)

on_premise_gpu_server = GPUServer.from_defaults(
    "on premise GPU server",
    server_type=ServerTypes.on_premise(),
    lifespan=SourceValue(6 * u.year, source=None),
    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, source=None),
    average_carbon_intensity=SourceValue(100 * u.g / u.kWh, source=None),
    server_utilization_rate=SourceValue(0.9 * u.dimensionless, source=None),
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

streaming_step = UsageJourneyStep(
    "20 min streaming",
    user_time_spent=SourceValue(20 * u.min, source=None),
    jobs=[web_application_job, genai_model_job, video_streaming_job, manually_written_job]
    )

usage_journey = UsageJourney("user journey", uj_steps=[streaming_step])

network = Network(
        "network",
        bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))

usage_pattern = UsagePattern(
    "usage pattern",
    usage_journey=usage_journey,
    devices=[
        Hardware(name="device on which the user journey is made",
                 carbon_footprint_fabrication=SourceValue(156 * u.kg, source=None),
                 power=SourceValue(50 * u.W, source=None),
                 lifespan=SourceValue(6 * u.year, source=None),
                 fraction_of_usage_time=SourceValue(7 * u.hour / u.day, source=None))],
    network=network,
    country=country_generator(
            "devices country", "its 3 letter shortname, for example FRA", SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
    hourly_usage_journey_starts=SourceHourlyValues(create_random_hourly_usage_df(timespan=3 * u.year)))

system = System("system", usage_patterns=[usage_pattern])

logger.info(f"computation took {round((time() - start), 3)} seconds")
