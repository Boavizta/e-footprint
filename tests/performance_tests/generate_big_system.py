import json
import os
from time import time

from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.tools import time_it

start = time()

from efootprint.abstract_modeling_classes.source_objects import SourceValue
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
from efootprint.builders.time_builders import create_random_source_hourly_values
from efootprint.logger import logger
from tests.performance_tests.test_big_system_from_and_to_json_performance import root_dir, update_on_system
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")


def generate_big_system(nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4):
    """
    Generates a big system with the specified number of servers, user journeys, and steps per user journey.
    """
    start = time()
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
                web_application_job = WebApplicationJob.from_defaults(
                    f"Web application job uj {uj_index} uj_step {uj_step_index} server {server_index}",
                    service=web_application)
                genai_model_job = GenAIJob.from_defaults(
                    f"Generative AI model job uj {uj_index} uj_step {uj_step_index} server {server_index}",
                    service=genai_model)
                manually_written_job = Job.from_defaults(
                    f"Manually defined job uj {uj_index} uj_step {uj_step_index} server {server_index}",
                    server=autoscaling_server)
                custom_gpu_job = GPUJob.from_defaults(
                    f"Manually defined GPU job uj {uj_index} uj_step {uj_step_index} server {server_index}", server=on_premise_gpu_server)

                uj_steps.append(UsageJourneyStep(
                    f"20 min streaming {uj_index} step {uj_step_index}",
                    user_time_spent=SourceValue(20 * u.min, source=None),
                    jobs=[web_application_job, genai_model_job, video_streaming_job, manually_written_job, custom_gpu_job]
                    ))

            usage_journey = UsageJourney(f"user journey {uj_index}", uj_steps=uj_steps)

            network = Network(
                    f"network {uj_index}",
                    bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))

            usage_patterns.append(
                UsagePattern(
                    f"usage pattern {uj_index}",
                    usage_journey=usage_journey,
                    devices=[
                        Device(name=f"device on which the user journey {uj_index} is made",
                                 carbon_footprint_fabrication=SourceValue(156 * u.kg, source=None),
                                 power=SourceValue(50 * u.W, source=None),
                                 lifespan=SourceValue(6 * u.year, source=None),
                                 fraction_of_usage_time=SourceValue(7 * u.hour / u.day, source=None))],
                    network=network,
                    country=country_generator(
                            f"devices country {uj_index}", "its 3 letter shortname, for example FRA",
                        SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
                    hourly_usage_journey_starts=create_random_source_hourly_values(timespan=3 * u.year)
                )
            )

    system = System("system", usage_patterns=usage_patterns)
    logger.info(f"Finished generating system in {round((time() - start), 3)} seconds")

    timed_system_to_json(system, save_calculated_attributes=False, output_filepath="big_system.json")
    timed_system_to_json(system, save_calculated_attributes=True, output_filepath="big_system_with_calc_attr.json")

    return system

@time_it
def timed_system_to_json(system, *args, **kwargs):
    return system_to_json(system, *args, **kwargs)

if __name__ == "__main__":
    # Live system editions benchmarking
    system = generate_big_system(nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4)

    edition_iterations = 10
    start = time()
    for i in range(edition_iterations):
        system.usage_patterns[0].usage_journey.uj_steps[0].jobs[0].data_transferred = SourceValue(100 * u.MB)
        system.usage_patterns[0].usage_journey.uj_steps[0].jobs[0].data_transferred = SourceValue(30 * u.MB)
    end = time()
    compute_time_per_edition = round(1000 * (end - start) / (edition_iterations * 2), 1)
    logger.info(f"edition took {compute_time_per_edition} ms on average per data transferred edition")

    start = time()
    for i in range(edition_iterations):
        system.usage_patterns[0].hourly_usage_journey_starts = create_random_source_hourly_values(timespan=3 * u.year)
    end = time()
    compute_time_per_edition = round(1000 * (end - start) / edition_iterations, 1)
    logger.info(f"edition took {compute_time_per_edition} ms on average per hourly usage journey starts edition")

    # System loaded from json edition benchmarking
    with open(os.path.join(root_dir, "big_system_with_calc_attr.json"), "r") as file:
        system_dict = json.load(file)

    nb_system_loadings = 10
    update_on_system(
        nb_system_loadings, system_dict, "UsagePattern", "hourly_usage_journey_starts",
        create_random_source_hourly_values(timespan=3 * u.year))

    update_on_system(
        nb_system_loadings, system_dict, "Storage", "data_storage_duration", SourceValue(3 * u.year))
