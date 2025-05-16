from time import time

from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.tools import time_it

start = time()

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
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
from efootprint.core.system import System
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_random_hourly_usage_df
from efootprint.logger import logger
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")

nb_of_servers_of_each_type = 2
nb_of_uj_per_each_server_type = 2
nb_of_uj_steps_per_uj = 4

usage_patterns = []
for server_index in range(1, nb_of_servers_of_each_type + 1):
    autoscaling_server = Server.from_defaults(
        f"server {server_index}",
        server_type=ServerTypes.autoscaling(),
        storage=Storage.ssd()
    )

    serverless_server = BoaviztaCloudServer.from_defaults(
        f"serverless cloud functions {server_index}",
        server_type=ServerTypes.serverless(),
        storage=Storage.ssd()
    )

    on_premise_gpu_server = GPUServer.from_defaults(
        f"on premise GPU server {server_index}",
        server_type=ServerTypes.on_premise(),
        storage=Storage.ssd()
    )

    video_streaming = VideoStreaming.from_defaults(f"Video streaming service {server_index}", server=autoscaling_server)
    web_application = WebApplication.from_defaults(f"Web application service {server_index}", server=serverless_server)
    genai_model = GenAIModel.from_defaults(f"Generative AI model {server_index}", server=on_premise_gpu_server)

    for uj_index in range(1, nb_of_uj_per_each_server_type + 1):
        uj_steps = []
        for uj_step_index in range(1, nb_of_uj_steps_per_uj + 1):
            video_streaming_job = VideoStreamingJob.from_defaults(
                f"Video streaming job", service=video_streaming, video_duration=SourceValue(20 * u.min))
            web_application_job = WebApplicationJob.from_defaults(f"Web application job", service=web_application)
            genai_model_job = GenAIJob.from_defaults(f"Generative AI model job", service=genai_model)
            manually_written_job = Job.from_defaults(f"Manually defined job", server=autoscaling_server)
            custom_gpu_job = GPUJob.from_defaults(f"Manually defined GPU job", server=on_premise_gpu_server)

            uj_steps.append(UsageJourneyStep(
                "20 min streaming",
                user_time_spent=SourceValue(20 * u.min, source=None),
                jobs=[web_application_job, genai_model_job, video_streaming_job, manually_written_job, custom_gpu_job]
                ))

        usage_journey = UsageJourney("user journey", uj_steps=uj_steps)

        network = Network(
                "network",
                bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))

        usage_patterns.append(UsagePattern(
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
            hourly_usage_journey_starts=SourceHourlyValues(create_random_hourly_usage_df(timespan=3 * u.year)))
        )

system = System("system", usage_patterns=usage_patterns)

logger.info(f"computation took {round((time() - start), 3)} seconds")

@time_it
def timed_system_to_json(system, *args, **kwargs):
    system_to_json(system, *args, **kwargs)

timed_system_to_json(system, save_calculated_attributes=False, output_filepath="big_system.json")

from time import time
start = time()
usage_patterns[0].usage_journey.uj_steps[0].jobs[0].data_transferred = SourceValue(100 * u.MB, source=None)
end = time()
logger.info(f"edition took {round((end - start), 3)} seconds")