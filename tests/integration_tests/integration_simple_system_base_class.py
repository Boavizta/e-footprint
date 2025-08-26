import json
from copy import copy
import os
from datetime import datetime, timedelta, timezone
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
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
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.usage.edge_process import EdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE
from efootprint.builders.time_builders import create_source_hourly_values_from_list, create_hourly_usage_from_frequency
from efootprint.abstract_modeling_classes.source_objects import SourceRecurringValues
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestSimpleSystemBaseClass(IntegrationTestBaseClass):
    @staticmethod
    def generate_simple_system():
        storage = Storage(
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

        server = Server(
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
            storage=storage
        )

        streaming_job = Job("streaming", server=server, data_transferred=SourceValue((2.5 / 3) * u.GB),
                                data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min),
                                ram_needed=SourceValue(100 * u.MB),
                                compute_needed=SourceValue(1 * u.cpu_core))

        streaming_step = UsageJourneyStep(
            "20 min streaming on Youtube", user_time_spent=SourceValue(20 * u.min), jobs=[streaming_job])

        upload_job = Job("upload", server=server, data_transferred=SourceValue(300 * u.MB),
                             data_stored=SourceValue(300 * u.MB), request_duration=SourceValue(40 * u.s),
                             ram_needed=SourceValue(100 * u.MB), compute_needed=SourceValue(1 * u.cpu_core))

        upload_step = UsageJourneyStep(
            "40s of upload", user_time_spent=SourceValue(1 * u.min), jobs=[upload_job])

        uj = UsageJourney("Daily Youtube usage", uj_steps=[streaming_step, upload_step])
        network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        usage_pattern = UsagePattern(
            "Youtube usage in France", uj, [Device.laptop()], network, Countries.FRANCE(),
            create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], start_date))

        # Normalize usage pattern id before computation is made because it is used as dictionary key in intermediary
        # calculations
        usage_pattern.id = css_escape(usage_pattern.name)

        # Create edge objects
        edge_storage = EdgeStorage(
            "Edge SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(10 * u.GB),
        )

        edge_device = EdgeDevice(
            "Default edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg, Sources.HYPOTHESIS),
            power=SourceValue(30 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(4 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(5 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(8 * u.GB, Sources.HYPOTHESIS),
            compute=SourceValue(4 * u.cpu_core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.0 * u.dimensionless, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.8 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(1 * u.GB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core, Sources.HYPOTHESIS),
            storage=edge_storage
        )

        edge_process = EdgeProcess(
            "Default edge process",
            recurrent_compute_needed=SourceRecurringValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurringValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurringValues(
                Quantity(np.array([200] * 168, dtype=np.float32), u.MB))
        )

        edge_usage_journey = EdgeUsageJourney(
            "Default edge usage journey",
            edge_processes=[edge_process],
            edge_device=edge_device,
            usage_span=SourceValue(6 * u.year, Sources.HYPOTHESIS)
        )

        edge_usage_pattern = EdgeUsagePattern(
            "Default edge usage pattern",
            edge_usage_journey=edge_usage_journey,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 1, 2, 2, 3, 3, 1, 1, 2]], start_date)
        )
        edge_usage_pattern.id = css_escape(edge_usage_pattern.name)

        system = System("system 1", [usage_pattern], edge_usage_patterns=[edge_usage_pattern])
        mod_obj_list = [system] + system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj != usage_pattern and mod_obj != edge_usage_pattern:
                mod_obj.id = css_escape(mod_obj.name)

        return (system, storage, server, streaming_job, streaming_step, upload_job, upload_step, uj, network,
                start_date, usage_pattern, edge_storage, edge_device, edge_process, edge_usage_journey, 
                edge_usage_pattern)

    @classmethod
    def initialize_footprints(cls, system, storage, server, usage_pattern, network, edge_storage, edge_device):
        cls.initial_footprint = system.total_footprint

        cls.initial_fab_footprints = {
            storage: storage.instances_fabrication_footprint,
            server: server.instances_fabrication_footprint,
            usage_pattern: usage_pattern.devices_fabrication_footprint,
            edge_storage: edge_storage.instances_fabrication_footprint,
            edge_device: edge_device.instances_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            storage: storage.energy_footprint,
            server: server.energy_footprint,
            network: network.energy_footprint,
            usage_pattern: usage_pattern.devices_energy_footprint,
            edge_storage: edge_storage.energy_footprint,
            edge_device: edge_device.energy_footprint,
        }

        cls.initial_system_total_fab_footprint = system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = system.total_energy_footprint_sum_over_period

    @classmethod
    def setUpClass(cls):
        (cls.system, cls.storage, cls.server, cls.streaming_job, cls.streaming_step, cls.upload_job, 
         cls.upload_step, cls.uj, cls.network, cls.start_date, cls.usage_pattern, cls.edge_storage, 
         cls.edge_device, cls.edge_process, cls.edge_usage_journey, cls.edge_usage_pattern) = cls.generate_simple_system()

        cls.initialize_footprints(cls.system, cls.storage, cls.server, cls.usage_pattern, cls.network,
                                  cls.edge_storage, cls.edge_device)

        cls.ref_json_filename = "simple_system"

    def run_test_all_objects_linked_to_system(self):
        expected_objects = {
            self.server, self.storage, self.usage_pattern, self.network, self.uj, self.streaming_step,
            self.upload_step, self.streaming_job, self.upload_job, self.usage_pattern.devices[0],
            self.usage_pattern.country, self.edge_storage, self.edge_device, self.edge_process,
            self.edge_usage_journey, self.edge_usage_pattern
        }
        # Add the edge usage pattern country if it's different from the regular usage pattern country
        if self.edge_usage_pattern.country != self.usage_pattern.country:
            expected_objects.add(self.edge_usage_pattern.country)
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

    def _run_test_variations_on_inputs_from_object_list(
            self, streaming_step, server, storage, uj, network, usage_pattern, streaming_job, edge_device,
            edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system):
        self._test_variations_on_obj_inputs(streaming_step)
        self._test_variations_on_obj_inputs(
            server, attrs_to_skip=["fraction_of_usage_time", "server_type", "fixed_nb_of_instances"],
            special_mult={
                "ram": 0.01, "server_utilization_rate": 0.5,
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
        storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        self.assertEqual(old_initial_footprint, system.total_footprint)
        self.initial_footprint = old_initial_footprint
        self._test_variations_on_obj_inputs(uj)
        self._test_variations_on_obj_inputs(network)
        self._test_variations_on_obj_inputs(usage_pattern, attrs_to_skip=["hourly_usage_journey_starts"])
        self._test_variations_on_obj_inputs(streaming_job, special_mult={"data_stored": 1000000})
        # Test edge object variations
        self._test_variations_on_obj_inputs(
            edge_device,
            # fraction_of_usage_time is an Hardware paramater not used in EdgeDevice
            # ram, base_ram_consumption and server_utilization_rate only matter to raise InsufficientCapacityError
            # and this behavior is already unit tested.
            attrs_to_skip=["fraction_of_usage_time", "ram", "base_ram_consumption", "server_utilization_rate"],
            special_mult={"base_compute_consumption": 10}
        )
        self._test_variations_on_obj_inputs(
            edge_storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"])
        self._test_variations_on_obj_inputs(
            # recurrent_ram_needed only matters to raise InsufficientCapacityError
            # and this behavior is already unit tested.
            edge_process, attrs_to_skip=["recurrent_ram_needed"],
            special_mult={"recurrent_compute_needed": 2, "recurrent_storage_needed": 2})
        self._test_variations_on_obj_inputs(edge_usage_journey)
        self._test_variations_on_obj_inputs(
            edge_usage_pattern, attrs_to_skip=["hourly_edge_usage_journey_starts"])

    def run_test_variations_on_inputs(self):
        self._run_test_variations_on_inputs_from_object_list(
            self.streaming_step, self.server, self.storage, self.uj, self.network, self.usage_pattern,
            self.streaming_job, self.edge_device, self.edge_storage, self.edge_process, self.edge_usage_journey,
            self.edge_usage_pattern, self.system)

    def run_test_variations_on_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        streaming_step = next(iter(class_obj_dict["UsageJourneyStep"].values()))
        server = next(iter(class_obj_dict["Server"].values()))
        storage = next(iter(class_obj_dict["Storage"].values()))
        uj = next(iter(class_obj_dict["UsageJourney"].values()))
        network = next(iter(class_obj_dict["Network"].values()))
        usage_pattern = next(iter(class_obj_dict["UsagePattern"].values()))
        streaming_job = next(iter(class_obj_dict["Job"].values()))
        system = next(iter(class_obj_dict["System"].values()))
        edge_device = next(iter(class_obj_dict.get("EdgeDevice", {}).values()))
        edge_storage = next(iter(class_obj_dict.get("EdgeStorage", {}).values()))
        edge_process = next(iter(class_obj_dict.get("EdgeProcess", {}).values()))
        edge_usage_journey = next(iter(class_obj_dict.get("EdgeUsageJourney", {}).values()))
        edge_usage_pattern = next(iter(class_obj_dict.get("EdgeUsagePattern", {}).values()))

        self._run_test_variations_on_inputs_from_object_list(
            streaming_step, server, storage, uj, network, usage_pattern, streaming_job,
            edge_device, edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system)

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

    def run_test_update_edge_usage_pattern_hourly_starts(self):
        logger.warning("Updating edge usage pattern hourly starts")
        initial_hourly_starts = self.edge_usage_pattern.hourly_edge_usage_journey_starts
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = create_source_hourly_values_from_list(
            [elt for elt in [2, 3, 4, 5, 6, 7, 2, 3, 4]], self.start_date)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = initial_hourly_starts
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_uj_step_update(self):
        logger.warning("Updating uj steps in default user journey")
        self.uj.uj_steps = [self.streaming_step]
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.uj.uj_steps = [self.streaming_step, self.upload_step]
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
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial job server")
        self.streaming_job.server = self.server
        self.upload_job.server = self.server
        self.assertEqual(0, new_server.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_server.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.server])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_storage(self):
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
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial jobs storage")
        self.server.storage = self.storage
        self.assertEqual(0, new_storage.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_storage.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.storage])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_jobs(self):
        logger.warning("Modifying streaming jobs")
        new_job = Job("new job", self.server, data_transferred=SourceValue(5 * u.GB),
         data_stored=SourceValue(50 * u.MB), request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
         compute_needed=SourceValue(1 * u.cpu_core))

        self.streaming_step.jobs += [new_job]

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.usage_pattern])
        self.footprint_has_changed([self.storage, self.server, self.network])

        logger.warning("Changing back to previous jobs")
        self.streaming_step.jobs = [self.streaming_job]

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def run_test_update_uj_steps(self):
        logger.warning("Modifying uj steps")
        new_step = UsageJourneyStep(
            "new_step", user_time_spent=SourceValue(2 * u.min),
            jobs=[Job("new job", self.server, data_transferred=SourceValue(5 * u.GB), data_stored=SourceValue(5 * u.kB),
                      request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
                      compute_needed=SourceValue(1 * u.cpu_core))]
        )
        self.uj.uj_steps = [new_step]

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.storage, self.server, self.network], system=self.system)

        logger.warning("Changing back to previous uj steps")
        self.uj.uj_steps = [self.streaming_step, self.upload_step]

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def run_test_update_usage_journey(self):
        logger.warning("Changing user journey")
        new_uj = UsageJourney("New version of daily Youtube usage", uj_steps=[self.streaming_step])
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
        new_network = Network(
            "New network with same specs as default", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
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

        step_without_job = UsageJourneyStep(
            "User checks her phone", user_time_spent=SourceValue(20 * u.min), jobs=[])

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
            country=self.usage_pattern.country, network=Network.wifi_network(),
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

    def run_test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def run_test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def run_test_update_usage_journey_after_json_to_system(self):
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
        self.assertNotEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_changed([storage, server, network, usage_pattern])

        logger.warning("Changing back to previous uj")
        usage_pattern.usage_journey = previous_uj

        self.assertEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_not_changed([storage, server, network, usage_pattern])

    def run_test_update_jobs_after_json_to_system(self):
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

        self.assertNotEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_not_changed([usage_pattern])
        self.footprint_has_changed([storage, server, network])

        logger.warning("Changing back to previous jobs")
        streaming_step.jobs = previous_jobs

        self.assertEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_not_changed([storage, server, network, usage_pattern])

    def run_test_modeling_object_prints(self):
        str(self.usage_pattern)
        str(self.usage_pattern)
        str(self.server)
        str(self.storage)
        str(self.upload_step)
        str(self.uj)
        str(self.network)
        str(self.system)
        str(self.edge_storage)
        str(self.edge_device)
        str(self.edge_process)
        str(self.edge_usage_journey)
        str(self.edge_usage_pattern)

    def run_test_update_footprint_job_datastored_from_positive_value_to_negative_value(self):
        initial_upload_data_stored = self.upload_job.data_stored
        initial_storage_need = self.storage.storage_needed
        initial_storage_freed = self.storage.storage_freed
        self.assertGreaterEqual(self.storage.storage_needed.min().magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.max().magnitude, 0)
        # data_stored is positive so storage_freed will be an EmptyExplainableObject

        self.upload_job.data_stored = SourceValue(-initial_upload_data_stored.value)

        self.assertNotEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)
        self.assertGreaterEqual(self.storage.storage_needed.min().magnitude, 0)
        self.assertLessEqual(self.storage.storage_freed.max().magnitude, 0)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.assertNotEqual(initial_storage_need, self.storage.storage_needed)
        self.assertNotEqual(initial_storage_freed, self.storage.storage_freed)

        self.footprint_has_changed([self.storage])

        logger.warning("Changing back to previous datastored value")
        self.upload_job.data_stored = initial_upload_data_stored

        self.assertEqual(initial_storage_need.value_as_float_list, self.storage.storage_needed.value_as_float_list)
        self.assertEqual(initial_storage_freed, self.storage.storage_freed)

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])
        self.assertEqual(initial_storage_need, self.storage.storage_needed)
        self.assertIsInstance(self.storage.storage_freed, EmptyExplainableObject)

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.streaming_step.user_time_spent, SourceValue(25 * u.min)]],
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
        for elt in self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, [elt.id for elt in simulation.values_to_recompute])

    def run_test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.streaming_step.user_time_spent, SourceValue(25 * u.min)],
                [self.server.compute, SourceValue(42 * u.cpu_core, Sources.USER_DATA)]],
                 self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for elt in self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.values():
            self.assertIn(elt.id, recomputed_elements_ids)
        self.assertIn(self.server.energy_footprint.id, recomputed_elements_ids)

    def run_test_simulation_add_new_object(self):
        new_server = Server.from_defaults("new server", storage=Storage.from_defaults("default storage"))
        new_job = Job("new job", new_server, data_transferred=SourceValue((2.5 / 3) * u.GB),
        data_stored=SourceValue(50 * u.kB), request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            compute_needed=SourceValue(1 * u.cpu_core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = ModelingUpdate([[self.upload_step.jobs, self.upload_step.jobs + [new_job]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job], self.upload_step.jobs)
        simulation.reset_values()

    def run_test_simulation_add_existing_object(self):
        simulation = ModelingUpdate([[self.upload_step.jobs, self.upload_step.jobs + [self.upload_job]]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [self.upload_job], self.upload_step.jobs)
        simulation.reset_values()

    def run_test_simulation_add_multiple_objects(self):
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

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_updated_values()
        self.assertEqual(initial_upload_step_jobs + [new_job, new_job2, self.streaming_job], self.upload_step.jobs)
        simulation.reset_values()

    def run_test_simulation_add_objects_and_make_input_changes(self):
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
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_compute_need.id, recomputed_elements_ids)
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)

    def run_test_change_network_and_hourly_usage_journey_starts_simultaneously_recomputes_in_right_order(self):
        logger.warning("Changing network and hourly usage journey starts simultaneously")
        new_network = Network(
            "New network with same specs as default", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
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
        self.upload_step.jobs = []
        logger.info("Deleting upload job")
        self.upload_job.self_delete()
        logger.info("Reinitialize system")
        self.setUpClass()
    