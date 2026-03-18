from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.constants.sources import Sources
from efootprint.core.hardware.network import Network
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.usage.job import JobBase
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.utils import create_mod_obj_mock


class TestNetwork(TestCase):
    def setUp(self):
        self.network = Network("Wifi network", SourceValue(0 * u("kWh/GB"), Sources.TRAFICOM_STUDY))
        self.network.trigger_modeling_updates = False

    def test_update_energy_footprint_simple_case(self):
        usage_pattern = MagicMock()
        usage_pattern.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)

        job1 = MagicMock()
        job1.hourly_data_transferred_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([2, 4, 10], pint_unit=u.GB)}
        job1.usage_patterns = [usage_pattern]

        with patch.object(Network, "jobs", new_callable=PropertyMock) as mock_jobs,\
            patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups,\
            patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_jobs.return_value = [job1]
            mock_ups.return_value = [usage_pattern]
            self.network.update_energy_footprint()

            self.assertEqual(u.kg, self.network.energy_footprint.unit)
            self.assertTrue(np.allclose([0.2, 0.4, 1], self.network.energy_footprint.magnitude))

    def test_update_energy_footprint_job_with_no_up(self):
        job = MagicMock()
        job.usage_patterns = []

        with patch.object(Network, "jobs", new_callable=PropertyMock) as mock_jobs, \
                patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups, \
                patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_jobs.return_value = [job]
            mock_ups.return_value = []
            self.network.update_energy_footprint()

            self.assertEqual(0, self.network.energy_footprint)

    def test_update_energy_footprint_complex_case(self):
        usage_pattern = MagicMock()
        usage_pattern.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)

        job1 = MagicMock()
        job1.hourly_data_transferred_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([2, 4, 10], pint_unit=u.GB)}
        job1.usage_patterns = [usage_pattern]

        usage_pattern2 = MagicMock()
        usage_pattern2.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern3 = MagicMock()
        job2 = MagicMock()
        job2.hourly_data_transferred_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([2, 4, 10], pint_unit=u.GB),
            usage_pattern2: create_source_hourly_values_from_list([2, 4, 10], pint_unit=u.GB),
            # Should be ignored in the calculation as usage_pattern3 will not be linked to the network
            usage_pattern3: create_source_hourly_values_from_list([2, 4, 10], pint_unit=u.GB)}
        job2.usage_patterns = [usage_pattern, usage_pattern2, usage_pattern3]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups, \
                patch.object(Network, "jobs", new_callable=PropertyMock) as mock_jobs, \
                patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_ups.return_value = [usage_pattern, usage_pattern2]
            mock_jobs.return_value = [job1, job2]
            self.network.update_energy_footprint()

            self.assertEqual(u.kg, self.network.energy_footprint.unit)
            self.assertTrue(np.allclose([0.6, 1.2, 3], self.network.energy_footprint.magnitude))

    def test_update_fabrication_impact_repartition_weights_uses_job_data_transferred_and_hourly_occurrences(self):
        usage_pattern = create_mod_obj_mock(UsagePattern, name="Usage Pattern")
        job_1 = create_mod_obj_mock(
            JobBase, name="Job 1",
            data_transferred=SourceValue(2 * u.dimensionless),
            hourly_avg_occurrences_across_usage_patterns=SourceValue(3 * u.concurrent))
        job_2 = create_mod_obj_mock(
            JobBase, name="Job 2",
            data_transferred=SourceValue(4 * u.dimensionless),
            hourly_avg_occurrences_across_usage_patterns=SourceValue(1 * u.concurrent))
        usage_pattern.jobs = [job_1, job_2]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups:
            mock_ups.return_value = [usage_pattern]

            self.network.update_fabrication_impact_repartition_weights()

        self.assertEqual(6, self.network.fabrication_impact_repartition_weights[job_1].magnitude)
        self.assertEqual(4, self.network.fabrication_impact_repartition_weights[job_2].magnitude)
        self.assertEqual(u.concurrent, self.network.fabrication_impact_repartition_weights[job_1].unit)

    def test_update_usage_impact_repartition_weights_uses_country_weighted_network_energy(self):
        usage_pattern_fr = create_mod_obj_mock(UsagePattern, name="Usage Pattern FR")
        usage_pattern_fr.country = MagicMock()
        usage_pattern_fr.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_us = create_mod_obj_mock(UsagePattern, name="Usage Pattern US")
        usage_pattern_us.country = MagicMock()
        usage_pattern_us.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)

        job_1 = create_mod_obj_mock(JobBase, name="Job 1")
        job_1.usage_patterns = [usage_pattern_fr]
        job_1.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_fr: create_source_hourly_values_from_list([2], pint_unit=u.GB)
        }
        job_2 = create_mod_obj_mock(JobBase, name="Job 2")
        job_2.usage_patterns = [usage_pattern_us]
        job_2.hourly_data_transferred_per_usage_pattern = {
            usage_pattern_us: create_source_hourly_values_from_list([2], pint_unit=u.GB)
        }
        usage_pattern_fr.jobs = [job_1]
        usage_pattern_us.jobs = [job_2]

        with patch.object(Network, "usage_patterns", new_callable=PropertyMock) as mock_ups, \
                patch.object(self.network, "bandwidth_energy_intensity", SourceValue(1 * u.kWh / u.GB)):
            mock_ups.return_value = [usage_pattern_fr, usage_pattern_us]

            self.network.update_usage_impact_repartition_weights()

        self.assertTrue(np.allclose([0.2], self.network.usage_impact_repartition_weights[job_1].magnitude))
        self.assertTrue(np.allclose([0.4], self.network.usage_impact_repartition_weights[job_2].magnitude))
        self.assertEqual(u.kg, self.network.usage_impact_repartition_weights[job_1].unit)
