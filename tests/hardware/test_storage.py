from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from datetime import datetime

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.constants.units import u
from efootprint.core.attribution import atoms_of
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage, cumulative_storage_need_with_dumps
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import (
    assert_hourly_quantities_equal, assert_source_atoms_conserve, sum_atom_values)
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

            self.storage_base.update_shared_storage_per_job()
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


class TestCumulativeStorageNeedWithDumps(TestCase):
    def test_cumulative_storage_need_with_dumps_drops_data_after_storage_duration(self):
        """Test data written at hour h is dumped at h + data_storage_duration."""
        # rate = [2, 0, 0, 0] TB, duration 2h: delta = [2, 0, -2, 0], cumulative = [2, 2, 0, 0]
        rate = create_source_hourly_values_from_list([2, 0, 0, 0], pint_unit=u.TB_stored)

        cumulative = cumulative_storage_need_with_dumps(rate, SourceValue(2 * u.hours))

        self.assertEqual([2, 2, 0, 0], cumulative.value_as_float_list)

    def test_cumulative_storage_need_with_dumps_is_linear(self):
        """Test cumsum-with-dumps of a sum of rates equals the sum of per-rate cumulatives — the linearity
        that makes per-cell retention cumulatives sum exactly to per-job cumulatives."""
        rate_a = create_source_hourly_values_from_list([2, 0, 1, 0], pint_unit=u.TB_stored)
        rate_b = create_source_hourly_values_from_list([0, 3, 0, 0], pint_unit=u.TB_stored)
        duration = SourceValue(2 * u.hours)

        summed_cumulatives = (cumulative_storage_need_with_dumps(rate_a, duration)
                              + cumulative_storage_need_with_dumps(rate_b, duration))
        cumulative_of_sum = cumulative_storage_need_with_dumps(rate_a + rate_b, duration)

        # cum(a) = [2, 2, 1, 1], cum(b) = [0, 3, 3, 0], cum(a + b) = [2, 5, 4, 1]
        self.assertEqual([2, 5, 4, 1], cumulative_of_sum.value_as_float_list)
        self.assertTrue(np.allclose(cumulative_of_sum.magnitude, summed_cumulatives.magnitude))

    def test_cumulative_storage_need_with_dumps_returns_empty_for_empty_rate(self):
        """Test an empty storage rate yields an EmptyExplainableObject cumulative."""
        self.assertIsInstance(
            cumulative_storage_need_with_dumps(EmptyExplainableObject(), SourceValue(2 * u.hours)),
            EmptyExplainableObject)


class TestStorageAttributionAtoms(TestCase):
    """Storage atom builder on a real model with web + edge writes: the retention / baseline stream split
    sums to the fabrication footprint exactly, each stream conserves through its own weights, and the
    per-cell retention cumulatives sum to the per-job cumulative (cumsum linearity)."""

    @classmethod
    def setUpClass(cls):
        def country(name, carbon_intensity):
            return Country(name, name[:3].upper(), SourceValue(carbon_intensity),
                           ExplainableTimezone(pytz.utc, "UTC timezone"))

        cls.storage = Storage.from_defaults(
            "storage atoms storage", base_storage_need=SourceValue(0.5 * u.TB_stored))
        cls.server = Server.from_defaults("storage atoms server", storage=cls.storage)
        cls.dual_job = Job.from_defaults(
            "storage atoms dual side job", server=cls.server, data_stored=SourceValue(2 * u.GB_stored),
            request_duration=SourceValue(30 * u.min))
        cls.web_only_job = Job.from_defaults(
            "storage atoms web only job", server=cls.server, data_stored=SourceValue(0.5 * u.GB_stored))

        cls.step_a = UsageJourneyStep("storage atoms step a", SourceValue(30 * u.min),
                                      [cls.dual_job, cls.web_only_job])
        cls.step_b = UsageJourneyStep("storage atoms step b", SourceValue(1 * u.hour), [cls.dual_job])
        cls.journey = UsageJourney("storage atoms journey", [cls.step_a, cls.step_b])

        device = Device.from_defaults("storage atoms laptop")
        network = Network("storage atoms network", SourceValue(0.05 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        cls.up1 = UsagePattern(
            "storage atoms web usage pattern 1", cls.journey, [device], network,
            country("storage atoms first country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([10, 0, 5, 0, 8], start_date))
        cls.up2 = UsagePattern(
            "storage atoms web usage pattern 2", cls.journey, [device], network,
            country("storage atoms second country", 300 * u.g / u.kWh),
            create_source_hourly_values_from_list([3, 7], start_date))

        workload_component = EdgeWorkloadComponent.from_defaults("storage atoms workload component")
        edge_device = EdgeDevice.from_defaults("storage atoms edge device", components=[workload_component])
        component_need = RecurrentEdgeComponentNeed(
            "storage atoms workload need", workload_component,
            SourceRecurrentValues(Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent)))
        device_need = RecurrentEdgeDeviceNeed("storage atoms device need", edge_device, [component_need])
        cls.rsn = RecurrentServerNeed(
            "storage atoms recurrent server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([2.0] * 168, dtype=np.float32), u.occurrence)),
            [cls.dual_job])
        edge_function = EdgeFunction("storage atoms edge function", [device_need], [cls.rsn])
        edge_journey = EdgeUsageJourney(
            "storage atoms edge journey", [edge_function], usage_span=SourceValue(1 * u.year))
        cls.edge_up = EdgeUsagePattern(
            "storage atoms edge usage pattern", edge_journey, network,
            country("storage atoms edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([4, 0, 6], start_date))

        cls.system = System(
            "storage atoms system", [cls.up1, cls.up2], edge_usage_patterns=[cls.edge_up])

    def test_storage_streams_sum_to_fabrication_footprint_exactly(self):
        """Test retention + baseline == instances_fabrication_footprint (nb_of_instances cancels in each)."""
        assert_hourly_quantities_equal(
            self, self.storage.instances_fabrication_footprint,
            self.storage.storage_retention_fabrication_footprint
            + self.storage.storage_baseline_fabrication_footprint)

    def test_storage_atoms_conserve_per_stream(self):
        """Test that Σ atoms recovers the eager fabrication total and that each stream conserves its own
        footprint (retention over per-cell cumulative / N weights, baseline over flat occurrence shares)."""
        assert_source_atoms_conserve(
            self, self.storage,
            stream_footprints_by_phase={
                LifeCyclePhases.MANUFACTURING: {
                    "retention": self.storage.storage_retention_fabrication_footprint,
                    "baseline": self.storage.storage_baseline_fabrication_footprint}})

    def test_per_cell_retention_cumulatives_sum_to_per_job_cumulative(self):
        """Test cumsum linearity on the real model: Σ over a job's cells of the per-cell cumulatives equals
        full_cumulative_storage_need_per_job, web + edge cells included."""
        for job in (self.dual_job, self.web_only_job):
            assert_hourly_quantities_equal(
                self, self.storage.full_cumulative_storage_need_per_job[job],
                sum((self.storage.retention_cumulative_per_cell[cell] for cell in job.attribution_cells),
                    start=EmptyExplainableObject()))

    def test_retention_conserves_across_web_and_edge_writes(self):
        """Test that the dual-side job's retention atoms carry nonzero mass on both the web steps and the
        edge recurrent server need (a storage written from both sides never lands 100% web-side)."""
        retention_atoms = [atom for atom in atoms_of(self.storage, LifeCyclePhases.MANUFACTURING)
                           if atom.stream == "retention" and atom.job == self.dual_job]
        web_sum = sum_atom_values(atom for atom in retention_atoms if atom.step is not None)
        edge_sum = sum_atom_values(atom for atom in retention_atoms if atom.rsn is not None)
        self.assertGreater(web_sum.sum().magnitude, 0)
        self.assertGreater(edge_sum.sum().magnitude, 0)

    def test_baseline_flat_shares_carry_footprint_at_idle_hours(self):
        """Test the fallback-0/1 fix: at an hour with zero job occurrences the baseline stream is nonzero
        (storage instances are on 24/7) and Σ baseline atoms recovers it — an hourly occurrence ratio would
        be 0/0 there, where fallback 0 drops the footprint and fallback 1 books it once per cell."""
        storage = Storage.from_defaults("idle hours storage", base_storage_need=SourceValue(1 * u.TB_stored))
        server = Server.from_defaults("idle hours storage server", storage=storage)
        job = Job.from_defaults(
            "idle hours storage job", server=server, data_stored=SourceValue(1 * u.GB_stored),
            request_duration=SourceValue(10 * u.min))
        step = UsageJourneyStep("idle hours storage step", SourceValue(30 * u.min), [job])
        journey = UsageJourney("idle hours storage journey", [step])
        up = UsagePattern(
            "idle hours storage usage pattern", journey, [Device.from_defaults("idle hours storage laptop")],
            Network("idle hours storage network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("idle hours storage country", "IHS", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([4, 0, 0, 0, 0, 0], datetime(2026, 1, 1)))
        System("idle hours storage system", [up], edge_usage_patterns=[])

        idle_hour = 5
        self.assertEqual(0, np.append(
            job.hourly_avg_occurrences_across_usage_patterns.magnitude, np.zeros(6))[idle_hour])
        baseline_footprint = storage.storage_baseline_fabrication_footprint
        self.assertGreater(baseline_footprint.magnitude[idle_hour], 0)
        baseline_atoms_sum = sum_atom_values(
            atom for atom in atoms_of(storage, LifeCyclePhases.MANUFACTURING) if atom.stream == "baseline")
        self.assertAlmostEqual(
            baseline_footprint.magnitude[idle_hour], baseline_atoms_sum.magnitude[idle_hour], places=6)

    def test_baseline_equal_share_fallback_conserves_on_zero_traffic_model(self):
        """Test the zero-traffic fallback: with all-zero journey starts and a nonzero base_storage_need the
        fabrication footprint is nonzero, baseline job weights fall back to equal shares summing to 1 and the
        baseline atoms (the only nonzero stream) still conserve the fabrication footprint."""
        storage = Storage.from_defaults("zero traffic storage", base_storage_need=SourceValue(1 * u.TB_stored))
        server = Server.from_defaults("zero traffic storage server", storage=storage)
        job_a = Job.from_defaults(
            "zero traffic storage job a", server=server, data_stored=SourceValue(1 * u.GB_stored))
        job_b = Job.from_defaults(
            "zero traffic storage job b", server=server, data_stored=SourceValue(2 * u.GB_stored))
        step = UsageJourneyStep("zero traffic storage step", SourceValue(30 * u.min), [job_a, job_b])
        journey = UsageJourney("zero traffic storage journey", [step])
        up = UsagePattern(
            "zero traffic storage usage pattern", journey,
            [Device.from_defaults("zero traffic storage laptop")],
            Network("zero traffic storage network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("zero traffic storage country", "ZTS", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([0, 0, 0], datetime(2026, 1, 1)))
        System("zero traffic storage system", [up], edge_usage_patterns=[])

        self.assertGreater(storage.instances_fabrication_footprint.sum().magnitude, 0)
        shares = storage.baseline_flat_share_per_job
        self.assertEqual([0.5, 0.5], [shares[job].magnitude for job in (job_a, job_b)])
        assert_source_atoms_conserve(
            self, storage,
            stream_footprints_by_phase={
                LifeCyclePhases.MANUFACTURING: {
                    "retention": storage.storage_retention_fabrication_footprint,
                    "baseline": storage.storage_baseline_fabrication_footprint}})

    def test_edge_storage_is_not_an_attribution_source(self):
        """Test the EdgeStorage-on-device distinction stays untouched: EdgeStorage is an EdgeComponent, not a
        Storage, and does not implement the atom contract (RecurrentEdgeStorageNeed is the EdgeDevice
        builder's territory)."""
        self.assertFalse(hasattr(EdgeStorage, "attribution_atoms"))
