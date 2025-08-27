import unittest
from unittest.mock import patch, MagicMock

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableObject
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage

from efootprint.builders.hardware.boavizta_server_from_config import BoaviztaServerFromConfig


class TestBoaviztaServerFromConfig(unittest.TestCase):
    def setUp(self):
        """
        Create a BoaviztaServerFromConfig instance, either by manual init
        or a hypothetical .from_defaults() if you have such a classmethod.
        """
        self.test_server = BoaviztaServerFromConfig(
            name="Test Boavizta Config Server",
            server_type=ServerTypes.on_premise(),
            nb_of_cpu_units=SourceValue(2 * u.dimensionless),
            nb_of_cores_per_cpu_unit=SourceValue(4 * u.dimensionless),
            nb_of_ram_units=SourceValue(2 * u.dimensionless),
            ram_quantity_per_unit=SourceValue(8 * u.GB),
            average_carbon_intensity=SourceValue(0.233 * u.kg / u.kWh),
            lifespan=SourceValue(6 * u.year),
            idle_power=SourceValue(0 * u.W),
            power_usage_effectiveness=SourceValue(1.4 * u.dimensionless),
            utilization_rate=SourceValue(0.7 * u.dimensionless),
            base_ram_consumption=SourceValue(0 * u.GB),
            base_compute_consumption=SourceValue(0 * u.cpu_core),
            storage=Storage.ssd(storage_capacity=SourceValue(32 * u.GB)),
            fixed_nb_of_instances=EmptyExplainableObject()
        )

    def test_update_cpu_config(self):
        """
        Verify that update_cpu_config() uses self.nb_of_cpu_units & self.nb_of_cores_per_cpu_unit
        to set self.cpu_config properly.
        """
        # The default: nb_of_cpu_units=2, nb_of_cores_per_cpu_unit=4
        self.test_server.update_cpu_config()
        self.assertIsInstance(self.test_server.cpu_config, ExplainableObject)
        self.assertEqual(
            self.test_server.cpu_config.value,
            {"units": 2, "core_units": 4}
        )
        self.assertIn("cpu config", self.test_server.cpu_config.label)

    def test_update_ram_config(self):
        """
        Verify update_ram_config() uses nb_of_ram_units & ram_quantity_per_unit to set self.ram_config.
        """
        # The default: nb_of_ram_units=2, ram_quantity_per_unit=8GB
        self.test_server.update_ram_config()
        self.assertIsInstance(self.test_server.ram_config, ExplainableObject)
        self.assertEqual(
            self.test_server.ram_config.value,
            {"units": 2, "capacity": 8}
        )
        self.assertIn("ram config", self.test_server.ram_config.label)

    @patch("efootprint.builders.hardware.boavizta_server_from_config.call_boaviztapi")
    def test_update_api_call_response(self, mock_call):
        """
        Check that update_api_call_response() posts the CPU/RAM config to Boavizta,
        then sets self.api_call_response to an ExplainableObject containing the result.
        """
        # First, make sure we have some pre-existing configs
        self.test_server.cpu_config = ExplainableObject(
            {"units": 2, "core_units": 4}, label="test cpu config"
        )
        self.test_server.ram_config = ExplainableObject(
            {"units": 2, "capacity": 8}, label="test ram config"
        )

        # Mock the result of call_boaviztapi
        mock_response = {
            "impacts": {
                "gwp": {
                    "embedded": {"value": 999.9}
                }
            },
            "verbose": {
                "CPU-1": {"units": {"value": 2}, "core_units": {"value": 4}},
                "RAM-1": {"units": {"value": 2}, "capacity": {"value": 8}}
            }
        }
        mock_call.return_value = mock_response

        self.test_server.update_api_call_response()

        # The call to call_boaviztapi should have used POST with certain json data
        expected_api_call_data = {
            "model": {"type": "rack"},
            "configuration": {
                "cpu": {"units": 2, "core_units": 4},
                "ram": {"units": 2, "capacity": 8}
            }
        }
        mock_call.assert_called_once()
        call_args = mock_call.call_args.kwargs
        self.assertEqual(call_args["url"], self.test_server.impact_url)
        self.assertIn("method", call_args)
        self.assertEqual(call_args["method"], "POST")
        self.assertIn("json", call_args)
        self.assertEqual(call_args["json"], expected_api_call_data)

        # Check that the server's api_call_response is updated:
        self.assertIsInstance(self.test_server.api_call_response, ExplainableObject)
        self.assertEqual(self.test_server.api_call_response.value, mock_response)
        self.assertIn("api call data", self.test_server.api_call_response.label)

    def test_update_carbon_footprint_fabrication(self):
        """
        Check that update_carbon_footprint_fabrication calculates properly by subtracting
        the storage part from the total embedded footprint.
        """
        # Provide an appropriate mock api_call_response:
        self.test_server.api_call_response = ExplainableObject({
            "impacts": {
                "gwp": {
                    "embedded": {"value": 500.0}  # total
                }
            },
            "verbose": {
                "SSD-1": {
                    "impacts": {
                        "gwp": {
                            "embedded": {"value": 200.0}  # storage portion
                        }
                    }
                }
            }
        }, label="Mocked response")

        self.test_server.update_carbon_footprint_fabrication()

        # carbon_footprint_fabrication should be total (500) minus storage portion (200) => 300 kg
        self.assertEqual(
            self.test_server.carbon_footprint_fabrication.value,
            300.0 * u.kg
        )
        self.assertIn("Fabrication footprint", self.test_server.carbon_footprint_fabrication.label)

    def test_update_power(self):
        """
        Check update_power sets self.power from the average_power in verbose data.
        """
        self.test_server.api_call_response = ExplainableObject({
            "impacts": {},
            "verbose": {
                "avg_power": {"value": 60.0, "unit": "W"},
                "use_time_ratio": {"value": 1.0}
            }
        }, label="Mocked response")

        self.test_server.update_power()
        self.assertEqual(self.test_server.power.value, 60.0 * u.W)
        self.assertIn("power", self.test_server.power.label)

    def test_update_ram(self):
        """
        update_ram picks up the 'RAM-1' entry in 'verbose' to fill self.ram
        """
        self.test_server.api_call_response = ExplainableObject({
            "verbose": {
                "RAM-1": {
                    "units": {"value": 2},
                    "capacity": {"value": 16}
                }
            }
        }, label="Mocked response")

        self.test_server.update_ram()
        self.assertEqual(self.test_server.ram.value, 32 * u.GB)
        self.assertIn("ram", self.test_server.ram.label)

    def test_update_compute(self):
        """
        update_compute picks up the 'CPU-1' entry in 'verbose' to fill self.compute
        """
        self.test_server.api_call_response = ExplainableObject({
            "verbose": {
                "CPU-1": {
                    "units": {"value": 2},
                    "core_units": {"value": 4}
                }
            }
        }, label="Mocked response")

        self.test_server.update_compute()
        self.assertEqual(self.test_server.compute.value, 8 * u.cpu_core)
        self.assertIn("compute", self.test_server.compute.label)


if __name__ == "__main__":
    unittest.main()
