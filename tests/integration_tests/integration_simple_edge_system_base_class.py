import json
from copy import copy
import os
from datetime import datetime, timedelta, timezone
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_function import EdgeFunction
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
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(100 * u.GB),
        )

        edge_computer = EdgeComputer(
            "Default edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=edge_storage
        )

        edge_process = RecurrentEdgeProcess(
            "Default edge process",
            edge_device=edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([200] * 84 + [-200] * 84, dtype=np.float32), u.MB))
        )

        edge_function = EdgeFunction(
            "Default edge function",
            recurrent_edge_device_needs=[edge_process]
        )

        edge_usage_journey = EdgeUsageJourney(
            "Default edge usage journey",
            edge_functions=[edge_function],
            usage_span=SourceValue(6 * u.year)
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

        return (system, edge_storage, edge_computer, edge_process, edge_function, edge_usage_journey,
                edge_usage_pattern, start_date)

    @classmethod
    def initialize_footprints(cls, system, edge_storage, edge_computer):
        cls.initial_footprint = system.total_footprint

        cls.initial_fab_footprints = {
            edge_storage: edge_storage.instances_fabrication_footprint,
            edge_computer: edge_computer.instances_fabrication_footprint,
        }

        cls.initial_energy_footprints = {
            edge_storage: edge_storage.energy_footprint,
            edge_computer: edge_computer.energy_footprint,
        }

        cls.initial_system_total_fab_footprint = system.total_fabrication_footprint_sum_over_period
        cls.initial_system_total_energy_footprint = system.total_energy_footprint_sum_over_period

    @classmethod
    def setUpClass(cls):
        (cls.system, cls.edge_storage, cls.edge_computer, cls.edge_process, cls.edge_function,
         cls.edge_usage_journey, cls.edge_usage_pattern, cls.start_date) = cls.generate_simple_edge_system()

        cls.initialize_footprints(cls.system, cls.edge_storage, cls.edge_computer)

        cls.ref_json_filename = "simple_edge_system"

    def run_test_system_calculation_graph_right_after_json_to_system(self):
        # Because it exists in the json integration test and classes must implement same methods.
        pass

    def run_test_modeling_object_prints(self):
        str(self.system)
        str(self.edge_storage)
        str(self.edge_computer)
        str(self.edge_process)
        str(self.edge_function)
        str(self.edge_usage_journey)
        str(self.edge_usage_pattern)

    def run_test_all_objects_linked_to_system(self):
        expected_objects = {
            self.edge_storage, self.edge_computer, self.edge_process, self.edge_function,
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
            self, edge_computer, edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system):
        # Test edge object variations
        self._test_variations_on_obj_inputs(
            edge_computer,
            # fraction_of_usage_time is an Hardware parameter not used in EdgeComputer
            # ram and base_ram_consumption only matter to raise InsufficientCapacityError
            # and this behavior is already unit tested.
            attrs_to_skip=["fraction_of_usage_time", "ram", "base_ram_consumption"],
            special_mult={"base_compute_consumption": 10}
        )
        self._test_variations_on_obj_inputs(
            edge_storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"])
        self._test_variations_on_obj_inputs(
            # recurrent_ram_needed only matters to raise InsufficientCapacityError
            # and this behavior is already unit tested.
            edge_process, attrs_to_skip=["recurrent_ram_needed"],
            special_mult={"recurrent_compute_needed": 2, "recurrent_storage_needed": 2})
        self._test_variations_on_obj_inputs(edge_usage_journey, special_mult={"usage_span": 1.1})
        self._test_variations_on_obj_inputs(
            edge_usage_pattern, attrs_to_skip=["hourly_edge_usage_journey_starts"])

    def run_test_variations_on_inputs(self):
        self._run_test_variations_on_edge_inputs_from_object_list(
            self.edge_computer, self.edge_storage, self.edge_process, self.edge_usage_journey,
            self.edge_usage_pattern, self.system)

    def run_test_variations_on_inputs_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        system = next(iter(class_obj_dict["System"].values()))
        edge_computer = next(iter(class_obj_dict.get("EdgeComputer", {}).values()))
        edge_storage = next(iter(class_obj_dict.get("EdgeStorage", {}).values()))
        edge_process = next(iter(class_obj_dict.get("RecurrentEdgeProcess", {}).values()))
        edge_usage_journey = next(iter(class_obj_dict.get("EdgeUsageJourney", {}).values()))
        edge_usage_pattern = next(iter(class_obj_dict.get("EdgeUsagePattern", {}).values()))

        self._run_test_variations_on_edge_inputs_from_object_list(
            edge_computer, edge_storage, edge_process, edge_usage_journey, edge_usage_pattern, system)

    def run_test_update_edge_usage_pattern_hourly_starts(self):
        logger.warning("Updating edge usage pattern hourly starts")
        initial_hourly_starts = self.edge_usage_pattern.hourly_edge_usage_journey_starts
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = create_source_hourly_values_from_list(
            [elt for elt in [2, 3, 4, 5, 6, 7, 2, 3, 4]], self.start_date)

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.edge_usage_pattern.hourly_edge_usage_journey_starts = initial_hourly_starts
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    # OBJECT LINKS UPDATES TESTING

    def run_test_update_edge_process(self):
        logger.warning("Changing edge resource needs in edge function")
        self.edge_function.recurrent_edge_device_needs = []
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        logger.warning("Putting back initial edge processes")
        self.edge_function.recurrent_edge_device_needs = [self.edge_process]
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_edge_storage(self):
        new_edge_storage = EdgeStorage(
            "New Edge SSD storage, identical to default one",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(100 * u.GB),
        )
        logger.warning("Changing edge device storage")
        self.edge_computer.storage = new_edge_storage
        self.footprint_has_changed([self.edge_storage], system=self.system)
        self.assertEqual(0, self.edge_storage.instances_fabrication_footprint.max().magnitude)
        self.assertEqual(0, self.edge_storage.energy_footprint.max().magnitude)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial edge storage")
        self.edge_computer.storage = self.edge_storage
        self.assertEqual(0, new_edge_storage.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_edge_storage.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.edge_storage])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_update_edge_computer(self):
        new_edge_storage = EdgeStorage(
            "storage for new edge device",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(100 * u.GB),
        )

        new_edge_computer = EdgeComputer(
            "New edge device, identical to default one",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=new_edge_storage
        )

        logger.warning("Changing edge process device")
        self.edge_process.edge_device = new_edge_computer
        self.footprint_has_changed([self.edge_computer, self.edge_storage], system=self.system)
        self.assertEqual(0, self.edge_computer.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, self.edge_computer.energy_footprint.magnitude)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

        logger.warning("Changing back to initial edge device")
        self.edge_process.edge_device = self.edge_computer
        self.assertEqual(0, new_edge_computer.instances_fabrication_footprint.magnitude)
        self.assertEqual(0, new_edge_computer.energy_footprint.magnitude)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])
        self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def run_test_add_edge_process(self):
        logger.warning("Adding new edge process")
        new_edge_process = RecurrentEdgeProcess(
            "Additional edge process",
            edge_device=self.edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([0.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([100] * 84 + [-100] * 84, dtype=np.float32), u.MB))
        )

        self.edge_function.recurrent_edge_device_needs = (
            self.edge_function.recurrent_edge_device_needs + [new_edge_process])

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.edge_computer, self.edge_storage])

        logger.warning("Removing the new edge process")
        self.edge_function.recurrent_edge_device_needs = (
            self.edge_function.recurrent_edge_device_needs[:-1])
        new_edge_process.self_delete()

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])

    def run_test_update_edge_processes(self):
        logger.warning("Modifying edge processes list")
        new_edge_process = RecurrentEdgeProcess(
            "Replacement edge process",
            edge_device=self.edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([3] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([300] * 84 + [-300] * 84, dtype=np.float32), u.MB))
        )
        self.edge_function.recurrent_edge_device_needs = [new_edge_process]

        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.edge_computer, self.edge_storage], system=self.system)

        logger.warning("Changing back to previous edge processes")
        self.edge_function.recurrent_edge_device_needs = [self.edge_process]

        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])

    def run_test_update_edge_usage_journey(self):
        logger.warning("Changing edge usage journey")
        new_edge_storage = EdgeStorage(
            "New edge SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(100 * u.GB),
        )

        new_edge_computer = EdgeComputer(
            "New edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=new_edge_storage
        )

        new_edge_process = RecurrentEdgeProcess(
            "New edge process",
            edge_device=new_edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([200] * 84 + [-200] * 84, dtype=np.float32), u.MB))
        )

        new_edge_function = EdgeFunction(
            "New edge function",
            recurrent_edge_device_needs=[new_edge_process]
        )

        new_edge_usage_journey = EdgeUsageJourney(
            "New edge usage journey",
            edge_functions=[new_edge_function],
            usage_span=SourceValue(6 * u.year)
        )
        self.edge_usage_pattern.edge_usage_journey = new_edge_usage_journey
        
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.edge_computer, self.edge_storage], system=self.system)
        
        logger.warning("Changing back to previous edge usage journey")
        self.edge_usage_pattern.edge_usage_journey = self.edge_usage_journey
        
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])

    def run_test_update_country_in_edge_usage_pattern(self):
        logger.warning("Changing edge usage pattern country")
        
        self.edge_usage_pattern.country = Countries.MALAYSIA()
        
        self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_changed([self.edge_computer, self.edge_storage])
        
        logger.warning("Changing back to initial edge usage pattern country")
        self.edge_usage_pattern.country = Countries.FRANCE()
        
        self.assertEqual(self.initial_footprint, self.system.total_footprint)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])

    def run_test_add_edge_usage_pattern_to_system_and_reuse_existing_edge_process(self):
        new_edge_function = EdgeFunction("additional edge function", recurrent_edge_device_needs=[self.edge_process])

        new_edge_usage_journey = EdgeUsageJourney(
            "additional edge usage journey",
            edge_functions=[new_edge_function],
            usage_span=SourceValue(6 * u.year)
        )

        new_edge_usage_pattern = EdgeUsagePattern(
            "Additional edge usage pattern",
            edge_usage_journey=new_edge_usage_journey,
            country=self.edge_usage_pattern.country,
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt for elt in [0.5, 0.5, 1, 1, 1.5, 1.5, 0.5, 0.5, 1]], self.start_date)
        )
        self.assertEqual(1, len(self.edge_process.unitary_hourly_storage_need_per_usage_pattern))
        logger.warning(f"Adding edge usage pattern {new_edge_usage_pattern.name} to system")
        self.system.edge_usage_patterns += [new_edge_usage_pattern]
        
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(2, len(self.edge_process.unitary_hourly_storage_need_per_usage_pattern))
        
        logger.warning("Removing the new edge usage pattern from the system")
        self.system.edge_usage_patterns = self.system.edge_usage_patterns[:-1]
        logger.warning("Deleting the edge usage pattern")
        edge_usage_pattern_id = new_edge_usage_pattern.id
        new_edge_usage_pattern.self_delete()
        # Make sure that calculus graph references to the deleted usage pattern are removed
        for direct_child in self.edge_usage_pattern.country.average_carbon_intensity.direct_children_with_id:
            self.assertNotEqual(direct_child.modeling_obj_container.id, edge_usage_pattern_id)
        self.assertEqual(1, len(self.edge_process.unitary_hourly_storage_need_per_usage_pattern))
        self.assertEqual(self.system.total_footprint, self.initial_footprint)

    def run_test_add_edge_usage_pattern_to_edge_usage_journey(self):
        new_edge_usage_pattern = EdgeUsagePattern(
            "Additional edge usage pattern",
            edge_usage_journey=self.edge_usage_journey,
            country=self.edge_usage_pattern.country,
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt for elt in [0.5, 0.5, 1, 1, 1.5, 1.5, 0.5, 0.5, 1]], self.start_date)
        )
        logger.warning(f"Adding edge usage pattern {new_edge_usage_pattern.name} to system")
        self.system.edge_usage_patterns += [new_edge_usage_pattern]

        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.footprint_has_changed([self.edge_computer])

        logger.warning("Removing the new edge usage pattern from the system")
        self.system.edge_usage_patterns = self.system.edge_usage_patterns[:-1]
        logger.warning("Deleting the edge usage pattern")
        edge_usage_pattern_id = new_edge_usage_pattern.id
        new_edge_usage_pattern.self_delete()
        # Make sure that calculus graph references to the deleted usage pattern are removed
        for direct_child in self.edge_usage_pattern.country.average_carbon_intensity.direct_children_with_id:
            self.assertNotEqual(direct_child.modeling_obj_container.id, edge_usage_pattern_id)

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.footprint_has_not_changed([self.edge_computer])

    def run_test_update_edge_usage_journey_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        new_edge_storage = EdgeStorage(
            "New edge SSD storage",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            base_storage_need=SourceValue(100 * u.GB),
        )

        new_edge_computer = EdgeComputer(
            "New edge device",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(8 * u.GB_ram),
            compute=SourceValue(4 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=new_edge_storage
        )

        new_edge_process = RecurrentEdgeProcess(
            "New edge process",
            edge_device=new_edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([2] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([200] * 84 + [-200] * 84, dtype=np.float32), u.MB))
        )

        new_edge_function = EdgeFunction(
            "New edge function",
            recurrent_edge_device_needs=[new_edge_process]
        )

        new_edge_usage_journey = EdgeUsageJourney(
            "New edge usage journey",
            edge_functions=[new_edge_function],
            usage_span=SourceValue(6 * u.year)
        )

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)
        edge_usage_pattern = next(iter(class_obj_dict["EdgeUsagePattern"].values()))
        previous_edge_usage_journey = edge_usage_pattern.edge_usage_journey
        edge_usage_pattern.edge_usage_journey = new_edge_usage_journey

        system = next(iter(class_obj_dict["System"].values()))
        edge_storage = next(iter(class_obj_dict["EdgeStorage"].values()))
        edge_computer = next(iter(class_obj_dict["EdgeComputer"].values()))
        self.assertEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_changed([edge_computer, edge_storage], system=system)

        logger.warning("Changing back to previous edge usage journey")
        edge_usage_pattern.edge_usage_journey = previous_edge_usage_journey

        self.assertEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_not_changed([edge_storage, edge_computer])

    def run_test_update_edge_processes_after_json_to_system(self):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(full_dict)
        edge_usage_pattern = next(iter(class_obj_dict["EdgeUsagePattern"].values()))
        edge_usage_journey = edge_usage_pattern.edge_usage_journey
        edge_function = edge_usage_journey.edge_functions[0]
        previous_edge_needs = copy(edge_function.recurrent_edge_device_needs)
        system = next(iter(class_obj_dict["System"].values()))
        edge_storage = next(iter(class_obj_dict["EdgeStorage"].values()))
        edge_computer = next(iter(class_obj_dict["EdgeComputer"].values()))
        logger.warning("Modifying edge processes")
        new_edge_process = RecurrentEdgeProcess(
            "new edge process",
            edge_device=edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([0.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([100] * 84 + [-100] * 84, dtype=np.float32), u.MB))
        )

        edge_function.recurrent_edge_device_needs = edge_function.recurrent_edge_device_needs + [new_edge_process]

        self.assertNotEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_changed([edge_storage, edge_computer])

        logger.warning("Changing back to previous edge processes")
        edge_function.recurrent_edge_device_needs = previous_edge_needs

        self.assertEqual(self.initial_footprint, system.total_footprint)
        self.footprint_has_not_changed([edge_storage, edge_computer])

    # SIMULATION TESTING

    def run_test_simulation_input_change(self):
        simulation = ModelingUpdate([[self.edge_computer.power, SourceValue(35 * u.W)]],
                                    self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.edge_computer.energy_footprint.plot(plt_show=False, cumsum=False)
        self.edge_computer.energy_footprint.plot(plt_show=False, cumsum=True)
        self.system.total_footprint.plot(plt_show=False, cumsum=False)
        self.system.total_footprint.plot(plt_show=False, cumsum=True)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))

    def run_test_simulation_multiple_input_changes(self):
        simulation = ModelingUpdate([
                [self.edge_computer.power, SourceValue(35 * u.W)],
                [self.edge_computer.compute, SourceValue(6 * u.cpu_core, Sources.USER_DATA)]],
                 self.start_date.replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.edge_computer.power, self.edge_computer.compute])
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.edge_computer.energy_footprint.id, recomputed_elements_ids)

    def run_test_simulation_add_new_edge_process(self):
        new_edge_process = RecurrentEdgeProcess(
            "New edge process",
            edge_device=self.edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([0.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([100] * 84 + [-100] * 84, dtype=np.float32), u.MB))
        )

        initial_edge_needs = copy(self.edge_function.recurrent_edge_device_needs)
        simulation = ModelingUpdate([[self.edge_function.recurrent_edge_device_needs,
                                    self.edge_function.recurrent_edge_device_needs + [new_edge_process]]],
                                    copy(self.start_date).replace(tzinfo=timezone.utc) + timedelta(hours=1))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        self.assertEqual(initial_edge_needs, self.edge_function.recurrent_edge_device_needs)
        simulation.set_updated_values()
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(initial_edge_needs + [new_edge_process], self.edge_function.recurrent_edge_device_needs)
        simulation.reset_values()

    def run_test_simulation_add_existing_edge_process(self):
        simulation = ModelingUpdate([[self.edge_function.recurrent_edge_device_needs,
                                    self.edge_function.recurrent_edge_device_needs + [self.edge_process]]],
                                    copy(self.start_date).replace(tzinfo=timezone.utc) + timedelta(hours=1))

        initial_edge_needs = copy(self.edge_function.recurrent_edge_device_needs)
        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        self.assertEqual(initial_edge_needs, self.edge_function.recurrent_edge_device_needs)
        simulation.set_updated_values()
        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.assertEqual(initial_edge_needs + [self.edge_process], self.edge_function.recurrent_edge_device_needs)
        simulation.reset_values()

    def run_test_add_edge_usage_journey_to_edge_computer(self):
        logger.warning("Adding new edge usage journey to edge computer")

        new_edge_process = RecurrentEdgeProcess(
            "Additional edge process for second journey",
            edge_device=self.edge_computer,
            recurrent_compute_needed=SourceRecurrentValues(
                Quantity(np.array([0.5] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(
                Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
            recurrent_storage_needed=SourceRecurrentValues(
                Quantity(np.array([100] * 84 + [-100] * 84, dtype=np.float32), u.MB))
        )

        new_edge_function = EdgeFunction(
            "Second edge function",
            recurrent_edge_device_needs=[new_edge_process]
        )

        new_edge_usage_journey = EdgeUsageJourney(
            "Second edge usage journey",
            edge_functions=[new_edge_function],
            usage_span=SourceValue(6 * u.year)
        )

        new_edge_usage_pattern = EdgeUsagePattern(
            "Second edge usage pattern",
            edge_usage_journey=new_edge_usage_journey,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
                [elt for elt in [0.5, 0.5, 1, 1, 1.5, 1.5, 0.5, 0.5, 1]], self.start_date)
        )

        # Verify edge computer now has multiple journeys
        self.assertEqual(2, len(self.edge_computer.edge_usage_journeys))
        self.assertIn(self.edge_usage_journey, self.edge_computer.edge_usage_journeys)
        self.assertIn(new_edge_usage_journey, self.edge_computer.edge_usage_journeys)

        # Add the new pattern to the system
        logger.warning(f"Adding edge usage pattern {new_edge_usage_pattern.name} to system")
        self.system.edge_usage_patterns += [new_edge_usage_pattern]

        self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
        self.footprint_has_changed([self.edge_computer, self.edge_storage])

        # Verify edge computer aggregates patterns from both journeys
        self.assertEqual(2, len(self.edge_computer.edge_usage_patterns))
        self.assertIn(self.edge_usage_pattern, self.edge_computer.edge_usage_patterns)
        self.assertIn(new_edge_usage_pattern, self.edge_computer.edge_usage_patterns)

        # Verify edge computer aggregates functions from both journeys
        self.assertEqual(2, len(self.edge_computer.edge_functions))
        self.assertIn(self.edge_function, self.edge_computer.edge_functions)
        self.assertIn(new_edge_function, self.edge_computer.edge_functions)

        logger.warning("Removing the new edge usage pattern from the system")
        self.system.edge_usage_patterns = self.system.edge_usage_patterns[:-1]
        logger.warning("Deleting the edge usage pattern and journey")
        new_edge_usage_pattern.self_delete()
        new_edge_usage_journey.self_delete()
        new_edge_function.self_delete()
        new_edge_process.self_delete()

        # Verify edge computer is back to single journey
        self.assertEqual(1, len(self.edge_computer.edge_usage_journeys))
        self.assertEqual(1, len(self.edge_computer.edge_usage_patterns))
        self.assertEqual(1, len(self.edge_computer.edge_functions))

        self.assertEqual(self.system.total_footprint, self.initial_footprint)
        self.footprint_has_not_changed([self.edge_computer, self.edge_storage])

    def run_test_semantic_units_in_calculated_attributes(self):
        """Test that all calculated attributes use correct semantic units (occurrence, concurrent, byte_ram)."""
        self.check_semantic_units_in_calculated_attributes(self.system)
