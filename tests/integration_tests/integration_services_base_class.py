import json
import os
from datetime import datetime

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import css_escape
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
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.logger import logger
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestServicesBaseClass(IntegrationTestBaseClass):
    REF_JSON_FILENAME = "system_with_services"
    OBJECT_NAMES_MAP = {
        "storage": "Web server SSD storage",
        "server": "Web server",
        "gpu_server": "GPU server",
        "video_streaming_service": "Youtube streaming service",
        "web_application_service": "Web application service",
        "genai_service": "GenAI service",
        "video_streaming_job": "Streaming job",
        "web_application_job": "web app job",
        "genai_job": "GenAI job",
        "direct_gpu_job": "direct GPU server job",
        "network": "Default network",
        "uj": "Daily Youtube usage",
        "usage_pattern": "Youtube usage in France",
    }

    @staticmethod
    def generate_system_with_services():
        storage = Storage.ssd("Web server SSD storage")
        server = BoaviztaCloudServer.from_defaults(
            "Web server", storage=storage, base_ram_consumption=SourceValue(1 * u.GB_ram))
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
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date))

        usage_pattern.id = css_escape(usage_pattern.name)

        system = System("system 1", [usage_pattern], edge_usage_patterns=[])
        mod_obj_list = [system] + system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj != usage_pattern:
                mod_obj.id = css_escape(mod_obj.name)

        return system, start_date

    @classmethod
    def setUpClass(cls):
        system, start_date = cls.generate_system_with_services()
        cls._setup_from_system(system, start_date)

    def run_test_variations_on_services_inputs(self):
        self._test_variations_on_obj_inputs(self.video_streaming_service, attrs_to_skip=["base_compute_consumption"],
                                            special_mult={"base_ram_consumption": 2, "ram_buffer_per_user": 5})
        self._test_variations_on_obj_inputs(
            self.genai_service, attrs_to_skip=["provider", "model_name", "base_compute_consumption"],
            special_mult={"llm_memory_factor": 2, "ram_per_gpu": 16, "nb_of_bits_per_parameter": 2})
        self._test_variations_on_obj_inputs(
            self.web_application_service,
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

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])

    def run_test_update_service_jobs(self):
        new_storage = self.storage.copy_with()
        new_server = self.server.copy_with(storage=new_storage)
        new_gpu_storage = self.gpu_server.storage.copy_with()
        new_gpu_server = self.gpu_server.copy_with(storage=new_gpu_storage)

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

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.storage, self.server, self.gpu_server], system=self.system)
        self.assertEqual(self.server.jobs, [])
        self.footprint_has_not_changed([self.network, self.usage_pattern])

        logger.info("Linking jobs back to initial services")
        self.direct_gpu_job.server = self.gpu_server
        self.video_streaming_job.service = self.video_streaming_service
        self.web_application_job.service = self.web_application_service
        self.genai_job.service = self.genai_service

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern, self.gpu_server])

    def run_test_install_new_service_on_server_and_make_sure_system_is_recomputed(self):
        logger.info("Installing new service on server")
        new_service = VideoStreaming.from_defaults("New streaming service", server=self.server)

        self.assertEqual(set(self.server.installed_services),
                         {new_service, self.web_application_service, self.video_streaming_service})
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.network, self.usage_pattern, self.gpu_server])

        logger.info("Uninstalling new service from server")
        new_service.self_delete()
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.network, self.usage_pattern, self.gpu_server, self.server])
