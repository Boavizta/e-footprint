import os.path
from copy import copy
from datetime import datetime, timedelta, timezone
import numpy as np
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
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass


class IntegrationTestComplexSystemBaseClass(IntegrationTestBaseClass):
    @staticmethod
    def generate_complex_system():
        storage_1 = Storage(
            "Default SSD storage 1",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(4 * u.hour),
            base_storage_need=SourceValue(100 * u.TB)
        )

        storage_2 = Storage(
            "Default SSD storage 2",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(4 * u.hour),
            base_storage_need=SourceValue(100 * u.TB)
        )

        server1 = Server(
            "Server 1",
            server_type=ServerTypes.autoscaling(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W),
            lifespan=SourceValue(6 * u.year),
            idle_power=SourceValue(50 * u.W),
            ram=SourceValue(12 * u.GB),
            compute=SourceValue(6 * u.cpu_core),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
            utilization_rate=SourceValue(0.9 * u.dimensionless),
            base_ram_consumption=SourceValue(300 * u.MB),
            base_compute_consumption=SourceValue(2 * u.cpu_core),
            storage=storage_1
        )
        cores_per_cpu_units = SourceValue(2 * u.cpu_core)
        nb_cpu_units = SourceValue(3 * u.dimensionless)
        server2 = Server(
            "Server 2",
            server_type=ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W),
            lifespan=SourceValue(6 * u.year),
            idle_power=SourceValue(50 * u.W),
            ram=SourceValue(12 * u.GB),
            compute=cores_per_cpu_units * nb_cpu_units,
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
            utilization_rate=SourceValue(0.9 * u.dimensionless),
            base_ram_consumption=SourceValue(300 * u.MB),
            base_compute_consumption=SourceValue(2 * u.cpu_core),
            storage=storage_2
        )
        server3 = Server.from_defaults(
            "Server 3", server_type=ServerTypes.serverless(),
            storage=Storage.ssd("Default SSD storage 3"),
            base_ram_consumption=SourceValue(300 * u.MB),
            base_compute_consumption=SourceValue(2 * u.cpu_core))
        storage_3 = server3.storage

        server1_job1 = Job("server 1 job 1", server1, data_transferred=SourceValue(1 * u.GB),
                                data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
                                ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))
        uj_step_1 = UsageJourneyStep(
            "UJ step 1", user_time_spent=SourceValue(20 * u.min), jobs=[server1_job1])

        server1_job2 = Job("server 1 job 2", server1, data_transferred=SourceValue(300 * u.kB),
                             data_stored=SourceValue(300 * u.kB), request_duration=SourceValue(0.4 * u.s),
                             ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))
        uj_step_2 = UsageJourneyStep(
            "UJ step 2", user_time_spent=SourceValue(1 * u.s), jobs=[server1_job2])

        server1_job3 = Job(
            "server 1 job 3", server1, data_transferred=SourceValue(3.3 * u.MB),
            data_stored=SourceValue(300 * u.kB), request_duration=SourceValue(1 * u.s),
            ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))

        uj_step_3 = UsageJourneyStep(
            "UJ step 3", user_time_spent=SourceValue(1 * u.min), jobs=[server1_job3])

        server2_job = Job(
            "server 2 job", server2, data_transferred=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(0 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        server3_job = Job(
            "server 3 job", server3, data_transferred=SourceValue(50 * u.kB),
            data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        uj_step_4 = UsageJourneyStep(
            "UJ step 4", user_time_spent=SourceValue(20 * u.min),
            jobs=[server2_job, server3_job])

        uj = UsageJourney(
            "Usage journey", uj_steps=[uj_step_1, uj_step_2, uj_step_3, uj_step_4])

        network1 = Network("network 1", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern1 = UsagePattern(
            "Usage pattern 1", uj, [Device.laptop()], network1,
            Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date=start_date))

        network2 = Network("network 2", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
        usage_pattern2 = UsagePattern(
            "Usage pattern 2", uj, [Device.laptop()], network2,
            Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [4, 2, 1, 5, 2, 1, 7, 8, 3]], start_date=start_date))

        # Edge components
        edge_storage = EdgeStorage(
            "Edge SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(10 * u.GB)
        )

        edge_device = EdgeDevice(
            "Edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB),
            compute=SourceValue(4 * u.cpu_core),
            power_usage_effectiveness=SourceValue(1.0 * u.dimensionless),
            utilization_rate=SourceValue(0.8 * u.dimensionless),
            base_ram_consumption=SourceValue(1 * u.GB),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=edge_storage
        )

        edge_process = RecurrentEdgeProcess(
            "Edge process",
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([200] * 168, dtype=np.float32), u.MB))
        )

        edge_usage_journey = EdgeUsageJourney(
            "Edge usage journey",
            edge_processes=[edge_process],
            edge_device=edge_device,
            usage_span=SourceValue(6 * u.year)
        )

        edge_usage_pattern = EdgeUsagePattern(
            "Edge usage pattern",
            edge_usage_journey=edge_usage_journey,
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

        return system, storage_1, storage_2, storage_3, server1, server2, server3, \
            server1_job1, server1_job2, server1_job3, server2_job, server3_job, \
            uj_step_1, uj_step_2, uj_step_3, uj_step_4, \
            start_date, usage_pattern1, usage_pattern2, uj, network1, network2, \
            edge_storage, edge_device, edge_process, edge_usage_journey, edge_usage_pattern

    @classmethod
    def initialize_footprints(cls, system, storage_1, storage_2, storage_3, server1, server2, server3, usage_pattern1,
                              usage_pattern2, network1, network2, edge_storage, edge_device):
        cls.initial_footprint = system.total_footprint
        cls.initial_fab_footprints = {
            storage_1: storage_1.instances_fabrication_footprint,
            storage_2: storage_2.instances_fabrication_footprint,
            storage_3: storage_3.instances_fabrication_footprint,
            server1: server1.instances_fabrication_footprint,
            server2: server2.instances_fabrication_footprint,
            server3: server3.instances_fabrication_footprint,
            usage_pattern1: usage_pattern1.instances_fabrication_footprint,
            usage_pattern2: usage_pattern2.instances_fabrication_footprint,
            edge_storage: edge_storage.instances_fabrication_footprint,
            edge_device: edge_device.instances_fabrication_footprint,
        }
        cls.initial_energy_footprints = {
            storage_1: storage_1.energy_footprint,
            storage_2: storage_2.energy_footprint,
            storage_3: storage_3.energy_footprint,
            server1: server1.energy_footprint,
            server2: server2.energy_footprint,
            server3: server3.energy_footprint,
            network1: network1.energy_footprint,
            network2: network2.energy_footprint,
            usage_pattern1: usage_pattern1.energy_footprint,
            usage_pattern2: usage_pattern2.energy_footprint,
            edge_storage: edge_storage.energy_footprint,
            edge_device: edge_device.energy_footprint,
        }

        cls.initial_system_total_fab_footprint = system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = system.total_energy_footprint_sum_over_period


    @classmethod
    def setUpClass(cls):
        cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2, cls.server3, \
            cls.server1_job1, cls.server1_job2, cls.server1_job3, cls.server2_job, cls.server3_job, \
            cls.uj_step_1, cls.uj_step_2, cls.uj_step_3, cls.uj_step_4, \
            cls.start_date, cls.usage_pattern1, cls.usage_pattern2, cls.uj, cls.network1, cls.network2, \
            cls.edge_storage, cls.edge_device, cls.edge_process, cls.edge_usage_journey, cls.edge_usage_pattern = cls.generate_complex_system()

        cls.initialize_footprints(cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2,
                                  cls.server3, cls.usage_pattern1, cls.usage_pattern2, cls.network1, cls.network2,
                                  cls.edge_storage, cls.edge_device)

        cls.ref_json_filename = "complex_system"

    def run_test_all_objects_linked_to_system(self):
        expected_list = [
            self.server2, self.server1, self.server3, self.storage_1, self.storage_2, self.storage_3,
            self.usage_pattern1, self.usage_pattern2, self.edge_usage_pattern,
            self.network1, self.network2, self.uj, self.uj_step_1, self.uj_step_2, self.uj_step_3,
            self.uj_step_4, self.server1_job1, self.server1_job2, self.server1_job3, self.server2_job,
            self.server3_job, self.usage_pattern1.devices[0], self.usage_pattern2.devices[0],
            self.usage_pattern1.country, self.usage_pattern2.country, self.edge_storage, self.edge_device,
            self.edge_process, self.edge_usage_journey, self.edge_usage_pattern.country]
        self.assertEqual(set(expected_list), set(self.system.all_linked_objects))

    def run_test_remove_uj_steps_1_and_2(self):
        logger.warning("Removing uj steps 1 and 2")
        self.uj.uj_steps = [self.uj_step_1, self.uj_step_2]

        self.footprint_has_changed([self.server1, self.server2, self.storage_1, self.storage_2])
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.warning("Putting uj steps 1 and 2 back")
        self.uj.uj_steps = [self.uj_step_1, self.uj_step_2, self.uj_step_3, self.uj_step_4]

        self.footprint_has_not_changed([self.server1, self.server2, self.storage_1, self.storage_2])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_remove_uj_step_3_job(self):
        logger.warning("Removing uj step 3 job")
        self.uj_step_3.jobs = []

        self.footprint_has_changed([self.server1, self.storage_1])
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.warning("Putting uj step 3 job back")
        self.uj_step_3.jobs = [self.server1_job3]

        self.footprint_has_not_changed([self.server1, self.storage_1])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_remove_one_uj_step_4_job(self):
        logger.warning("Removing the uj step 4 job that links to server 3")
        self.uj_step_4.jobs = [self.server2_job]

        self.footprint_has_changed([self.server3, self.storage_3], system=self.system)
        self.footprint_has_not_changed([self.server2, self.storage_2])
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.warning("Putting job back")
        self.uj_step_4.jobs = [self.server2_job, self.server3_job]

        self.footprint_has_not_changed([self.server3, self.storage_3, self.server2, self.storage_2])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_remove_all_uj_step_4_jobs(self):
        logger.warning("Removing all uj step 4 jobs")
        self.uj_step_4.jobs = []

        self.footprint_has_changed([self.server2, self.storage_2, self.server3, self.storage_3],
                                   system=self.system)
        self.footprint_has_not_changed([self.server1])
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.warning("Putting jobs back")
        self.uj_step_4.jobs = [self.server2_job, self.server3_job]

        self.footprint_has_not_changed([self.server3, self.storage_3, self.server2, self.storage_2])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_add_new_job(self):
        logger.warning("Adding job")
        new_job = Job(
            "new job", self.server1, data_transferred=SourceValue(3 * u.MB), data_stored=SourceValue(3 * u.MB),
            request_duration=SourceValue(1 * u.s), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        new_uj_step = UsageJourneyStep(
            "new uj step", user_time_spent=SourceValue(1 * u.s), jobs=[new_job])
        self.uj.uj_steps += [new_uj_step]

        self.footprint_has_changed([self.server1, self.storage_1])
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)

        logger.warning("Removing new job")
        self.uj.uj_steps = self.uj.uj_steps[:-1]
        job = new_uj_step.jobs[0]
        new_uj_step.self_delete()
        job.self_delete()

        self.footprint_has_not_changed([self.server1, self.storage_1])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_add_new_usage_pattern_with_new_network_and_edit_its_hourly_uj_starts(self):
        new_network = Network.wifi_network()
        new_up = UsagePattern(
            "New usage pattern video watching in France", self.uj, [Device.laptop()], new_network, Countries.FRANCE(),
            create_source_hourly_values_from_list([elt * 1000 for elt in [1, 4, 1, 5, 3, 1, 5, 23, 2]]))

        streaming = self.server1_job1
        up = self.usage_pattern2
        hour_occs_per_up = streaming.hourly_occurrences_per_usage_pattern[up]
        logger.warning("Adding new usage pattern")
        self.system.usage_patterns += [new_up]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        # streaming has been recomputed, hour_occs_per_up should not be linked to a modeling object anymore
        self.assertIsNone(hour_occs_per_up.modeling_obj_container)
        # streaming has 3 usage patterns so its hourly_avg_occurrences_across_usage_patterns should have 3 ancestors
        self.assertEqual(len(streaming.hourly_avg_occurrences_across_usage_patterns.direct_ancestors_with_id), 3)

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
        logger.warning("Adding new edge usage pattern")
        new_edge_storage = EdgeStorage(
            "New edge SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(10 * u.GB)
        )

        new_edge_device = EdgeDevice(
            "New edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB),
            compute=SourceValue(4 * u.cpu_core),
            power_usage_effectiveness=SourceValue(1.0 * u.dimensionless),
            utilization_rate=SourceValue(0.8 * u.dimensionless),
            base_ram_consumption=SourceValue(1 * u.GB),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=new_edge_storage
        )

        new_edge_process = RecurrentEdgeProcess(
            "New edge process",
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([1.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([3] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([300] * 168, dtype=np.float32), u.MB))
        )

        new_edge_usage_journey = EdgeUsageJourney(
            "New edge usage journey",
            edge_processes=[new_edge_process],
            edge_device=new_edge_device,
            usage_span=SourceValue(6 * u.year)
        )

        new_edge_usage_pattern = EdgeUsagePattern(
            "New edge usage pattern",
            edge_usage_journey=new_edge_usage_journey,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt * 50 for elt in [2, 1, 3, 2, 4, 2, 1, 2, 3]], self.start_date)
        )

        self.system.edge_usage_patterns += [new_edge_usage_pattern]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_device, self.edge_storage])

        logger.warning("Removing the new edge usage pattern")
        self.system.edge_usage_patterns = [self.edge_usage_pattern]
        new_edge_usage_pattern.self_delete()

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_device, self.edge_storage])

    def run_test_plot_footprints_by_category_and_object(self):
        self.system.plot_footprints_by_category_and_object()

    def run_test_plot_footprints_by_category_and_object_return_only_html(self):
        html = self.system.plot_footprints_by_category_and_object(width=400, height=100, return_only_html=True)
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
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

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
        simulation = ModelingUpdate(
            [[self.uj_step_2.jobs, self.uj_step_2.jobs + [self.server1_job2]]],
            self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

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
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

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
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
        compute_needed=SourceValue(1 * u.cpu_core))

        new_job2 = Job("new job 2", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
         data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
         compute_needed=SourceValue(1 * u.cpu_core))

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
