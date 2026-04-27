from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from datetime import datetime

import numpy as np

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.job import Job
from tests.utils import create_mod_obj_mock


class TestStorage(TestCase):
    def setUp(self):
        self.storage_base = Storage(
            "storage_base",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(0 * u.kg/u.TB_stored),
            lifespan=SourceValue(0 * u.years),
            storage_capacity=SourceValue(0 * u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            data_replication_factor=SourceValue(0 * u.dimensionless),
            data_storage_duration=SourceValue(0 * u.years),
            base_storage_need=SourceValue(0 * u.TB_stored)
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
        job = create_mod_obj_mock(
            Job, name="job1", hourly_data_stored_across_usage_patterns=create_source_hourly_values_from_list([2, 4, 6], pint_unit=u.TB_stored)
        )
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
        job = create_mod_obj_mock(
            Job,
            name="job_replication",
            data_stored=SourceValue(1 * u.TB_stored),
            hourly_data_stored_across_usage_patterns=create_source_hourly_values_from_list([1, 2, 3], pint_unit=u.TB_stored),
        )
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
        job1 = create_mod_obj_mock(Job, name="positive_job", data_stored=SourceValue(1 * u.TB_stored))
        job2 = create_mod_obj_mock(Job, name="negative_job", data_stored=SourceValue(-1 * u.TB_stored))
        per_job = ExplainableObjectDict({
            job1: create_source_hourly_values_from_list([2, 0, 4, 1, 5], start_date, pint_unit=u.TB_stored),
            job2: create_source_hourly_values_from_list([1, 2, 3, 4, 5], start_date, pint_unit=u.TB_stored),
        })
        with patch.object(self.storage_base, "full_cumulative_storage_need_per_job", per_job), \
                patch.object(self.storage_base, "base_storage_need", SourceValue(5 * u.TB_stored)):
            self.storage_base.update_full_cumulative_storage_need()
            self.assertEqual([8, 7, 12, 10, 15], self.storage_base.full_cumulative_storage_need.value_as_float_list)

    def test_update_instances_energy_sets_empty_explainable_object(self):
        """Test that update_instances_energy sets instances_energy to EmptyExplainableObject."""
        self.storage_base.update_instances_energy()
        self.assertIsInstance(self.storage_base.instances_energy, EmptyExplainableObject)

    def test_raw_nb_of_instances(self):
        """Test raw_nb_of_instances = full_cumulative_storage_need / storage_capacity."""
        full_storage_data = create_source_hourly_values_from_list([10, 12, 14], pint_unit=u.TB_stored)
        storage_capacity = SourceValue(2 * u.TB_stored)

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

    def test_nb_of_instances_serverless_uses_raw_nb_of_instances(self):
        """Test nb_of_instances equals raw_nb_of_instances (no ceiling) when server is serverless."""
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.concurrent)
        server_mock = create_mod_obj_mock(Server, "Serverless server", server_type=ServerTypes.serverless())

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
                patch.object(Storage, "server", new_callable=PropertyMock) as mock_server:
            mock_server.return_value = server_mock
            self.storage_base.update_nb_of_instances()
            self.assertEqual([1.5, 2.5, 3.5], self.storage_base.nb_of_instances.value_as_float_list)
            self.assertEqual(u.concurrent, self.storage_base.nb_of_instances.unit)

    def test_nb_of_instances_serverless_ignores_fixed_nb_of_instances(self):
        """Test nb_of_instances ignores fixed_nb_of_instances when server is serverless."""
        raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 2.5, 3.5], pint_unit=u.concurrent)
        server_mock = create_mod_obj_mock(Server, "Serverless server", server_type=ServerTypes.serverless())
        fixed_nb_of_instances = SourceValue(5 * u.dimensionless)

        with patch.object(self.storage_base, "raw_nb_of_instances", raw_nb_of_instances), \
                patch.object(self.storage_base, "fixed_nb_of_instances", fixed_nb_of_instances), \
                patch.object(Storage, "server", new_callable=PropertyMock) as mock_server:
            mock_server.return_value = server_mock
            self.storage_base.update_nb_of_instances()
            self.assertEqual([1.5, 2.5, 3.5], self.storage_base.nb_of_instances.value_as_float_list)

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
        server_mock = create_mod_obj_mock(
            Server, "Server", average_carbon_intensity=SourceValue(100 * u.g / u.kWh), storage=self.storage_base)
        self.storage_base.contextual_modeling_obj_containers = [
            ContextualModelingObjectAttribute(self.storage_base, server_mock, "storage")]

        with patch.object(self.storage_base, "instances_energy", new=instance_energy), \
                patch.object(Storage, "server", new_callable=PropertyMock) as mock_property:
            mock_property.return_value = server_mock
            self.storage_base.update_energy_footprint()
            self.assertTrue(np.allclose([0.09, 0.18, 0.27], self.storage_base.energy_footprint.magnitude))
            self.assertEqual(u.kg, self.storage_base.energy_footprint.unit)

    def test_update_fabrication_impact_repartition_weights_shares_unused_and_base_storage_equally(self):
        """Test fabrication weights add equal unused/base storage share on top of each job cumulative need."""
        job_1 = create_mod_obj_mock(Job, name="Job 1")
        job_2 = create_mod_obj_mock(Job, name="Job 2")

        with patch.object(Storage, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = [job_1, job_2]
            self.storage_base.full_cumulative_storage_need_per_job = ExplainableObjectDict({
                job_1: create_source_hourly_values_from_list([2], pint_unit=u.TB_stored),
                job_2: create_source_hourly_values_from_list([4], pint_unit=u.TB_stored),
            })
            self.storage_base.full_cumulative_storage_need = create_source_hourly_values_from_list([8], pint_unit=u.TB_stored)
            self.storage_base.nb_of_instances = create_source_hourly_values_from_list([5], pint_unit=u.concurrent)
            self.storage_base.storage_capacity = SourceValue(2 * u.TB_stored)
            self.storage_base.base_storage_need = SourceValue(2 * u.TB_stored)

            self.storage_base.update_fabrication_impact_repartition_weights()

        # full cumulative = 8 TB (including 2 TB base), total provisioned = 10 TB, unused = 2 TB, shared = 2 TB/job
        self.assertTrue(np.allclose([4], self.storage_base.fabrication_impact_repartition_weights[job_1].magnitude))
        self.assertTrue(np.allclose([6], self.storage_base.fabrication_impact_repartition_weights[job_2].magnitude))
        self.assertEqual(u.TB_stored, self.storage_base.fabrication_impact_repartition_weights[job_1].unit)

    def test_usage_impact_repartition_weights_returns_empty_dict_when_energy_is_empty(self):
        """Test storage usage repartition weights are empty while storage energy footprint is empty."""
        self.storage_base.energy_footprint = EmptyExplainableObject()

        self.assertEqual({}, self.storage_base.usage_impact_repartition_weights)

    def test_usage_impact_repartition_weights_raises_when_energy_logic_is_missing(self):
        """Test storage usage repartition raises error if a non-empty energy footprint exists without attribution logic."""
        self.storage_base.energy_footprint = SourceValue(1 * u.kg)

        with self.assertRaises(NotImplementedError):
            _ = self.storage_base.usage_impact_repartition_weights
