import json
import os.path
from copy import copy
from datetime import datetime, timedelta, timezone

from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.logger import logger
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestComplexSystem(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.storage_1 = Storage(
            "Default SSD storage 1",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            data_storage_duration=SourceValue(4 * u.hour, Sources.HYPOTHESIS),
            base_storage_need=SourceValue(100 * u.TB, Sources.HYPOTHESIS)
        )

        cls.storage_2 = Storage(
            "Default SSD storage 2",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            data_storage_duration=SourceValue(4 * u.hour, Sources.HYPOTHESIS),
            base_storage_need=SourceValue(100 * u.TB, Sources.HYPOTHESIS)
        )

        cls.server1 = Server(
            "Server 1",
            server_type=ServerTypes.autoscaling(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(12 * u.GB, Sources.HYPOTHESIS),
            compute=SourceValue(6 * u.cpu_core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS),
            storage=cls.storage_1
        )
        cores_per_cpu_units = SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS)
        nb_cpu_units = SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS)
        cls.server2 = Server(
            "Server 2",
            server_type=ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(12 * u.GB, Sources.HYPOTHESIS),
            compute=cores_per_cpu_units * nb_cpu_units,
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS),
            storage=cls.storage_2
        )
        cls.server3 = Server.from_defaults(
            "TikTok Analytics server", server_type=ServerTypes.serverless(),
            storage=Storage.ssd("TikTok Analytics storage"))
        cls.server3.base_ram_consumption = SourceValue(300 * u.MB, Sources.HYPOTHESIS)
        cls.server3.base_compute_consumption = SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS)
        cls.storage_3 = cls.server3.storage

        cls.streaming_job = Job("streaming", cls.server1, data_transferred=SourceValue(1 * u.GB),
                                data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
                                ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))
        cls.streaming_step = UsageJourneyStep(
            "20 min streaming on Youtube", user_time_spent=SourceValue(20 * u.min), jobs=[cls.streaming_job])

        cls.upload_job = Job("upload", cls.server1, data_transferred=SourceValue(300 * u.kB),
                             data_stored=SourceValue(300 * u.kB), request_duration=SourceValue(0.4 * u.s),
                             ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))
        cls.upload_step = UsageJourneyStep(
            "0.4s of upload", user_time_spent=SourceValue(1 * u.s), jobs=[cls.upload_job])

        cls.dailymotion_job = Job(
            "dailymotion", cls.server1, data_transferred=SourceValue(3.3 * u.MB),
             data_stored=SourceValue(300 * u.kB), request_duration=SourceValue(1 * u.s),
             ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))

        cls.dailymotion_step = UsageJourneyStep(
            "Dailymotion step", user_time_spent=SourceValue(1 * u.min), jobs=[cls.dailymotion_job])

        cls.tiktok_job = Job(
            "tiktok", cls.server2, data_transferred=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(0 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        cls.tiktok_analytics_job = Job(
            "tiktok analytics", cls.server3, data_transferred=SourceValue(50 * u.kB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        cls.tiktok_step = UsageJourneyStep(
            "20 min streaming on TikTok", user_time_spent=SourceValue(20 * u.min),
            jobs=[cls.tiktok_job, cls.tiktok_analytics_job])

        cls.uj = UsageJourney(
            "Daily video usage", uj_steps=[cls.streaming_step, cls.upload_step, cls.dailymotion_step, cls.tiktok_step])

        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        cls.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        cls.usage_pattern1 = UsagePattern(
            "Video watching in France in the morning", cls.uj, [Device.laptop()], cls.network,
            Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                    [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date=cls.start_date)))

        cls.usage_pattern2 = UsagePattern(
            "Video watching in France in the evening", cls.uj, [Device.laptop()], cls.network,
            Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                [elt * 1000 for elt in [4, 2, 1, 5, 2, 1, 7, 8, 3]], start_date=cls.start_date)))

        # Normalize usage pattern ids before computation is made because it is used as dictionary key in intermediary calculations
        cls.usage_pattern1.id = "uuid" + cls.usage_pattern1.id[9:]
        cls.usage_pattern2.id = "uuid" + cls.usage_pattern2.id[9:]

        cls.system = System("system 1", [cls.usage_pattern1, cls.usage_pattern2])
        mod_obj_list = [cls.system] + cls.system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj not in [cls.usage_pattern1, cls.usage_pattern2]:
                mod_obj.id = "uuid" + mod_obj.id[9:]

        cls.initial_footprint = cls.system.total_footprint
        cls.initial_fab_footprints = {
            cls.storage_1: cls.storage_1.instances_fabrication_footprint,
            cls.storage_2: cls.storage_2.instances_fabrication_footprint,
            cls.storage_3: cls.storage_3.instances_fabrication_footprint,
            cls.server1: cls.server1.instances_fabrication_footprint,
            cls.server2: cls.server2.instances_fabrication_footprint,
            cls.server3: cls.server3.instances_fabrication_footprint,
            cls.usage_pattern1: cls.usage_pattern1.instances_fabrication_footprint,
            cls.usage_pattern2: cls.usage_pattern2.instances_fabrication_footprint,
        }
        cls.initial_energy_footprints = {
            cls.storage_1: cls.storage_1.energy_footprint,
            cls.storage_2: cls.storage_2.energy_footprint,
            cls.storage_3: cls.storage_3.energy_footprint,
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

    def test_all_objects_linked_to_system(self):
        expected_list = [
            self.server2, self.server1, self.server3, self.storage_1, self.storage_2, self.storage_3,
            self.usage_pattern1, self.usage_pattern2,
            self.network, self.uj, self.streaming_step, self.upload_step, self.dailymotion_step, self.tiktok_step,
            self.streaming_job, self.upload_job, self.dailymotion_job, self.tiktok_job, self.tiktok_analytics_job,
            self.usage_pattern1.devices[0], self.usage_pattern2.devices[0], self.usage_pattern1.country,
            self.usage_pattern2.country]
        self.assertEqual(set(expected_list), set(self.system.all_linked_objects))

    def test_storage_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        logger.warning("Setting storage fixed_nb_of_instances to not empty")
        old_fixed_nb_of_instances = self.storage_1.fixed_nb_of_instances
        self.storage_1.fixed_nb_of_instances = SourceValue(1000 * u.dimensionless, Sources.HYPOTHESIS)

        self.footprint_has_changed([self.storage_1])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Setting fixed_nb_of_instances back to empty")
        self.storage_1.fixed_nb_of_instances = old_fixed_nb_of_instances

        self.footprint_has_not_changed([self.storage_1])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_on_premise_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        logger.warning("Setting on premise fixed_nb_of_instances to not empty")
        old_fixed_nb_of_instances = self.server2.fixed_nb_of_instances
        self.server2.fixed_nb_of_instances = SourceValue(1000 * u.dimensionless, Sources.HYPOTHESIS)

        self.footprint_has_changed([self.server2])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Setting fixed_nb_of_instances back to empty")
        self.server2.fixed_nb_of_instances = old_fixed_nb_of_instances

        self.footprint_has_not_changed([self.server2])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_dailymotion_and_tiktok_uj_step(self):
        logger.warning("Removing Dailymotion and TikTok uj step")
        self.uj.uj_steps = [self.streaming_step, self.upload_step]

        self.footprint_has_changed([self.server1, self.server2, self.storage_1, self.storage_2])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting Dailymotion and TikTok uj step back")
        self.uj.uj_steps = [self.streaming_step, self.upload_step, self.dailymotion_step, self.tiktok_step]

        self.footprint_has_not_changed([self.server1, self.server2, self.storage_1, self.storage_2])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_dailymotion_single_job(self):
        logger.warning("Removing Dailymotion job")
        self.dailymotion_step.jobs = []

        self.footprint_has_changed([self.server1, self.storage_1])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting Dailymotion job back")
        self.dailymotion_step.jobs = [self.dailymotion_job]

        self.footprint_has_not_changed([self.server1, self.storage_1])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_one_tiktok_job(self):
        logger.warning("Removing one TikTok job")
        self.tiktok_step.jobs = [self.tiktok_job]

        self.footprint_has_changed([self.server3, self.storage_3], system=self.system)
        self.footprint_has_not_changed([self.server2, self.storage_2])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Putting TikTok job back")
        self.tiktok_step.jobs = [self.tiktok_job, self.tiktok_analytics_job]

        self.footprint_has_not_changed([self.server3, self.storage_3, self.server2, self.storage_2])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_remove_all_tiktok_jobs(self):
        logger.warning("Removing all TikTok jobs")
        self.tiktok_step.jobs = []

        self.footprint_has_changed([self.server2, self.storage_2, self.server3, self.storage_3],
                                   system=self.system)
        self.footprint_has_not_changed([self.server1])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint))

        logger.warning("Putting TikTok jobs back")
        self.tiktok_step.jobs = [self.tiktok_job, self.tiktok_analytics_job]

        self.footprint_has_not_changed([self.server3, self.storage_3, self.server2, self.storage_2])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_new_job(self):
        logger.warning("Adding job")
        new_job = Job(
            "new job", self.server1, data_transferred=SourceValue(3 * u.MB), data_stored=SourceValue(3 * u.MB),
            request_duration=SourceValue(1 * u.s), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        new_uj_step = UsageJourneyStep(
            "new uj step", user_time_spent=SourceValue(1 * u.s), jobs=[new_job])
        self.uj.uj_steps += [new_uj_step]

        self.footprint_has_changed([self.server1, self.storage_1])
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.warning("Removing new job")
        self.uj.uj_steps = self.uj.uj_steps[:-1]
        job = new_uj_step.jobs[0]
        new_uj_step.self_delete()
        job.self_delete()

        self.footprint_has_not_changed([self.server1, self.storage_1])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_new_usage_pattern(self):
        new_up = UsagePattern(
            "New usage pattern video watching in France", self.uj, [Device.laptop()], self.network, Countries.FRANCE(),
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
            "New usage pattern video watching in France", current_ups[0].usage_journey, [Device.laptop()],
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

        old_data_transferred = self.streaming_step.jobs[0].data_transferred
        self.streaming_step.jobs[0].data_transferred = SourceValue(500 * u.kB)
        self.system.plot_emission_diffs(filepath=file)
        self.streaming_step.jobs[0].data_transferred = old_data_transferred

        self.assertTrue(os.path.isfile(file))

    def test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.streaming_step.user_time_spent, SourceValue(25 * u.min)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        # Depending job occurrences should have been recomputed since a changing user_time_spent might shift jobs
        # distribution across time
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id,
                      [elt.id for elt in simulation.values_to_recompute])

    def test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.streaming_step.user_time_spent, SourceValue(25 * u.min)],
                [self.server1.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server1.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertIn(self.server1.energy_footprint.id, recomputed_elements_ids)

    def test_simulation_add_new_object(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = ModelingUpdate(
            [[self.upload_step.jobs, self.upload_step.jobs + [new_job]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_existing_object(self):
        simulation = ModelingUpdate(
            [[self.upload_step.jobs, self.upload_step.jobs + [self.upload_job]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [self.upload_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_multiple_objects(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = ModelingUpdate(
            [[self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job, new_job2, self.streaming_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_objects_and_make_input_changes(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
         data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
         compute_needed=SourceValue(1 * u.cpu_core))

        simulation = ModelingUpdate(
            [
                [self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job]],
                [self.streaming_step.user_time_spent, SourceValue(25 * u.min)],
                [self.server1.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
        self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server1.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
