"""Structural integration coverage for the EcoLogits video trio.

Assertions are deliberately structural (units, presence, non-negative, monotonicity in
duration) — never literal magnitudes. EcoLogits may re-fit its regression coefficients
between releases; we don't want this test to churn on every upstream bump.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def _build_system(duration_s: float):
    api = EcoLogitsVideoGenExternalAPI(
        name="Sora-2-Pro API",
        provider=SourceObject("openai"),
        model_name=SourceObject("sora-2-pro"))
    job = EcoLogitsVideoGenExternalAPIJob(
        name="Sora job",
        external_api=api,
        resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(duration_s * u.s),
        with_audio=SourceObject(True))
    uj_step = UsageJourneyStep.from_defaults("UJ step", jobs=[job])
    uj = UsageJourney("Usage journey", uj_steps=[uj_step])
    network = Network.from_defaults("Default network")
    start = datetime.strptime("2025-01-01", "%Y-%m-%d")
    up = UsagePattern(
        "Usage Pattern", uj, [Device.laptop()], network, Countries.FRANCE(),
        create_source_hourly_values_from_list([1, 2, 4, 5, 8, 12, 2, 2, 3], start))
    system = System("Video system", [up], edge_usage_patterns=[])
    return system, api, job


class TestEcoLogitsVideoIntegration(unittest.TestCase):
    def test_system_calculation_produces_expected_units_and_non_negative_footprints(self):
        system, api, job = _build_system(duration_s=8)
        try:
            server = api.server
            self.assertIsInstance(server.instances_fabrication_footprint, ExplainableHourlyQuantities)
            self.assertIsInstance(server.instances_energy, ExplainableHourlyQuantities)
            self.assertIsInstance(server.energy_footprint, ExplainableHourlyQuantities)

            self.assertEqual(
                (1 * u.kg).dimensionality, server.instances_fabrication_footprint.value.dimensionality)
            self.assertEqual(
                (1 * u.kWh).dimensionality, server.instances_energy.value.dimensionality)
            self.assertEqual(
                (1 * u.kg).dimensionality, server.energy_footprint.value.dimensionality)

            self.assertTrue((server.instances_fabrication_footprint.magnitude >= 0).all())
            self.assertTrue((server.instances_energy.magnitude >= 0).all())
            self.assertTrue((server.energy_footprint.magnitude >= 0).all())
        finally:
            system.self_delete()

    def test_server_energy_footprint_is_monotonic_in_job_duration(self):
        short_system, short_api, _ = _build_system(duration_s=4)
        long_system, long_api, _ = _build_system(duration_s=16)
        try:
            short_footprint = short_api.server.energy_footprint.magnitude.sum()
            long_footprint = long_api.server.energy_footprint.magnitude.sum()
            # Longer per-call duration → larger per-call usage GWP → higher server energy footprint sum.
            self.assertGreater(long_footprint, short_footprint)
        finally:
            short_system.self_delete()
            long_system.self_delete()

    def test_long_request_spreads_server_footprint_across_multiple_hours(self):
        # A 300s clip yields a generation_latency (== request_duration) of ~11h, genuinely
        # exceeding one hour. The aggregator must spread the server impact over the hours the
        # request runs rather than booking it length-1 in the start hour. This pins the
        # duration-spread regression at the real public-API call site
        # (request_duration + hourly_avg_occurrences_across_usage_patterns), not via mocks.
        system, api, job = _build_system(duration_s=300)
        try:
            server = api.server
            self.assertGreater(job.request_duration.value.to(u.hour).magnitude, 1)

            energy = server.energy_footprint
            fabrication = server.instances_fabrication_footprint
            self.assertIsInstance(energy, ExplainableHourlyQuantities)
            self.assertIsInstance(fabrication, ExplainableHourlyQuantities)

            # The impact must land in more than one hour bucket, i.e. it spreads over the
            # multi-hour run window instead of collapsing length-1 into the start hour.
            self.assertGreater(int((energy.magnitude > 0).sum()), 1)
            self.assertGreater(int((fabrication.magnitude > 0).sum()), 1)
        finally:
            system.self_delete()

    def test_system_json_roundtrip_preserves_calculated_attributes(self):
        system, api, job = _build_system(duration_s=8)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "video_system.json")
                system_to_json(system, save_calculated_attributes=True, output_filepath=path)
                with open(path) as f:
                    system_dict = json.load(f)
                _, flat_obj_dict, _ = json_to_system(system_dict)

            reloaded_api = flat_obj_dict[api.id]
            reloaded_job = flat_obj_dict[job.id]
            self.assertEqual(
                job.generation_latency.value, reloaded_job.generation_latency.value)
            self.assertEqual(
                job.request_energy.value, reloaded_job.request_energy.value)
            self.assertEqual(
                job.request_usage_gwp.value, reloaded_job.request_usage_gwp.value)
            self.assertEqual(
                job.request_embodied_gwp.value, reloaded_job.request_embodied_gwp.value)
            self.assertNotIsInstance(reloaded_api.server.energy_footprint, EmptyExplainableObject)
        finally:
            system.self_delete()


if __name__ == "__main__":
    unittest.main()
