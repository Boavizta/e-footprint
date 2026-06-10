from datetime import timedelta, datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.services.service_base_class import Service
from efootprint.builders.services.service_job_base_class import ServiceJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue, SourceObject
from efootprint.constants.units import u
from efootprint.core.attribution import atoms_of
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.server_base import on_premise_provisioned_tier_shares
from efootprint.core.hardware.storage import Storage
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import DirectServerJob, Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import assert_source_atoms_conserve, sum_atom_values
from tests.utils import create_mod_obj_mock


class TestServer(TestCase):
    def setUp(self):
        self.country = MagicMock()
        self.server_base = Server(
            "Test server",
            server_type=ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(0 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(0 * u.W),
            lifespan=SourceValue(0 * u.year),
            idle_power=SourceValue(0 * u.W),
            ram=SourceValue(0 * u.GB_ram),
            compute=SourceValue(0 * u.cpu_core),
            power_usage_effectiveness=SourceValue(0 * u.dimensionless),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
            utilization_rate=SourceValue(0 * u.dimensionless),
            base_ram_consumption=SourceValue(0 * u.GB_ram),
            base_compute_consumption=SourceValue(0 * u.cpu_core),
            storage=MagicMock(spec=Storage)
        )
        self.server_base.trigger_modeling_updates = False

    def test_installable_services(self):
        self.assertEqual(set(Server.installable_services()), {VideoStreaming})

    def test_update_hour_by_hour_compute_need(self):
        job1 = MagicMock()
        job2 = MagicMock()

        job1.hourly_avg_occurrences_across_usage_patterns = create_source_hourly_values_from_list([10, 20, 1, 0])
        job2.hourly_avg_occurrences_across_usage_patterns = create_source_hourly_values_from_list([20, 15, 5, 3])
        job1.compute_needed = SourceValue(2 * u.cpu_core)
        job2.compute_needed = SourceValue(3 * u.cpu_core)

        with patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = {job1, job2}
            self.server_base.update_hour_by_hour_compute_need()

        self.assertEqual([80, 85, 17, 9], self.server_base.hour_by_hour_compute_need.value_as_float_list)

    def test_update_hour_by_hour_ram_need(self):
        job1 = MagicMock()
        job2 = MagicMock()

        job1.hourly_avg_occurrences_across_usage_patterns = create_source_hourly_values_from_list([10, 20, 1, 0])
        job2.hourly_avg_occurrences_across_usage_patterns = create_source_hourly_values_from_list([20, 15, 5, 3])
        job1.ram_needed = SourceValue(2 * u.GB_ram)
        job2.ram_needed = SourceValue(3 * u.GB_ram)

        with patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = {job1, job2}
            self.server_base.update_hour_by_hour_ram_need()

        self.assertEqual([80, 85, 17, 9], self.server_base.hour_by_hour_ram_need.value_as_float_list)


    def test_available_compute_per_instance(self):
        with patch.object(self.server_base, "occupied_compute_per_instance", SourceValue(2 * u.cpu_core)), \
                patch.object(self.server_base, "compute", SourceValue(24 * u.cpu_core)), \
                patch.object(self.server_base, "utilization_rate", SourceValue(0.7 * u.dimensionless)):
            self.server_base.update_available_compute_per_instance()
            expected_value = SourceValue((24 * 0.7 - 2) * u.cpu_core)

            self.assertEqual(expected_value, self.server_base.available_compute_per_instance)

    def test_available_ram_per_instance(self):
        with patch.object(self.server_base, "occupied_ram_per_instance", SourceValue(2 * u.GB_ram)), \
                patch.object(self.server_base, "ram", SourceValue(24 * u.GB_ram)), \
                patch.object(self.server_base, "utilization_rate", SourceValue(0.7 * u.dimensionless)):
            self.server_base.update_available_ram_per_instance()
            expected_value = SourceValue((24 * 0.7 - 2) * u.GB_ram)

            self.assertEqual(expected_value, self.server_base.available_ram_per_instance)


    def test_available_ram_per_instance_should_raise_value_error_when_demand_exceeds_server_capacity(self):
        with patch.object(self.server_base, "ram", SourceValue(128 * u.GB_ram)), \
            patch.object(self.server_base, "occupied_ram_per_instance", SourceValue(129 * u.GB_ram)), \
            patch.object(self.server_base, "utilization_rate", SourceValue(0.7 * u.dimensionless)):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.server_base.update_available_ram_per_instance()
            self.assertIn(
                "Test server has available RAM capacity of 89.6 gigabyte_ram but is asked for 129.0 gigabyte_ram",
                str(context.exception))

    def test_occupied_compute_per_instance(self):
        service_1 = MagicMock()
        service_2 = MagicMock()
        service_1.base_compute_consumption = SourceValue(2 * u.cpu_core)
        service_2.base_compute_consumption = SourceValue(3 * u.cpu_core)
        with patch.object(self.server_base, "base_compute_consumption", SourceValue(5 * u.cpu_core)), \
                patch.object(Server, "installed_services", [service_1, service_2]):
            self.server_base.update_occupied_compute_per_instance()
            expected_value = SourceValue(10 * u.cpu_core)

            self.assertEqual(expected_value.value, self.server_base.occupied_compute_per_instance.value)

    def test_occupied_ram_per_instance(self):
        service_1 = MagicMock()
        service_2 = MagicMock()
        service_1.base_ram_consumption = SourceValue(2 * u.GB_ram)
        service_2.base_ram_consumption = SourceValue(3 * u.GB_ram)
        with patch.object(self.server_base, "base_ram_consumption", SourceValue(5 * u.GB_ram)), \
                patch.object(Server, "installed_services", [service_1, service_2]):
            self.server_base.update_occupied_ram_per_instance()
            expected_value = SourceValue(10 * u.GB_ram)

            self.assertEqual(expected_value.value, self.server_base.occupied_ram_per_instance.value)

    def test_raw_nb_of_instances_autoscaling_simple_case(self):
        ram_need = create_source_hourly_values_from_list([0, 1, 3, 3, 10], pint_unit=u.GB_ram)
        cpu_need = create_source_hourly_values_from_list([2, 4, 2, 6, 3], pint_unit=u.cpu_core)

        with patch.object(self.server_base, "hour_by_hour_ram_need", new=ram_need), \
                patch.object(self.server_base, "hour_by_hour_compute_need", new=cpu_need), \
                patch.object(self.server_base, "available_ram_per_instance", new=SourceValue(2 * u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", new=SourceValue(4 * u.cpu_core)):
            self.server_base.update_raw_nb_of_instances()

            self.assertEqual([0.5, 1, 1.5, 1.5, 5], self.server_base.raw_nb_of_instances.value_as_float_list)

    def test_raw_nb_of_instances_autoscaling_different_timespan_case(self):
        start_date_a = datetime.strptime("2025-01-01", "%Y-%m-%d")
        start_date_b = datetime.strptime("2025-01-02", "%Y-%m-%d")

        ram_need_a = create_source_hourly_values_from_list([0, 1, 3, 3, 10], start_date_a, pint_unit=u.GB_ram)
        ram_need_b = create_source_hourly_values_from_list([0, 1, 3, 3, 10], start_date_b, pint_unit=u.GB_ram)
        cpu_need_a = create_source_hourly_values_from_list([2, 4, 2, 6, 3], start_date_a, pint_unit=u.cpu_core)
        cpu_need_b = create_source_hourly_values_from_list([2, 4, 2, 6, 3], start_date_b, pint_unit=u.cpu_core)
        all_ram_need = (ram_need_a + ram_need_b).set_label("all_ram_need")
        all_cpu_need = (cpu_need_a + cpu_need_b).set_label("all_cpu_need")

        expected_data = [0.5, 1, 1.5, 1.5, 5] + [0] * 19 + [0.5, 1, 1.5, 1.5, 5]
        expected_max_date = start_date_b + timedelta(hours=(len(ram_need_b)-1))

        with patch.object(self.server_base, "hour_by_hour_ram_need", new=all_ram_need), \
                patch.object(self.server_base, "hour_by_hour_compute_need", new=all_cpu_need), \
                patch.object(self.server_base, "available_ram_per_instance", new=SourceValue(2 * u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", new=SourceValue(4 * u.cpu_core)):
            self.server_base.update_raw_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.raw_nb_of_instances.value_as_float_list)
            self.assertEqual(start_date_a, self.server_base.raw_nb_of_instances.start_date)

    def test_compute_instances_energy_simple_case(self):
        with patch.object(self.server_base, "nb_of_instances",
                          create_source_hourly_values_from_list([1, 0, 2])), \
                patch.object(self.server_base, "raw_nb_of_instances",
                             create_source_hourly_values_from_list([1, 0, 2])), \
                patch.object(self.server_base, "power", SourceValue(300 * u.W)), \
                patch.object(self.server_base, "idle_power", SourceValue(50 * u.W)), \
                patch.object(self.server_base, "power_usage_effectiveness", SourceValue(3 * u.dimensionless)):
            self.server_base.update_instances_energy()
            self.assertEqual(u.kWh, self.server_base.instances_energy.unit)
            self.assertTrue(np.allclose([0.9, 0, 1.8], self.server_base.instances_energy.magnitude))

    def test_compute_instances_energy_complex_case(self):
        with patch.object(self.server_base, "nb_of_instances",
                          create_source_hourly_values_from_list([1, 0, 2])), \
                patch.object(self.server_base, "raw_nb_of_instances",
                             create_source_hourly_values_from_list([1, 0, 1.5])), \
                patch.object(self.server_base, "power", SourceValue(300 * u.W)), \
                patch.object(self.server_base, "idle_power", SourceValue(50 * u.W)), \
                patch.object(self.server_base, "power_usage_effectiveness", SourceValue(3 * u.dimensionless)):
            self.server_base.update_instances_energy()
            self.assertEqual(u.kWh, self.server_base.instances_energy.unit)
            self.assertTrue(np.allclose([0.9, 0, 0.9 + 0.525], self.server_base.instances_energy.magnitude))

    def test_energy_footprints(self):
        """Test that the idle footprint scales with nb_of_instances, the load footprint with raw_nb_of_instances,
        and the energy footprint sums them."""
        with patch.object(self.server_base, "nb_of_instances", create_source_hourly_values_from_list([1, 0, 2])), \
                patch.object(self.server_base, "raw_nb_of_instances",
                             create_source_hourly_values_from_list([1, 0, 1.5])), \
                patch.object(self.server_base, "power", SourceValue(300 * u.W)), \
                patch.object(self.server_base, "idle_power", SourceValue(50 * u.W)), \
                patch.object(self.server_base, "power_usage_effectiveness", SourceValue(3 * u.dimensionless)):
            self.server_base.update_idle_energy_footprint()
            self.server_base.update_load_energy_footprint()
            self.server_base.update_energy_footprint()

            # idle energy = 50W * 3 * 1h * nb = [0.15, 0, 0.3] kWh; load = 250W * 3 * 1h * raw = [0.75, 0, 1.125]
            # CI = 100 g/kWh
            self.assertTrue(np.allclose([0.015, 0, 0.03], self.server_base.idle_energy_footprint.magnitude))
            self.assertTrue(np.allclose([0.075, 0, 0.1125], self.server_base.load_energy_footprint.magnitude))
            self.assertTrue(np.allclose([0.09, 0, 0.1425], self.server_base.energy_footprint.magnitude))
            self.assertEqual(u.kg, self.server_base.energy_footprint.unit)

    def test_autoscaling_nb_of_instances(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5]
        expected_data = [1, 1, 2, 2, 5]

        hourly_raw_data = create_source_hourly_values_from_list(raw_data, pint_unit=u.concurrent)
        with patch.object(self.server_base, "raw_nb_of_instances", hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.autoscaling()):
            self.server_base.update_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_on_premise_rounds_up_to_next_integer(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5.5]
        expected_data = [6, 6, 6, 6, 6]

        hourly_raw_data = create_source_hourly_values_from_list(raw_data, pint_unit=u.concurrent)
        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()):
            self.server_base.update_nb_of_instances()
            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_takes_fixed_nb_of_instances_into_account(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5.5]
        expected_data = [12, 12, 12, 12, 12]

        hourly_raw_data = create_source_hourly_values_from_list(raw_data, pint_unit=u.concurrent)

        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()), \
                patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.dimensionless)):
            self.server_base.update_nb_of_instances()
            self.assertEqual(
                expected_data,
                self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_raises_error_if_fixed_number_of_instances_is_surpassed(self):
        raw_data = [0.5, 1, 1.5, 1.5, 14]

        hourly_raw_data = create_source_hourly_values_from_list(raw_data, pint_unit=u.concurrent)

        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()), \
                patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.concurrent)):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.server_base.update_nb_of_instances()
            self.assertIn(
                "Test server has available number of instances capacity of 12.0 concurrent but is asked for 14.0 concurrent",
                str(context.exception))

    def test_nb_of_instances_returns_emptyexplainableobject_if_raw_nb_of_instances_is_emptyexplainableobject(self):
        with patch.object(self.server_base, "raw_nb_of_instances", new=EmptyExplainableObject()), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()):
            self.server_base.update_nb_of_instances()
            self.assertIsInstance(self.server_base.nb_of_instances, EmptyExplainableObject)

    def test_nb_of_instances_serverless(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5]
        expected_data = [0.5, 1, 1.5, 1.5, 5]

        hourly_raw_data = create_source_hourly_values_from_list(raw_data, pint_unit=u.concurrent)
        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.serverless()):
            self.server_base.update_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_server_raises_error_if_server_type_is_not_supported(self):
        with self.assertRaises(ValueError):
            self.server_base.server_type = SourceObject("unsupported_server_type")

    def test_server_raises_error_if_fixed_nb_of_instances_is_defined_for_non_on_premise_server(self):
        with patch.object(self.server_base, "server_type", ServerTypes.serverless()):
            with self.assertRaises(ValueError):
                self.server_base.fixed_nb_of_instances = SourceValue(12 * u.dimensionless)

    def test_server_raises_error_if_fixed_nb_of_instances_is_defined_and_server_type_changes_for_non_on_premise_server(
            self):
        with patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.dimensionless)):
            with self.assertRaises(ValueError):
                self.server_base.server_type = ServerTypes.serverless()

    def test_service_total_job_volumes(self):
        """Test that the service_total_job_volumes cached property sums occurrences across all jobs of each
        service."""
        service_a = create_mod_obj_mock(Service, "Service A")
        job_a1 = create_mod_obj_mock(ServiceJob, "Job A1",
                                     hourly_avg_occurrences_across_usage_patterns=SourceValue(10 * u.concurrent))
        job_a2 = create_mod_obj_mock(ServiceJob, "Job A2",
                                     hourly_avg_occurrences_across_usage_patterns=SourceValue(30 * u.concurrent))
        service_a.jobs = [job_a1, job_a2]

        service_b = create_mod_obj_mock(Service, "Service B")
        job_b1 = create_mod_obj_mock(ServiceJob, "Job B1",
                                     hourly_avg_occurrences_across_usage_patterns=SourceValue(5 * u.concurrent))
        service_b.jobs = [job_b1]

        with patch.object(Server, "installed_services", new_callable=PropertyMock) as mock_services:
            mock_services.return_value = [service_a, service_b]
            service_total_job_volumes = self.server_base.service_total_job_volumes

        self.assertAlmostEqual(40, service_total_job_volumes[service_a].value.magnitude)
        self.assertAlmostEqual(5, service_total_job_volumes[service_b].value.magnitude)

    def test_update_job_repartition_weights_direct_server_job(self):
        """Test direct-server job repartition weight: (compute/server_compute + ram/server_ram) * occurrences."""
        job = create_mod_obj_mock(DirectServerJob, "Direct job",
                                  compute_needed=SourceValue(2 * u.cpu_core),
                                  ram_needed=SourceValue(4 * u.GB_ram),
                                  server=self.server_base,
                                  hourly_avg_occurrences_across_usage_patterns=SourceValue(10 * u.concurrent))

        with patch.object(self.server_base, "compute", SourceValue(10 * u.cpu_core)), \
                patch.object(self.server_base, "ram", SourceValue(20 * u.GB_ram)), \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job]
            self.server_base.update_job_repartition_weights()

        # weight = (2/10 + 4/20) * 10 = (0.2 + 0.2) * 10 = 4.0
        self.assertAlmostEqual(4.0, self.server_base.job_repartition_weights[job].value.magnitude)

    def test_update_job_repartition_weights_service_jobs(self):
        """Test service-job repartition weight: base service consumption is distributed proportionally to job volumes."""
        service = create_mod_obj_mock(Service, "Test service",
                                      base_compute_consumption=SourceValue(2 * u.cpu_core),
                                      base_ram_consumption=SourceValue(4 * u.GB_ram))

        job1 = create_mod_obj_mock(ServiceJob, "Service job 1",
                                   service=service, server=self.server_base,
                                   compute_needed=SourceValue(1 * u.cpu_core),
                                   ram_needed=SourceValue(2 * u.GB_ram),
                                   hourly_avg_occurrences_across_usage_patterns=SourceValue(30 * u.concurrent))

        job2 = create_mod_obj_mock(ServiceJob, "Service job 2",
                                   service=service, server=self.server_base,
                                   compute_needed=SourceValue(1 * u.cpu_core),
                                   ram_needed=SourceValue(2 * u.GB_ram),
                                   hourly_avg_occurrences_across_usage_patterns=SourceValue(10 * u.concurrent))

        service.jobs = [job1, job2]
        nb_of_instances = create_source_hourly_values_from_list([2], pint_unit=u.concurrent)

        with patch.object(self.server_base, "compute", SourceValue(10 * u.cpu_core)), \
                patch.object(self.server_base, "ram", SourceValue(20 * u.GB_ram)), \
                patch.object(self.server_base, "nb_of_instances", nb_of_instances), \
                patch.object(Server, "installed_services", new_callable=PropertyMock) as mock_services, \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_services.return_value = [service]
            mock_jobs.return_value = [job1, job2]
            self.server_base.update_job_repartition_weights()

        # service_base_weight = (2/10 + 4/20) * 2 = 0.4 * 2 = 0.8
        # total_volume = 30 + 10 = 40
        # job1_volume_share = 30 / 40 = 0.75
        # job1_own_weight = (1/10 + 2/20) * 30 = 0.2 * 30 = 6.0
        # job1_weight = 0.8 * 0.75 + 6.0 = 0.6 + 6.0 = 6.6
        self.assertAlmostEqual(6.6, self.server_base.job_repartition_weights[job1].value.magnitude, places=5)
        # job2_volume_share = 10 / 40 = 0.25
        # job2_own_weight = (1/10 + 2/20) * 10 = 0.2 * 10 = 2.0
        # job2_weight = 0.8 * 0.25 + 2.0 = 0.2 + 2.0 = 2.2
        self.assertAlmostEqual(2.2, self.server_base.job_repartition_weights[job2].value.magnitude, places=5)

    def test_phase_impact_repartition_weights_reuse_job_repartition_weights(self):
        job = create_mod_obj_mock(DirectServerJob, "Direct job")
        self.server_base.job_repartition_weights = ExplainableObjectDict({
            job: SourceValue(1 * u.concurrent)
        })

        self.assertIs(self.server_base.job_repartition_weights, self.server_base.fabrication_impact_repartition_weights)
        self.assertIs(self.server_base.job_repartition_weights, self.server_base.usage_impact_repartition_weights)

    def test_binding_demand_per_job_charges_the_binding_resource_per_hour(self):
        """Test that a job's binding demand follows the server-level binding resource hour by hour: compute
        binds at hour 0, RAM binds at hour 1, so a RAM-heavy job on a compute-bound hour is charged compute."""
        job = create_mod_obj_mock(
            DirectServerJob, "Ram heavy job", compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(8 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [2, 1], pint_unit=u.concurrent))

        with patch.object(self.server_base, "hour_by_hour_compute_need",
                          create_source_hourly_values_from_list([8, 2], pint_unit=u.cpu_core)), \
                patch.object(self.server_base, "hour_by_hour_ram_need",
                             create_source_hourly_values_from_list([10, 30], pint_unit=u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", SourceValue(4 * u.cpu_core)), \
                patch.object(self.server_base, "available_ram_per_instance", SourceValue(10 * u.GB_ram)), \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job]
            binding_demand = self.server_base.binding_demand_per_job[job]

        # pressures: compute [8/4, 2/4] = [2, 0.5], ram [10/10, 30/10] = [1, 3] -> compute binds h0, ram binds h1
        # demand = [(1/4) * 2, (8/10) * 1] = [0.5, 0.8]
        self.assertTrue(np.allclose([0.5, 0.8], binding_demand.magnitude))

    def test_binding_demand_per_job_service_job_carries_its_volume_share_of_service_base_consumption(self):
        """Test that a ServiceJob's binding demand adds its volume share of its service's base consumption in
        binding-resource units, on top of its own demand — paid by the service's own jobs only."""
        service = create_mod_obj_mock(Service, "Base service",
                                      base_compute_consumption=SourceValue(2 * u.cpu_core),
                                      base_ram_consumption=SourceValue(4 * u.GB_ram))
        job1 = create_mod_obj_mock(
            ServiceJob, "Service job one", service=service, compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(2 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [30], pint_unit=u.concurrent))
        job2 = create_mod_obj_mock(
            ServiceJob, "Service job two", service=service, compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(2 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [10], pint_unit=u.concurrent))
        service.jobs = [job1, job2]

        with patch.object(self.server_base, "hour_by_hour_compute_need",
                          create_source_hourly_values_from_list([8], pint_unit=u.cpu_core)), \
                patch.object(self.server_base, "hour_by_hour_ram_need",
                             create_source_hourly_values_from_list([10], pint_unit=u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", SourceValue(4 * u.cpu_core)), \
                patch.object(self.server_base, "available_ram_per_instance", SourceValue(10 * u.GB_ram)), \
                patch.object(self.server_base, "nb_of_instances",
                             create_source_hourly_values_from_list([2], pint_unit=u.concurrent)), \
                patch.object(Server, "installed_services", new_callable=PropertyMock) as mock_services, \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_services.return_value = [service]
            mock_jobs.return_value = [job1, job2]
            binding_demand_per_job = self.server_base.binding_demand_per_job
            dynamic_share_per_job = self.server_base.dynamic_share_per_job

        # compute binds (pressure 2 vs 1); own demand = (1/4) * occ; service base = (2/4) * 2 instances * share
        # job1 = 7.5 + 1 * 0.75 = 8.25; job2 = 2.5 + 1 * 0.25 = 2.75
        self.assertAlmostEqual(8.25, binding_demand_per_job[job1].magnitude[0], places=5)
        self.assertAlmostEqual(2.75, binding_demand_per_job[job2].magnitude[0], places=5)
        self.assertAlmostEqual(0.75, dynamic_share_per_job[job1].magnitude[0], places=5)
        self.assertAlmostEqual(0.25, dynamic_share_per_job[job2].magnitude[0], places=5)

    def test_dynamic_share_per_job_is_zero_at_zero_demand_hours(self):
        """Test that dynamic shares split demand proportionally at active hours and fall back to 0 (not NaN, not
        an equal split) at hours with zero total demand."""
        job1 = create_mod_obj_mock(
            DirectServerJob, "Active job", compute_needed=SourceValue(2 * u.cpu_core),
            ram_needed=SourceValue(1 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [3, 0], pint_unit=u.concurrent))
        job2 = create_mod_obj_mock(
            DirectServerJob, "Other active job", compute_needed=SourceValue(2 * u.cpu_core),
            ram_needed=SourceValue(1 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [1, 0], pint_unit=u.concurrent))

        with patch.object(self.server_base, "hour_by_hour_compute_need",
                          create_source_hourly_values_from_list([8, 0], pint_unit=u.cpu_core)), \
                patch.object(self.server_base, "hour_by_hour_ram_need",
                             create_source_hourly_values_from_list([4, 0], pint_unit=u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", SourceValue(4 * u.cpu_core)), \
                patch.object(self.server_base, "available_ram_per_instance", SourceValue(10 * u.GB_ram)), \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job1, job2]
            dynamic_share_per_job = self.server_base.dynamic_share_per_job

        self.assertTrue(np.allclose([0.75, 0], dynamic_share_per_job[job1].magnitude))
        self.assertTrue(np.allclose([0.25, 0], dynamic_share_per_job[job2].magnitude))

    def test_provisioned_share_per_job_collapses_to_dynamic_for_autoscaling(self):
        """Test that an autoscaling server's provisioned shares are exactly its dynamic shares (hourly
        re-provisioning leaves no always-on capacity to spread)."""
        job = create_mod_obj_mock(
            DirectServerJob, "Autoscaled job", compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(1 * u.GB_ram),
            hourly_avg_occurrences_across_usage_patterns=create_source_hourly_values_from_list(
                [2], pint_unit=u.concurrent))

        with patch.object(self.server_base, "server_type", ServerTypes.autoscaling()), \
                patch.object(self.server_base, "hour_by_hour_compute_need",
                             create_source_hourly_values_from_list([2], pint_unit=u.cpu_core)), \
                patch.object(self.server_base, "hour_by_hour_ram_need",
                             create_source_hourly_values_from_list([2], pint_unit=u.GB_ram)), \
                patch.object(self.server_base, "available_compute_per_instance", SourceValue(4 * u.cpu_core)), \
                patch.object(self.server_base, "available_ram_per_instance", SourceValue(10 * u.GB_ram)), \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job]
            self.assertIs(self.server_base.dynamic_share_per_job, self.server_base.provisioned_share_per_job)

    def test_provisioned_share_per_job_on_premise_uses_per_tier_weights(self):
        """Test that an on-premise server's provisioned shares are the flat per-tier weights, summing to 1."""
        job1 = create_mod_obj_mock(DirectServerJob, "Peak job")
        job2 = create_mod_obj_mock(DirectServerJob, "Off peak job")
        self.server_base.__dict__["binding_demand_per_job"] = {
            job1: create_source_hourly_values_from_list([3, 1], pint_unit=u.concurrent),
            job2: create_source_hourly_values_from_list([0, 1], pint_unit=u.concurrent)}

        with patch.object(self.server_base, "raw_nb_of_instances",
                          create_source_hourly_values_from_list([3, 2], pint_unit=u.concurrent)), \
                patch.object(self.server_base, "nb_of_instances",
                             create_source_hourly_values_from_list([3, 3], pint_unit=u.concurrent)), \
                patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job1, job2]
            provisioned_share_per_job = self.server_base.provisioned_share_per_job

        # tiers 1 & 2 needed both hours (shares 4/5, 1/5); tier 3 needed at hour 0 only (shares 1, 0)
        self.assertAlmostEqual((0.8 + 0.8 + 1) / 3, provisioned_share_per_job[job1].magnitude, places=5)
        self.assertAlmostEqual((0.2 + 0.2 + 0) / 3, provisioned_share_per_job[job2].magnitude, places=5)


class TestOnPremiseProvisionedTierShares(TestCase):
    """The per-tier provisioned weight helper in isolation — the subtlest physics of the server attribution."""

    def test_off_peak_job_still_pays_the_lower_tiers_it_requires(self):
        """Test that a job present only off-peak gets a nonzero flat weight (it needs the lower tiers), with
        weights summing to 1."""
        shares = on_premise_provisioned_tier_shares(
            {"peak_job": np.array([3.0, 1.0]), "off_peak_job": np.array([0.0, 1.0])},
            raw_nb_of_instances=np.array([3.0, 2.0]), nb_of_tiers=3)

        # tiers 1 & 2 needed both hours: demand shares 4/5 vs 1/5; tier 3 needed at hour 0 only: 1 vs 0
        self.assertAlmostEqual((0.8 + 0.8 + 1) / 3, shares["peak_job"], places=6)
        self.assertAlmostEqual((0.2 + 0.2 + 0) / 3, shares["off_peak_job"], places=6)
        self.assertAlmostEqual(1, sum(shares.values()), places=6)

    def test_tier_above_peak_falls_back_to_period_total_demand_shares(self):
        """Test that a tier no hour needs (fixed_nb_of_instances above peak) is paid by the period-total demand
        shares instead of being dropped."""
        shares = on_premise_provisioned_tier_shares(
            {"big_job": np.array([4.0, 0.0]), "small_job": np.array([0.0, 1.0])},
            raw_nb_of_instances=np.array([2.0, 1.0]), nb_of_tiers=3)

        # tier 1: both hours -> 4/5, 1/5; tier 2: hour 0 only -> 1, 0; tier 3: never needed -> period 4/5, 1/5
        self.assertAlmostEqual((0.8 + 1 + 0.8) / 3, shares["big_job"], places=6)
        self.assertAlmostEqual((0.2 + 0 + 0.2) / 3, shares["small_job"], places=6)
        self.assertAlmostEqual(1, sum(shares.values()), places=6)

    def test_fractional_raw_pins_the_tier_hours_predicate(self):
        """Test the tier-hours set {h: raw[h] > k - 1} on fractional raw values: at raw = 2.5 the top tier
        (k = 3) is needed at that hour (a `raw >= k` off-by-one would wrongly drop it to the period fallback)."""
        shares = on_premise_provisioned_tier_shares(
            {"big_job": np.array([2.0, 0.0]), "small_job": np.array([0.5, 1.0])},
            raw_nb_of_instances=np.array([2.5, 1.0]), nb_of_tiers=3)

        # tier 1: both hours -> 2/3.5, 1.5/3.5; tiers 2 & 3: hour 0 only (2.5 > 1 and 2.5 > 2) -> 0.8, 0.2
        self.assertAlmostEqual((2 / 3.5 + 0.8 + 0.8) / 3, shares["big_job"], places=6)
        self.assertAlmostEqual((1.5 / 3.5 + 0.2 + 0.2) / 3, shares["small_job"], places=6)
        self.assertAlmostEqual(1, sum(shares.values()), places=6)

    def test_zero_total_demand_falls_back_to_equal_shares(self):
        """Test that a zero-traffic model still gets sum-to-1 equal flat weights for the always-on stream."""
        shares = on_premise_provisioned_tier_shares(
            {"job_a": np.array([0.0, 0.0]), "job_b": np.array([0.0, 0.0])},
            raw_nb_of_instances=np.array([0.0, 0.0]), nb_of_tiers=2)

        self.assertAlmostEqual(0.5, shares["job_a"], places=6)
        self.assertAlmostEqual(0.5, shares["job_b"], places=6)


class TestServerAttributionAtoms(TestCase):
    """Conservation of the server atom builder on a real model with web + edge cells and an on-premise server,
    including the always-on fix: flat provisioned shares carry footprint at zero-occurrence hours."""

    @classmethod
    def setUpClass(cls):
        def country(name, carbon_intensity):
            return Country(name, name[:3].upper(), SourceValue(carbon_intensity),
                           ExplainableTimezone(pytz.utc, "UTC timezone"))

        cls.server = Server.from_defaults(
            "server atoms server", server_type=ServerTypes.on_premise(),
            storage=Storage.from_defaults("server atoms storage"))
        cls.dual_job = Job.from_defaults(
            "server atoms dual side job", server=cls.server, request_duration=SourceValue(90 * u.min),
            ram_needed=SourceValue(2 * u.GB_ram))
        cls.web_only_job = Job.from_defaults(
            "server atoms web only job", server=cls.server, request_duration=SourceValue(10 * u.min))

        cls.step_a = UsageJourneyStep("server atoms step a", SourceValue(30 * u.min),
                                      [cls.dual_job, cls.web_only_job])
        cls.step_b = UsageJourneyStep("server atoms step b", SourceValue(1 * u.hour), [cls.dual_job])
        cls.journey = UsageJourney("server atoms journey", [cls.step_a, cls.step_b])

        device = Device.from_defaults("server atoms laptop")
        network = Network("server atoms network", SourceValue(0.05 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        cls.up1 = UsagePattern(
            "server atoms web usage pattern 1", cls.journey, [device], network,
            country("server atoms first country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([10, 0, 5, 0, 8], start_date))
        cls.up2 = UsagePattern(
            "server atoms web usage pattern 2", cls.journey, [device], network,
            country("server atoms second country", 300 * u.g / u.kWh),
            create_source_hourly_values_from_list([3, 7], start_date))

        workload_component = EdgeWorkloadComponent.from_defaults("server atoms workload component")
        edge_device = EdgeDevice.from_defaults("server atoms edge device", components=[workload_component])
        component_need = RecurrentEdgeComponentNeed(
            "server atoms workload need", workload_component,
            SourceRecurrentValues(Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent)))
        device_need = RecurrentEdgeDeviceNeed("server atoms device need", edge_device, [component_need])
        cls.rsn = RecurrentServerNeed(
            "server atoms recurrent server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([2.0] * 168, dtype=np.float32), u.occurrence)),
            [cls.dual_job])
        edge_function = EdgeFunction("server atoms edge function", [device_need], [cls.rsn])
        edge_journey = EdgeUsageJourney(
            "server atoms edge journey", [edge_function], usage_span=SourceValue(1 * u.year))
        cls.edge_up = EdgeUsagePattern(
            "server atoms edge usage pattern", edge_journey, network,
            country("server atoms edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([4, 0, 6], start_date))

        cls.system = System(
            "server atoms system", [cls.up1, cls.up2], edge_usage_patterns=[cls.edge_up])

    def test_server_atoms_conserve_per_stream_with_web_and_edge_cells(self):
        """Test that Σ atoms per phase equals the eager phase totals and that each stream conserves its own
        footprint (provisioned over fabrication and idle energy, dynamic over load energy)."""
        assert_source_atoms_conserve(
            self, self.server,
            stream_footprints_by_phase={
                LifeCyclePhases.MANUFACTURING: {"provisioned": self.server.instances_fabrication_footprint},
                LifeCyclePhases.USAGE: {"provisioned": self.server.idle_energy_footprint,
                                        "dynamic": self.server.load_energy_footprint}})

    def test_dual_side_job_splits_across_web_steps_and_edge_rsns(self):
        """Test that a job triggered both by web steps and by a recurrent server need carries nonzero atoms on
        both sides, for both streams of the usage phase."""
        usage_atoms = [atom for atom in atoms_of(self.server, LifeCyclePhases.USAGE)
                       if atom.job == self.dual_job]
        for stream in ("provisioned", "dynamic"):
            web_sum = sum_atom_values(
                atom for atom in usage_atoms if atom.stream == stream and atom.step is not None)
            edge_sum = sum_atom_values(
                atom for atom in usage_atoms if atom.stream == stream and atom.rsn is not None)
            self.assertGreater(web_sum.sum().magnitude, 0)
            self.assertGreater(edge_sum.sum().magnitude, 0)

    def test_flat_provisioned_share_carries_footprint_at_a_cell_zero_occurrence_hour(self):
        """Test the plan §1.2 J2 | B·US row: at an hour where a cell has zero occurrences but the on-premise
        server is provisioned, the cell's dynamic atom is zero while its provisioned atom stays nonzero (flat
        share of the idle footprint)."""
        zero_occurrence_hour = 4  # up2 journey starts are [3, 7] and the job runs 10 min, so hour 4 is idle
        cell_occurrences = self.web_only_job.get_hourly_avg_occurrences_per_usage_pattern_per_step(
            self.up2, self.step_a)
        self.assertEqual(
            0, np.append(cell_occurrences.magnitude, np.zeros(5))[zero_occurrence_hour])

        usage_atoms = [
            atom for atom in atoms_of(self.server, LifeCyclePhases.USAGE)
            if atom.job == self.web_only_job and atom.step == self.step_a and atom.up == self.up2]
        dynamic_atom = next(atom for atom in usage_atoms if atom.stream == "dynamic")
        provisioned_atom = next(atom for atom in usage_atoms if atom.stream == "provisioned")
        self.assertEqual(0, dynamic_atom.value.magnitude[zero_occurrence_hour])
        self.assertGreater(provisioned_atom.value.magnitude[zero_occurrence_hour], 0)

    def test_provisioned_atoms_carry_the_idle_footprint_at_idle_server_hours(self):
        """Test that at an hour with zero demand on the whole on-premise server, the dynamic atoms are zero and
        the provisioned atoms sum to the idle energy footprint, which is nonzero (instances on 24/7)."""
        server = Server.from_defaults(
            "idle hours server", server_type=ServerTypes.on_premise(),
            storage=Storage.from_defaults("idle hours storage"))
        job = Job.from_defaults("idle hours job", server=server, request_duration=SourceValue(10 * u.min))
        step = UsageJourneyStep("idle hours step", SourceValue(30 * u.min), [job])
        journey = UsageJourney("idle hours journey", [step])
        up = UsagePattern(
            "idle hours usage pattern", journey, [Device.from_defaults("idle hours laptop")],
            Network("idle hours network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("idle hours country", "IHC", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([4, 0, 0, 0, 0, 0], datetime(2026, 1, 1)))
        System("idle hours system", [up], edge_usage_patterns=[])

        idle_hour = 5
        self.assertEqual(0, server.raw_nb_of_instances.magnitude[idle_hour])
        self.assertGreater(server.idle_energy_footprint.magnitude[idle_hour], 0)
        usage_atoms = list(atoms_of(server, LifeCyclePhases.USAGE))
        provisioned_sum = sum_atom_values(atom for atom in usage_atoms if atom.stream == "provisioned")
        dynamic_sum = sum_atom_values(atom for atom in usage_atoms if atom.stream == "dynamic")
        self.assertAlmostEqual(
            server.idle_energy_footprint.magnitude[idle_hour], provisioned_sum.magnitude[idle_hour], places=6)
        self.assertEqual(0, dynamic_sum.magnitude[idle_hour])


class TestJobRepartitionWeightsAfterAttributionQuery(TestCase):
    def test_modeling_update_recomputes_service_job_weights_after_an_attribution_query(self):
        """Test the render-then-update sequence on a service model: materializing the lazy attribution caches
        then changing an input must neither crash the ModelingUpdate nor leave stale service totals in the
        eager job_repartition_weights."""
        server = Server.from_defaults(
            "stale weights server", server_type=ServerTypes.on_premise(),
            storage=Storage.from_defaults("stale weights storage"))
        service = VideoStreaming.from_defaults("stale weights service", server=server)
        job = VideoStreamingJob.from_defaults(
            "stale weights job", service=service, video_duration=SourceValue(10 * u.min))
        step = UsageJourneyStep("stale weights step", SourceValue(15 * u.min), [job])
        journey = UsageJourney("stale weights journey", [step])
        up = UsagePattern(
            "stale weights usage pattern", journey, [Device.from_defaults("stale weights laptop")],
            Network("stale weights network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("stale weights country", "SWC", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([10, 20], datetime(2026, 1, 1)))
        System("stale weights system", [up], edge_usage_patterns=[])

        _ = server.binding_demand_per_job  # a render materializes the lazy attribution caches

        up.hourly_usage_journey_starts = create_source_hourly_values_from_list([100, 200], datetime(2026, 1, 1))

        weight_after_update = server.job_repartition_weights[job].magnitude.copy()
        server.flush_cached_properties()
        server.update_job_repartition_weights()
        self.assertTrue(np.allclose(weight_after_update, server.job_repartition_weights[job].magnitude))
