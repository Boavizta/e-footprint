import unittest
from unittest import TestCase

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.constants.units import u


class TestEcoLogitsExplainableQuantityJsonRoundtrip(TestCase):
    def test_from_json_dict_returns_ecologits_explainable_quantity(self):
        """Test that serializing and deserializing via ExplainableObject.from_json_dict returns an identical EcoLogitsExplainableQuantity."""
        original = EcoLogitsExplainableQuantity(
            0.001 * u.kWh,
            label="test request energy",
            ancestors={"gpu_energy": 0.001, "server_energy": 0.002},
            formula="request_energy = server_energy * datacenter_pue",
            source=Source(name="Ecologits", link="https://github.com/genai-impact/ecologits"),
        )

        json_dict = original.to_json()
        result = ExplainableObject.from_json_dict(json_dict)

        self.assertIsInstance(result, EcoLogitsExplainableQuantity)
        self.assertEqual(original, result)
        self.assertEqual(original.label, result.label)
        self.assertEqual(original.formula, result.formula)
        self.assertEqual(original._ancestors, result._ancestors)


if __name__ == "__main__":
    unittest.main()