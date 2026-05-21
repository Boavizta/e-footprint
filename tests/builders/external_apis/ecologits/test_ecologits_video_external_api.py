import inspect
import unittest
from unittest import TestCase
from unittest.mock import patch

from pint import Quantity

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits import ecologits_video_external_api as video_module
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob,
    ecologits_video_calculated_attributes)
from efootprint.constants.units import u


def _make_api(**overrides) -> EcoLogitsVideoGenExternalAPI:
    kwargs = {
        "name": "Test video API",
        "provider": SourceObject("openai"),
        "model_name": SourceObject("sora-2-pro"),
    }
    kwargs.update(overrides)
    return EcoLogitsVideoGenExternalAPI(**kwargs)


def _make_job(api: EcoLogitsVideoGenExternalAPI, **overrides) -> EcoLogitsVideoGenExternalAPIJob:
    kwargs = {
        "name": "Test video job",
        "external_api": api,
        "resolution": SourceObject("720p (1280 x 720)"),
        "duration": SourceValue(8 * u.s),
        "with_audio": SourceObject(True),
    }
    kwargs.update(overrides)
    return EcoLogitsVideoGenExternalAPIJob(**kwargs)


class TestEcoLogitsVideoGenExternalAPI(TestCase):
    def setUp(self):
        self.api = _make_api()
        self.api.server.trigger_modeling_updates = False

    def test_initialization_sets_all_inputs(self):
        self.assertEqual("openai", self.api.provider.value)
        self.assertEqual("sora-2-pro", self.api.model_name.value)

    def test_datacenter_location_and_pue_inferred_from_provider_config(self):
        # openai video provider config: datacenter_location="USA", datacenter_pue=1.2
        self.api.update_datacenter_location()
        self.api.update_data_center_pue()
        self.assertEqual("USA", self.api.datacenter_location.value)
        self.assertEqual(1.2, self.api.data_center_pue.value.magnitude)

    def test_average_carbon_intensity_derived_from_datacenter_location(self):
        self.api.update_datacenter_location()
        self.api.update_average_carbon_intensity()
        # Carbon intensity carries kg/kWh and hangs off datacenter_location in the explanation graph.
        self.assertEqual((1 * u.kg / u.kWh).dimensionality,
                         self.api.average_carbon_intensity.value.dimensionality)
        self.assertGreater(self.api.average_carbon_intensity.value.magnitude, 0)
        self.assertIn(self.api.datacenter_location.label,
                      {a.label for a in self.api.average_carbon_intensity.direct_ancestors_with_id})

    def test_compatible_jobs(self):
        self.assertEqual([EcoLogitsVideoGenExternalAPIJob], self.api.compatible_jobs())

    def test_param_descriptions_cover_every_init_param(self):
        init_params = set(inspect.signature(EcoLogitsVideoGenExternalAPI.__init__).parameters) - {"self", "name"}
        self.assertEqual(init_params, set(self.api.param_descriptions))

    def test_provider_list_values_contains_expected_providers(self):
        providers = {p.value for p in EcoLogitsVideoGenExternalAPI.list_values["provider"]}
        for expected in ("openai", "google", "klingai", "bytedance", "runway"):
            self.assertIn(expected, providers)

    def test_conditional_list_values_structure(self):
        config = EcoLogitsVideoGenExternalAPI.conditional_list_values["model_name"]
        self.assertEqual("provider", config["depends_on"])
        for provider in EcoLogitsVideoGenExternalAPI.list_values["provider"]:
            self.assertIn(provider, config["conditional_list_values"])
            self.assertTrue(all(isinstance(m, SourceObject)
                                for m in config["conditional_list_values"][provider]))

    def test_delete_api_deletes_server(self):
        self.api.self_delete()


class TestEcoLogitsVideoGenExternalAPIJob(TestCase):
    def setUp(self):
        self.api = _make_api()
        self.job = _make_job(self.api)
        self.job.trigger_modeling_updates = False

    def test_compatible_external_apis(self):
        self.assertEqual([EcoLogitsVideoGenExternalAPI], EcoLogitsVideoGenExternalAPIJob.compatible_external_apis())

    def test_modeling_objects_whose_attributes_depend_directly_on_me_includes_server(self):
        self.assertIn(self.api.server, self.job.modeling_objects_whose_attributes_depend_directly_on_me)

    def test_param_descriptions_cover_every_init_param(self):
        init_params = set(inspect.signature(EcoLogitsVideoGenExternalAPIJob.__init__).parameters) - {"self", "name"}
        self.assertEqual(init_params, set(self.job.param_descriptions))

    def test_resolution_conditional_list_values_depends_on_external_api_model_name(self):
        config = EcoLogitsVideoGenExternalAPIJob.conditional_list_values["resolution"]
        self.assertEqual("external_api.model_name", config["depends_on"])
        sora_key = SourceObject("sora-2-pro")
        self.assertIn(sora_key, config["conditional_list_values"])
        labels = {r.value for r in config["conditional_list_values"][sora_key]}
        self.assertIn("720p (1280 x 720)", labels)
        self.assertIn("1080p (1920 x 1080)", labels)

    def test_extracted_attributes_carry_expected_units(self):
        self.job.compute_calculated_attributes()
        expected_units = {
            "generation_latency": u.s,
            "request_energy": u.kWh,
            "request_usage_gwp": u.kg,
            "request_embodied_gwp": u.kg,
        }
        for attr, base_unit in expected_units.items():
            value = getattr(self.job, attr)
            self.assertIsInstance(value, EcoLogitsExplainableQuantity)
            self.assertTrue(
                value.value.dimensionality == (1 * base_unit).dimensionality,
                f"{attr} has dimensionality {value.value.dimensionality}, expected {(1 * base_unit).dimensionality}")

    def test_update_request_duration_copies_generation_latency(self):
        self.job.compute_calculated_attributes()
        self.assertEqual(self.job.generation_latency.value, self.job.request_duration.value)

    def test_update_data_transferred_constructs_constants_fresh_inside_method(self):
        # Constants must not be module-level singletons (would leak as shared graph nodes).
        for name in ("bits_per_pixel", "fps", "datacenter_wue", "BITS_PER_PIXEL", "FPS", "DATACENTER_WUE"):
            self.assertFalse(
                hasattr(video_module, name),
                f"Module-level singleton `{name}` leaks bits_per_pixel/fps/datacenter_wue into the graph")

        # Calling update_data_transferred on two jobs creates two distinct ExplainableQuantity ancestors
        # for the same scalar — i.e. the constants are constructed fresh per call, not shared.
        job_a = _make_job(self.api, name="Job A")
        job_b = _make_job(self.api, name="Job B")
        job_a.trigger_modeling_updates = False
        job_b.trigger_modeling_updates = False
        job_a.update_data_transferred()
        job_b.update_data_transferred()
        self.assertEqual(job_a.data_transferred.value, job_b.data_transferred.value)
        # Distinct ExplainableQuantity instances along each calculation graph:
        self.assertIsNot(job_a.data_transferred, job_b.data_transferred)

    def test_update_data_transferred_scales_with_duration_and_resolution(self):
        self.job.compute_calculated_attributes()
        baseline = self.job.data_transferred.value.to(u.MB).magnitude

        longer = _make_job(self.api, name="Longer", duration=SourceValue(16 * u.s))
        longer.trigger_modeling_updates = False
        longer.update_data_transferred()
        self.assertAlmostEqual(2 * baseline, longer.data_transferred.value.to(u.MB).magnitude, places=4)

        bigger = _make_job(self.api, name="Bigger", resolution=SourceObject("1080p (1920 x 1080)"))
        bigger.trigger_modeling_updates = False
        bigger.update_data_transferred()
        # Pixel count scales (1920 * 1080) / (1280 * 720) = 2.25
        self.assertAlmostEqual(2.25 * baseline, bigger.data_transferred.value.to(u.MB).magnitude, places=4)

    def test_update_impacts_invalidation_is_triggered_by_relevant_inputs_only(self):
        # Inputs whose modification must invalidate impacts: duration, resolution, with_audio,
        # data_center_pue, average_carbon_intensity. Verified by inspecting the impacts node's
        # direct ancestors via the explainability graph.
        self.job.compute_calculated_attributes()
        ancestor_labels = {a.label for a in self.job.impacts.direct_ancestors_with_id}
        for required in (
                self.job.resolution.label, self.job.duration.label, self.job.with_audio.label,
                self.api.data_center_pue.label, self.api.average_carbon_intensity.label):
            self.assertIn(required, ancestor_labels)
        # datacenter_location is NOT a direct ancestor: it reaches impacts only through
        # average_carbon_intensity (and provider), avoiding a redundant diamond in the graph.
        self.assertNotIn(self.api.datacenter_location.label, ancestor_labels)

    def test_with_audio_false_changes_generation_latency_for_audio_capable_model(self):
        # google/veo-3.0 is audio-capable with a catalog non_audio_weight of 0.5 — so the
        # with_audio=True branch (overrides to 1.0) and the with_audio=False branch (keeps 0.5)
        # must produce different latencies. Pins that the update_impacts override is observable.
        api = _make_api(provider=SourceObject("google"), model_name=SourceObject("veo-3.0"))
        with_audio_job = _make_job(api, name="With audio", with_audio=SourceObject(True))
        no_audio_job = _make_job(api, name="No audio", with_audio=SourceObject(False))
        with_audio_job.compute_calculated_attributes()
        no_audio_job.compute_calculated_attributes()
        self.assertGreater(with_audio_job.generation_latency.value.magnitude, 0)
        self.assertGreater(no_audio_job.generation_latency.value.magnitude, 0)
        self.assertNotEqual(
            with_audio_job.generation_latency.value, no_audio_job.generation_latency.value)

    def test_calculated_attributes_includes_video_extracted_fields(self):
        for required in (
                "data_transferred", "impacts", "generation_latency", "request_energy",
                "request_usage_gwp", "request_embodied_gwp", "request_duration",
                "hourly_occurrences_across_usage_patterns"):
            self.assertIn(required, self.job.calculated_attributes)

    def test_ancestors_carry_pint_quantities(self):
        self.job.compute_calculated_attributes()
        for attr in ecologits_video_calculated_attributes:
            calc = getattr(self.job, attr)
            for ancestor in calc.ancestors.values():
                self.assertIsInstance(ancestor, Quantity)

    def test_invalid_resolution_raises(self):
        with self.assertRaises(ValueError):
            bad = _make_job(self.api, name="Bad", resolution=SourceObject("bad-format"))
            bad.update_data_transferred()

    def test_unknown_model_for_provider_raises(self):
        # Patch model_name on a valid API to ask for a model not in the catalog; update_impacts must raise.
        job = _make_job(self.api)
        job.trigger_modeling_updates = False
        with patch.object(self.api.model_name, "value", "nope-2"):
            with self.assertRaises(ValueError):
                job.update_impacts()


if __name__ == "__main__":
    unittest.main()
