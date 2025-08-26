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
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurringValues
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
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.system import System
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass, INTEGRATION_TEST_DIR


class IntegrationTestSimpleEdgeSystemBaseClass(IntegrationTestBaseClass):
    @staticmethod
    def generate_simple_edge_system():
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

        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        edge_usage_pattern = EdgeUsagePattern(
            "Default edge usage pattern",
            edge_usage_journey=edge_usage_journey,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt * 1000 for elt in [1, 1, 2, 2, 3, 3, 1, 1, 2]], start_date)
        )
        edge_usage_pattern.id = css_escape(edge_usage_pattern.name)

        system = System("Edge system", [], edge_usage_patterns=[edge_usage_pattern])
        mod_obj_list = [system] + system.all_linked_objects
        for mod_obj in mod_obj_list:
            if mod_obj != edge_usage_pattern:
                mod_obj.id = css_escape(mod_obj.name)

        return (system, edge_storage, edge_device, edge_process, edge_usage_journey, 
                edge_usage_pattern, start_date)

    @classmethod
    def initialize_footprints(cls, system, edge_storage, edge_device):
        cls.initial_footprint = system.total_footprint

        cls.initial_fab_footprints = {
            edge_storage: edge_storage.instances_fabrication_footprint,
            edge_device: edge_device.instances_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            edge_storage: edge_storage.energy_footprint,
            edge_device: edge_device.energy_footprint,
        }

        cls.initial_system_total_fab_footprint = system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = system.total_energy_footprint_sum_over_period

    @classmethod
    def setUpClass(cls):
        (cls.system, cls.edge_storage, cls.edge_device, cls.edge_process, cls.edge_usage_journey,
         cls.edge_usage_pattern, cls.start_date) = cls.generate_simple_edge_system()

        cls.initialize_footprints(cls.system, cls.edge_storage, cls.edge_device)

        cls.ref_json_filename = "simple_edge_system"

    def run_test_system_calculation_graph_right_after_json_to_system(self):
        # Because it exists in the json integration test and classes must implement same methods.
        pass

    def run_test_modeling_object_prints(self):
        str(self.system)
        str(self.edge_storage)
        str(self.edge_device)
        str(self.edge_process)
        str(self.edge_usage_journey)
        str(self.edge_usage_pattern)

    def run_test_all_objects_linked_to_system(self):
        expected_objects = {
            self.edge_storage, self.edge_device, self.edge_process,
            self.edge_usage_journey, self.edge_usage_pattern, self.edge_usage_pattern.country
        }
        self.assertEqual(expected_objects, set(self.system.all_linked_objects))

    def run_test_calculation_graph(self):
        graph = build_calculus_graph(self.system.total_footprint)
        graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "edge_calculation_graph.html"), notebook=False)
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "edge_calculation_graph.html"), "r") as f:
            content = f.read()
        self.assertGreater(len(content), 30000)

    def run_test_object_relationship_graph(self):
        object_relationships_graph = build_object_relationships_graph(
            self.system, classes_to_ignore=USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE)
        object_relationships_graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "edge_object_relationships_graph.html"),
            notebook=False)

    # INPUT VARIATION TESTING

    def _run_test_variations_on_edge_inputs_from_object_list(
            self, edge_device, edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system):
        # Test edge object variations
        self._test_variations_on_obj_inputs(
            edge_device,
            # fraction_of_usage_time is an Hardware parameter not used in EdgeDevice
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
        self._run_test_variations_on_edge_inputs_from_object_list(
            self.edge_device, self.edge_storage, self.edge_process, self.edge_usage_journey,
            self.edge_usage_pattern, self.system)

    def run_test_variations_on_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        system = next(iter(class_obj_dict["System"].values()))
        edge_device = next(iter(class_obj_dict.get("EdgeDevice", {}).values()))
        edge_storage = next(iter(class_obj_dict.get("EdgeStorage", {}).values()))
        edge_process = next(iter(class_obj_dict.get("EdgeProcess", {}).values()))
        edge_usage_journey = next(iter(class_obj_dict.get("EdgeUsageJourney", {}).values()))
        edge_usage_pattern = next(iter(class_obj_dict.get("EdgeUsagePattern", {}).values()))

        self._run_test_variations_on_edge_inputs_from_object_list(
            edge_device, edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system)

    def run_test_update_edge_usage_pattern_hourly_starts(self):
        logger.warning("Updating edge usage pattern hourly starts")
        initial_hourly_starts = self.edge_usage_pattern.hourly_edge_usage_journey_starts
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = create_source_hourly_values_from_list(
            [elt for elt in [2, 3, 4, 5, 6, 7, 2, 3, 4]], self.start_date)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = initial_hourly_starts
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    # SIMULATION TESTING

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.edge_device.power, SourceValue(35 * u.W)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.edge_device.energy_footprint.plot(plt_show=False, cumsum=False)
        self.edge_device.energy_footprint.plot(plt_show=False, cumsum=True)
        self.system.total_footprint.plot(plt_show=False, cumsum=False)
        self.system.total_footprint.plot(plt_show=False, cumsum=True)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))

    def run_test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.edge_device.power, SourceValue(35 * u.W)],
                [self.edge_device.compute, SourceValue(6 * u.cpu_core, Sources.USER_DATA)]],
                 self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.edge_device.power, self.edge_device.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.edge_device.energy_footprint.id, recomputed_elements_ids)

    def run_test_simulation_add_new_edge_process(self):
        new_edge_process = EdgeProcess(
            "New edge process",
            recurrent_compute_needed=SourceRecurringValues(
                Quantity(np.array([0.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurringValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurringValues(
                Quantity(np.array([100] * 168, dtype=np.float32), u.MB))
        )

        initial_edge_processes = copy(self.edge_usage_journey.edge_processes)
        simulation = ModelingUpdate([[self.edge_usage_journey.edge_processes, 
                                    self.edge_usage_journey.edge_processes + [new_edge_process]]],
                                    copy(self.start_date).replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        self.assertEqual(initial_edge_processes, self.edge_usage_journey.edge_processes)
        simulation.set_updated_values()
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(initial_edge_processes + [new_edge_process], self.edge_usage_journey.edge_processes)
        simulation.reset_values()

    def run_test_simulation_add_existing_edge_process(self):
        simulation = ModelingUpdate([[self.edge_usage_journey.edge_processes, 
                                    self.edge_usage_journey.edge_processes + [self.edge_process]]],
                                    copy(self.start_date).replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_edge_processes = copy(self.edge_usage_journey.edge_processes)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        self.assertEqual(initial_edge_processes, self.edge_usage_journey.edge_processes)
        simulation.set_updated_values()
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(initial_edge_processes + [self.edge_process], self.edge_usage_journey.edge_processes)
        simulation.reset_values()
