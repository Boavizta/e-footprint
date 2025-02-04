import unittest
from unittest.mock import patch

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.builders.services.video_streaming import VideoStreaming
from efootprint.builders.services.web_application import WebApplication
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server_base import ServerTypes

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer


class TestBoaviztaCloudServer(unittest.TestCase):
    def setUp(self):
        """
        Instantiate a BoaviztaCloudServer with minimal required arguments.
        """
        self.test_server = BoaviztaCloudServer(
            name="Test Boavizta Server",
            provider=SourceObject("scaleway"),
            instance_type=SourceObject("dev1-s"),
            server_type=ServerTypes.autoscaling(),
            lifespan=SourceValue(6 * u.year),
            idle_power=SourceValue(0 * u.W),
            power_usage_effectiveness=SourceValue(1.2 * u.dimensionless),
            average_carbon_intensity=SourceValue(0.233 * u.kg / u.kWh),
            server_utilization_rate=SourceValue(0.9 * u.dimensionless),
            base_ram_consumption=SourceValue(0 * u.GB),
            base_compute_consumption=SourceValue(0 * u.cpu_core),
            storage=Storage.ssd(storage_capacity=SourceValue(32 * u.GB)),
            fixed_nb_of_instances=EmptyExplainableObject()  # or None, if you prefer
        )

    @patch("efootprint.builders.hardware.boavizta_cloud_server.call_boaviztapi")
    def test_update_api_call_response(self, mock_call):
        """
        Test that update_api_call_response fetches data from boavizta, then sets self.api_call_response
        as an ExplainableObject whose value is the raw dictionary.
        """
        mock_response_data = {
            "impacts": {
                "gwp": {
                    "embedded": {"value": 123.45}
                }
            },
            "verbose": {
                "avg_power": {
                    "value": 50.0,
                    "unit": "W"
                },
                "use_time_ratio": {
                    "value": 1.0
                },
                "RAM-1": {
                    "units": {"value": 2},
                    "capacity": {"value": 16}
                },
                "CPU-1": {
                    "units": {"value": 2},
                    "core_units": {"value": 4}
                }
            }
        }
        mock_call.return_value = mock_response_data

        self.test_server.update_api_call_response()

        # api_call_response should now be an ExplainableQuantity with the entire dictionary in .value
        self.assertIsInstance(self.test_server.api_call_response, ExplainableObject)
        self.assertEqual(self.test_server.api_call_response.value, mock_response_data)
        self.assertEqual(self.test_server.api_call_response.operator, "combined in Boavizta API call with")
        # Source checks
        self.assertIn("scaleway", self.test_server.api_call_response.left_parent.value)
        self.assertIn("dev1-s", self.test_server.api_call_response.right_parent.value)

    def test_update_carbon_footprint_fabrication(self):
        """
        Test that update_carbon_footprint_fabrication uses self.api_call_response.value to set the attribute.
        We'll skip calling boaviztapi for simplicity; we'll just patch the existing api_call_response
        to mimic the data we want.
        """
        mock_data = {
            "impacts": {"gwp": {"embedded": {"value": 123.45}}},
            "verbose": {}
        }
        # Provide a pre-populated ExplainableQuantity as if update_api_call_response had run
        self.test_server.api_call_response = ExplainableObject(mock_data, "API call response")

        self.test_server.update_carbon_footprint_fabrication()
        self.assertEqual(
            self.test_server.carbon_footprint_fabrication.value,
            123.45 * u.kg
        )
        self.assertIn("fabrication carbon footprint",
                      self.test_server.carbon_footprint_fabrication.label)

    def test_update_power(self):
        """
        Test that update_power uses avg_power and use_time_ratio from self.api_call_response.value.
        """
        mock_data = {
            "impacts": {},
            "verbose": {
                "avg_power": {"value": 60.0, "unit": "W"},
                "use_time_ratio": {"value": 1.0}
            }
        }
        self.test_server.api_call_response = ExplainableObject(mock_data, "API call response")

        self.test_server.update_power()
        self.assertEqual(self.test_server.power.value, 60.0 * u.W)
        self.assertIn("power", self.test_server.power.label)

    def test_update_ram(self):
        """
        Test that update_ram extracts the RAM-1 spec from self.api_call_response.value.
        """
        mock_data = {
            "impacts": {},
            "verbose": {
                "RAM-1": {
                    "units": {"value": 2},
                    "capacity": {"value": 16}
                }
            }
        }
        self.test_server.api_call_response = ExplainableObject(mock_data, "API call response")

        self.test_server.update_ram()
        # 2 * 16 = 32 GB
        self.assertEqual(self.test_server.ram.value, 32 * u.GB)
        self.assertIn("ram", self.test_server.ram.label)

    def test_update_compute(self):
        """
        Test that update_compute extracts the CPU-1 spec from self.api_call_response.value.
        """
        mock_data = {
            "impacts": {},
            "verbose": {
                "CPU-1": {
                    "units": {"value": 2},
                    "core_units": {"value": 4}
                }
            }
        }
        self.test_server.api_call_response = ExplainableObject(mock_data, "API call response")

        self.test_server.update_compute()
        # 2 * 4 = 8 cpu_cores
        self.assertEqual(self.test_server.compute.value, 8 * u.cpu_core)
        self.assertIn("compute", self.test_server.compute.label)

    def test_installable_services(self):
        self.assertEqual(set(BoaviztaCloudServer.installable_services()), {WebApplication, VideoStreaming})


if __name__ == "__main__":
    unittest.main()
