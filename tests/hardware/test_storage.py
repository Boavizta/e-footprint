from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from datetime import datetime

import numpy as np

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.job import Job
from tests.utils import initialize_explainable_object_dict_key


class TestStorage(TestCase):
    def setUp(self):
        self.storage_base = Storage(
            "storage_base",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(0 * u.kg/u.TB),
            lifespan=SourceValue(0 * u.years),
            storage_capacity=SourceValue(0 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(0 * u.dimensionless),
            data_storage_duration=SourceValue(0 * u.years),
            base_storage_need=SourceValue(0 * u.TB)
        )
        self.storage_base.trigger_modeling_updates = False

    def test_storage_with_two_servers_raises_error(self):
        """Test that associating a Storage with two servers raises PermissionError."""
        storage = self.storage_base
        server1 = MagicMock()
        server2 = MagicMock()
        with (patch.object(Storage, "modeling_obj_containers", new_callable=PropertyMock)
              as modeling_obj_containers_mock):
            modeling_obj_containers_mock.return_value = [server1, server2]
            with self.assertRaises(PermissionError):
                storage.server

    def test_update_full_cumulative_storage_need_per__job(self):
        """Test per-job cumulative for a positive job: cumsum(rate + auto_dumps) with replication."""
        # job stores [2, 4, 6] TB across time, replication=1, storage duration=1 hour
        # rate = [2, 4, 6] TB, auto_dumps = -shift([2, 4, 6], 1) = [0, -2, -4]
        # delta = [2, 2, 2], cumsum = [2, 4, 6]
        job = initialize_explainable_object_dict_key(MagicMock(spec=Job))
        job.name = "job1"
        job.id = "job1"
        job.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list(
            [2, 4, 6], pint_unit=u.TB)
        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(1 * u.dimensionless)), \
                patch.object(self.storage_base, "data_storage_duration", SourceValue(1 * u.hours)):
            jobs_mock.return_value = [job]
            self.storage_base.update_full_cumulative_storage_need_per_job()
            self.assertEqual([2, 4, 6], self.storage_base.full_cumulative_storage_need_per_job[job].value_as_float_list)

    def test_update_full_cumulative_storage_need_per_job_with_replication(self):
        """Test per-job cumulative applies data_replication_factor."""
        # rate = [1, 2, 3] * 3 (replication) = [3, 6, 9], storage_duration=5h (no dumps within 3h)
        # delta = [3, 6, 9], cumsum = [3, 9, 18]
        job = initialize_explainable_object_dict_key(MagicMock(spec=Job))
        job.data_stored = SourceValue(1 * u.TB)
        job.name = "job_replication"
        job.id = "job_replication"
        job.hourly_data_stored_across_usage_patterns = create_source_hourly_values_from_list(
            [1, 2, 3], pint_unit=u.TB)
        with patch.object(Storage, "jobs", new_callable=PropertyMock) as jobs_mock, \
                patch.object(self.storage_base, "data_replication_factor", SourceValue(3 * u.dimensionless)), \
                patch.object(self.storage_base, "data_storage_duration", SourceValue(5 * u.hours)):
            jobs_mock.return_value = [job]
            self.storage_base.update_full_cumulative_storage_need_per_job()
            self.assertEqual([3, 9, 18], self.storage_base.full_cumulative_storage_need_per_job[job].value_as_float_list)

    def test_update_full_cumulative_storage_need_from_per_job_dict(self):
        """Test full cumulative = sum(per-job cumulatives) + base_storage_need."""
        # per-job cumulatives: job1=[2, 0, 4, 1, 5], job2 =[1, 2, 3, 4, 5]
        # sum = [3, 2, 7, 5, 10], + base=5 → [8, 7, 12, 10, 15]
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        job1 = initialize_explainable_object_dict_key(MagicMock(spec=Job))
        job1.data_stored = SourceValue(1 * u.TB)
        job1.name = "positive_job"
        job1.id = "positive_job"
        job2 = initialize_explainable_object_dict_key(MagicMock(spec=Job))
        job2.data_stored = SourceValue(-1 * u.TB)
        job2.name = "negative_job"
        job2.id = "negative_job"
        per_job = ExplainableObjectDict({
            job1: create_source_hourly_values_from_list([2, 0, 4, 1, 5], start_date, pint_unit=u.TB),
            job2: create_source_hourly_values_from_list([1, 2, 3, 4, 5], start_date, pint_unit=u.TB),
        })
        with patch.object(self.storage_base, "full_cumulative_storage_need_per_job", per_job), \
                patch.object(self.storage_base, "base_storage_need", SourceValue(5 * u.TB)):
            self.storage_base.update_full_cumulative_storage_need()
            self.assertEqual([8, 7, 12, 10, 15], self.storage_base.full_cumulative_storage_need.value_as_float_list)

    def test_update_instances_energy_sets_empty_explainable_object(self):
        """Test that update_instances_energy sets instances_energy to EmptyExplainableObject."""
        self.storage_base.update_instances_energy()
        self.assertIsInstance(self.storage_base.instances_energy, EmptyExplainableObject)

    def test_raw_nb_of_instances(self):
        """Test raw_nb_of_instances = full_cumulative_storage_need / storage_capacity."""
        full_storage_data = create_source_hourly_values_from_list([10, 12, 14], pint_unit=u.TB)
        storage_capacity = SourceValue(2 * u.TB)

        with patch.object(self.storage_base, "full_cumulative_storage_need", full_storage_data), \
                patch.object(self.storage_base, "storage_capacity", storage_capacity):
            self.storage_base.update_raw_nb_of_instances()
            self.assertEqual([5, 6, 7], self.storage_base.raw_nb_of_instances.value_as_float_list)

    def test_nb_of_instances(self):
        """Test nb_of_instances = ceil(raw_nb_of_instances)."""
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.concurrent)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertEqual([2, 3, 4], self.storage_base.nb_of_instances.value_as_float_list)
            self.assertEqual(u.concurrent, self.storage_base.nb_of_instances.unit)

    def test_nb_of_instances_with_fixed_nb_of_instances(self):
        """Test nb_of_instances uses fixed_nb_of_instances when set and capacity is sufficient."""
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.concurrent)
        fixed_nb_of_instances = SourceValue(5 * u.dimensionless)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
            patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertEqual([5, 5, 5], self.storage_base.nb_of_instances.value_as_float_list)
            self.assertEqual(u.concurrent, self.storage_base.nb_of_instances.unit)

    def test_nb_of_instances_raises_error_if_fixed_number_of_instances_is_surpassed(self):
        """Test InsufficientCapacityError is raised when fixed_nb_of_instances is exceeded."""
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.concurrent)
        fixed_nb_of_instances = SourceValue(2 * u.concurrent)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
            patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            with self.assertRaises(InsufficientCapacityError) as context:
                self.storage_base.update_nb_of_instances()
            self.assertIn(
                "storage_base has available number of instances capacity of 2.0 concurrent but is asked for "
                "4.0 concurrent", str(context.exception))

    def test_nb_of_instances_returns_empty_explainable_object_if_raw_nb_of_instances_is_empty(self):
        """Test nb_of_instances is EmptyExplainableObject when raw_nb_of_instances is empty."""
        raw_nb_of_instances = EmptyExplainableObject()
        fixed_nb_of_instances = SourceValue(2 * u.concurrent)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
                patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances):
            self.storage_base.update_nb_of_instances()
            self.assertIsInstance(self.storage_base.nb_of_instances, EmptyExplainableObject)

    def test_update_energy_footprint(self):
        """Test energy_footprint = instances_energy * average_carbon_intensity."""
        instance_energy = create_source_hourly_values_from_list([0.9, 1.8, 2.7], pint_unit=u.kWh)
        server_mock = MagicMock(spec=Server)
        server_mock.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        server_mock.storage = self.storage_base
        self.storage_base.contextual_modeling_obj_containers = [
            ContextualModelingObjectAttribute(self.storage_base, server_mock, "storage")]

        with patch.object(self.storage_base, "instances_energy", new=instance_energy), \
                patch.object(Storage, "server", new_callable=PropertyMock) as mock_property:
            mock_property.return_value = server_mock
            self.storage_base.update_energy_footprint()
            self.assertTrue(np.allclose([0.09, 0.18, 0.27], self.storage_base.energy_footprint.magnitude))
            self.assertEqual(u.kg, self.storage_base.energy_footprint.unit)
