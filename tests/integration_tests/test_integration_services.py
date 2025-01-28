import json
import os
from datetime import datetime

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues, SourceObject
from efootprint.core.hardware.hardware import Hardware
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.logger import logger
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class ServiceIntegrationTest(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.storage = Storage.ssd("Web server SSD storage")
        cls.server = BoaviztaCloudServer.from_defaults(
            "Web server", storage=cls.storage, base_ram_consumption=SourceValue(1 * u.GB))
        cls.gpu_server = GPUServer.from_defaults("GPU server", storage=Storage.ssd())

        cls.video_streaming_service = VideoStreaming.from_defaults(
            "Youtube streaming service", server=cls.server)
        cls.web_application_service = WebApplication(
            "Web application service", cls.server, technology=SourceObject("php-symfony"))
        cls.genai_service = GenAIModel.from_defaults(
            "GenAI service", provider=SourceObject("openai"), model_name=SourceObject("gpt-3.5-turbo-1106"),
            server=cls.gpu_server)

        cls.video_streaming_job = VideoStreamingJob.from_defaults(
            "Streaming job", service=cls.video_streaming_service, resolution=SourceObject("720p (1280 x 720)"),
            video_duration=SourceValue(20 * u.min))
        cls.web_application_job = WebApplicationJob.from_defaults("web app job", service=cls.web_application_service)
        cls.genai_job = GenAIJob("GenAI job", cls.genai_service, output_token_count=SourceValue(1000 * u.dimensionless))

        cls.streaming_step = UserJourneyStep(
            "20 min streaming on Youtube with genAI chat", user_time_spent=SourceValue(20 * u.min),
            jobs=[cls.video_streaming_job, cls.web_application_job, cls.genai_job])

        cls.uj = UserJourney("Daily Youtube usage", uj_steps=[cls.streaming_step])
        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        cls.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        cls.usage_pattern = UsagePattern(
            "Youtube usage in France", cls.uj, [Hardware.laptop()], cls.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], cls.start_date)))

        cls.system = System("system 1", [cls.usage_pattern])
        cls.initial_footprint = cls.system.total_footprint

        cls.initial_fab_footprints = {
            cls.storage: cls.storage.instances_fabrication_footprint,
            cls.server: cls.server.instances_fabrication_footprint,
            cls.gpu_server: cls.gpu_server.instances_fabrication_footprint,
            cls.usage_pattern: cls.usage_pattern.devices_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            cls.storage: cls.storage.energy_footprint,
            cls.server: cls.server.energy_footprint,
            cls.gpu_server: cls.gpu_server.energy_footprint,
            cls.network: cls.network.energy_footprint,
            cls.usage_pattern: cls.usage_pattern.devices_energy_footprint,
        }

        cls.initial_system_total_fab_footprint = cls.system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = cls.system.total_energy_footprint_sum_over_period

        cls.ref_json_filename = "system_with_services"

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_variations_on_services_inputs(self):
        self._test_variations_on_obj_inputs(self.video_streaming_service, attrs_to_skip=["base_compute_consumption"],
                                            special_mult={"base_ram_consumption": 114, "ram_buffer_per_user": 500})
        self._test_variations_on_obj_inputs(
            self.genai_service, attrs_to_skip=["provider", "model_name", "base_compute_consumption"],
            special_mult={"llm_memory_factor": 2, "ram_per_gpu": 16, "nb_of_bits_per_parameter": 2})
        self._test_variations_on_obj_inputs(
            self.web_application_service,
            attrs_to_skip=["technology", "base_compute_consumption", "base_ram_consumption"])

    def test_variations_on_services_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["VideoStreaming"].values())),
            attrs_to_skip = ["base_compute_consumption"],
            special_mult = {"base_ram_consumption": 114, "ram_buffer_per_user": 500})
        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["GenAIModel"].values())),
            attrs_to_skip=["provider", "model_name", "base_compute_consumption"],
            special_mult={"llm_memory_factor": 2, "ram_per_gpu": 16, "nb_of_bits_per_parameter": 2})
        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["WebApplication"].values())),
            attrs_to_skip=["technology", "base_compute_consumption", "base_ram_consumption"])

    def test_update_service_servers(self):
        logger.info("Linking services to new servers")
        new_server = BoaviztaCloudServer.from_defaults("New server", storage=Storage.ssd())
        new_gpu_server = GPUServer.from_defaults("New GPU server", storage=Storage.ssd())
        self.video_streaming_service.server = new_server
        self.web_application_service.server = new_server
        self.genai_service.server = new_gpu_server

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

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])

    def test_update_service_jobs(self):
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
        self.video_streaming_job.service = new_video_streaming_service
        self.web_application_job.service = new_web_application_service
        self.genai_job.service = new_genai_service

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.gpu_server], system=self.system)
        self.assertEqual(self.server.jobs, [])
        self.footprint_has_not_changed([self.network, self.usage_pattern])

        logger.info("Linking jobs back to initial services")
        self.video_streaming_job.service = self.video_streaming_service
        self.web_application_job.service = self.web_application_service
        self.genai_job.service = self.genai_service

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])