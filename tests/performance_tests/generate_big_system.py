from time import time
start = time()

import os
os.environ["USE_BOAVIZTAPI_PACKAGE"] = "true"

from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.tools import time_it
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
from efootprint.builders.time_builders import create_hourly_usage_from_frequency, create_random_source_hourly_values
from efootprint.logger import logger
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")


def generate_big_system(
        nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3,
        nb_years=5):
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
                    f"Video streaming job", service=video_streaming, video_duration=SourceValue(2.5 * u.hour))
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
            for up_nb in range(1, nb_of_up_per_uj + 1):
                usage_patterns.append(
                    UsagePattern(
                        f"usage pattern {up_nb} of {uj_index}",
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
                        hourly_usage_journey_starts=create_hourly_usage_from_frequency(
                            timespan=nb_years * u.year, input_volume=1000, frequency='weekly',
                            active_days=[0, 1, 2, 3, 4, 5], hours=[8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19])
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
    nb_years = 5
    system = generate_big_system(
        nb_of_servers_of_each_type=3, nb_of_uj_per_each_server_type=3, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3, nb_years=nb_years)

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
        system.usage_patterns[0].hourly_usage_journey_starts = create_random_source_hourly_values(
            timespan=nb_years * u.year)
    end = time()
    compute_time_per_edition = round(1000 * (end - start) / edition_iterations, 1)
    logger.info(f"edition took {compute_time_per_edition} ms on average per hourly usage journey starts edition")

    from efootprint.abstract_modeling_classes.modeling_object import compute_times
    total_time = 0
    for data in compute_times.values():
        total_time += data["total_duration"]
    nb_update_functions = len(compute_times)
    print(f"Total time in update functions: {round(total_time, 3)}s, nb_update_functions: {nb_update_functions}, "
          f"avg %: {round(100 / nb_update_functions, 2)}")
    from efootprint.abstract_modeling_classes.modeling_object import time_spent_doing_sums
    print(f"Time spent doing sums: {round(time_spent_doing_sums["value"], 3)} "
          f"({round(time_spent_doing_sums["value"] / total_time * 100, 2)}%)")
    cumulated_time = 0
    i = 0
    for update_function_name, update_function_dict in sorted(compute_times.items(), key=lambda x: -x[1]["total_duration"]):
        i += 1
        update_function_time = update_function_dict.get("total_duration")
        cumulated_time += update_function_time
        time_pct = round(100 * update_function_time / total_time, 2)
        cum_time_pct = round(100 * cumulated_time / total_time, 2)
        print(f"{i}: {update_function_time:.3f}s ({time_pct}%, cum {cum_time_pct}%) for {update_function_dict["nb_calls"]} calls of {update_function_name}")
