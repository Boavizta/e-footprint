import os.path
from copy import copy
from datetime import datetime, timedelta, timezone
import numpy as np
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from pint import Quantity

from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
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
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, ObjectLinkScenario


class IntegrationTestComplexSystemBaseClass(IntegrationTestBaseClass):
    REF_JSON_FILENAME = "complex_system"
    OBJECT_NAMES_MAP = {
        "storage_1": "Default SSD storage 1",
        "storage_2": "Default SSD storage 2",
        "storage_3": "Default SSD storage 3",
        "server1": "Server 1",
        "server2": "Server 2",
        "server3": "Server 3",
        "server1_job1": "server 1 job 1",
        "server1_job2": "server 1 job 2",
        "server1_job3": "server 1 job 3",
        "server2_job": "server 2 job",
        "server3_job": "server 3 job",
        "server3_job2": "server 3 job 2",
        "uj_step_1": "UJ step 1",
        "uj_step_2": "UJ step 2",
        "uj_step_3": "UJ step 3",
        "uj_step_4": "UJ step 4",
        "usage_pattern1": "Usage pattern 1",
        "usage_pattern2": "Usage pattern 2",
        "uj": "Usage journey",
        "network1": "network 1",
        "network2": "network 2",
        "edge_storage": "Edge SSD storage",
        "edge_computer": "Edge device",
        "edge_process": "Edge process",
        "rsn1": "Recurrent server need 1",
        "rsn2": "Recurrent server need 2",
        "edge_function": "Edge function",
        "edge_usage_journey": "Edge usage journey",
        "edge_usage_pattern": "Edge usage pattern",
    }

    @staticmethod
    def generate_complex_system():
        storage_1 = Storage.from_defaults("Default SSD storage 1")
        storage_2 = Storage.from_defaults("Default SSD storage 2")
        server1 = Server.from_defaults("Server 1", storage=storage_1)
        server2 = Server.from_defaults("Server 2", server_type=ServerTypes.on_premise(), storage=storage_2)
        server3 = Server.from_defaults(
            "Server 3", server_type=ServerTypes.serverless(), storage=Storage.ssd("Default SSD storage 3"))

        server1_job1 = Job.from_defaults("server 1 job 1", server=server1)
        uj_step_1 = UsageJourneyStep.from_defaults("UJ step 1", jobs=[server1_job1])
        server1_job2 = Job.from_defaults("server 1 job 2", server=server1)
        uj_step_2 = UsageJourneyStep.from_defaults("UJ step 2", jobs=[server1_job2])
        server1_job3 = Job.from_defaults("server 1 job 3", server=server1)
        uj_step_3 = UsageJourneyStep.from_defaults("UJ step 3", jobs=[server1_job3])
        server2_job = Job.from_defaults("server 2 job", server=server2)
        server3_job = Job.from_defaults("server 3 job", server=server3)
        uj_step_4 = UsageJourneyStep.from_defaults("UJ step 4", jobs=[server2_job, server3_job])

        uj = UsageJourney(
            "Usage journey", uj_steps=[uj_step_1, uj_step_2, uj_step_3, uj_step_4])

        network1 = Network.from_defaults("network 1")
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern1 = UsagePattern(
            "Usage pattern 1", uj, [Device.laptop()], network1,
            Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date=start_date))

        network2 = Network.from_defaults("network 2")
        usage_pattern2 = UsagePattern(
            "Usage pattern 2", uj, [Device.laptop()], network2,
            Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [4, 2, 1, 5, 2, 1, 7, 8, 3]], start_date=start_date))

        # Edge components
        edge_storage = EdgeStorage.from_defaults("Edge SSD storage")
        edge_computer = EdgeComputer.from_defaults("Edge device", storage=edge_storage)
        edge_process = RecurrentEdgeProcess.from_defaults("Edge process", edge_device=edge_computer)
        server3_job2 = Job.from_defaults("server 3 job 2", server=server3)
        rsn_1 = RecurrentServerNeed.from_defaults(
            "Recurrent server need 1", edge_device=edge_computer, jobs=[server1_job1, server3_job2])
        rsn_2 = RecurrentServerNeed.from_defaults(
            "Recurrent server need 2", edge_device=edge_computer, jobs=[server2_job])
        edge_function = EdgeFunction("Edge function", recurrent_edge_device_needs=[edge_process],
                                     recurrent_server_needs=[rsn_1, rsn_2])
        edge_usage_journey = EdgeUsageJourney.from_defaults("Edge usage journey", edge_functions=[edge_function])

        edge_usage_pattern = EdgeUsagePattern(
            "Edge usage pattern",
            edge_usage_journey=edge_usage_journey,
            network=network1,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt * 100 for elt in [1, 1, 2, 2, 3, 3, 1, 1, 2]], start_date)
        )

        # Normalize usage pattern ids before computation is made because it is used as dictionary key in intermediary calculations
        usage_pattern1.id = css_escape(usage_pattern1.name)
        usage_pattern2.id = css_escape(usage_pattern2.name)
        edge_usage_pattern.id = css_escape(edge_usage_pattern.name)

        system = System("system 1", [usage_pattern1, usage_pattern2], edge_usage_patterns=[edge_usage_pattern])
        mod_obj_list = [system] + system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj not in [usage_pattern1, usage_pattern2]:
                mod_obj.id = css_escape(mod_obj.name)
        for edge_process_need in edge_process.recurrent_edge_component_needs:
            edge_process_need.id = css_escape(edge_process_need.name)
        for edge_computer_component in edge_computer.components:
            edge_computer_component.id = css_escape(edge_computer_component.name)

        return system, start_date

    @classmethod
    def setUpClass(cls):
        system, start_date = cls.generate_complex_system()
        cls._setup_from_system(system, start_date)

    def run_test_all_objects_linked_to_system(self):
        expected_list = [
            self.server2, self.server1, self.server3, self.storage_1, self.storage_2, self.storage_3,
            self.usage_pattern1, self.usage_pattern2, self.edge_usage_pattern,
            self.network1, self.network2, self.uj, self.uj_step_1, self.uj_step_2, self.uj_step_3,
            self.uj_step_4, self.server1_job1, self.server1_job2, self.server1_job3, self.server2_job,
            self.server3_job, self.server3_job2, self.usage_pattern1.devices[0], self.usage_pattern2.devices[0],
            self.usage_pattern1.country, self.usage_pattern2.country, self.edge_storage, self.edge_computer,
            self.edge_process, self.edge_function, self.edge_usage_journey, self.edge_usage_pattern.country
        ] + self.edge_computer.components + self.edge_process.recurrent_edge_component_needs + [self.rsn1, self.rsn2]
        self.assertEqual(set(expected_list), set(self.system.all_linked_objects))

    def run_test_remove_uj_steps_1_and_2(self):
        scenario = ObjectLinkScenario(
            name="remove_uj_steps_1_and_2",
            updates_builder=[[self.uj.uj_steps, [self.uj_step_1, self.uj_step_2]]],
            expected_changed=[self.server1, self.server2, self.storage_1, self.storage_2],
        )
        self._run_object_link_scenario(scenario)

    def run_test_remove_uj_step_3_job(self):
        scenario = ObjectLinkScenario(
            name="remove_uj_step_3_job",
            updates_builder=[[self.uj_step_3.jobs, []]],
            expected_changed=[self.server1, self.storage_1],
        )
        self._run_object_link_scenario(scenario)

    def run_test_remove_one_uj_step_4_job(self):
        scenario = ObjectLinkScenario(
            name="remove_one_uj_step_4_job",
            updates_builder=[[self.uj_step_4.jobs, [self.server2_job]]],
            expected_changed=[self.server3, self.storage_3],
            expected_unchanged=[self.server2, self.storage_2],
        )
        self._run_object_link_scenario(scenario)

    def run_test_remove_all_uj_step_4_jobs(self):
        scenario = ObjectLinkScenario(
            name="remove_all_uj_step_4_jobs",
            updates_builder=[[self.uj_step_4.jobs, []]],
            expected_changed=[self.server2, self.storage_2, self.server3, self.storage_3],
            expected_unchanged=[self.server1],
        )
        self._run_object_link_scenario(scenario)

    def run_test_add_new_job(self):
        new_job = Job.from_defaults("new job", server=self.server1)
        new_uj_step = UsageJourneyStep.from_defaults("new uj step", jobs=[new_job])
        updated_steps = self.uj.uj_steps + [new_uj_step]

        scenario = ObjectLinkScenario(
            name="add_new_job",
            updates_builder=[[self.uj.uj_steps, updated_steps]],
            expected_changed=[self.server1, self.storage_1],
        )
        self._run_object_link_scenario(scenario)

    def run_test_add_new_usage_pattern_with_new_network_and_edit_its_hourly_uj_starts(self):
        new_network = Network.wifi_network()
        new_up = UsagePattern(
            "New usage pattern video watching in France", self.uj, [Device.laptop()], new_network, Countries.FRANCE(),
            create_source_hourly_values_from_list([elt * 1000 for elt in [1, 4, 1, 5, 3, 1, 5, 23, 2]]))

        server1_job1 = self.server1_job1
        up = self.usage_pattern2
        hour_occs_per_up = server1_job1.hourly_occurrences_per_usage_pattern[up]
        logger.warning("Adding new usage pattern")
        self.system.usage_patterns += [new_up]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        # server1_job1 has been recomputed, hour_occs_per_up should not be linked to a modeling object anymore
        self.assertIsNone(hour_occs_per_up.modeling_obj_container)
        # server1_job1 has 4 usage patterns (2 web + 1 edge initially, + the new one)
        # so its hourly_avg_occurrences_across_usage_patterns should have 3 ancestors
        self.assertEqual(len(server1_job1.hourly_avg_occurrences_across_usage_patterns.direct_ancestors_with_id), 4)

        logger.warning("Editing the usage pattern network")
        new_up.hourly_usage_journey_starts = create_source_hourly_values_from_list(
            [elt * 1000 for elt in [2, 4, 1, 5, 3, 1, 5, 23, 2]])
        # self.network1.energy_footprint should not have been recomputed, nor its ancestors
        for elt in self.network1.energy_footprint.direct_ancestors_with_id:
            self.assertIsNotNone(elt.modeling_obj_container)

        logger.warning("Removing the new usage pattern")
        self.system.usage_patterns = [self.usage_pattern1, self.usage_pattern2]
        new_up.self_delete()

        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_add_edge_usage_pattern(self):
        new_edge_storage = EdgeStorage.from_defaults("New edge SSD storage")
        new_edge_computer = EdgeComputer.from_defaults("New edge device", storage=new_edge_storage)
        new_edge_process = RecurrentEdgeProcess.from_defaults("New edge process", edge_device=new_edge_computer)
        new_edge_function = EdgeFunction("New edge function", recurrent_edge_device_needs=[new_edge_process],
                                         recurrent_server_needs=[])
        new_edge_usage_journey = EdgeUsageJourney.from_defaults(
            "New edge usage journey", edge_functions=[new_edge_function])
        new_edge_usage_pattern = EdgeUsagePattern(
            "New edge usage pattern",
            edge_usage_journey=new_edge_usage_journey,
            network=Network.wifi_network(),
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt * 50 for elt in [2, 1, 3, 2, 4, 2, 1, 2, 3]], self.start_date)
        )
        updated_edge_usage_patterns = self.system.edge_usage_patterns + [new_edge_usage_pattern]
        scenario = ObjectLinkScenario(
            name="add_edge_usage_pattern",
            updates_builder=[[self.system.edge_usage_patterns, updated_edge_usage_patterns]],
            expected_unchanged=[self.edge_computer, self.edge_storage],
        )
        self._run_object_link_scenario(scenario)

    def run_test_plot_footprints_by_category_and_object(self):
        self.system.plot_footprints_by_category_and_object()

    def run_test_plot_footprints_by_category_and_object_notebook_false(self):
        fig = self.system.plot_footprints_by_category_and_object(width=400, height=100, notebook=False)
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        self.assertTrue(len(html) > 1000)

    def run_test_plot_emission_diffs(self):
        file = "system_emission_diffs.png"
        self.system.previous_change = None

        with self.assertRaises(ValueError):
            self.system.plot_emission_diffs(filepath=file)

        old_data_transferred = self.uj_step_1.jobs[0].data_transferred
        self.uj_step_1.jobs[0].data_transferred = SourceValue(500 * u.kB)
        self.system.plot_emission_diffs(filepath=file)
        self.uj_step_1.jobs[0].data_transferred = old_data_transferred

        self.assertTrue(os.path.isfile(file))

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.uj_step_1.user_time_spent, SourceValue(25 * u.min)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.uj_step_1.user_time_spent])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        # Depending job occurrences should have been recomputed since a changing user_time_spent might shift jobs
        # distribution across time
        for elt in self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, [elt.id for elt in simulation.values_to_recompute])

    def run_test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.uj_step_1.user_time_spent, SourceValue(25 * u.min)],
                [self.server1.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.uj_step_1.user_time_spent, self.server1.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for elt in self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, recomputed_elements_ids)
        self.assertIn(self.server1.energy_footprint.id, recomputed_elements_ids)

    def run_test_simulation_add_new_object(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job.from_defaults(
            "new job", server=new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
            data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
            ram_needed=SourceValue(100 * u.MB_ram), compute_needed=SourceValue(1 * u.cpu_core))

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        simulation = ModelingUpdate(
            [[self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [new_job], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_existing_object(self):
        logger.info(f"Launching simulation")
        simulation = ModelingUpdate(
            [[self.uj_step_2.jobs, self.uj_step_2.jobs + [self.server1_job2]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))
        logger.info("Simulation computed")

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.server1_job2.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [self.server1_job2], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_multiple_objects(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job.from_defaults(
            "new job", server=new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
            data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
            ram_needed=SourceValue(100 * u.MB_ram), compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job.from_defaults(
            "new job 2", server=new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
            data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
            ram_needed=SourceValue(100 * u.MB_ram), compute_needed=SourceValue(1 * u.cpu_core))

        initial_uj_step_2_jobs = copy(self.uj_step_2.jobs)
        simulation = ModelingUpdate(
            [[self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job, new_job2, self.server1_job1]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.server1_job1]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_uj_step_2_jobs, self.uj_step_2.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_uj_step_2_jobs + [new_job, new_job2, self.server1_job1], self.uj_step_2.jobs)
        simulation.reset_values()

    def run_test_simulation_add_objects_and_make_input_changes(self):
        new_server = Server.from_defaults("new server", server_type=ServerTypes.on_premise(),
                                          storage=Storage.from_defaults("new storage"))
        new_job = Job.from_defaults(
            "new job", server=new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
            data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
            ram_needed=SourceValue(100 * u.MB_ram), compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job.from_defaults(
            "new job 2", server=new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
            data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
            ram_needed=SourceValue(100 * u.MB_ram), compute_needed=SourceValue(1 * u.cpu_core))

        simulation = ModelingUpdate(
            [
                [self.uj_step_2.jobs, self.uj_step_2.jobs + [new_job, new_job2, self.server1_job1]],
                [self.uj_step_1.user_time_spent, SourceValue(25 * u.min)],
                [self.server1.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
        self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.uj_step_1.user_time_spent, self.server1.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.server1_job1]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertIn(self.uj_step_2.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)

    def run_test_semantic_units_in_calculated_attributes(self):
        """Test that all calculated attributes use correct semantic units (occurrence, concurrent, byte_ram)."""
        self.check_semantic_units_in_calculated_attributes(self.system)
