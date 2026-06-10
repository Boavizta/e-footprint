from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.constants.sources import Sources
from efootprint.core.attribution import atoms_of
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job, JobBase
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import (
    assert_hourly_quantities_equal, assert_source_atoms_conserve, sum_atom_values)
from tests.utils import create_mod_obj_mock


class TestNetwork(TestCase):
    def setUp(self):
        self.network = Network("Wifi network", SourceValue(0 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
        self.network.trigger_modeling_updates = False

    def test_update_energy_footprint_per_job_uses_country_weighted_network_energy(self):
        usage_pattern_fr = create_mod_obj_mock(UsagePattern, name="Usage Pattern FR")
        usage_pattern_fr.country = MagicMock()
        usage_pattern_fr.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_us = create_mod_obj_mock(UsagePattern, name="Usage Pattern US")
        usage_pattern_us.country = MagicMock()
        usage_pattern_us.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)
        usage_pattern_ignored = create_mod_obj_mock(UsagePattern, name="Usage Pattern Ignored")
        usage_pattern_ignored.country = MagicMock()
        usage_pattern_ignored.country.average_carbon_intensity = SourceValue(500 * u.g / u.kWh)

        job_1 = create_mod_obj_mock(JobBase, name="Job 1")
        job_1.usage_patterns = [usage_pattern_fr]
        job_1.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_fr: create_source_hourly_values_from_list([2], pint_unit=u.GB)
        }
        job_2 = create_mod_obj_mock(JobBase, name="Job 2")
        job_2.usage_patterns = [usage_pattern_fr, usage_pattern_us, usage_pattern_ignored]
        job_2.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_fr: create_source_hourly_values_from_list([1], pint_unit=u.GB),
            usage_pattern_us: create_source_hourly_values_from_list([2], pint_unit=u.GB),
            usage_pattern_ignored: create_source_hourly_values_from_list([10], pint_unit=u.GB),
        }
        usage_pattern_fr.jobs = [job_1, job_2]
        usage_pattern_us.jobs = [job_2]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups, \
                patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_ups.return_value = [usage_pattern_fr, usage_pattern_us]

            self.network.update_energy_footprint_per_job()

        self.assertTrue(np.allclose([0.2], self.network.energy_footprint_per_job[job_1].magnitude))
        self.assertTrue(np.allclose([0.5], self.network.energy_footprint_per_job[job_2].magnitude))
        self.assertEqual(u.kg, self.network.energy_footprint_per_job[job_1].unit)

    def test_energy_footprint_for_data_volume_and_usage_pattern_applies_intensity_and_carbon_intensity(self):
        """Test the data→carbon physics fn: bandwidth energy intensity × data volume × the pattern's CI."""
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Physics fn usage pattern")
        usage_pattern.country = MagicMock()
        usage_pattern.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        data_volume = create_source_hourly_values_from_list([2, 4], pint_unit=u.GB)

        with patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            footprint = self.network.energy_footprint_for_data_volume_and_usage_pattern(
                data_volume, usage_pattern).to(u.kg)

        # 1 kWh/GB × [2, 4] GB × 100 g/kWh = [0.2, 0.4] kg
        self.assertTrue(np.allclose([0.2, 0.4], footprint.magnitude))

    def test_compute_energy_footprint_for_job_and_usage_pattern_delegates_to_physics_fn(self):
        """Test the per-job method reproduces the physics fn applied to the job's per-pattern data volume."""
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Thin caller usage pattern")
        usage_pattern.country = MagicMock()
        usage_pattern.country.average_carbon_intensity = SourceValue(150 * u.g / u.kWh)
        job = create_mod_obj_mock(JobBase, name="Thin caller job")
        job_data = create_source_hourly_values_from_list([3, 1], pint_unit=u.GB)
        job.hourly_data_transferred_per_usage_pattern = {usage_pattern: job_data}

        with patch.object(self.network, "bandwidth_energy_intensity", SourceValue(0.5 * u.kWh / u.GB)):
            per_job_footprint = self.network._compute_energy_footprint_for_job_and_usage_pattern(
                job, usage_pattern).to(u.kg)
            physics_fn_footprint = self.network.energy_footprint_for_data_volume_and_usage_pattern(
                job_data, usage_pattern).to(u.kg)

        self.assertTrue(np.allclose(physics_fn_footprint.magnitude, per_job_footprint.magnitude))

    def test_energy_footprint_per_usage_pattern_uses_country_weighted_network_energy(self):
        """Test per-usage-pattern energy footprint sums each pattern's jobs weighted by its country's carbon intensity."""
        usage_pattern_fr = create_mod_obj_mock(UsagePattern, name="Usage Pattern FR")
        usage_pattern_fr.country = MagicMock()
        usage_pattern_fr.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_us = create_mod_obj_mock(UsagePattern, name="Usage Pattern US")
        usage_pattern_us.country = MagicMock()
        usage_pattern_us.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)

        job_1 = create_mod_obj_mock(JobBase, name="Job 1")
        job_1.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_fr: create_source_hourly_values_from_list([2], pint_unit=u.GB),
            usage_pattern_us: create_source_hourly_values_from_list([1], pint_unit=u.GB),
        }
        job_2 = create_mod_obj_mock(JobBase, name="Job 2")
        job_2.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_fr: create_source_hourly_values_from_list([3], pint_unit=u.GB),
        }
        usage_pattern_fr.jobs = [job_1, job_2]
        usage_pattern_us.jobs = [job_1]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups, \
                patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_ups.return_value = [usage_pattern_fr, usage_pattern_us]

            energy_footprint_per_usage_pattern = self.network.energy_footprint_per_usage_pattern

        self.assertTrue(np.allclose([0.5], energy_footprint_per_usage_pattern[usage_pattern_fr].magnitude))
        self.assertTrue(np.allclose([0.2], energy_footprint_per_usage_pattern[usage_pattern_us].magnitude))
        self.assertEqual(u.kg, energy_footprint_per_usage_pattern[usage_pattern_fr].unit)

    def test_update_energy_footprint_sums_precomputed_per_job_values(self):
        job_1 = create_mod_obj_mock(JobBase, name="Job 1")
        job_2 = create_mod_obj_mock(JobBase, name="Job 2")
        self.network.energy_footprint_per_job = ExplainableObjectDict({
            job_1: create_source_hourly_values_from_list([0.2, 0.4], pint_unit=u.kg),
            job_2: create_source_hourly_values_from_list([0.3, 0.1], pint_unit=u.kg),
        })

        self.network.update_energy_footprint()

        self.assertEqual(u.kg, self.network.energy_footprint.unit)
        self.assertTrue(np.allclose([0.5, 0.5], self.network.energy_footprint.magnitude))

    def test_update_fabrication_impact_repartition_weights_returns_empty_dict_without_fabrication_footprint(self):
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Usage Pattern")
        job_1 = create_mod_obj_mock(JobBase, name="Job 1")
        job_2 = create_mod_obj_mock(JobBase, name="Job 2")
        usage_pattern.jobs = [job_1, job_2]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups:
            mock_ups.return_value = [usage_pattern]

            self.network.update_fabrication_impact_repartition_weights()

        self.assertEqual({}, self.network.fabrication_impact_repartition_weights)

    def test_update_fabrication_impact_repartition_weights_raises_if_network_fabrication_is_added_without_logic(self):
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Usage Pattern")
        job = create_mod_obj_mock(JobBase, name="Job 1")
        usage_pattern.jobs = [job]
        self.network.instances_fabrication_footprint = SourceValue(1 * u.kg)

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups:
            mock_ups.return_value = [usage_pattern]

            with self.assertRaises(NotImplementedError):
                self.network.update_fabrication_impact_repartition_weights()

    def test_usage_impact_repartition_weights_reuses_energy_footprint_per_job(self):
        job = create_mod_obj_mock(JobBase, name="Job 1")
        self.network.energy_footprint_per_job = ExplainableObjectDict({
            job: create_source_hourly_values_from_list([0.2], pint_unit=u.kg)
        })

        self.assertIs(self.network.energy_footprint_per_job, self.network.usage_impact_repartition_weights)


class TestNetworkAttributionAtoms(TestCase):
    """Network atom builder on a real model with web + edge cells: conservation against the eager totals and
    per-pattern dicts, with CI[up] carried inside each cell (two patterns with different carbon intensities
    never blend)."""

    @classmethod
    def setUpClass(cls):
        def country(name, carbon_intensity):
            return Country(name, name[:3].upper(), SourceValue(carbon_intensity),
                           ExplainableTimezone(pytz.utc, "UTC timezone"))

        cls.network = Network("network atoms network", SourceValue(0.05 * u.kWh / u.GB))
        server = Server.from_defaults(
            "network atoms server", storage=Storage.from_defaults("network atoms storage"))
        cls.dual_job = Job.from_defaults(
            "network atoms dual side job", server=server, data_transferred=SourceValue(1 * u.GB))
        cls.step = UsageJourneyStep("network atoms step", SourceValue(30 * u.min), [cls.dual_job])
        cls.journey = UsageJourney("network atoms journey", [cls.step])

        device = Device.from_defaults("network atoms laptop")
        start_date = datetime(2026, 1, 1)
        identical_traffic = [6, 2]
        cls.low_ci_up = UsagePattern(
            "network atoms low ci pattern", cls.journey, [device], cls.network,
            country("network atoms low ci country", 50 * u.g / u.kWh),
            create_source_hourly_values_from_list(identical_traffic, start_date))
        cls.high_ci_up = UsagePattern(
            "network atoms high ci pattern", cls.journey, [device], cls.network,
            country("network atoms high ci country", 500 * u.g / u.kWh),
            create_source_hourly_values_from_list(identical_traffic, start_date))

        workload_component = EdgeWorkloadComponent.from_defaults("network atoms workload component")
        edge_device = EdgeDevice.from_defaults("network atoms edge device", components=[workload_component])
        component_need = RecurrentEdgeComponentNeed(
            "network atoms workload need", workload_component,
            SourceRecurrentValues(Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent)))
        device_need = RecurrentEdgeDeviceNeed("network atoms device need", edge_device, [component_need])
        cls.rsn = RecurrentServerNeed(
            "network atoms recurrent server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([2.0] * 168, dtype=np.float32), u.occurrence)),
            [cls.dual_job])
        edge_function = EdgeFunction("network atoms edge function", [device_need], [cls.rsn])
        edge_journey = EdgeUsageJourney(
            "network atoms edge journey", [edge_function], usage_span=SourceValue(1 * u.year))
        cls.edge_up = EdgeUsagePattern(
            "network atoms edge usage pattern", edge_journey, cls.network,
            country("network atoms edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([4, 0, 6], start_date))

        cls.system = System(
            "network atoms system", [cls.low_ci_up, cls.high_ci_up], edge_usage_patterns=[cls.edge_up])

    def test_network_atoms_conserve(self):
        """Test that Σ atoms recovers the eager energy footprint (and the empty fabrication total)."""
        assert_source_atoms_conserve(self, self.network)

    def test_network_atoms_regroup_per_usage_pattern(self):
        """Test that Σ atoms over each pattern's cells recovers energy_footprint_per_usage_pattern."""
        usage_atoms = list(atoms_of(self.network, LifeCyclePhases.USAGE))
        for usage_pattern in (self.low_ci_up, self.high_ci_up, self.edge_up):
            assert_hourly_quantities_equal(
                self, self.network.energy_footprint_per_usage_pattern[usage_pattern],
                sum_atom_values(atom for atom in usage_atoms if atom.up == usage_pattern))

    def test_per_cell_carbon_intensity_never_blended(self):
        """Test that two patterns with identical traffic but a ×10 carbon-intensity ratio carry a ×10 atom
        ratio — each cell converts its own data volume with its own pattern's CI."""
        usage_atoms = list(atoms_of(self.network, LifeCyclePhases.USAGE))
        low_ci_sum = sum_atom_values(atom for atom in usage_atoms if atom.up == self.low_ci_up)
        high_ci_sum = sum_atom_values(atom for atom in usage_atoms if atom.up == self.high_ci_up)
        self.assertGreater(low_ci_sum.sum().magnitude, 0)
        self.assertTrue(np.allclose(10 * low_ci_sum.magnitude, high_ci_sum.magnitude))

    def test_edge_cells_carry_rsn_and_ef_coordinates(self):
        """Test that the dual-side job's edge atoms surface at the (rsn, ef) cell with nonzero value."""
        edge_atoms = [atom for atom in atoms_of(self.network, LifeCyclePhases.USAGE)
                      if atom.up == self.edge_up]
        self.assertTrue(edge_atoms)
        for atom in edge_atoms:
            self.assertIsNone(atom.step)
            self.assertEqual(self.rsn.id, atom.rsn.id)
            self.assertIsNotNone(atom.ef)
        self.assertGreater(sum_atom_values(edge_atoms).sum().magnitude, 0)
