import json
from copy import copy
import os
from datetime import datetime, timedelta, timezone

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.hardware.device import Device
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE
from efootprint.builders.time_builders import create_hourly_usage_df_from_list, create_hourly_usage_from_frequency
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTest(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.storage = Storage(
            "Default SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )

        cls.server = Server(
            "Default server",
            ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(128 * u.GB, Sources.USER_DATA),
            compute=SourceValue(24 * u.cpu_core, Sources.USER_DATA),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.USER_DATA),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.USER_DATA),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS),
            storage=cls.storage
        )

        cls.streaming_job = Job("streaming", server=cls.server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        cls.streaming_step = UsageJourneyStep(
            "20 min streaming on Youtube", user_time_spent=SourceValue(20 * u.min), jobs=[cls.streaming_job])

        cls.upload_job = Job("upload", server=cls.server, data_transferred=SourceValue(300 * u.MB),
            data_stored=SourceValue(300 * u.MB), request_duration=SourceValue(40 * u.s),
            ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))

        cls.upload_step = UsageJourneyStep(
            "40s of upload", user_time_spent=SourceValue(1 * u.min), jobs=[cls.upload_job])

        cls.uj = UsageJourney("Daily Youtube usage", uj_steps=[cls.streaming_step, cls.upload_step])
        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        cls.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        cls.usage_pattern = UsagePattern(
            "Youtube usage in France", cls.uj, [Device.laptop()], cls.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], cls.start_date)))

        # Normalize usage pattern id before computation is made because it is used as dictionary key in intermediary
        # calculations
        cls.usage_pattern.id = "uuid" + cls.usage_pattern.id[9:]

        cls.system = System("system 1", [cls.usage_pattern])
        mod_obj_list = [cls.system] + cls.system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj != cls.usage_pattern:
                mod_obj.id = "uuid" + mod_obj.id[9:]

        cls.initial_footprint = cls.system.total_footprint

        cls.initial_fab_footprints = {
            cls.storage: cls.storage.instances_fabrication_footprint,
            cls.server: cls.server.instances_fabrication_footprint,
            cls.usage_pattern: cls.usage_pattern.devices_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            cls.storage: cls.storage.energy_footprint,
            cls.server: cls.server.energy_footprint,
            cls.network: cls.network.energy_footprint,
            cls.usage_pattern: cls.usage_pattern.devices_energy_footprint,
        }

        cls.initial_system_total_fab_footprint = cls.system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = cls.system.total_energy_footprint_sum_over_period

        cls.ref_json_filename = "simple_system"

        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "system_with_calculated_attributes.json")
        system_to_json(cls.system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)

    def test_all_objects_linked_to_system(self):
        self.assertEqual(
            {self.server, self.storage, self.usage_pattern, self.network, self.uj, self.streaming_step,
             self.upload_step, self.streaming_job, self.upload_job, self.usage_pattern.devices[0],
             self.usage_pattern.country}, set(self.system.all_linked_objects))

    def test_calculation_graph(self):
        graph = build_calculus_graph(self.system.total_footprint)
        graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_calculation_graph.html"), notebook=False)

    def test_object_relationship_graph(self):
        object_relationships_graph = build_object_relationships_graph(
            self.system, classes_to_ignore=USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE)
        object_relationships_graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "object_relationships_graph.html"), notebook=False)

    def test_variations_on_inputs(self):
        self._test_variations_on_obj_inputs(self.streaming_step)
        self._test_variations_on_obj_inputs(
            self.server, attrs_to_skip=["fraction_of_usage_time", "server_type", "fixed_nb_of_instances"],
            special_mult={
                "ram": 0.01, "server_utilization_rate": 0.5,
                "base_ram_consumption": 380,
                "base_compute_consumption": 10
            })
        self._test_input_change(self.server.fixed_nb_of_instances, SourceValue(10000 * u.dimensionless), self.server,
                                "fixed_nb_of_instances")
        self._test_input_change(self.server.server_type, ServerTypes.serverless(), self.server, "server_type")
        self._test_input_change(self.server.server_type, ServerTypes.autoscaling(), self.server, "server_type")
        self._test_variations_on_obj_inputs(
            self.storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"],)
        self._test_input_change(self.storage.fixed_nb_of_instances, EmptyExplainableObject(), self.storage, "fixed_nb_of_instances")
        self.storage.fixed_nb_of_instances = EmptyExplainableObject()
        old_initial_footprint = self.initial_footprint
        self.initial_footprint = self.system.total_footprint
        self._test_input_change(
            self.storage.base_storage_need, SourceValue(5000 * u.TB), self.storage, "base_storage_need")
        self.storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        self.assertEqual(old_initial_footprint, self.system.total_footprint)
        self.initial_footprint = old_initial_footprint
        self._test_variations_on_obj_inputs(self.uj)
        self._test_variations_on_obj_inputs(self.network)
        self._test_variations_on_obj_inputs(self.usage_pattern, attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(self.streaming_job)

    def test_variations_on_inputs_after_system_reloading_with_calculated_attributes(self):
        with open(self.system_json_filepath, "r") as file:
            system_data = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_data, launch_system_computations=False)
        streaming_step = flat_obj_dict[self.streaming_step.id]
        server = flat_obj_dict[self.server.id]
        system = flat_obj_dict[self.system.id]
        uj = flat_obj_dict[self.uj.id]
        network = flat_obj_dict[self.network.id]
        storage = flat_obj_dict[self.storage.id]
        usage_pattern = flat_obj_dict[self.usage_pattern.id]
        streaming_job = flat_obj_dict[self.streaming_job.id]
        self._test_variations_on_obj_inputs(streaming_step)
        self._test_variations_on_obj_inputs(
            server, attrs_to_skip=["fraction_of_usage_time", "server_type", "fixed_nb_of_instances"],
            special_mult={
                "ram": 0.01, "server_utilization_rate": 0.5,
                "base_ram_consumption": 380,
                "base_compute_consumption": 10
            })
        self._test_input_change(server.fixed_nb_of_instances, SourceValue(10000 * u.dimensionless), server,
                                "fixed_nb_of_instances")
        self._test_input_change(server.server_type, ServerTypes.serverless(), server, "server_type")
        self._test_input_change(server.server_type, ServerTypes.autoscaling(), server, "server_type")
        self._test_variations_on_obj_inputs(
            self.storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"],)
        self._test_input_change(storage.fixed_nb_of_instances, EmptyExplainableObject(), storage, "fixed_nb_of_instances")
        self.storage.fixed_nb_of_instances = EmptyExplainableObject()
        old_initial_footprint = self.initial_footprint
        self.initial_footprint = system.total_footprint
        self._test_input_change(
            storage.base_storage_need, SourceValue(5000 * u.TB), storage, "base_storage_need")
        self.storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        self.assertEqual(old_initial_footprint, system.total_footprint)
        self.initial_footprint = old_initial_footprint
        self._test_variations_on_obj_inputs(uj)
        self._test_variations_on_obj_inputs(network)
        self._test_variations_on_obj_inputs(usage_pattern, attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(streaming_job)

    def test_set_uj_duration_to_0_and_back_to_previous_value(self):
        logger.info("Setting user journey steps duration to 0")
        previous_user_time_spents = []
        for uj_step in self.uj.uj_steps:
            previous_user_time_spents.append(uj_step.user_time_spent)
            uj_step.user_time_spent = SourceValue(0 * u.min)

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))

        logger.info("Setting user journey steps user_time_spent back to previous values")

        for uj_step, previous_user_time_spent in zip(self.uj.uj_steps, previous_user_time_spents):
            uj_step.user_time_spent = previous_user_time_spent

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_hourly_usage_journey_starts_update(self):
        logger.warning("Updating hourly user journey starts")
        initial_hourly_uj_starts = self.usage_pattern.hourly_usage_journey_starts
        self.usage_pattern.hourly_usage_journey_starts = SourceHourlyValues(
            create_hourly_usage_df_from_list([elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]]))

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.usage_pattern.hourly_usage_journey_starts = initial_hourly_uj_starts
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_uj_step_update(self):
        logger.warning("Updating uj steps in default user journey")
        self.uj.uj_steps = [self.streaming_step]
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.uj.uj_steps = [self.streaming_step, self.upload_step]
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_device_pop_update(self):
        logger.warning("Updating devices in usage pattern")
        self.usage_pattern.devices = [Device.laptop(), Device.screen()]
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        up_laptop_with_normalized_id = Device.laptop()
        up_laptop_with_normalized_id.id = "uuid" + up_laptop_with_normalized_id.id[9:]
        self.usage_pattern.devices = [up_laptop_with_normalized_id]
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_update_server(self):
        new_storage = Storage(
            "new SSD storage, identical in specs to default one",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )

        new_server = Server(
            "New server, identical in specs to default one",
            server_type=ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(128 * u.GB, Sources.HYPOTHESIS),
            compute=SourceValue(24 * u.cpu_core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(2 * u.cpu_core, Sources.HYPOTHESIS),
            storage=new_storage
        )

        logger.warning("Changing jobs server")
        self.streaming_job.server = new_server
        self.footprint_has_changed([self.server])
        self.upload_job.server = new_server
        self.assertEqual(0, self.server.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, self.server.energy_footprint.magnitude)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Changing back to initial job server")
        self.streaming_job.server = self.server
        self.upload_job.server = self.server
        self.assertEqual(0, new_server.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_server.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.server])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_update_storage(self):
        new_storage = Storage(
            "New storage, identical in specs to Default SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )
        logger.warning("Changing jobs storage")

        self.server.storage = new_storage
        self.footprint_has_changed([self.storage], system=self.system)

        self.assertEqual(0, self.storage.instances_fabrication_footprint.max().magnitude)
        self.assertEqual(0, self.storage.energy_footprint.max().magnitude)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Changing back to initial jobs storage")
        self.server.storage = self.storage
        self.assertEqual(0, new_storage.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_storage.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.storage])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_update_jobs(self):
        logger.warning("Modifying streaming jobs")
        new_job = Job("new job", self.server, data_transferred=SourceValue(5 * u.GB),
         data_stored=SourceValue(50 * u.MB), request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
         compute_needed=SourceValue(1 * u.cpu_core))

        self.streaming_step.jobs += [new_job]

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.usage_pattern])
        self.footprint_has_changed([self.storage, self.server, self.network])

        logger.warning("Changing back to previous jobs")
        self.streaming_step.jobs = [self.streaming_job]

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def test_update_uj_steps(self):
        logger.warning("Modifying uj steps")
        new_step = UsageJourneyStep(
            "new_step", user_time_spent=SourceValue(2 * u.min),
            jobs=[Job("new job", self.server, data_transferred=SourceValue(5 * u.GB), data_stored=SourceValue(5 * u.kB),
                      request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
                      compute_needed=SourceValue(1 * u.cpu_core))]
        )
        self.uj.uj_steps = [new_step]

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.network], system=self.system)

        logger.warning("Changing back to previous uj steps")
        self.uj.uj_steps = [self.streaming_step, self.upload_step]

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def test_update_usage_journey(self):
        logger.warning("Changing user journey")
        new_uj = UsageJourney("New version of daily Youtube usage", uj_steps=[self.streaming_step])
        self.usage_pattern.usage_journey = new_uj

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.network, self.usage_pattern], system=self.system)

        logger.warning("Changing back to previous uj")
        self.usage_pattern.usage_journey = self.uj

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def test_update_country_in_usage_pattern(self):
        logger.warning("Changing usage pattern country")

        self.usage_pattern.country = Countries.MALAYSIA()

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.network, self.usage_pattern])

        logger.warning("Changing back to initial usage pattern country")
        self.usage_pattern.country = Countries.FRANCE()

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.network, self.usage_pattern])

    def test_update_network(self):
        logger.warning("Changing network")
        new_network = Network(
            "New network with same specs as default", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
        self.usage_pattern.network = new_network

        self.assertEqual(0, self.network.energy_footprint.max().magnitude)
        self.footprint_has_changed([self.network], system=self.system)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Changing back to initial network")
        self.usage_pattern.network = self.network
        self.assertEqual(0, new_network.energy_footprint.max().magnitude)
        self.footprint_has_not_changed([self.network])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_uj_step_without_job(self):
        logger.warning("Add uj step without job")

        step_without_job = UsageJourneyStep(
            "User checks her phone", user_time_spent=SourceValue(20 * u.min), jobs=[])

        self.uj.uj_steps.append(step_without_job)

        self.footprint_has_not_changed([self.server, self.storage])
        self.footprint_has_changed([self.usage_pattern])
        self.assertFalse(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Setting user time spent of the new step to 0s")
        step_without_job.user_time_spent = SourceValue(0 * u.min)
        self.footprint_has_not_changed([self.server, self.storage])
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Deleting the new uj step")
        self.uj.uj_steps = self.uj.uj_steps[:-1]
        step_without_job.self_delete()
        self.footprint_has_not_changed([self.server, self.storage])
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

    def test_add_usage_pattern(self):
        from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
        analytics_server = BoaviztaCloudServer.from_defaults(
            f"analytics provider server", server_type=ServerTypes.serverless(), storage=Storage.ssd())
        data_upload_job = Job(
            f"analytics provider data upload", server=analytics_server, data_transferred=SourceValue(350 * u.GB),
            data_stored=SourceValue(350 * u.GB), compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(1 * u.GB), request_duration=SourceValue(1 * u.hour)
        )
        daily_analytics_uj = UsageJourney(f"Daily analytics provider usage journey", uj_steps=[
            UsageJourneyStep(f"Ingest daily data", user_time_spent=SourceValue(1 * u.s),
                             jobs=[data_upload_job])
        ])
        usage_pattern = UsagePattern(
            f"analytics provider daily uploads", daily_analytics_uj, devices=[Device.smartphone()],
            country=Countries.FRANCE(), network=Network.wifi_network(),
            hourly_usage_journey_starts=create_hourly_usage_from_frequency(
                timespan=1 * u.year, input_volume=1, frequency="daily",
                start_date=datetime.strptime("2024-01-01", "%Y-%m-%d"))
        )

        self.system.usage_patterns += [usage_pattern]

        self.assertFalse(self.system.total_footprint.value.equals(self.initial_footprint.value))

        self.system.usage_patterns = self.system.usage_patterns[:-1]

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_variations_on_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        self._test_variations_on_obj_inputs(next(iter(class_obj_dict["UsageJourneyStep"].values())))
        server = next(iter(class_obj_dict["Server"].values()))
        self._test_variations_on_obj_inputs(
            server,
            attrs_to_skip=["fraction_of_usage_time", "server_type", "fixed_nb_of_instances"],
            special_mult={
                "ram": 0.01, "server_utilization_rate": 0.5,
                "base_ram_consumption": 380,
                "base_compute_consumption": 10
            })
        self._test_input_change(server.fixed_nb_of_instances, SourceValue(10000 * u.dimensionless), server,
                                "fixed_nb_of_instances")
        self._test_input_change(server.server_type, ServerTypes.serverless(), server, "server_type")
        self._test_input_change(server.server_type, ServerTypes.autoscaling(), server, "server_type")
        storage = next(iter(class_obj_dict["Storage"].values()))
        self._test_variations_on_obj_inputs(
            storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"],)
        self._test_input_change(storage.fixed_nb_of_instances, EmptyExplainableObject(), storage, "fixed_nb_of_instances")
        storage.fixed_nb_of_instances = EmptyExplainableObject()
        old_initial_footprint = self.initial_footprint
        system = next(iter(class_obj_dict["System"].values()))
        self.initial_footprint = system.total_footprint
        self._test_input_change(
            storage.base_storage_need, SourceValue(5000 * u.TB), storage, "base_storage_need")
        storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        self.assertEqual(old_initial_footprint, system.total_footprint)
        self.initial_footprint = old_initial_footprint
        self._test_variations_on_obj_inputs(next(iter(class_obj_dict["UsageJourney"].values())))
        self._test_variations_on_obj_inputs(next(iter(class_obj_dict["Network"].values())))
        self._test_variations_on_obj_inputs(
            next(iter(class_obj_dict["UsagePattern"].values())), attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(next(iter(class_obj_dict["Job"].values())))

    def test_update_usage_journey_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)
        new_uj = UsageJourney("New version of daily Youtube usage",
                             uj_steps=[next(iter(class_obj_dict["UsageJourneyStep"].values()))])
        usage_pattern = next(iter(class_obj_dict["UsagePattern"].values()))
        previous_uj = usage_pattern.usage_journey
        usage_pattern.usage_journey = new_uj

        system = next(iter(class_obj_dict["System"].values()))
        storage = next(iter(class_obj_dict["Storage"].values()))
        server = next(iter(class_obj_dict["Server"].values()))
        network = next(iter(class_obj_dict["Network"].values()))
        self.assertFalse(self.initial_footprint.value.equals(system.total_footprint.value))
        self.footprint_has_changed([storage, server, network, usage_pattern])

        logger.warning("Changing back to previous uj")
        usage_pattern.usage_journey = previous_uj

        self.assertTrue(self.initial_footprint.value.equals(system.total_footprint.value))
        self.footprint_has_not_changed([storage, server, network, usage_pattern])

    def test_update_jobs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)
        usage_pattern = next(iter(class_obj_dict["UsagePattern"].values()))
        usage_journey = usage_pattern.usage_journey
        streaming_step = usage_journey.uj_steps[0]
        previous_jobs = copy(streaming_step.jobs)
        system = next(iter(class_obj_dict["System"].values()))
        storage = next(iter(class_obj_dict["Storage"].values()))
        server = next(iter(class_obj_dict["Server"].values()))
        network = next(iter(class_obj_dict["Network"].values()))
        logger.warning("Modifying streaming jobs")
        new_job = Job("new job", server, data_transferred=SourceValue(5 * u.GB), data_stored=SourceValue(50 * u.MB),
                      request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
                      compute_needed=SourceValue(1 * u.cpu_core))

        streaming_step.jobs += [new_job]

        self.assertFalse(self.initial_footprint.value.equals(system.total_footprint.value))
        self.footprint_has_not_changed([usage_pattern])
        self.footprint_has_changed([storage, server, network])

        logger.warning("Changing back to previous jobs")
        streaming_step.jobs = previous_jobs

        self.assertTrue(self.initial_footprint.value.equals(system.total_footprint.value))
        self.footprint_has_not_changed([storage, server, network, usage_pattern])

    def test_modeling_object_prints(self):
        str(self.usage_pattern)
        str(self.usage_pattern)
        str(self.server)
        str(self.storage)
        str(self.upload_step)
        str(self.uj)
        str(self.network)
        str(self.system)

    def test_update_footprint_job_datastored_from_positive_value_to_negative_value(self):
        initial_upload_data_stored = self.upload_job.data_stored
        initial_storage_need = self.storage.storage_needed
        initial_storage_freed = self.storage.storage_freed
        self.assertGreaterEqual(self.storage.storage_needed.value.min().iloc[0].magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.value.max().iloc[0].magnitude, 0)
        # data_stored is positive so storage_freed will be an EmptyExplainableObject

        self.upload_job.data_stored = SourceValue(-initial_upload_data_stored.value)

        self.assertNotEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)
        self.assertGreaterEqual(self.storage.storage_needed.value.min().iloc[0].magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.value.max().iloc[0].magnitude, 0)

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.assertNotEqual(initial_storage_need, self.storage.storage_needed)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)

        self.footprint_has_changed([self.storage])

        logger.warning("Changing back to previous datastored value")
        self.upload_job.data_stored = initial_upload_data_stored

        self.assertEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertEqual(initial_storage_freed, self.storage.storage_freed)

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])
        self.assertEqual(initial_storage_need, self.storage.storage_needed)
        self.assertIsInstance(self.storage.storage_freed, EmptyExplainableObject)

    def test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.streaming_step.user_time_spent, SourceValue(25 * u.min)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=False)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=True)
        self.system.total_footprint.plot(plt_show=False, cumsum=False)
        self.system.total_footprint.plot(plt_show=False, cumsum=True)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        # Depending job occurrences should have been recomputed since a changing user_time_spent might shift jobs
        # distribution across time
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id,
                      [elt.id for elt in simulation.values_to_recompute])

    def test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.streaming_step.user_time_spent, SourceValue(25 * u.min)],
                [self.server.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                 self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertIn(self.server.energy_footprint.id, recomputed_elements_ids)

    def test_simulation_add_new_object(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = ModelingUpdate([[self.upload_step.jobs, self.upload_step.jobs + [new_job]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_existing_object(self):
        simulation = ModelingUpdate([[self.upload_step.jobs, self.upload_step.jobs + [self.upload_job]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [self.upload_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_multiple_objects(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = ModelingUpdate([
                [self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job, new_job2, self.streaming_job], self.upload_step.jobs)
        simulation.reset_values()

    def test_simulation_add_objects_and_make_input_changes(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
         data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
         compute_needed=SourceValue(1 * u.cpu_core))

        simulation = ModelingUpdate([
                [self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job]],
                [self.streaming_step.user_time_spent, SourceValue(25 * u.min)],
                [self.server.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
    