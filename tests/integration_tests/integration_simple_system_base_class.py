from copy import copy
import os
from datetime import datetime, timedelta, timezone

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
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
from efootprint.builders.time_builders import create_source_hourly_values_from_list, create_hourly_usage_from_frequency
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR
from tests.utils import check_all_calculus_graph_dependencies_consistencies


class IntegrationTestSimpleSystemBaseClass(IntegrationTestBaseClass):
    REF_JSON_FILENAME = "simple_system"
    OBJECT_NAMES_MAP = {
        "storage": "Default SSD storage",
        "server": "Default server",
        "job_1": "job 1",
        "job_2": "job 2",
        "uj_step_1": "UJ step 1",
        "uj_step_2": "UJ step 2",
        "uj": "Usage journey",
        "network": "Default network",
        "usage_pattern": "Usage Pattern",
    }

    @staticmethod
    def generate_simple_system():
        storage = Storage.from_defaults(
            "Default SSD storage", fixed_nb_of_instances=SourceValue(10000 * u.dimensionless),
            idle_power=SourceValue(0.5 * u.W), data_storage_duration=SourceValue(3 * u.hours))
        server = Server.from_defaults("Default server", server_type=ServerTypes.on_premise(), storage=storage,
                                      base_ram_consumption=SourceValue(300 * u.MB),
                                      base_compute_consumption=SourceValue(2 * u.cpu_core))
        job_1 = Job.from_defaults("job 1", server=server)
        uj_step_1 = UsageJourneyStep.from_defaults("UJ step 1", jobs=[job_1])
        job_2 = Job.from_defaults("job 2", server=server)
        uj_step_2 = UsageJourneyStep.from_defaults("UJ step 2", jobs=[job_2])
        uj = UsageJourney("Usage journey", uj_steps=[uj_step_1, uj_step_2])
        network = Network.from_defaults("Default network")

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern = UsagePattern(
            "Usage Pattern", uj, [Device.laptop()], network, Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date))

        # Normalize usage pattern id before computation is made because it is used as dictionary key in intermediary
        # calculations
        usage_pattern.id = css_escape(usage_pattern.name)

        system = System("system 1", [usage_pattern], edge_usage_patterns=[])
        mod_obj_list = [system] + system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj != usage_pattern:
                mod_obj.id = css_escape(mod_obj.name)

        return system, start_date

    @classmethod
    def setUpClass(cls):
        system, start_date = cls.generate_simple_system()
        cls._setup_from_system(system, start_date)

    def run_test_system_calculation_graph_right_after_json_to_system(self):
        # Created just because it exists in the IntegrationTestSimpleSystem class and another test makes sure that both
        # classes have the same methods.
        pass

    def run_test_modeling_object_prints(self):
        str(self.usage_pattern)
        str(self.usage_pattern)
        str(self.server)
        str(self.storage)
        str(self.uj_step_2)
        str(self.uj)
        str(self.network)
        str(self.system)

    def run_test_all_objects_linked_to_system(self):
        expected_objects = {
            self.server, self.storage, self.usage_pattern, self.network, self.uj, self.uj_step_1,
            self.uj_step_2, self.job_1, self.job_2, self.usage_pattern.devices[0],
            self.usage_pattern.country
        }
        self.assertEqual(expected_objects, set(self.system.all_linked_objects))

    def run_test_calculation_graph(self):
        graph = build_calculus_graph(self.system.total_footprint)
        graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_calculation_graph.html"), notebook=False)
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_calculation_graph.html"), "r") as f:
            content = f.read()
        self.assertGreater(len(content), 50000)

    def run_test_object_relationship_graph(self):
        object_relationships_graph = build_object_relationships_graph(
            self.system, classes_to_ignore=USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE)
        object_relationships_graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "object_relationships_graph.html"), notebook=False)

    # INPUT VARIATION TESTING

    def _run_test_variations_on_inputs_from_object_list(
            self, uj_step_1, server, storage, uj, network, usage_pattern, job_1, system):
        self._test_variations_on_obj_inputs(uj_step_1)
        self._test_input_change(
            uj_step_1.user_time_spent, SourceValue(10 * u.min), uj_step_1, "user_time_spent",
            calculated_attributes_that_should_be_updated=[uj.duration, usage_pattern.energy_footprint])
        self._test_variations_on_obj_inputs(
            server, attrs_to_skip=["fraction_of_usage_time", "server_type", "fixed_nb_of_instances"],
            special_mult={
                "ram": 0.01, "utilization_rate": 0.5,
                "base_ram_consumption": 380,
                "base_compute_consumption": 10
            })
        self._test_input_change(
            server.fixed_nb_of_instances, SourceValue(10000 * u.dimensionless), server,
            "fixed_nb_of_instances")
        self._test_input_change(server.server_type, ServerTypes.serverless(), server, "server_type")
        self._test_input_change(server.server_type, ServerTypes.autoscaling(), server, "server_type")
        self._test_variations_on_obj_inputs(
            storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"],)
        self._test_input_change(
            storage.fixed_nb_of_instances, EmptyExplainableObject(), storage, "fixed_nb_of_instances")
        storage.fixed_nb_of_instances = EmptyExplainableObject()
        old_initial_footprint = self.initial_footprint
        self.initial_footprint = system.total_footprint
        self._test_input_change(
            storage.base_storage_need, SourceValue(5000 * u.TB), storage, "base_storage_need")
        storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless)
        self.assertEqual(old_initial_footprint, system.total_footprint)
        self.initial_footprint = old_initial_footprint
        self._test_variations_on_obj_inputs(uj)
        self._test_variations_on_obj_inputs(network)
        self._test_variations_on_obj_inputs(usage_pattern, attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(job_1, special_mult={"data_stored": 1000})

    def run_test_variations_on_inputs(self):
        self._run_test_variations_on_inputs_from_object_list(
            self.uj_step_1, self.server, self.storage, self.uj, self.network, self.usage_pattern,
            self.job_1, self.system)

    def run_test_set_uj_duration_to_0_and_back_to_previous_value(self):
        logger.info("Setting user journey steps duration to 0")
        previous_user_time_spents = []
        for uj_step in self.uj.uj_steps:
            previous_user_time_spents.append(uj_step.user_time_spent)
            uj_step.user_time_spent = SourceValue(0 * u.min)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.info("Setting user journey steps user_time_spent back to previous values")

        for uj_step, previous_user_time_spent in zip(self.uj.uj_steps, previous_user_time_spents):
            uj_step.user_time_spent = previous_user_time_spent

        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_hourly_usage_journey_starts_update(self):
        logger.warning("Updating hourly user journey starts")
        initial_hourly_uj_starts = self.usage_pattern.hourly_usage_journey_starts
        self.usage_pattern.hourly_usage_journey_starts = create_source_hourly_values_from_list(
            [elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]])

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.usage_pattern.hourly_usage_journey_starts = initial_hourly_uj_starts
        self.assertEqual(self.initial_footprint, self.system.total_footprint)


    def run_test_update_footprint_job_datastored_from_positive_value_to_negative_value(self):
        logger.warning("Updating job data_stored from positive to negative value")
        # Release storage nb of instances constraint to make impact clearer
        initial_storage_fixed_nb_of_instances = self.storage.fixed_nb_of_instances
        initial_base_storage_need = self.storage.base_storage_need
        ModelingUpdate([[self.storage.fixed_nb_of_instances, EmptyExplainableObject()],
        [self.storage.base_storage_need, SourceValue(50 * u.TB)]])
        self.footprint_has_changed([self.storage])
        storage_footprint_before_updating_job = (self.storage.instances_fabrication_footprint
                                                 + self.storage.energy_footprint)

        initial_upload_data_stored = self.job_2.data_stored
        initial_storage_need = self.storage.storage_needed
        initial_storage_freed = self.storage.storage_freed
        self.assertGreaterEqual(self.storage.storage_needed.min().magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.max().magnitude, 0)
        # data_stored is positive so storage_freed will be an EmptyExplainableObject

        self.job_2.data_stored = SourceValue(-initial_upload_data_stored.value)

        self.assertNotEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)
        self.assertGreaterEqual(self.storage.storage_needed.min().magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.max().magnitude, 0)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.assertNotEqual(initial_storage_need, self.storage.storage_needed)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)

        self.assertNotEqual(self.storage.instances_fabrication_footprint + self.storage.energy_footprint,
                            storage_footprint_before_updating_job)

        logger.warning("Changing back to previous datastored value")
        self.job_2.data_stored = initial_upload_data_stored

        self.assertEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertEqual(initial_storage_freed, self.storage.storage_freed)

        self.storage.base_storage_need = initial_base_storage_need
        self.storage.fixed_nb_of_instances = initial_storage_fixed_nb_of_instances
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])
        self.assertEqual(initial_storage_need, self.storage.storage_needed)
        self.assertIsInstance(self.storage.storage_freed, EmptyExplainableObject)

    def run_test_make_sure_updating_available_capacity_raises_error_if_necessary(self):
        """Test that InsufficientCapacityError is raised for server and storage when capacities are exceeded."""
        from efootprint.core.hardware.hardware_base import InsufficientCapacityError

        # Server RAM capacity check
        logger.warning("Testing Server available RAM per instance error")
        original_base_ram_consumption = self.server.base_ram_consumption
        with self.assertRaises(InsufficientCapacityError):
            self.server.base_ram_consumption = SourceValue(200 * u.GB_ram)
        self.server.base_ram_consumption = original_base_ram_consumption

        # Server compute capacity check
        logger.warning("Testing Server available compute per instance error")
        original_base_compute_consumption = self.server.base_compute_consumption
        with self.assertRaises(InsufficientCapacityError):
            self.server.base_compute_consumption = SourceValue(30 * u.cpu_core)
        self.server.base_compute_consumption = original_base_compute_consumption

        # Server fixed number of instances vs required instances check
        logger.warning("Testing Server fixed number of instances error")
        original_server_fixed_nb_of_instances = self.server.fixed_nb_of_instances
        initial_server_cpu = self.server.compute
        # Decrease server cpu to force required instances to be > 1
        self.server.compute = SourceValue(2.4 * u.cpu_core)
        with self.assertRaises(InsufficientCapacityError):
            self.server.fixed_nb_of_instances = SourceValue(1 * u.dimensionless)
        self.server.fixed_nb_of_instances = original_server_fixed_nb_of_instances
        self.server.compute = initial_server_cpu

        # Storage fixed number of instances vs required instances check
        logger.warning("Testing Storage fixed number of instances error")
        original_storage_fixed_nb_of_instances = self.storage.fixed_nb_of_instances
        # Decrease storage capacity to force required instances to be > 1
        initial_storage_capacity = self.storage.storage_capacity
        self.storage.storage_capacity = SourceValue(10 * u.GB)
        with self.assertRaises(InsufficientCapacityError):
            self.storage.fixed_nb_of_instances = SourceValue(1 * u.dimensionless)
        self.storage.fixed_nb_of_instances = original_storage_fixed_nb_of_instances
        self.storage.storage_capacity = initial_storage_capacity

        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    # OBJECT LINKS UPDATES TESTING

    def run_test_generate_new_system_with_json_saving_halfway_keeps_calculation_graph_intact(self):
        storage = Storage.from_defaults("Storage")
        server = Server.from_defaults("Server", storage=storage)
        job = Job.from_defaults("Job", server=server)
        json_job = job.to_json(save_calculated_attributes=True)
        job_from_json, _ = Job.from_json_dict(
            json_job, flat_obj_dict={server.id: server}, is_loaded_from_system_with_calculated_attributes=True)
        job.self_delete()
        uj_step = UsageJourneyStep.from_defaults("UJ step", jobs=[job_from_json])
        uj = UsageJourney.from_defaults("Usage journey", uj_steps=[uj_step])
        network = Network.from_defaults("Network")
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern = UsagePattern(
            "Usage pattern", uj, [Device.laptop()], network, Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date))
        system = System("System", [usage_pattern], edge_usage_patterns=[])
        # job data transferred should save its children calculated attributes to json
        children_data = job_from_json.data_transferred.to_json(save_calculated_attributes=True)[
            "direct_children_with_id"]
        self.assertGreater(len(children_data), 0)

    def run_test_uj_step_update(self):
        logger.warning("Updating uj steps in default user journey")
        self.uj.uj_steps = [self.uj_step_1]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.uj.uj_steps = [self.uj_step_1, self.uj_step_2]
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_device_pop_update(self):
        logger.warning("Updating devices in usage pattern")
        self.usage_pattern.devices = [Device.laptop(), Device.screen()]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        up_laptop_with_normalized_id = Device.laptop()
        up_laptop_with_normalized_id.id = css_escape(up_laptop_with_normalized_id.name)
        logger.warning("Setting devices back to laptop with normalized id")
        self.usage_pattern.devices = [up_laptop_with_normalized_id]
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_server(self):
        new_storage = self.storage.copy_with()
        new_server = self.server.copy_with(storage=new_storage)

        logger.warning("Changing jobs server")
        self.job_1.server = new_server
        self.footprint_has_changed([self.server])
        self.job_2.server = new_server
        self.assertEqual(0, self.server.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, self.server.energy_footprint.magnitude)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial job server")
        self.job_1.server = self.server
        self.job_2.server = self.server
        self.assertEqual(0, new_server.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_server.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.server])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_storage(self):
        new_storage = self.storage.copy_with()
        logger.warning("Changing jobs storage")

        self.server.storage = new_storage
        self.footprint_has_changed([self.storage], system=self.system)

        self.assertEqual(0, self.storage.instances_fabrication_footprint.max().magnitude)
        self.assertEqual(0, self.storage.energy_footprint.max().magnitude)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial jobs storage")
        self.server.storage = self.storage
        self.assertEqual(0, new_storage.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_storage.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.storage])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_jobs(self):
        logger.warning("Modifying streaming jobs")
        new_job = Job.from_defaults("new job", server=self.server)

        self.uj_step_1.jobs += [new_job]

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.usage_pattern])
        self.footprint_has_changed([self.storage, self.server, self.network])

        logger.warning("Changing back to previous jobs")
        self.uj_step_1.jobs = [self.job_1]

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def run_test_update_uj_steps(self):
        logger.warning("Modifying uj steps")
        new_step = UsageJourneyStep.from_defaults(
            "new_step", jobs=[Job.from_defaults("new job", server=self.server)]
        )
        self.uj.uj_steps = [new_step]

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.storage, self.server, self.network], system=self.system)

        logger.warning("Changing back to previous uj steps")
        self.uj.uj_steps = [self.uj_step_1, self.uj_step_2]

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def run_test_update_usage_journey(self):
        logger.warning("Changing user journey")
        new_uj = UsageJourney("New version of daily Youtube usage", uj_steps=[self.uj_step_1])
        self.usage_pattern.usage_journey = new_uj

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.storage, self.server, self.network, self.usage_pattern], system=self.system)

        logger.warning("Changing back to previous uj")
        self.usage_pattern.usage_journey = self.uj

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def run_test_update_country_in_usage_pattern(self):
        logger.warning("Changing usage pattern country")

        self.usage_pattern.country = Countries.MALAYSIA()

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.network, self.usage_pattern])

        logger.warning("Changing back to initial usage pattern country")
        self.usage_pattern.country = Countries.FRANCE()

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.network, self.usage_pattern])

    def run_test_update_network(self):
        logger.warning("Changing network")
        new_network = Network.from_defaults("New network with same specs as default")
        self.usage_pattern.network = new_network

        self.assertEqual(0, self.network.energy_footprint.max().magnitude)
        self.footprint_has_changed([self.network], system=self.system)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial network")
        self.usage_pattern.network = self.network
        self.assertEqual(0, new_network.energy_footprint.max().magnitude)
        self.footprint_has_not_changed([self.network])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_add_uj_step_without_job(self):
        logger.warning("Add uj step without job")

        step_without_job = UsageJourneyStep.from_defaults("User checks her phone", jobs=[])

        self.uj.uj_steps.append(step_without_job)

        self.footprint_has_not_changed([self.server, self.storage])
        self.footprint_has_changed([self.usage_pattern])
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Setting user time spent of the new step to 0s")
        step_without_job.user_time_spent = SourceValue(0 * u.min)
        self.footprint_has_not_changed([self.server, self.storage])
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Deleting the new uj step")
        self.uj.uj_steps = self.uj.uj_steps[:-1]
        step_without_job.self_delete()
        self.footprint_has_not_changed([self.server, self.storage])
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

    def run_test_add_usage_pattern(self):
        from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
        analytics_server = BoaviztaCloudServer.from_defaults(
            f"analytics provider server", server_type=ServerTypes.serverless(),
            storage=Storage.from_defaults("analytics provider storage"))
        data_job_2 = Job.from_defaults(f"analytics provider data upload", server=analytics_server)
        daily_analytics_uj = UsageJourney(
            f"Daily analytics provider usage journey",
            uj_steps=[UsageJourneyStep.from_defaults(f"Ingest daily data", jobs=[data_job_2])]
        )
        usage_pattern = UsagePattern(
            f"analytics provider daily uploads", daily_analytics_uj, devices=[Device.smartphone()],
            country=self.usage_pattern.country, network=Network.from_defaults("analytics provider network"),
            hourly_usage_journey_starts=create_hourly_usage_from_frequency(
                timespan=1 * u.year, input_volume=1, frequency="daily",
                start_date=datetime.strptime("2024-01-01", "%Y-%m-%d"))
        )
        logger.warning(f"Adding usage pattern {usage_pattern.name} to system")
        self.system.usage_patterns += [usage_pattern]

        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Removing the new usage pattern from the system")
        self.system.usage_patterns = self.system.usage_patterns[:-1]
        logger.warning("Deleting the usage pattern")
        usage_pattern_id = usage_pattern.id
        usage_pattern.self_delete()
        # Make sure that calculus graph references to the deleted usage pattern are removed
        for direct_child in self.usage_pattern.country.average_carbon_intensity.direct_children_with_id:
            self.assertNotEqual(direct_child.modeling_obj_container.id, usage_pattern_id)

        self.assertEqual(self.system.total_footprint, self.initial_footprint)

    def run_test_change_network_and_hourly_usage_journey_starts_simultaneously_recomputes_in_right_order(self):
        logger.warning("Changing network and hourly usage journey starts simultaneously")
        new_network = Network.from_defaults("New network with same specs as default")
        initial_usage_journey_starts = self.usage_pattern.hourly_usage_journey_starts

        ModelingUpdate([
            [self.usage_pattern.network, new_network],
            [self.usage_pattern.hourly_usage_journey_starts, create_source_hourly_values_from_list(
                [elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]])]
        ])

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.network, self.usage_pattern], system=self.system)
        for ancestor in new_network.energy_footprint.direct_ancestors_with_id:
            self.assertIsNotNone(ancestor.modeling_obj_container)

        logger.warning("Changing back to initial network and hourly usage journey starts")

        ModelingUpdate([
            [self.usage_pattern.network, self.network],
            [self.usage_pattern.hourly_usage_journey_starts, initial_usage_journey_starts]
        ])

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.network, self.usage_pattern])

        for ancestor in self.network.energy_footprint.direct_ancestors_with_id:
            self.assertIsNotNone(ancestor.modeling_obj_container)

    def run_test_delete_job(self):
        logger.info("Removing upload job from upload step")
        self.uj_step_2.jobs = []
        logger.info("Deleting upload job")
        self.job_2.self_delete()
        logger.info("Reinitialize system")
        self.setUpClass()

    # SIMULATION TESTING

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.uj_step_1.user_time_spent, SourceValue(25 * u.min)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=False)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=True)
        self.system.total_footprint.plot(plt_show=False, cumsum=False)
        self.system.total_footprint.plot(plt_show=False, cumsum=True)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        # Depending job occurrences should have been recomputed since a changing user_time_spent might shift jobs
        # distribution across time
        for elt in self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, [elt.id for elt in simulation.values_to_recompute])

    def run_test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.uj_step_1.user_time_spent, SourceValue(25 * u.min)],
                [self.server.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                 self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.uj_step_1.user_time_spent, self.server.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for elt in self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, recomputed_elements_ids)
        self.assertIn(self.server.energy_footprint.id, recomputed_elements_ids)

    def run_test_simulation_add_new_object(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job.from_defaults("new job", server=new_server)

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        simulation = ModelingUpdate([[self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [new_job], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_existing_object(self):
        simulation = ModelingUpdate([[self.uj_step_2.jobs, self.uj_step_2.jobs + [self.job_2]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.job_2.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [self.job_2], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_multiple_objects(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job.from_defaults("new job", server=new_server)

        new_job2 = Job.from_defaults("new job 2", server=new_server)

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        simulation = ModelingUpdate([
                [self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job, new_job2, self.job_1]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.job_1]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [new_job, new_job2, self.job_1], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_objects_and_make_input_changes(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job.from_defaults("new job", server=new_server)

        new_job2 = Job.from_defaults("new job 2", server=new_server)

        simulation = ModelingUpdate([
                [self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job, new_job2, self.job_1]],
                [self.uj_step_1.user_time_spent, SourceValue(25 * u.min)],
                [self.server.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.job_1]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertIn(self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)

    def run_test_semantic_units_in_calculated_attributes(self):
        """Test that all calculated attributes use correct semantic units (occurrence, concurrent, byte_ram)."""
        self.check_semantic_units_in_calculated_attributes(self.system)

    def run_test_check_all_calculus_graph_dependencies_consistencies(self):
        check_all_calculus_graph_dependencies_consistencies(self.system)
