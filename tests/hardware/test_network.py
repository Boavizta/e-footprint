from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
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
