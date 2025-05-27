import json
import os
from datetime import datetime

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues, SourceObject
from efootprint.core.hardware.device import Device
from efootprint.core.usage.job import GPUJob
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.logger import logger
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestServicesBaseClass(IntegrationTestBaseClass):
    @staticmethod
    def generate_system_with_services():
        storage = Storage.ssd("Web server SSD storage")
        server = BoaviztaCloudServer.from_defaults(
            "Web server", storage=storage, base_ram_consumption=SourceValue(1 * u.GB))
        gpu_server = GPUServer.from_defaults("GPU server", storage=Storage.ssd())

        video_streaming_service = VideoStreaming.from_defaults(
            "Youtube streaming service", server=server)
        web_application_service = WebApplication(
            "Web application service", server, technology=SourceObject("php-symfony"))
        genai_service = GenAIModel.from_defaults(
            "GenAI service", provider=SourceObject("openai"), model_name=SourceObject("gpt-3.5-turbo-1106"),
            server=gpu_server)

        video_streaming_job = VideoStreamingJob.from_defaults(
            "Streaming job", service=video_streaming_service, resolution=SourceObject("720p (1280 x 720)"),
            video_duration=SourceValue(20 * u.min))
        web_application_job = WebApplicationJob.from_defaults("web app job", service=web_application_service)
        genai_job = GenAIJob("GenAI job", genai_service, output_token_count=SourceValue(1000 * u.dimensionless))
        direct_gpu_job = GPUJob.from_defaults(
            "direct GPU server job", compute_needed=SourceValue(1 * u.gpu), server=gpu_server)

        streaming_step = UsageJourneyStep(
            "20 min streaming on Youtube with genAI chat", user_time_spent=SourceValue(20 * u.min),
            jobs=[direct_gpu_job, video_streaming_job, web_application_job, genai_job])

        uj = UsageJourney("Daily Youtube usage", uj_steps=[streaming_step])
        network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern = UsagePattern(
            "Youtube usage in France", uj, [Device.laptop()], network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date)))

        system = System("system 1", [usage_pattern])

        return system, storage, server, gpu_server, video_streaming_service, web_application_service, genai_service, \
                video_streaming_job, web_application_job, genai_job, direct_gpu_job, network, uj, start_date, \
                usage_pattern

    @classmethod
    def initialize_footprints(cls, system, storage, server, gpu_server, usage_pattern, network):
        cls.initial_footprint = system.total_footprint

        cls.initial_fab_footprints = {
            storage: storage.instances_fabrication_footprint,
            server: server.instances_fabrication_footprint,
            gpu_server: gpu_server.instances_fabrication_footprint,
            usage_pattern: usage_pattern.devices_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            storage: storage.energy_footprint,
            server: server.energy_footprint,
            gpu_server: gpu_server.energy_footprint,
            network: network.energy_footprint,
            usage_pattern: usage_pattern.devices_energy_footprint,
        }

        cls.initial_system_total_fab_footprint = system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = system.total_energy_footprint_sum_over_period

    @classmethod
    def setUpClass(cls):
        (cls.system, cls.storage, cls.server, cls.gpu_server, cls.video_streaming_service, cls.web_application_service, 
         cls.genai_service, cls.video_streaming_job, cls.web_application_job, cls.genai_job, cls.direct_gpu_job, 
         cls.network, cls.uj, cls.start_date, cls.usage_pattern) = cls.generate_system_with_services()
        
        cls.initialize_footprints(cls.system, cls.storage, cls.server, cls.gpu_server, cls.usage_pattern, cls.network)

        cls.ref_json_filename = "system_with_services"

    def run_test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def run_test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def run_test_variations_on_services_inputs(self):
        self._test_variations_on_obj_inputs(self.video_streaming_service, attrs_to_skip=["base_compute_consumption"],
                                            special_mult={"base_ram_consumption": 2, "ram_buffer_per_user": 5})
        self._test_variations_on_obj_inputs(
            self.genai_service, attrs_to_skip=["provider", "model_name", "base_compute_consumption"],
            special_mult={"llm_memory_factor": 2, "ram_per_gpu": 16, "nb_of_bits_per_parameter": 2})
        self._test_variations_on_obj_inputs(
            self.web_application_service,
            attrs_to_skip=["technology", "base_compute_consumption", "base_ram_consumption"])

    def run_test_variations_on_services_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["VideoStreaming"].values())),
            attrs_to_skip = ["base_compute_consumption"],
            special_mult = {"base_ram_consumption": 2, "ram_buffer_per_user": 5})
        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["GenAIModel"].values())),
            attrs_to_skip=["provider", "model_name", "base_compute_consumption"],
            special_mult={"llm_memory_factor": 2, "ram_per_gpu": 16, "nb_of_bits_per_parameter": 2})
        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["WebApplication"].values())),
            attrs_to_skip=["technology", "base_compute_consumption", "base_ram_consumption"])

    def run_test_update_service_servers(self):
        logger.info("Linking services to new servers")
        new_server = BoaviztaCloudServer.from_defaults("New server", storage=Storage.ssd())
        new_gpu_server = GPUServer.from_defaults("New GPU server", storage=Storage.ssd())
        self.video_streaming_service.server = new_server
        self.web_application_service.server = new_server
        self.genai_service.server = new_gpu_server
        self.direct_gpu_job.server = new_gpu_server

        self.assertEqual(self.server.installed_services, [])
        self.assertEqual(self.server.jobs, [])
        self.assertIsInstance(self.server.hour_by_hour_ram_need, EmptyExplainableObject)
        self.assertIsInstance(self.server.hour_by_hour_compute_need, EmptyExplainableObject)
        self.assertEqual(
            set(new_server.installed_services), {self.video_streaming_service, self.web_application_service})
        self.assertEqual(self.gpu_server.installed_services, [])
        self.assertEqual(self.gpu_server.jobs, [])
        self.assertIsInstance(self.gpu_server.hour_by_hour_ram_need, EmptyExplainableObject)
        self.assertIsInstance(self.gpu_server.hour_by_hour_compute_need, EmptyExplainableObject)
        self.assertEqual(set(new_gpu_server.installed_services), {self.genai_service})

        logger.info("Linking services back to initial servers")
        self.web_application_service.server = self.server
        self.video_streaming_service.server = self.server
        self.genai_service.server = self.gpu_server
        self.direct_gpu_job.server = self.gpu_server

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])

    def run_test_update_service_jobs(self):
        new_storage = Storage.ssd("New web server SSD storage, identical to previous one")
        new_server = BoaviztaCloudServer.from_defaults(
            "New web server, identical to previous one", storage=new_storage,
            base_ram_consumption=SourceValue(1 * u.GB))
        new_gpu_server = GPUServer.from_defaults("New GPU server, identical to previous one", storage=Storage.ssd())

        new_video_streaming_service = VideoStreaming.from_defaults(
            "New Youtube streaming service", server=new_server)
        new_web_application_service = WebApplication(
            "New Web application service", new_server, technology=SourceObject("php-symfony"))
        new_genai_service = GenAIModel.from_defaults(
            "New GenAI service", provider=SourceObject("openai"), model_name=SourceObject("gpt-3.5-turbo-1106"),
            server=new_gpu_server)

        logger.info("Linking jobs to new services")
        ModelingUpdate([[self.direct_gpu_job.server, new_gpu_server],
        [self.video_streaming_job.service, new_video_streaming_service],
        [self.web_application_job.service, new_web_application_service],
        [self.genai_job.service, new_genai_service]])

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.gpu_server], system=self.system)
        self.assertEqual(self.server.jobs, [])
        self.footprint_has_not_changed([self.network, self.usage_pattern])

        logger.info("Linking jobs back to initial services")
        self.direct_gpu_job.server = self.gpu_server
        self.video_streaming_job.service = self.video_streaming_service
        self.web_application_job.service = self.web_application_service
        self.genai_job.service = self.genai_service

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])
