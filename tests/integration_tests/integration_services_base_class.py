from datetime import datetime

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.builders.external_apis.ecologits.ecologits_external_api import EcoLogitsGenAIExternalAPI, \
    EcoLogitsGenAIExternalAPIJob
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
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
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, ObjectLinkScenario


class IntegrationTestServicesBaseClass(IntegrationTestBaseClass):
    REF_JSON_FILENAME = "system_with_services"
    OBJECT_NAMES_MAP = {
        "storage": "Web server SSD storage",
        "server": "Web server",
        "gpu_server": "GPU server",
        "video_streaming_service": "Youtube streaming service",
        "genai_service": "GenAI service",
        "video_streaming_job": "Streaming job",
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
        genai_service = EcoLogitsGenAIExternalAPI.from_defaults(
            "GenAI service", provider=SourceObject("openai"), model_name=SourceObject("gpt-3.5-turbo-1106"))

        video_streaming_job = VideoStreamingJob.from_defaults(
            "Streaming job", service=video_streaming_service, resolution=SourceObject("720p (1280 x 720)"),
            video_duration=SourceValue(20 * u.min))
        genai_job = EcoLogitsGenAIExternalAPIJob(
            "GenAI job", genai_service, output_token_count=SourceValue(1000 * u.dimensionless))
        direct_gpu_job = GPUJob.from_defaults(
            "direct GPU server job", compute_needed=SourceValue(1 * u.gpu), server=gpu_server)

        streaming_step = UsageJourneyStep(
            "20 min streaming on Youtube with genAI chat", user_time_spent=SourceValue(20 * u.min),
            jobs=[direct_gpu_job, video_streaming_job, genai_job])

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
            self.genai_job, attrs_to_skip=["data_stored", "compute_needed", "ram_needed"])

    def run_test_update_service_servers(self):
        logger.info("Linking services to new servers")
        new_server = BoaviztaCloudServer.from_defaults("New server", storage=Storage.ssd())
        new_gpu_server = GPUServer.from_defaults("New GPU server", storage=Storage.ssd())
        updates = [
            [self.video_streaming_service.server, new_server],
            [self.direct_gpu_job.server, new_gpu_server],
        ]

        def post_assertions(test):
            test.assertEqual(test.server.installed_services, [])
            test.assertEqual(test.server.jobs, [])
            test.assertIsInstance(test.server.hour_by_hour_ram_need, EmptyExplainableObject)
            test.assertIsInstance(test.server.hour_by_hour_compute_need, EmptyExplainableObject)
            test.assertEqual(set(new_server.installed_services), {test.video_streaming_service})
            test.assertEqual(test.gpu_server.installed_services, [])
            test.assertEqual(test.gpu_server.jobs, [])
            test.assertIsInstance(test.gpu_server.hour_by_hour_ram_need, EmptyExplainableObject)
            test.assertIsInstance(test.gpu_server.hour_by_hour_compute_need, EmptyExplainableObject)

        scenario = ObjectLinkScenario(
            name="update_service_servers",
            updates_builder=updates,
            expected_changed=[self.server, self.gpu_server, self.storage],
            expected_unchanged=[self.network, self.usage_pattern],
            post_assertions=post_assertions,
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_service_jobs(self):
        new_storage = self.storage.copy_with()
        new_server = self.server.copy_with(storage=new_storage)
        new_gpu_storage = self.gpu_server.storage.copy_with()
        new_gpu_server = self.gpu_server.copy_with(storage=new_gpu_storage)

        new_video_streaming_service = VideoStreaming.from_defaults(
            "New Youtube streaming service", server=new_server)
        new_genai_service = EcoLogitsGenAIExternalAPI.from_defaults(
            "New GenAI service", provider=SourceObject("openai"), model_name=SourceObject("gpt-3.5-turbo-1106"))

        updates = [
            [self.direct_gpu_job.server, new_gpu_server],
            [self.video_streaming_job.service, new_video_streaming_service],
            [self.genai_job.external_api, new_genai_service],
        ]

        def post_assertions(test):
            test.assertEqual(test.server.jobs, [])

        scenario = ObjectLinkScenario(
            name="update_service_jobs",
            updates_builder=updates,
            expected_changed=[self.storage, self.server, self.gpu_server],
            expected_unchanged=[self.network, self.usage_pattern],
            expect_total_change=False,
            post_assertions=post_assertions,
        )
        self._run_object_link_scenario(scenario)

    def run_test_install_new_service_on_server_and_make_sure_system_is_recomputed(self):
        logger.info("Installing new service on server")
        new_service = VideoStreaming.from_defaults("New streaming service", server=self.server)

        self.assertEqual(set(self.server.installed_services),
                         {new_service, self.video_streaming_service})
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.network, self.usage_pattern, self.gpu_server])

        logger.info("Uninstalling new service from server")
        new_service.self_delete()
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.network, self.usage_pattern, self.gpu_server, self.server])

    def run_test_try_to_update_model_provider_and_get_error(self):
        previous_provider = self.genai_service.provider
        with self.assertRaises(ValueError):
            self.genai_service.provider = SourceObject("anthropic")
        self.assertEqual(self.genai_service.provider, previous_provider)

    def run_test_change_provider_and_model_name_and_check_footprint_changes(self):
        previous_provider = self.genai_service.provider
        previous_model_name = self.genai_service.model_name
        previous_footprint = self.system.total_footprint

        new_provider = SourceObject("anthropic")
        new_model_name = SourceObject("claude-opus-4-5")
        logger.info(f"Change provider {previous_provider} -> {new_provider} "
                    f"and model name {previous_model_name} -> {new_model_name}")
        ModelingUpdate([[self.genai_service.provider, new_provider], [self.genai_service.model_name, new_model_name]])
        self.assertNotEqual(previous_footprint, self.system.total_footprint)

        # revert changes
        logger.info("Revert changes to provider and model name")
        ModelingUpdate([[self.genai_service.provider, previous_provider], [self.genai_service.model_name, previous_model_name]])
        self.assertEqual(previous_footprint, self.system.total_footprint)
