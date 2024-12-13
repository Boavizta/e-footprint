from copy import copy
import os
from datetime import datetime, timedelta

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.simulation import Simulation
from efootprint.builders.hardware.servers_defaults import default_onpremise
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
from efootprint.abstract_modeling_classes.modeling_object import get_subclass_attributes, ModelingObject
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE
from efootprint.builders.hardware.devices_defaults import default_laptop, default_screen
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass


class IntegrationTest(IntegrationTestBaseClass):
    @classmethod
    def setUpClass(cls):

        cls.storage = Storage(
            "Default SSD storage",
            carbon_footprint_fabrication=SourceValue(160 * u.kg, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power=SourceValue(1.3 * u.W, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )

        cls.server = Autoscaling(
            "Default server",
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(128 * u.GB, Sources.USER_DATA),
            cpu_cores=SourceValue(24 * u.core, Sources.USER_DATA),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.USER_DATA),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.USER_DATA),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_cpu_consumption=SourceValue(2 * u.core, Sources.HYPOTHESIS),
            storage=cls.storage
        )

        cls.streaming_job = Job("streaming", server=cls.server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        cls.streaming_step = UserJourneyStep(
            "20 min streaming on Youtube", user_time_spent=SourceValue(20 * u.min), jobs=[cls.streaming_job])

        cls.upload_job = Job("upload", server=cls.server, data_upload=SourceValue(300 * u.MB),
            data_download=SourceValue(0 * u.GB), data_stored=SourceValue(300 * u.MB),
            request_duration=SourceValue(40 * u.s), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        cls.upload_step = UserJourneyStep(
            "40s of upload", user_time_spent=SourceValue(1 * u.min), jobs=[cls.upload_job])

        cls.uj = UserJourney("Daily Youtube usage", uj_steps=[cls.streaming_step, cls.upload_step])
        cls.network = Network("Default network", SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

        cls.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        cls.usage_pattern = UsagePattern(
            "Youtube usage in France", cls.uj, [default_laptop()], cls.network, Countries.FRANCE(),
            SourceHourlyValues(create_hourly_usage_df_from_list(
                [elt * 1000 for elt in [1, 2, 4, 5, 8, 12, 2, 2, 3]], cls.start_date)))

        cls.system = System("system 1", [cls.usage_pattern])

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
        def test_input_change(expl_attr, expl_attr_new_value, input_object, expl_attr_name):
            expl_attr_new_value.label = expl_attr.label
            logger.info(f"{expl_attr_new_value.label} changing from {expl_attr} to"
                        f" {expl_attr_new_value.value}")
            input_object.__setattr__(expl_attr_name, expl_attr_new_value)
            new_footprint = self.system.total_footprint
            logger.info(f"system footprint went from \n{self.initial_footprint} to \n{new_footprint}")
            self.assertFalse(self.initial_footprint.value.equals(new_footprint.value))
            input_object.__setattr__(expl_attr_name, expl_attr)
            self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        def test_variations_on_obj_inputs(input_object: ModelingObject, attrs_to_skip=None, special_mult=None):
            if attrs_to_skip is None:
                attrs_to_skip = []
            logger.warning(f"Testing input variations on {input_object.name}")
            for expl_attr_name, expl_attr in get_subclass_attributes(input_object, ExplainableObject).items():
                if expl_attr.left_parent is None and expl_attr.right_parent is None \
                        and expl_attr_name not in attrs_to_skip:

                    expl_attr_new_value = copy(expl_attr)
                    if special_mult and expl_attr_name in special_mult.keys():
                        expl_attr_new_value.value *= special_mult[expl_attr_name] * u.dimensionless
                    else:
                        expl_attr_new_value.value *= 100 * u.dimensionless
                    test_input_change(expl_attr, expl_attr_new_value, input_object, expl_attr_name)


        test_variations_on_obj_inputs(self.streaming_step)
        test_variations_on_obj_inputs(
            self.server, attrs_to_skip=["fraction_of_usage_time"],
            special_mult={
                "ram": 0.01, "server_utilization_rate": 0.5,
                "base_ram_consumption": 380,
                "base_cpu_consumption": 10
            })
        test_variations_on_obj_inputs(
            self.storage, attrs_to_skip=["fraction_of_usage_time", "base_storage_need"],)
        test_input_change(self.storage.fixed_nb_of_instances, EmptyExplainableObject(), self.storage, "fixed_nb_of_instances")
        self.storage.fixed_nb_of_instances = EmptyExplainableObject()
        old_initial_footprint = self.initial_footprint
        self.initial_footprint = self.system.total_footprint
        test_input_change(
            self.storage.base_storage_need, SourceValue(5000 * u.TB), self.storage, "base_storage_need")
        self.storage.fixed_nb_of_instances = SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        self.assertEqual(old_initial_footprint, self.system.total_footprint)
        self.initial_footprint = old_initial_footprint
        test_variations_on_obj_inputs(self.uj)
        test_variations_on_obj_inputs(self.network)
        test_variations_on_obj_inputs(self.usage_pattern, attrs_to_skip=["hourly_user_journey_starts"])
        test_variations_on_obj_inputs(self.streaming_job)

    def test_hourly_user_journey_starts_update(self):
        logger.warning("Updating hourly user journey starts")
        initial_hourly_uj_starts = self.usage_pattern.hourly_user_journey_starts
        self.usage_pattern.hourly_user_journey_starts = SourceHourlyValues(
            create_hourly_usage_df_from_list([elt * 1000 for elt in [12, 23, 41, 55, 68, 12, 23, 26, 43]]))

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.usage_pattern.hourly_user_journey_starts = initial_hourly_uj_starts
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_uj_step_update(self):
        logger.warning("Updating uj steps in default user journey")
        self.uj.uj_steps = [self.streaming_step]
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.uj.uj_steps = [self.streaming_step, self.upload_step]
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_device_pop_update(self):
        logger.warning("Updating devices in usage pattern")
        self.usage_pattern.devices = [default_laptop(), default_screen()]
        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.usage_pattern.devices = [default_laptop()]
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_update_server(self):
        new_storage = Storage(
            "new SSD storage, identical in specs to default one",
            carbon_footprint_fabrication=SourceValue(160 * u.kg, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power=SourceValue(1.3 * u.W, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0.1 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(3 * u.dimensionless),
            data_storage_duration=SourceValue(3 * u.hours),
            base_storage_need=SourceValue(50 * u.TB),
            fixed_nb_of_instances=SourceValue(10000 * u.dimensionless, Sources.HYPOTHESIS)
        )

        new_server = Autoscaling(
            "New server, identical in specs to default one",
            carbon_footprint_fabrication=SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(300 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(6 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(50 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(128 * u.GB, Sources.HYPOTHESIS),
            cpu_cores=SourceValue(24 * u.core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(300 * u.MB, Sources.HYPOTHESIS),
            base_cpu_consumption=SourceValue(2 * u.core, Sources.HYPOTHESIS),
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
            carbon_footprint_fabrication=SourceValue(160 * u.kg, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            power=SourceValue(1.3 * u.W, Sources.STORAGE_EMBODIED_CARBON_STUDY),
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
        self.footprint_has_changed([self.storage])

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
        new_job = Job("new job", self.server, data_upload=SourceValue(5 * u.MB),
                      data_download=SourceValue(5 * u.GB), data_stored=SourceValue(5 * u.MB),
                      request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
                      cpu_needed=SourceValue(1 * u.core))

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
        new_step = UserJourneyStep(
            "new_step", user_time_spent=SourceValue(2 * u.min),
            jobs=[Job("new job", self.server, data_upload=SourceValue(5 * u.kB),
                      data_download=SourceValue(5 * u.GB), data_stored=SourceValue(5 * u.kB),
                      request_duration=SourceValue(4 * u.s), ram_needed=SourceValue(100 * u.MB),
                      cpu_needed=SourceValue(1 * u.core))]
        )
        self.uj.uj_steps = [new_step]

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.network])

        logger.warning("Changing back to previous uj steps")
        self.uj.uj_steps = [self.streaming_step, self.upload_step]

        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_not_changed([self.storage, self.server, self.network, self.usage_pattern])

    def test_update_user_journey(self):
        logger.warning("Changing user journey")
        new_uj = UserJourney("New version of daily Youtube usage", uj_steps=[self.streaming_step])
        self.usage_pattern.user_journey = new_uj

        self.assertFalse(self.initial_footprint.value.equals(self.system.total_footprint.value))
        self.footprint_has_changed([self.storage, self.server, self.network, self.usage_pattern])

        logger.warning("Changing back to previous uj")
        self.usage_pattern.user_journey = self.uj

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
        self.footprint_has_changed([self.network])
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))

        logger.warning("Changing back to initial network")
        self.usage_pattern.network = self.network
        self.assertEqual(0, new_network.energy_footprint.max().magnitude)
        self.footprint_has_not_changed([self.network])
        self.assertTrue(self.initial_footprint.value.equals(self.system.total_footprint.value))

    def test_add_uj_step_without_job(self):
        logger.warning("Add uj step without job")

        step_without_job = UserJourneyStep(
            "User checks her phone", user_time_spent=SourceValue(20 * u.min), jobs=[])

        self.uj.add_step(step_without_job)

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

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

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
        simulation = Simulation(self.start_date + timedelta(hours=1),
                                [(self.streaming_step.user_time_spent, SourceValue(25 * u.min))])

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=False)
        self.usage_pattern.devices_energy_footprint.plot(plt_show=False, cumsum=True)
        self.system.total_footprint.plot(plt_show=False, cumsum=False)
        self.system.total_footprint.plot(plt_show=False, cumsum=True)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent])
        self.assertEqual(simulation.new_sourcevalues, [SourceValue(25 * u.min)])
        self.assertEqual([], simulation.old_mod_obj_links)
        self.assertEqual([], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        # Depending job occurrences should have been recomputed since a changing user_time_spent might shift jobs
        # distribution across time
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id,
                      [elt.id for elt in simulation.values_to_recompute])

    def test_simulation_multiple_input_changes(self):
        simulation = Simulation(
            self.start_date + timedelta(hours=1),[
                (self.streaming_step.user_time_spent, SourceValue(25 * u.min)),
                (self.server.cpu_cores, SourceValue(42 * u.core, Sources.USER_DATA))])

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server.cpu_cores])
        self.assertEqual(simulation.new_sourcevalues,
                         [SourceValue(25 * u.min), SourceValue(42 * u.core, Sources.USER_DATA)])
        self.assertEqual([], simulation.old_mod_obj_links)
        self.assertEqual([], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertIn(self.server.energy_footprint.id, recomputed_elements_ids)

    def test_simulation_add_new_object(self):
        new_server = default_onpremise()
        new_job = Job("new job", new_server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = Simulation(
            self.start_date + timedelta(hours=1), [
                (self.upload_step.jobs, self.upload_step.jobs + [new_job])])

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(simulation.new_sourcevalues,[])
        self.assertEqual([[self.upload_job]], simulation.old_mod_obj_links)
        self.assertEqual([[self.upload_job, new_job]], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_simulation_values()
        self.assertEqual(initial_upload_step_jobs + [new_job], self.upload_step.jobs)
        simulation.reset_pre_simulation_values()

    def test_simulation_add_existing_object(self):
        simulation = Simulation(
            self.start_date + timedelta(hours=1), [
                (self.upload_step.jobs, self.upload_step.jobs + [self.upload_job])])

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(simulation.new_sourcevalues, [])
        self.assertEqual([[self.upload_job]], simulation.old_mod_obj_links)
        self.assertEqual([[self.upload_job, self.upload_job]], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        self.assertIn(self.upload_job.server.hour_by_hour_cpu_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_simulation_values()
        self.assertEqual(initial_upload_step_jobs + [self.upload_job], self.upload_step.jobs)
        simulation.reset_pre_simulation_values()

    def test_simulation_add_multiple_objects(self):
        new_server = default_onpremise()
        new_job = Job("new job", new_server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        new_job2 = Job("new job 2", new_server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        initial_upload_step_jobs = copy(self.upload_step.jobs)
        simulation = Simulation(
            self.start_date + timedelta(hours=1), [
                (self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job])])

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [])
        self.assertEqual(simulation.new_sourcevalues, [])
        self.assertEqual([[self.upload_job]], simulation.old_mod_obj_links)
        self.assertEqual([[self.upload_job, new_job, new_job2, self.streaming_job]], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_cpu_need.id, recomputed_elements_ids)
        self.assertEqual(initial_upload_step_jobs, self.upload_step.jobs)
        simulation.set_simulation_values()
        self.assertEqual(initial_upload_step_jobs + [new_job, new_job2, self.streaming_job], self.upload_step.jobs)
        simulation.reset_pre_simulation_values()

    def test_simulation_add_objects_and_make_input_changes(self):
        new_server = default_onpremise()
        new_job = Job("new job", new_server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        new_job2 = Job("new job 2", new_server, data_upload=SourceValue(50 * u.kB),
            data_download=SourceValue((2.5 / 3) * u.GB), data_stored=SourceValue(50 * u.kB),
            request_duration=SourceValue(4 * u.min), ram_needed=SourceValue(100 * u.MB),
            cpu_needed=SourceValue(1 * u.core))

        simulation = Simulation(
            self.start_date + timedelta(hours=1), [
                (self.upload_step.jobs, self.upload_step.jobs + [new_job, new_job2, self.streaming_job]),
                (self.streaming_step.user_time_spent, SourceValue(25 * u.min)),
                (self.server.cpu_cores, SourceValue(42 * u.core, Sources.USER_DATA))])

        self.assertTrue(self.system.total_footprint.value.equals(self.initial_footprint.value))
        self.assertEqual(self.system.simulation, simulation)
        self.assertEqual(simulation.old_sourcevalues, [self.streaming_step.user_time_spent, self.server.cpu_cores])
        self.assertEqual(simulation.new_sourcevalues,
                         [SourceValue(25 * u.min), SourceValue(42 * u.core, Sources.USER_DATA)])
        self.assertEqual([[self.upload_job]], simulation.old_mod_obj_links)
        self.assertEqual([[self.upload_job, new_job, new_job2, self.streaming_job]], simulation.new_mod_obj_links)
        self.assertEqual(len(simulation.values_to_recompute), len(simulation.recomputed_values))
        recomputed_elements_ids = [elt.id for elt in simulation.values_to_recompute]
        for job in [new_job, new_job2, self.streaming_job]:
            self.assertIn(job.server.hour_by_hour_cpu_need.id, recomputed_elements_ids)
        self.assertIn(self.upload_step.jobs[0].hourly_occurrences_per_usage_pattern.id, recomputed_elements_ids)
    