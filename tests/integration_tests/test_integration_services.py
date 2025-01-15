import json
from copy import copy
import os
from datetime import datetime, timedelta

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.hardware.gpu_server_builder import GPUServerBuilder
from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.builders.services.video_streaming import VideoStreamingService
from efootprint.builders.services.web_application import WebApplicationService
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.hardware.servers.autoscaling import Autoscaling
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.builders.hardware.devices_defaults import default_laptop
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass


class ServiceIntegrationTest(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.storage = Storage(
            "Web server storage",
            carbon_footprint_fabrication=SourceValue(160 * u.kg, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power=SourceValue(1.3 * u.W, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )

        cls.server = Autoscaling(
            "Web server",
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(128 * u.GB, Sources.USER_DATA),
            cpu_cores=SourceValue(24 * u.core, Sources.USER_DATA),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.USER_DATA),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.USER_DATA),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_cpu_consumption=SourceValue(2 * u.core, Sources.HYPOTHESIS),
            storage=cls.storage
        )
        
        cls.gpu_server_builder = GPUServerBuilder("GPU server builder")
        cls.gpu_server = cls.gpu_server_builder.generate_gpu_server(
            "GPU server", "OnPremise", average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            nb_gpus_per_instance=SourceValue(4 * u.dimensionless, Sources.HYPOTHESIS),
            fixed_nb_of_instances=SourceValue(70 * u.dimensionless, Sources.HYPOTHESIS))
                                                                    
        cls.video_streaming_service = VideoStreamingService("Youtube streaming service", cls.server)
        cls.web_application_service = WebApplicationService(
            "Web application service", cls.server, technology="php-symfony")
        cls.genai_service = GenAIModel("GenAI service", "openai", "gpt-3.5-turbo-1106", cls.gpu_server)

        cls.video_streaming_job = cls.video_streaming_service.generate_job("720p (1280 x 720)", SourceValue(20 * u.min))
        cls.web_application_job = cls.web_application_service.generate_job(
            "default", data_upload=SourceValue(300 * u.kB), data_download=SourceValue(1 * u.MB),
            data_stored=SourceValue(300 * u.kB))
        cls.genai_job = cls.genai_service.generate_job(output_token_count=SourceValue(1000 * u.dimensionless))

        cls.streaming_step = UserJourneyStep(
            "20 min streaming on Youtube with genAI chat", user_time_spent=SourceValue(20 * u.min),
            jobs=[cls.video_streaming_job, cls.web_application_job, cls.genai_job])

        cls.uj = UserJourney("Daily Youtube usage", uj_steps=[cls.streaming_step])
        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        cls.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        cls.usage_pattern = UsagePattern(
            "Youtube usage in France", cls.uj, [default_laptop()], cls.network, Countries.FRANCE(),
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
        raise NotImplementedError("This test should be implemented")

    def test_variations_on_services_inputs_after_json_to_system(self):
        raise NotImplementedError("This test should be implemented")
