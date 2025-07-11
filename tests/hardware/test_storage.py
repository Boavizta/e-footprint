from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from datetime import datetime, timedelta

import numpy as np

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.constants.units import u
from efootprint.core.hardware.infra_hardware import InsufficientCapacityError
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage, NegativeCumulativeStorageNeedError
from efootprint.core.usage.job import Job


class TestStorage(TestCase):
    def setUp(self):
        self.storage_base = Storage(
            "storage_base",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(0 * u.kg/u.TB),
            power_per_storage_capacity=SourceValue(0 * u.W / u.TB),
            lifespan=SourceValue(0 * u.years, Sources.HYPOTHESIS),
            idle_power=SourceValue(0 * u.W, Sources.HYPOTHESIS),
            storage_capacity=SourceValue(0 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(0 * u.dimensionless, Sources.HYPOTHESIS),
            data_storage_duration=SourceValue(0 * u.years, Sources.HYPOTHESIS),
            base_storage_need=SourceValue(0 * u.TB, Sources.HYPOTHESIS)
        )

        self.storage_base.trigger_modeling_updates = False

    def test_storage_with_two_servers_raises_error(self):
        storage = self.storage_base
        server1 = MagicMock()
        server2 = MagicMock()
        with (patch.object(Storage, "modeling_obj_containers", new_callable=PropertyMock)
              as modeling_obj_containers_mock):
            modeling_obj_containers_mock.return_value = [server1, server2]
            with self.assertRaises(PermissionError):
                storage.server

    def test_update_storage_needs_single_job(self):
        job1 = MagicMock(data_stored=SourceValue(2 * u.TB))
        server1 = MagicMock()
        job1.server = server1
        job1.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB)
        server1.storage = self.storage_base
        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(3 * u.dimensionless)):
            jobs_mock.return_value = [job1]
            self.assertEqual([3, 6, 9], self.storage_base.storage_needed.value_as_float_list)
            self.assertEqual(u.TB, self.storage_base.storage_needed.unit)

    def test_update_storage_needs_multiple_jobs(self):
        job1 = MagicMock(data_stored=SourceValue(2 * u.TB))
        job2 = MagicMock(data_stored=SourceValue(2 * u.TB))
        job1.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB)
        job2.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB)

        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(3 * u.dimensionless)):
            jobs_mock.return_value = [job1, job2]
            self.assertEqual([6, 12, 18], self.storage_base.storage_needed.value_as_float_list)
            self.assertEqual(u.TB, self.storage_base.storage_needed.unit)

    def test_update_storage_needs_multiple_jobs_with_negative_data_stored(self):
        job1 = MagicMock(data_stored=SourceValue(2 * u.TB))
        job2 = MagicMock(data_stored=SourceValue(-2 * u.TB))
        job1.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB)
        job2.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([-2, -4, -6], pint_unit=u.TB)

        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(3 * u.dimensionless)):
            jobs_mock.return_value = [job1, job2]
            self.assertEqual([3, 6, 9], self.storage_base.storage_needed.value_as_float_list)
            self.assertEqual(u.TB, self.storage_base.storage_needed.unit)

    def test_update_storage_freed_multiple_jobs_with_negative_data_stored(self):
        job1 = MagicMock(data_stored=SourceValue(6 * u.TB))
        job2 = MagicMock(data_stored=SourceValue(-6 * u.TB))
        job1.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB)
        job2.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list(
            [-1, -2, -3], pint_unit=u.TB)

        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(3 * u.dimensionless)):
            jobs_mock.return_value = [job1, job2]
            self.assertEqual([-3, -6, -9], self.storage_base.storage_freed.value_as_float_list)
            self.assertEqual(u.TB, self.storage_base.storage_freed.unit)

    def test_update_automatic_storage_dumps_after_storage_duration(self):
        input_data = [2, 4, 6]
        storage_duration = 1
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        all_needed_storage = create_source_hourly_values_from_list(input_data, start_date, pint_unit=u.TB)

        with patch.object(Storage, "storage_needed", all_needed_storage), \
            patch.object(self.storage_base, "data_storage_duration", SourceValue(storage_duration * u.hours)):
            self.assertEqual(
                [0, -2, -4], self.storage_base.automatic_storage_dumps_after_storage_duration.value_as_float_list)
            self.assertEqual(
                start_date,
                self.storage_base.automatic_storage_dumps_after_storage_duration.start_date)

    def test_update_automatic_storage_dumps_after_storage_duration_returns_hourly_quantities_full_of_zeros_when_no_dump_during_period(self):
        input_data = [2, 4, 6]
        storage_duration = 5
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        all_needed_storage = create_source_hourly_values_from_list(input_data, start_date, pint_unit=u.TB)

        with patch.object(Storage, "storage_needed", all_needed_storage), \
            patch.object(self.storage_base, "data_storage_duration", SourceValue(storage_duration * u.hours)):
            self.assertEqual([0, 0, 0], self.storage_base.automatic_storage_dumps_after_storage_duration.value_as_float_list)
            self.assertEqual(start_date,
                             self.storage_base.automatic_storage_dumps_after_storage_duration.start_date)

    def test_storage_delta(self):
        input_data = [2, 4, 6]
        free_data = [0, 0, -1]
        dumps_data = [-2, -4]
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        all_needed_storage = create_source_hourly_values_from_list(input_data, start_date, pint_unit=u.TB)
        all_freed_storage = create_source_hourly_values_from_list(free_data, start_date, pint_unit=u.TB)
        dump_min_date = start_date + timedelta(hours=1)
        dump_need_update = create_source_hourly_values_from_list(dumps_data, dump_min_date, pint_unit=u.TB)

        with patch.object(Storage, "storage_needed", all_needed_storage), \
            patch.object(Storage, "automatic_storage_dumps_after_storage_duration", dump_need_update), \
            patch.object(Storage, "storage_freed", all_freed_storage):
            self.storage_base.update_storage_delta()
            self.assertEqual([2, 2, 1], self.storage_base.storage_delta.value_as_float_list)

    def test_storage_delta_with_no_freed_data(self):
        input_data = [2, 4, 6]
        dumps_data = [-2, -4]
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        all_needed_storage = create_source_hourly_values_from_list(input_data, start_date, pint_unit=u.TB)
        dump_min_date = start_date + timedelta(hours=1)
        dump_need_update = create_source_hourly_values_from_list(dumps_data, dump_min_date, pint_unit=u.TB)
        all_freed_data = EmptyExplainableObject()

        with patch.object(Storage, "storage_needed", all_needed_storage), \
            patch.object(Storage, "automatic_storage_dumps_after_storage_duration", dump_need_update), \
            patch.object(Storage, "storage_freed", all_freed_data):
            self.storage_base.update_storage_delta()

            self.assertEqual([2, 2, 2], self.storage_base.storage_delta.value_as_float_list)

    def test_update_full_cumulative_storage_need(self):
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        delta_data = create_source_hourly_values_from_list([2, -2, 4, -5, 6], start_date, pint_unit=u.TB)

        with patch.object(self.storage_base, "storage_delta", delta_data), \
                patch.object(self.storage_base, "base_storage_need", SourceValue(5 * u.TB)):
            self.storage_base.update_full_cumulative_storage_need()

            self.assertEqual([7, 5, 9, 4, 10], self.storage_base.full_cumulative_storage_need.value_as_float_list)

    def test_update_full_cumulative_storage_need_raises_negative_cumulative_storage_need_error(self):
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        delta_data = create_source_hourly_values_from_list([2, -2, 4, -5, -6], start_date, pint_unit=u.TB)
        job = Mock(spec=Job)
        job.data_stored = SourceValue(-10 * u.MB)
        job.name = "job1"

        with patch.object(self.storage_base, "storage_delta", delta_data), \
                patch.object(self.storage_base, "base_storage_need", SourceValue(5 * u.TB)), \
                patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock:
            jobs_mock.return_value = [job]
            with self.assertRaises(NegativeCumulativeStorageNeedError) as context:
                self.storage_base.update_full_cumulative_storage_need()
            self.assertEqual(
                "In Storage object storage_base, negative cumulative storage need detected: -2.0 TB. "
                "Please verify your jobs that delete data: ['name: job1 - value: -10.0 megabyte'] or "
                "increase the base_storage_need value, currently set to 5.0 terabyte",
            str(context.exception))

    def test_nb_of_active_instances(self):
        storage_capacity = SourceValue(1 * u.TB)
        storage_needed = create_source_hourly_values_from_list([-1, 1, 2, 3, 2], pint_unit=u.TB)
        storage_freed = create_source_hourly_values_from_list([0, -0.5, 0, -1, -5], pint_unit=u.TB)
        automatic_storage_dumps_after_storage_duration = create_source_hourly_values_from_list(
            [0, -0.5, -1, -0.5, 0], pint_unit=u.TB)
        nb_of_instances = create_source_hourly_values_from_list([3, 3, 3, 2, 6], pint_unit=u.dimensionless)

        with patch.object(Storage, "storage_needed", storage_needed), \
                patch.object(Storage, "storage_freed", storage_freed), \
                patch.object(Storage, "automatic_storage_dumps_after_storage_duration",
                             automatic_storage_dumps_after_storage_duration), \
                patch.object(self.storage_base, "nb_of_instances", nb_of_instances), \
                patch.object(self.storage_base, "storage_capacity", storage_capacity):
            self.storage_base.update_nb_of_active_instances()
            self.assertEqual([1, 1.5, 3, 2, 5], self.storage_base.nb_of_active_instances.value_as_float_list)

    def test_nb_of_active_instances_with_empty_explainable_object(self):
        storage_capacity = SourceValue(1 * u.TB)
        storage_needed = EmptyExplainableObject()
        storage_freed = EmptyExplainableObject()
        automatic_storage_dumps_after_storage_duration = EmptyExplainableObject()
        nb_of_instances = create_source_hourly_values_from_list([1, 2, 2], pint_unit=u.dimensionless)

        with patch.object(Storage, "storage_needed", storage_needed), \
                patch.object(Storage, "storage_freed", storage_freed), \
                patch.object(Storage, "automatic_storage_dumps_after_storage_duration",
                             automatic_storage_dumps_after_storage_duration), \
                patch.object(self.storage_base, "nb_of_instances", nb_of_instances), \
                patch.object(self.storage_base, "storage_capacity", storage_capacity):
            self.storage_base.update_nb_of_active_instances()
            self.assertEqual(self.storage_base.nb_of_active_instances.value_as_float_list, [0, 0, 0])

    def test_raw_nb_of_instances(self):
        full_storage_data = create_source_hourly_values_from_list([10, 12, 14], pint_unit=u.TB)
        storage_capacity = SourceValue(2 * u.TB)
        expected_data = [5, 6, 7]

        with patch.object(self.storage_base, "full_cumulative_storage_need", full_storage_data), \
                patch.object(self.storage_base, "storage_capacity", storage_capacity):
            self.storage_base.update_raw_nb_of_instances()
            self.assertEqual(expected_data, self.storage_base.raw_nb_of_instances.value_as_float_list)

    def test_nb_of_instances(self):
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.dimensionless)
        expected_data = [2, 3, 4]

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertEqual(expected_data, self.storage_base.nb_of_instances.value_as_float_list)
            self.assertEqual(u.dimensionless, self.storage_base.nb_of_instances.unit)

    def test_nb_of_instances_with_fixed_nb_of_instances(self):
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.dimensionless)
        expected_data = [5, 5, 5]
        fixed_nb_of_instances = SourceValue(5 * u.dimensionless, Sources.HYPOTHESIS)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
            patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertEqual(expected_data, self.storage_base.nb_of_instances.value_as_float_list)
            self.assertEqual(u.dimensionless, self.storage_base.nb_of_instances.unit)

    def test_nb_of_instances_raises_error_if_fixed_number_of_instances_is_surpassed(self):
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.dimensionless)
        fixed_nb_of_instances = SourceValue(2 * u.dimensionless, Sources.HYPOTHESIS)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
            patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.storage_base.update_nb_of_instances()
            self.assertIn(
                "storage_base has available number of instances capacity of 2.0 dimensionless but is asked for "
                "4.0 dimensionless", str(context.exception))

    def test_nb_of_instances_returns_empty_explainable_object_if_raw_nb_of_instances_is_empty(self):
        raw_nb_of_instances = EmptyExplainableObject()
        fixed_nb_of_instances = SourceValue(2 * u.dimensionless, Sources.HYPOTHESIS)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
                patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertIsInstance(self.storage_base.nb_of_instances, EmptyExplainableObject)

    def test_update_instances_energy(self):
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        all_instance_data = [2, 4, 6]
        all_active_data = [1, 2, 3]
        power_data = 100 * u.W
        power_idle_data = 50 * u.W
        server_mock = MagicMock(spec=Server)
        server_mock.storage = self.storage_base
        server_mock.power_usage_effectiveness = SourceValue(1 * u.dimensionless)

        all_instance = create_source_hourly_values_from_list(all_instance_data, start_date)
        all_active = create_source_hourly_values_from_list(all_active_data, start_date)

        with (
            patch.object(self.storage_base, "contextual_modeling_obj_containers", new=[
                ContextualModelingObjectAttribute(self.storage_base, server_mock, "storage")]), \
            patch.object(self.storage_base, "nb_of_instances", all_instance), \
            patch.object(self.storage_base, "nb_of_active_instances", all_active), \
            patch.object(self.storage_base, "power", SourceValue(power_data)), \
            patch.object(self.storage_base, "idle_power", SourceValue(power_idle_data))):
            self.storage_base.update_instances_energy()

            self.assertEqual(u.kWh, self.storage_base.instances_energy.unit)
            self.assertTrue(np.allclose([0.15, 0.3, 0.45], self.storage_base.instances_energy.magnitude))

    def test_update_energy_footprint(self):
        instance_energy = create_source_hourly_values_from_list([0.9, 1.8, 2.7], pint_unit=u.kWh)
        server_mock = MagicMock(spec=Server)
        server_mock.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        server_mock.storage = self.storage_base
        self.storage_base.contextual_modeling_obj_containers = [
            ContextualModelingObjectAttribute(self.storage_base, server_mock, "storage")]

        expected_footprint = [0.09, 0.18, 0.27]  # in kg

        with patch.object(self.storage_base, "instances_energy", new=instance_energy), \
                patch.object(Storage, "server", new_callable=PropertyMock) as mock_property:
            mock_property.return_value = server_mock
            self.storage_base.update_energy_footprint()
            self.assertTrue(np.allclose(expected_footprint, self.storage_base.energy_footprint.magnitude))
            self.assertEqual(u.kg, self.storage_base.energy_footprint.unit)
