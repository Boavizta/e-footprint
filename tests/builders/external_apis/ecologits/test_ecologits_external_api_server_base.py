from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_external_api_server_base import (
    EcoLogitsExternalAPIServerBase)
from efootprint.builders.external_apis.external_api_job_base_class import ExternalAPIJob
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEcoLogitsExternalAPIServerBase(TestCase):
    """Aggregation logic shared by the EcoLogits LLM and video servers, exercised once on the base class
    itself rather than duplicated per concrete subclass."""

    def setUp(self):
        self.server = EcoLogitsExternalAPIServerBase(name="Test server")
        self.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")

    def _attach_jobs(self, jobs):
        api = MagicMock()
        api.jobs = jobs
        api.model_name = "test-model"
        set_modeling_obj_containers(self.server, [api])

    def _occ(self, value, label, unit=u.occurrence):
        return ExplainableHourlyQuantities(
            Quantity(np.array([value] * 24), unit), self.start_date, label)

    def _job(self, name, request_duration=ExplainableQuantity(1 * u.hour, "1h"), **kwargs):
        # The aggregator spreads per-request totals over request_duration using
        # hourly_avg_occurrences_across_usage_patterns. Tests pass request_duration=1h and supply
        # the averaged occurrence series so the (1h / request_duration) factor collapses to 1.
        return create_mod_obj_mock(ExternalAPIJob, name, request_duration=request_duration, **kwargs)

    def _avg_occ(self, value, label):
        return self._occ(value, label, unit=u.concurrent)

    def test_update_instances_fabrication_footprint_spreads_embodied_gwp_over_request_duration_collapsing_at_1h(self):
        # request_duration=1h makes the (1h / request_duration) spread factor collapse to 1, so the
        # per-hour value reduces to request_embodied_gwp times the averaged occurrence series.
        self._attach_jobs([
            self._job("Job 1", request_embodied_gwp=ExplainableQuantity(10 * u.kg, "emb 1"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(5, "occ 1")),
            self._job("Job 2", request_embodied_gwp=ExplainableQuantity(20 * u.kg, "emb 2"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(3, "occ 2"))])

        self.server.update_instances_fabrication_footprint()

        self.assertTrue(np.allclose(
            [10 * 5 + 20 * 3] * 24, self.server.instances_fabrication_footprint.magnitude))

    def test_update_instances_fabrication_footprint_spreads_over_request_duration(self):
        # A 2h request spreads its per-request embodied GWP at half-rate per hour: the per-hour value
        # is request_embodied_gwp * (1h / 2h) = 5 kg, times the averaged occurrence series.
        self._attach_jobs([
            self._job("Long job", request_duration=ExplainableQuantity(2 * u.hour, "2h"),
                      request_embodied_gwp=ExplainableQuantity(10 * u.kg, "emb"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "avg occ"))])

        self.server.update_instances_fabrication_footprint()

        self.assertTrue(np.allclose([10 * 0.5 * 4] * 24, self.server.instances_fabrication_footprint.magnitude))

    def test_update_instances_fabrication_footprint_with_no_jobs(self):
        self._attach_jobs([])

        self.server.update_instances_fabrication_footprint()

        self.assertIsInstance(self.server.instances_fabrication_footprint, EmptyExplainableObject)

    def test_update_instances_energy_spreads_energy_over_request_duration_collapsing_at_1h(self):
        # request_duration=1h makes the (1h / request_duration) spread factor collapse to 1, so the
        # per-hour value reduces to request_energy times the averaged occurrence series.
        self._attach_jobs([
            self._job("Job 1", request_energy=ExplainableQuantity(100 * u.kWh, "energy 1"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(8, "occ 1")),
            self._job("Job 2", request_energy=ExplainableQuantity(50 * u.kWh, "energy 2"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "occ 2"))])

        self.server.update_instances_energy()

        self.assertTrue(np.allclose([100 * 8 + 50 * 4] * 24, self.server.instances_energy.magnitude))

    def test_update_instances_energy_with_no_jobs(self):
        self._attach_jobs([])

        self.server.update_instances_energy()

        self.assertIsInstance(self.server.instances_energy, EmptyExplainableObject)

    def test_update_energy_footprint_spreads_usage_gwp_over_request_duration_collapsing_at_1h(self):
        # request_duration=1h makes the (1h / request_duration) spread factor collapse to 1, so the
        # per-hour value reduces to request_usage_gwp times the averaged occurrence series.
        self._attach_jobs([
            self._job("Job 1", request_usage_gwp=ExplainableQuantity(25 * u.kg, "usage 1"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(6, "occ 1")),
            self._job("Job 2", request_usage_gwp=ExplainableQuantity(15 * u.kg, "usage 2"),
                      hourly_avg_occurrences_across_usage_patterns=self._avg_occ(10, "occ 2"))])

        self.server.update_energy_footprint()

        self.assertTrue(np.allclose([25 * 6 + 15 * 10] * 24, self.server.energy_footprint.magnitude))

    def test_update_energy_footprint_with_no_jobs(self):
        self._attach_jobs([])

        self.server.update_energy_footprint()

        self.assertIsInstance(self.server.energy_footprint, EmptyExplainableObject)
