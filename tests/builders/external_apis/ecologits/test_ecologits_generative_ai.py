import json
import os
import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob, ecologits_calculated_attributes)
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


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
        mock_job1 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job2 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])

        self.assertEqual(set(self.external_api.jobs), {mock_job1, mock_job2})

    def test_update_instances_fabrication_footprint_with_multiple_jobs(self):
        """Test instances fabrication footprint calculation with multiple jobs."""
        mock_job1 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job1.request_embodied_gwp = ExplainableQuantity(10 * u.kg, "test embodied gwp 1")
        mock_job1.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([5] * 24), u.occurrence), self.start_date, "test occurrences 1")

        mock_job2 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job2.request_embodied_gwp = ExplainableQuantity(20 * u.kg, "test embodied gwp 2")
        mock_job2.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([3] * 24), u.occurrence), self.start_date, "test occurrences 2")

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])
        # Formula: sum(job.request_embodied_gwp * job.hourly_occurrences_across_usage_patterns)

        self.external_api.server.update_instances_fabrication_footprint()

        expected_value = (10 * 5 + 20 * 3) * u.kg  # 50 + 60 = 110
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.instances_fabrication_footprint.magnitude))

    def test_update_instances_fabrication_footprint_with_no_jobs(self):
        """Test instances fabrication footprint calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_instances_fabrication_footprint()

        self.assertIsInstance(self.external_api.server.instances_fabrication_footprint, EmptyExplainableObject)

    def test_update_instances_energy_with_multiple_jobs(self):
        """Test instances energy calculation with multiple jobs."""
        mock_job1 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job1.request_energy = ExplainableQuantity(100 * u.kWh, "test energy 1")
        mock_job1.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([8] * 24), u.occurrence), self.start_date, "test occurrences 1")

        mock_job2 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job2.request_energy = ExplainableQuantity(50 * u.kWh, "test energy 2")
        mock_job2.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([4] * 24), u.occurrence), self.start_date, "test occurrences 2")

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])
        # Formula: sum(job.request_energy * job.hourly_occurrences_across_usage_patterns)

        self.external_api.server.update_instances_energy()

        expected_value = (100 * 8 + 50 * 4) * u.kWh  # 800 + 200 = 1000
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.instances_energy.magnitude))

    def test_update_instances_energy_with_no_jobs(self):
        """Test instances energy calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_instances_energy()

        self.assertIsInstance(self.external_api.server.instances_energy, EmptyExplainableObject)

    def test_update_energy_footprint_with_multiple_jobs(self):
        """Test energy footprint calculation with multiple jobs."""
        mock_job1 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job1.request_usage_gwp = ExplainableQuantity(25 * u.kg, "test usage gwp 1")
        mock_job1.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([6] * 24), u.occurrence), self.start_date, "test occurrences 1")

        mock_job2 = MagicMock(spec=EcoLogitsGenAIExternalAPIJob)
        mock_job2.request_usage_gwp = ExplainableQuantity(15 * u.kg, "test usage gwp 2")
        mock_job2.hourly_occurrences_across_usage_patterns = ExplainableHourlyQuantities(
            Quantity(np.array([10] * 24), u.occurrence), self.start_date, "test occurrences 2")

        set_modeling_obj_containers(self.external_api, [mock_job1, mock_job2])
        # Formula: sum(job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns)

        self.external_api.server.update_energy_footprint()

        expected_value = (25 * 6 + 15 * 10) * u.kg  # 150 + 150 = 300
        self.assertTrue(np.allclose(
            [expected_value.magnitude] * 24, self.external_api.server.energy_footprint.magnitude))

    def test_update_energy_footprint_with_no_jobs(self):
        """Test energy footprint calculation with no jobs."""
        set_modeling_obj_containers(self.external_api, [])

        self.external_api.server.update_energy_footprint()

        self.assertIsInstance(self.external_api.server.energy_footprint, EmptyExplainableObject)

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
            'data_transferred', 'impacts', 'gpu_energy', 'generation_latency', 'model_required_memory',
            'gpu_required_count', 'server_energy', 'request_energy', 'request_usage_gwp', 'server_gpu_embodied_gwp',
            'request_embodied_gwp', 'request_duration',
            'hourly_occurrences_per_usage_pattern', 'hourly_avg_occurrences_per_usage_pattern',
            'hourly_data_transferred_per_usage_pattern', 'hourly_data_stored_per_usage_pattern',
            'hourly_avg_occurrences_across_usage_patterns', 'hourly_data_transferred_across_usage_patterns',
            'hourly_data_stored_across_usage_patterns', 'hourly_occurrences_across_usage_patterns'
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
        for mod_obj in [self.external_api, self.external_api.server, self.job]:
            mod_obj.id = css_escape(mod_obj.name)
        self.job.compute_calculated_attributes()
        root_dir = os.path.dirname(__file__)
        tmp_filepath = os.path.join(root_dir, f"job_serialization_tmp_file.json")
        serialization_dict = {"job": self.job.to_json(save_calculated_attributes=True)}
        serialization_dict.update({"external_api": self.external_api.to_json(save_calculated_attributes=True)})
        with open(tmp_filepath, "w") as f:
            json.dump(serialization_dict, f, indent=2)

        with (open(os.path.join(root_dir, f"job_serialization.json"), 'r') as ref_file,
              open(tmp_filepath, 'r') as tmp_file):
            ref_file_content = ref_file.read()
            tmp_file_content = tmp_file.read()

            self.assertEqual(ref_file_content, tmp_file_content)

        os.remove(tmp_filepath)



if __name__ == "__main__":
    unittest.main()
