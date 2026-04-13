from copy import copy
import os
from datetime import datetime, timedelta, timezone

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
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
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, ObjectLinkScenario
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
            data_storage_duration=SourceValue(3 * u.hours))
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

        system = System("system 1", [usage_pattern], edge_usage_patterns=[])

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
            self.uj_step_2, self.job_1, self.job_2, self.usage_pattern.devices[0], self.usage_pattern.country}
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
            calculated_attributes_that_should_be_updated=[uj.duration, usage_pattern.devices[0].energy_footprint])
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
            storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need", "power", "data_replication_factor",
                                    "data_storage_duration"],)
        self._test_input_change(
            storage.fixed_nb_of_instances, EmptyExplainableObject(), storage, "fixed_nb_of_instances")
        with self.cleanup_stack(verify_total_footprint=False) as cleanup:
            cleanup.callback(setattr, self, "initial_footprint", self.initial_footprint)
            cleanup.callback(setattr, storage, "fixed_nb_of_instances", storage.fixed_nb_of_instances)
            storage.fixed_nb_of_instances = EmptyExplainableObject()
            self.initial_footprint = system.total_footprint
            self._test_input_change(
                storage.base_storage_need, SourceValue(5000 * u.TB_stored), storage, "base_storage_need")
        self.assertEqual(self.initial_footprint, system.total_footprint)
        self._test_variations_on_obj_inputs(uj)
        self._test_variations_on_obj_inputs(network)
        self._test_variations_on_obj_inputs(usage_pattern, attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(job_1, attrs_to_skip=["data_stored"])
        self._test_input_change(
            self.usage_pattern.hourly_usage_journey_starts,
            create_source_hourly_values_from_list([elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]]),
            self.usage_pattern, "hourly_usage_journey_starts")

    def run_test_variations_on_inputs(self):
        self._run_test_variations_on_inputs_from_object_list(
            self.uj_step_1, self.server, self.storage, self.uj, self.network, self.usage_pattern,
            self.job_1, self.system)

    def run_test_set_uj_duration_to_0_and_back_to_previous_value(self):
        logger.info("Setting user journey steps duration to 0")
        changes = []
        for uj_step in self.uj.uj_steps:
            changes.append([uj_step.user_time_spent, SourceValue(0 * u.min)])

        with self.cleanup_stack() as cleanup:
            update = ModelingUpdate(changes)
            cleanup.callback(update.reset_values)
            self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_make_sure_updating_available_capacity_raises_error_if_necessary(self):
        """Test that InsufficientCapacityError is raised for server and storage when capacities are exceeded."""
        from efootprint.core.hardware.hardware_base import InsufficientCapacityError

        # Server RAM capacity check
        logger.warning("Testing Server available RAM per instance error")
        with self.cleanup_stack() as cleanup:
            cleanup.callback(setattr, self.server, "base_ram_consumption", self.server.base_ram_consumption)
            with self.assertRaises(InsufficientCapacityError):
                self.server.base_ram_consumption = SourceValue(200 * u.GB_ram)

        # Server compute capacity check
        logger.warning("Testing Server available compute per instance error")
        with self.cleanup_stack() as cleanup:
            cleanup.callback(setattr, self.server, "base_compute_consumption", self.server.base_compute_consumption)
            with self.assertRaises(InsufficientCapacityError):
                self.server.base_compute_consumption = SourceValue(30 * u.cpu_core)

        # Server fixed number of instances vs required instances check
        logger.warning("Testing Server fixed number of instances error")
        with self.cleanup_stack() as cleanup:
            cleanup.callback(setattr, self.server, "fixed_nb_of_instances", self.server.fixed_nb_of_instances)
            cleanup.callback(setattr, self.server, "compute", self.server.compute)
            self.server.compute = SourceValue(2.4 * u.cpu_core)
            with self.assertRaises(InsufficientCapacityError):
                self.server.fixed_nb_of_instances = SourceValue(1 * u.dimensionless)

        # Storage fixed number of instances vs required instances check
        logger.warning("Testing Storage fixed number of instances error")
        with self.cleanup_stack() as cleanup:
            cleanup.callback(setattr, self.storage, "fixed_nb_of_instances", self.storage.fixed_nb_of_instances)
            cleanup.callback(setattr, self.storage, "storage_capacity", self.storage.storage_capacity)
            self.storage.storage_capacity = SourceValue(10 * u.GB_stored)
            with self.assertRaises(InsufficientCapacityError):
                self.storage.fixed_nb_of_instances = SourceValue(1 * u.dimensionless)

    def run_test_make_sure_that_storage_fabrication_footprint_is_linked_to_jobs(self):
        self.assertIn(self.storage, self.job_1.attributed_fabrication_footprint_per_source)
        self.assertIn(self.storage, self.job_1.attributed_fabrication_footprint_per_source)

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
        scenario = ObjectLinkScenario(
            name="uj_step_update",
            updates_builder=[[self.uj.uj_steps, [self.uj_step_1]]],
        )
        self._run_object_link_scenario(scenario)

    def run_test_device_pop_update(self):
        scenario = ObjectLinkScenario(
            name="device_pop_update",
            updates_builder=[[self.usage_pattern.devices, [Device.laptop(), Device.screen()]]],
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_server(self):
        new_storage = self.storage.copy_with()
        new_server = self.server.copy_with(storage=new_storage)
        scenario = ObjectLinkScenario(
            name="update_server",
            updates_builder=[[self.job_1.server, new_server], [self.job_2.server, new_server]],
            expected_changed=[self.server],
            expect_total_change=False,
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_storage(self):
        new_storage = self.storage.copy_with()
        scenario = ObjectLinkScenario(
            name="update_storage",
            updates_builder=[[self.server.storage, new_storage]],
            expected_changed=[self.storage],
            expect_total_change=False
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_jobs(self):
        new_job = Job.from_defaults("new job", server=self.server)
        scenario = ObjectLinkScenario(
            name="update_jobs",
            updates_builder=[[self.uj_step_1.jobs, self.uj_step_1.jobs + [new_job]]],
            # storage doesn’t change since it has fixed number of instances.
            expected_changed=[self.server, self.network],
            expected_unchanged=[self.usage_pattern.devices[0]],
        )
        self._run_object_link_scenario(scenario)
        new_job.self_delete()

    def run_test_update_uj_steps(self):
        new_step = UsageJourneyStep.from_defaults(
            "new_step", jobs=[Job.from_defaults("new job", server=self.server)]
        )
        scenario = ObjectLinkScenario(
            name="update_uj_steps",
            updates_builder=[[self.uj.uj_steps, [new_step]]],
            expected_changed=[self.server, self.network],
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_usage_journey(self):
        new_uj = UsageJourney("New version of daily Youtube usage", uj_steps=[self.uj_step_1])
        scenario = ObjectLinkScenario(
            name="update_usage_journey",
            updates_builder=[[self.usage_pattern.usage_journey, new_uj]],
            expected_changed=[self.server, self.network, self.usage_pattern.devices[0]],
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_country_in_usage_pattern(self):
        scenario = ObjectLinkScenario(
            name="update_usage_pattern_country",
            updates_builder=[[self.usage_pattern.country, Countries.MALAYSIA()]],
            expected_changed=[self.network, self.usage_pattern.devices[0]],
        )
        self._run_object_link_scenario(scenario)

    def run_test_update_network(self):
        new_network = Network.from_defaults("New network with same specs as default")

        def post_assertions(test):
            test.assertEqual(0, test.network.energy_footprint.max().magnitude)

        scenario = ObjectLinkScenario(
            name="update_network",
            updates_builder=[[self.usage_pattern.network, new_network]],
            expected_changed=[self.network],
            expect_total_change=False,
            post_assertions=post_assertions,
        )
        self._run_object_link_scenario(scenario)

    def run_test_add_uj_step_without_job(self):
        logger.warning("Add uj step without job")

        step_without_job = UsageJourneyStep.from_defaults("User checks her phone", jobs=[])
        with self.cleanup_stack(verify_unchanged=[self.server, self.storage]) as cleanup:
            initial_steps = copy(self.uj.uj_steps)
            cleanup.callback(step_without_job.self_delete)
            cleanup.callback(setattr, self.uj, "uj_steps", initial_steps)
            self.uj.uj_steps.append(step_without_job)

            self.footprint_has_not_changed([self.server, self.storage])
            self.footprint_has_changed([self.usage_pattern.devices[0]])
            self.assertNotEqual(self.system.total_footprint, self.initial_footprint)

            logger.warning("Setting user time spent of the new step to 0s")
            step_without_job.user_time_spent = SourceValue(0 * u.min)
            self.footprint_has_not_changed([self.server, self.storage])
            self.assertEqual(self.system.total_footprint, self.initial_footprint)

    def run_test_add_usage_pattern(self):
        from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer

        analytics_server = BoaviztaCloudServer.from_defaults(
            "analytics provider server", server_type=ServerTypes.on_premise(),
            storage=Storage.from_defaults("analytics provider storage"))
        data_job_2 = Job.from_defaults("analytics provider data upload", server=analytics_server)
        daily_analytics_uj = UsageJourney(
            "Daily analytics provider usage journey",
            uj_steps=[UsageJourneyStep.from_defaults("Ingest daily data", jobs=[data_job_2])]
        )
        usage_pattern = UsagePattern(
            "analytics provider daily uploads", daily_analytics_uj, devices=[Device.smartphone()],
            country=self.usage_pattern.country, network=Network.from_defaults("analytics provider network"),
            hourly_usage_journey_starts=create_hourly_usage_from_frequency(
                timespan=1 * u.year, input_volume=1, frequency="daily",
                start_date=datetime.strptime("2024-01-01", "%Y-%m-%d"))
        )

        def post_reset(test):
            usage_pattern.self_delete()
            for direct_child in test.usage_pattern.country.average_carbon_intensity.direct_children_with_id:
                test.assertNotEqual(direct_child.modeling_obj_container.id, usage_pattern.id)

        scenario = ObjectLinkScenario(
            name="add_usage_pattern",
            updates_builder=[[self.system.usage_patterns, self.system.usage_patterns + [usage_pattern]]],
            post_reset_assertions=post_reset,
        )
        self._run_object_link_scenario(scenario)

    def run_test_change_network_and_hourly_usage_journey_starts_simultaneously_recomputes_in_right_order(self):
        new_network = Network.from_defaults("New network with same specs as default")
        new_hourly = create_source_hourly_values_from_list(
            [elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]])

        def post_assertions(test):
            for ancestor in new_network.energy_footprint.direct_ancestors_with_id:
                test.assertIsNotNone(ancestor.modeling_obj_container)

        def post_reset(test):
            for ancestor in test.network.energy_footprint.direct_ancestors_with_id:
                test.assertIsNotNone(ancestor.modeling_obj_container)

        scenario = ObjectLinkScenario(
            name="change_network_and_hourly_usage_starts",
            updates_builder=[
                [self.usage_pattern.network, new_network],
                [self.usage_pattern.hourly_usage_journey_starts, new_hourly],
            ],
            expected_changed=[self.network, self.usage_pattern.devices[0]],
            post_assertions=post_assertions,
            post_reset_assertions=post_reset,
        )
        self._run_object_link_scenario(scenario)

    def run_test_delete_job(self):
        def restore_job_2():
            current_jobs = [job for job in self.uj_step_2.jobs if job.name == "job 2"]
            restored_job = current_jobs[0] if current_jobs else Job.from_defaults("job 2", server=self.server)
            self.uj_step_2.jobs = [restored_job]
            type(self).job_2 = restored_job

        with self.cleanup_stack() as cleanup:
            cleanup.callback(restore_job_2)
            logger.info("Removing upload job from upload step")
            self.uj_step_2.jobs = []
            logger.info("Deleting upload job")
            self.job_2.self_delete()

    # SIMULATION TESTING

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.uj_step_1.user_time_spent, SourceValue(25 * u.min)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.usage_pattern.devices[0].energy_footprint.plot(plt_show=False, cumsum=False)
        self.usage_pattern.devices[0].energy_footprint.plot(plt_show=False, cumsum=True)
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

    def run_test_dict_container_integrity(self):
        """Test bidirectional consistency of explainable_object_dicts_containers tracking."""
        self.verify_dict_container_integrity(self.system)

    def run_test_semantic_units_in_calculated_attributes(self):
        """Test that all calculated attributes use correct semantic units (occurrence, concurrent, byte_ram)."""
        self.check_semantic_units_in_calculated_attributes(self.system)

    def run_test_check_all_calculus_graph_dependencies_consistencies(self):
        check_all_calculus_graph_dependencies_consistencies(self.system)

    def run_test_impact_repartition_sankey(self):
        from efootprint.utils.impact_repartition import ImpactRepartitionSankey
        sankey = ImpactRepartitionSankey(self.system)
        fig = sankey.figure()
        print('Nodes:', sankey.node_labels)
        print('Links:', list(zip(sankey.link_sources, sankey.link_targets, sankey.link_values)))
