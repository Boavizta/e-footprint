import json
import os.path
from copy import copy

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.usage.job import Job
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.hardware.servers.autoscaling import Autoscaling
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.builders.hardware.devices_defaults import default_laptop
from efootprint.builders.hardware.servers_defaults import default_autoscaling
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestComplexSystem(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.server1 = Autoscaling(
            "Server 1",
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(12 * u.GB, Sources.HYPOTHESIS),
            cpu_cores=SourceValue(6 * u.core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_cpu_consumption=SourceValue(2 * u.core, Sources.HYPOTHESIS)
        )
        cls.storage = Storage(
            "Default SSD storage",
            carbon_footprint_fabrication=SourceValue(160 * u.kg, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power=SourceValue(1.3 * u.W, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            data_replication_factor=SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            data_storage_duration=SourceValue(4 * u.hour, Sources.HYPOTHESIS),
            base_storage_need=SourceValue(100 * u.TB, Sources.HYPOTHESIS),
        )

        cls.server2 = Autoscaling(
            "Server 2",
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(12 * u.GB, Sources.HYPOTHESIS),
            cpu_cores=SourceValue(6 * u.core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_cpu_consumption=SourceValue(2 * u.core, Sources.HYPOTHESIS)
        )
        cls.server3 = default_autoscaling("TikTok Analytics server")
        cls.server3.base_ram_consumption = SourceValue(300 * u.MB, Sources.HYPOTHESIS)
        cls.server3.base_cpu_consumption = SourceValue(2 * u.core, Sources.HYPOTHESIS)

        cls.streaming_job = Job("streaming", cls.server1, cls.storage, data_upload=SourceValue(50 * u.kB),
                                data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
                                request_duration=SourceValue(4 * u.min),
                                ram_needed=SourceValue(100 * u.MB), cpu_needed=SourceValue(1 * u.core))
        cls.streaming_step = UserJourneyStep(
            "20 min streaming on Youtube", user_time_spent=SourceValue(20 * u.min), jobs=[cls.streaming_job])

        cls.upload_job = Job("upload", cls.server1, cls.storage, data_upload=SourceValue(300 * u.kB),
                             data_download=SourceValue(0 * u.GB), data_stored=SourceValue(300 * u.kB),
                             request_duration=SourceValue(0.4 * u.s), ram_needed=SourceValue(100 * u.MB),
                             cpu_needed=SourceValue(1 * u.core))
        cls.upload_step = UserJourneyStep(
            "0.4s of upload", user_time_spent=SourceValue(1 * u.s), jobs=[cls.upload_job])

        cls.dailymotion_job = Job(
            "dailymotion", cls.server1, cls.storage, data_upload=SourceValue(300 * u.kB),
            data_download=SourceValue(3 * u.MB), data_stored=SourceValue(300 * u.kB),
            request_duration=SourceValue(1 * u.s), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        cls.dailymotion_step = UserJourneyStep(
            "Dailymotion step", user_time_spent=SourceValue(1 * u.min), jobs=[cls.dailymotion_job])

        cls.tiktok_job = Job(
            "tiktok", cls.server2, cls.storage, data_upload=SourceValue(0 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(0 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        cls.tiktok_analytics_job = Job(
            "tiktok analytics", cls.server3, cls.storage, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue(0 * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        cls.tiktok_step = UserJourneyStep(
            "20 min streaming on TikTok", user_time_spent=SourceValue(20 * u.min),
            jobs=[cls.tiktok_job, cls.tiktok_analytics_job])

        cls.uj = UserJourney(
            "Daily video usage", uj_steps=[cls.streaming_step, cls.upload_step, cls.dailymotion_step, cls.tiktok_step])

        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
        cls.usage_pattern1 = UsagePattern(
            "Video watching in France in the morning", cls.uj, [default_laptop()], cls.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list([elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]])))

        cls.usage_pattern2 = UsagePattern(
            "Video watching in France in the evening", cls.uj, [default_laptop()], cls.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list([elt * 1000 for elt in [4, 2, 1, 5, 2, 1, 7, 8, 3]])))

        cls.system = System("system 1", [cls.usage_pattern1, cls.usage_pattern2])

        cls.initial_footprint = cls.system.total_footprint
        cls.initial_fab_footprints = {
            cls.storage: cls.storage.instances_fabrication_footprint,
            cls.server1: cls.server1.instances_fabrication_footprint,
            cls.server2: cls.server2.instances_fabrication_footprint,
            cls.server3: cls.server3.instances_fabrication_footprint,
            cls.usage_pattern1: cls.usage_pattern1.instances_fabrication_footprint,
            cls.usage_pattern2: cls.usage_pattern2.instances_fabrication_footprint,
        }
        cls.initial_energy_footprints = {
            cls.storage: cls.storage.energy_footprint,
            cls.server1: cls.server1.energy_footprint,
            cls.server2: cls.server2.energy_footprint,
            cls.server3: cls.server3.energy_footprint,
            cls.network: cls.network.energy_footprint,
            cls.usage_pattern1: cls.usage_pattern1.energy_footprint,
            cls.usage_pattern2: cls.usage_pattern2.energy_footprint,
        }

        cls.initial_system_total_fab_footprint = cls.system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = cls.system.total_energy_footprint_sum_over_period

        cls.ref_json_filename = "complex_system"

    def test_remove_dailymotion_and_tiktok_uj_step(self):
        logger.warning("Removing Dailymotion and TikTok uj step")
        self.uj.uj_steps = [self.streaming_step, self.upload_step]

        self.footprint_has_changed([self.server1, self.server2, self.storage])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting Dailymotion and TikTok uj step back")
        self.uj.uj_steps = [self.streaming_step, self.upload_step, self.dailymotion_step, self.tiktok_step]

        self.footprint_has_not_changed([self.server1, self.server2, self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_dailymotion_single_job(self):
        logger.warning("Removing Dailymotion job")
        self.dailymotion_step.jobs = []

        self.footprint_has_changed([self.server1, self.storage])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting Dailymotion job back")
        self.dailymotion_step.jobs = [self.dailymotion_job]

        self.footprint_has_not_changed([self.server1, self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_one_tiktok_job(self):
        logger.warning("Removing one TikTok job")
        self.tiktok_step.jobs = [self.tiktok_job]

        self.footprint_has_changed([self.server3, self.storage])
        self.footprint_has_not_changed([self.server2])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting TikTok job back")
        self.tiktok_step.jobs = [self.tiktok_job, self.tiktok_analytics_job]

        self.footprint_has_not_changed([self.server3, self.server2, self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_all_tiktok_jobs(self):
        logger.warning("Removing all TikTok jobs")
        self.tiktok_step.jobs = []

        self.footprint_has_changed([self.server2, self.server3, self.storage])
        self.footprint_has_not_changed([self.server1])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint))

        logger.warning("Putting TikTok jobs back")
        self.tiktok_step.jobs = [self.tiktok_job, self.tiktok_analytics_job]

        self.footprint_has_not_changed([self.server3, self.server2, self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_new_job(self):
        logger.warning("Adding job")
        new_job = Job(
    "dailymotion", self.server1, self.storage, data_upload=SourceValue(300 * u.kB),
            data_download=SourceValue(3 * u.MB), data_stored=SourceValue(3 * u.MB),
            request_duration=SourceValue(1 * u.s), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        new_uj = UserJourneyStep(
            "new uj step", user_time_spent=SourceValue(1 * u.s), jobs=[new_job])
        self.uj.uj_steps += [new_uj]

        self.footprint_has_changed([self.server1, self.storage])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Removing new job")
        self.uj.uj_steps = self.uj.uj_steps[:-1]
        job = new_uj.jobs[0]
        new_uj.self_delete()
        job.self_delete()

        self.footprint_has_not_changed([self.server1, self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_new_usage_pattern(self):
        new_up = UsagePattern(
            "New usage pattern video watching in France", self.uj, [default_laptop()], self.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list([elt * 1000 for elt in [1, 4, 1, 5, 3, 1, 5, 23, 2]])))

        logger.warning("Adding new usage pattern")
        self.system.usage_patterns += [new_up]
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Removing the new usage pattern")
        self.system.usage_patterns = [self.usage_pattern1, self.usage_pattern2]
        new_up.self_delete()

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_add_usage_pattern_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR,  f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        for obj in class_obj_dict["System"].values():
            system = obj

        current_ups = copy(system.usage_patterns)
        new_up = UsagePattern(
            "New usage pattern video watching in France", current_ups[0].user_journey, [default_laptop()],
            current_ups[0].network, Countries.FRANCE(),
            SourceHourlyValues(
                create_hourly_usage_df_from_list([elt * 1000 for elt in [4, 23, 12, 52, 24, 51, 71, 85, 3]])))

        logger.warning("Adding new usage pattern")
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        system.usage_patterns += [new_up]
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.assertFalse(self.initial_footprint.value.equals(system.total_footprint.value))

        logger.warning("Removing the new usage pattern")
        system.usage_patterns = current_ups
        new_up.self_delete()

        self.assertTrue(self.initial_footprint.value.equals(system.total_footprint.value))

    def test_plot_footprints_by_category_and_object(self):
        self.system.plot_footprints_by_category_and_object()

    def test_plot_footprints_by_category_and_object_return_only_html(self):
        html = self.system.plot_footprints_by_category_and_object(width=400, height=100, return_only_html=True)
        self.assertTrue(len(html) > 1000)

    def test_plot_emission_diffs(self):
        file = "system_emission_diffs.png"
        self.system.previous_change = None

        with self.assertRaises(ValueError):
            self.system.plot_emission_diffs(filepath=file)

        self.streaming_step.jobs[0].data_upload = SourceValue(500 * u.kB)
        self.system.plot_emission_diffs(filepath=file)
        self.streaming_step.jobs[0].data_upload = SourceValue(
            50 * u.kB, label="Data upload of request streaming")

        self.assertTrue(os.path.isfile(file))
