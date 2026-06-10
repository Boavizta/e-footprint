import json
import os
import unittest
from datetime import datetime
from unittest import TestCase

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob, ecologits_calculated_attributes)
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.job import JobAttributionCell
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import assert_source_atoms_conserve
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEcoLogitsGenAIExternalAPI(TestCase):
    def setUp(self):
        self.provider = SourceObject("mistralai")
        self.model_name = SourceObject("open-mistral-7b")
        self.external_api = EcoLogitsGenAIExternalAPI(
            name="Test EcoLogits API", provider=self.provider, model_name=self.model_name)
        self.external_api.server.trigger_modeling_updates = False
        self.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")

    def test_initialization_sets_provider_and_model_name(self):
        """Test that initialization correctly sets provider and model_name."""
        self.assertEqual(self.external_api.provider.value, "mistralai")
        self.assertEqual(self.external_api.model_name.value, "open-mistral-7b")

    def test_compatible_jobs(self):
        """Test that compatible_jobs returns the correct job class."""
        compatible_jobs = self.external_api.compatible_jobs()
        self.assertEqual([EcoLogitsGenAIExternalAPIJob], compatible_jobs)

    def test_jobs_property_returns_modeling_obj_containers(self):
        """Test that jobs property returns the modeling_obj_containers."""
        mock_job1 = create_mod_obj_mock(EcoLogitsGenAIExternalAPIJob, "Job 1")
        mock_job2 = create_mod_obj_mock(EcoLogitsGenAIExternalAPIJob, "Job 2")
        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])

        self.assertEqual(set(self.external_api.jobs), {mock_job1, mock_job2})

    def _avg_occ(self, value, label):
        return ExplainableHourlyQuantities(
            Quantity(np.array([value] * 24), u.concurrent), self.start_date, label)

    def _spread_job(self, name, request_duration=ExplainableQuantity(1 * u.hour, "1h"), **kwargs):
        # The aggregator spreads per-request totals over request_duration using
        # hourly_avg_occurrences_across_usage_patterns. Default request_duration=1h makes the
        # (1h / request_duration) spread factor collapse to 1.
        return create_mod_obj_mock(
            EcoLogitsGenAIExternalAPIJob, name, request_duration=request_duration, **kwargs)

    def test_update_instances_fabrication_footprint_spreads_embodied_gwp_over_request_duration_collapsing_at_1h(self):
        """request_duration=1h collapses the spread factor to 1, so the per-hour value reduces to
        request_embodied_gwp times the averaged occurrence series."""
        mock_job1 = self._spread_job(
            "Job 1", request_embodied_gwp=ExplainableQuantity(10 * u.kg, "gwp 1"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(5, "test occurrences 1"))
        mock_job2 = self._spread_job(
            "Job 2", request_embodied_gwp=ExplainableQuantity(20 * u.kg, "gwp 2"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(3, "test occurrences 2"))

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])

        self.external_api.server.update_instances_fabrication_footprint()

        expected_value = (10 * 5 + 20 * 3) * u.kg  # 50 + 60 = 110
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.instances_fabrication_footprint.magnitude))

    def test_update_instances_fabrication_footprint_spreads_over_request_duration(self):
        """A 2h request spreads its per-request embodied GWP at half-rate per hour: the per-hour value
        is request_embodied_gwp * (1h / 2h) = 5 kg, times the averaged occurrence series."""
        mock_job = self._spread_job(
            "Long job", request_duration=ExplainableQuantity(2 * u.hour, "2h"),
            request_embodied_gwp=ExplainableQuantity(10 * u.kg, "emb"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "avg occ"))

        set_modeling_obj_containers(self.external_api, [mock_job])

        self.external_api.server.update_instances_fabrication_footprint()

        self.assertTrue(np.allclose(
            [10 * 0.5 * 4] * 24, self.external_api.server.instances_fabrication_footprint.magnitude))

    def test_update_instances_fabrication_footprint_with_no_jobs(self):
        """Test instances fabrication footprint calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_instances_fabrication_footprint()

        self.assertIsInstance(self.external_api.server.instances_fabrication_footprint, EmptyExplainableObject)

    def test_update_instances_energy_spreads_energy_over_request_duration_collapsing_at_1h(self):
        """request_duration=1h collapses the spread factor to 1, so the per-hour value reduces to
        request_energy times the averaged occurrence series."""
        mock_job1 = self._spread_job(
            "Job 1", request_energy=ExplainableQuantity(100 * u.kWh, "energy 1"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(8, "test occurrences 1"))
        mock_job2 = self._spread_job(
            "Job 2", request_energy=ExplainableQuantity(50 * u.kWh, "energy 2"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "test occurrences 2"))

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])

        self.external_api.server.update_instances_energy()

        expected_value = (100 * 8 + 50 * 4) * u.kWh  # 800 + 200 = 1000
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.instances_energy.magnitude))

    def test_update_instances_energy_with_no_jobs(self):
        """Test instances energy calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_instances_energy()

        self.assertIsInstance(self.external_api.server.instances_energy, EmptyExplainableObject)

    def test_update_energy_footprint_spreads_usage_gwp_over_request_duration_collapsing_at_1h(self):
        """request_duration=1h collapses the spread factor to 1, so the per-hour value reduces to
        request_usage_gwp times the averaged occurrence series."""
        mock_job1 = self._spread_job(
            "Job 1", request_usage_gwp=ExplainableQuantity(25 * u.kg, "usage 1"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(6, "test occurrences 1"))
        mock_job2 = self._spread_job(
            "Job 2", request_usage_gwp=ExplainableQuantity(15 * u.kg, "usage 2"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(10, "test occurrences 2"))

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])

        self.external_api.server.update_energy_footprint()

        expected_value = (25 * 6 + 15 * 10) * u.kg  # 150 + 150 = 300
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.energy_footprint.magnitude))

    def test_update_energy_footprint_with_no_jobs(self):
        """Test energy footprint calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_energy_footprint()

        self.assertIsInstance(self.external_api.server.energy_footprint, EmptyExplainableObject)

    def test_spread_over_request_duration_returns_empty_when_per_request_value_is_empty(self):
        """A job with no usage patterns has an EmptyExplainableObject per-request value and its
        request_duration is still the 0 s default; the spread helper must short-circuit to an
        EmptyExplainableObject rather than dividing by 0 s."""
        mock_job = self._spread_job(
            "Empty job", request_duration=ExplainableQuantity(0 * u.s, "0s"),
            request_energy=EmptyExplainableObject(),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(5, "avg occ"))

        result = self.external_api.server._spread_over_request_duration(mock_job, mock_job.request_energy)

        self.assertIsInstance(result, EmptyExplainableObject)

    def test_update_phase_specific_impact_repartition_weights_use_matching_request_footprints_per_job(self):
        """Test server weights split embodied and usage request impacts by phase."""
        mock_job_1 = self._spread_job(
            name="Job 1",
            request_embodied_gwp=ExplainableQuantity(2 * u.kg, "test embodied gwp 1"),
            request_usage_gwp=ExplainableQuantity(3 * u.kg, "test usage gwp 1"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "test occurrences 1"),
        )

        mock_job_2 = self._spread_job(
            name="Job 2",
            request_embodied_gwp=ExplainableQuantity(1 * u.kg, "test embodied gwp 2"),
            request_usage_gwp=ExplainableQuantity(1 * u.kg, "test usage gwp 2"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(10, "test occurrences 2"),
        )

        set_modeling_obj_containers(self.external_api, [mock_job_1, mock_job_2])

        self.external_api.server.update_fabrication_impact_repartition_weights()
        self.external_api.server.update_usage_impact_repartition_weights()

        self.assertTrue(np.allclose([8] * 24, self.external_api.server.fabrication_impact_repartition_weights[mock_job_1].magnitude))
        self.assertTrue(np.allclose([10] * 24, self.external_api.server.fabrication_impact_repartition_weights[mock_job_2].magnitude))
        self.assertTrue(np.allclose([12] * 24, self.external_api.server.usage_impact_repartition_weights[mock_job_1].magnitude))
        self.assertTrue(np.allclose([10] * 24, self.external_api.server.usage_impact_repartition_weights[mock_job_2].magnitude))

    def test_impact_repartition_weights_spread_over_request_duration(self):
        """A 2h request spreads its per-request GWP at half-rate per hour on both repartition-weight
        paths: the weight is request_*_gwp * (1h / 2h) times the averaged occurrence series."""
        mock_job = self._spread_job(
            name="Long job", request_duration=ExplainableQuantity(2 * u.hour, "2h"),
            request_embodied_gwp=ExplainableQuantity(8 * u.kg, "embodied"),
            request_usage_gwp=ExplainableQuantity(6 * u.kg, "usage"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "avg occ"),
        )

        set_modeling_obj_containers(self.external_api, [mock_job])

        self.external_api.server.update_fabrication_impact_repartition_weights()
        self.external_api.server.update_usage_impact_repartition_weights()

        self.assertTrue(np.allclose(
            [8 * 0.5 * 4] * 24, self.external_api.server.fabrication_impact_repartition_weights[mock_job].magnitude))
        self.assertTrue(np.allclose(
            [6 * 0.5 * 4] * 24, self.external_api.server.usage_impact_repartition_weights[mock_job].magnitude))

    def test_update_instances_energy_spreads_over_request_duration(self):
        """A 2h request spreads its per-request energy at half-rate per hour: the per-hour value is
        request_energy * (1h / 2h) times the averaged occurrence series."""
        mock_job = self._spread_job(
            "Long job", request_duration=ExplainableQuantity(2 * u.hour, "2h"),
            request_energy=ExplainableQuantity(100 * u.kWh, "energy"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "avg occ"))

        set_modeling_obj_containers(self.external_api, [mock_job])

        self.external_api.server.update_instances_energy()

        self.assertTrue(np.allclose(
            [100 * 0.5 * 4] * 24, self.external_api.server.instances_energy.magnitude))

    def test_attribution_atoms_conserve_eager_phase_totals(self):
        """Test that Σ of the API server's atoms over each job's cells recovers the eager fabrication and
        energy footprints (single demand stream, hourly cell shares)."""
        def cell(up_name, hourly_share, flat_share):
            flat_share_quantity = ExplainableQuantity(flat_share * u.dimensionless, f"flat share in {up_name}")
            return JobAttributionCell(
                up=create_mod_obj_mock(UsagePattern, up_name),
                hourly_share=ExplainableHourlyQuantities(
                    Quantity(np.full(24, hourly_share, dtype=np.float32), u.dimensionless), self.start_date,
                    left_parent=flat_share_quantity, operator="hourly share matching"),
                flat_share=flat_share_quantity,
                step=create_mod_obj_mock(UsageJourneyStep, f"step of {up_name}"))

        mock_job_1 = self._spread_job(
            "Conserving job 1",
            request_embodied_gwp=ExplainableQuantity(2 * u.kg, "embodied gwp 1"),
            request_usage_gwp=ExplainableQuantity(3 * u.kg, "usage gwp 1"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(4, "occurrences 1"),
            attribution_cells=(cell("conserving up 1", 0.25, 0.25), cell("conserving up 2", 0.75, 0.75)))
        mock_job_2 = self._spread_job(
            "Conserving job 2",
            request_embodied_gwp=ExplainableQuantity(1 * u.kg, "embodied gwp 2"),
            request_usage_gwp=ExplainableQuantity(1 * u.kg, "usage gwp 2"),
            hourly_avg_occurrences_across_usage_patterns=self._avg_occ(10, "occurrences 2"),
            attribution_cells=(cell("conserving up 3", 1, 1),))
        set_modeling_obj_containers(self.external_api, [mock_job_1, mock_job_2])
        server = self.external_api.server
        server.update_instances_fabrication_footprint()
        server.update_energy_footprint()

        assert_source_atoms_conserve(self, server)
        fabrication_atoms = list(server.attribution_atoms(LifeCyclePhases.MANUFACTURING))
        self.assertEqual(3, len(fabrication_atoms))
        self.assertEqual({"single"}, {atom.stream for atom in fabrication_atoms})
        job_1_up_1_atom = next(
            atom for atom in fabrication_atoms if atom.job == mock_job_1 and atom.up.name == "conserving up 1")
        self.assertTrue(np.allclose([2 * 4 * 0.25] * 24, job_1_up_1_atom.value.magnitude))

    def test_usage_impact_repartition_property_returns_server_usage_impact_repartition(self):
        """Test ExternalAPI exposes the server-level usage impact repartition without copying it."""
        mock_job = create_mod_obj_mock(EcoLogitsGenAIExternalAPIJob, name="Job")
        expected_repartition = ExplainableObjectDict({mock_job: SourceValue(1 * u.concurrent)})
        self.external_api.server.usage_impact_repartition = expected_repartition

        self.assertIs(expected_repartition, self.external_api.usage_impact_repartition)

    def test_provider_list_values_contains_valid_providers(self):
        """Test that list_values contains valid provider options."""
        self.assertIn("provider", EcoLogitsGenAIExternalAPI.list_values)
        providers = [p.value for p in EcoLogitsGenAIExternalAPI.list_values["provider"]]
        self.assertIn("mistralai", providers)
        self.assertGreater(len(providers), 0)
        self.assertTrue(all(isinstance(p, str) for p in providers))

    def test_conditional_list_values_has_correct_structure(self):
        """Test that conditional_list_values has the correct structure."""
        self.assertIn("model_name", EcoLogitsGenAIExternalAPI.conditional_list_values)
        model_config = EcoLogitsGenAIExternalAPI.conditional_list_values["model_name"]
        self.assertEqual(model_config["depends_on"], "provider")
        self.assertIn("conditional_list_values", model_config)

    def test_conditional_list_values_provides_models_for_each_provider(self):
        """Test that conditional list values provides models for each provider."""
        model_config = EcoLogitsGenAIExternalAPI.conditional_list_values["model_name"]
        conditional_values = model_config["conditional_list_values"]

        for provider in EcoLogitsGenAIExternalAPI.list_values["provider"]:
            self.assertIn(provider, conditional_values)
            models = conditional_values[provider]
            self.assertGreater(len(models), 0)
            self.assertTrue(all(isinstance(m, SourceObject) for m in models))

    def test_delete_external_api(self):
        """Test that deleting the external API also deletes its server."""
        self.external_api.self_delete()


class TestEcoLogitsGenAIExternalAPIJob(TestCase):
    def setUp(self):
        self.provider = SourceObject("openai")
        self.model_name = SourceObject("gpt-4o")
        self.external_api = EcoLogitsGenAIExternalAPI(
            name="Test EcoLogits API", provider=self.provider, model_name=self.model_name)
        self.output_token_count = SourceValue(1000 * u.dimensionless)
        self.job = EcoLogitsGenAIExternalAPIJob(
            name="Test Job", external_api=self.external_api, output_token_count=self.output_token_count)
        self.job.trigger_modeling_updates = False

    def test_modeling_objects_whose_attributes_depend_directly_on_me_returns_external_api_server(self):
        """Test that the job returns its external_api as a dependency."""
        self.assertEqual(self.job.modeling_objects_whose_attributes_depend_directly_on_me, [self.external_api.server])

    def test_compatible_external_apis(self):
        self.assertEqual(EcoLogitsGenAIExternalAPIJob.compatible_external_apis(), [EcoLogitsGenAIExternalAPI])

    def test_update_data_transferred(self):
        """Test data transferred calculation."""
        self.job.output_token_count = SourceValue(1000 * u.dimensionless)
        # Formula: data_transferred = 5 bytes/token * output_token_count

        self.job.update_data_transferred()

        expected = 5 * 1000 * u.B  # 5000 bytes
        self.assertEqual(expected, self.job.data_transferred.value)

    def test_update_impacts_creates_impacts(self):
        """Test that impacts are created correctly."""
        self.job.update_impacts()

        self.assertIsNotNone(self.job.impacts)
        self.assertGreater(len(self.job.impacts.value), 0)

    def test_compute_calculated_attributes_computes_ecologits_calculated_attributes(self):
        """Test that all calculated attributes are computed without errors."""
        self.job.compute_calculated_attributes()
        for ecologits_attr in ecologits_calculated_attributes:
            self.assertTrue(hasattr(self.job, ecologits_attr))
            self.assertIsInstance(getattr(self.job, ecologits_attr), EcoLogitsExplainableQuantity)

    def test_calculated_attributes(self):
        calculated_attributes = [
            "data_transferred", "impacts", "gpu_energy", "generation_latency", "model_required_memory",
            "gpu_required_count", "server_energy", "request_energy", "request_it_energy",
            "request_usage_gwp", "server_gpu_embodied_gwp",
            "request_embodied_gwp", "request_duration",
            "hourly_occurrences_per_usage_pattern", "hourly_avg_occurrences_per_usage_pattern",
            "hourly_data_transferred_per_usage_pattern", "hourly_data_stored_per_usage_pattern",
            "hourly_avg_occurrences_across_usage_patterns", "hourly_data_transferred_across_usage_patterns",
            "hourly_data_stored_across_usage_patterns",
            "fabrication_impact_repartition_weights", "fabrication_impact_repartition_weight_sum",
            "fabrication_impact_repartition", "usage_impact_repartition_weights",
            "usage_impact_repartition_weight_sum", "usage_impact_repartition",
            "hourly_occurrences_across_usage_patterns"
        ]
        self.assertEqual(self.job.calculated_attributes, calculated_attributes)

    def test_ancestors(self):
        """Test that ancestors are correctly set for calculated attributes."""
        self.job.compute_calculated_attributes()
        for attr in ecologits_calculated_attributes:
            calculated_attr = getattr(self.job, attr)
            self.assertIsInstance(calculated_attr, EcoLogitsExplainableQuantity)
            for ancestor in calculated_attr.ancestors.values():
                self.assertIsInstance(ancestor, Quantity)

    def test_to_json(self):
        self.job.compute_calculated_attributes()
        root_dir = os.path.dirname(__file__)
        tmp_filepath = os.path.join(root_dir, f"job_serialization_tmp_file.json")
        serialization_dict = {"job": self.job.to_json(save_calculated_attributes=True)}
        serialization_dict.update({"external_api": self.external_api.to_json(save_calculated_attributes=True)})
        with open(tmp_filepath, "w") as f:
            json.dump(serialization_dict, f, indent=2)

        with (open(os.path.join(root_dir, f"job_serialization.json"), "r") as ref_file,
              open(tmp_filepath, "r") as tmp_file):
            ref_file_content = ref_file.read()
            tmp_file_content = tmp_file.read()

            self.assertEqual(ref_file_content, tmp_file_content)

        os.remove(tmp_filepath)

    def test_create_2_ecologits_external_api_jobs_then_delete_them(self):
        """Test creating two jobs linked to the same external API, then deleting them."""
        external_api = EcoLogitsGenAIExternalAPI(
            name="Test EcoLogits API for Jobs deletion", provider=SourceObject("mistralai"),
            model_name=SourceObject("open-mistral-7b"))
        job1 = EcoLogitsGenAIExternalAPIJob(
            name="Test Job 1", external_api=external_api, output_token_count=SourceValue(500 * u.dimensionless))
        job2 = EcoLogitsGenAIExternalAPIJob(
            name="Test Job 2", external_api=external_api, output_token_count=SourceValue(1500 * u.dimensionless))

        self.assertIn(job1, external_api.jobs)
        self.assertIn(job2, external_api.jobs)

        job1.self_delete()
        self.assertNotIn(job1, external_api.jobs)
        self.assertIn(job2, external_api.jobs)

        # There was a bug (resolved in efootprint 16.0.4) where serializing job2 wouldn’t work because
        # the external API would have been recomputed after job2 had been recomputed.
        # The serialization shouldn’t raise any error.
        job2_serialization = job2.to_json(save_calculated_attributes=True)

        job2.self_delete()
        self.assertNotIn(job2, external_api.jobs)



if __name__ == "__main__":
    unittest.main()
