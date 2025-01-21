import unittest
from unittest.mock import patch

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.hardware.gpu_server_builder import GPUServer

class TestGPUServer(unittest.TestCase):

    def setUp(self):
        self.builder = GPUServer("Test GPU Server Builder")

    def test_initialization(self):
        self.assertEqual(self.builder.gpu_power.value, 400 * u.W)
        self.assertEqual(self.builder.gpu_idle_power.value, 50 * u.W)
        self.assertEqual(self.builder.ram_per_gpu.value, 80 * u.GB)
        self.assertEqual(self.builder.carbon_footprint_fabrication_one_gpu.value, 150 * u.kg)
        self.assertEqual(self.builder.nb_of_cpu_cores_per_gpu.value, 1 * u.core)

    @patch("efootprint.builders.hardware.gpu_server_builder.Autoscaling")
    @patch("efootprint.builders.hardware.gpu_server_builder.OnPremise")
    @patch("efootprint.builders.hardware.gpu_server_builder.Serverless")
    def test_generate_gpu_server(self, mock_serverless, mock_on_premise, mock_autoscaling):
        """Test the generate_gpu_server method with various inputs."""
        name = "Test GPU Server"
        average_carbon_intensity = SourceValue(0.5 * u.kg / u.kWh)
        nb_gpus_per_instance = SourceValue(4 * u.dimensionless)

        # Test Autoscaling case
        self.builder.generate_gpu_server(name, "Autoscaling", average_carbon_intensity, nb_gpus_per_instance)
        mock_autoscaling.assert_called_once()

        # Test OnPremise case
        self.builder.generate_gpu_server(name, "OnPremise", average_carbon_intensity, nb_gpus_per_instance,
                                         fixed_nb_of_instances=SourceValue(5 * u.dimensionless))
        mock_on_premise.assert_called_once()

        # Test Serverless case
        self.builder.generate_gpu_server(name, "Serverless", average_carbon_intensity, nb_gpus_per_instance)
        mock_serverless.assert_called_once()

        # Test invalid fixed_nb_of_instances for non-OnPremise
        with self.assertRaises(AssertionError):
            self.builder.generate_gpu_server(name, "Serverless", average_carbon_intensity, nb_gpus_per_instance,
                                             fixed_nb_of_instances=SourceValue(5 * u.dimensionless))

    def test_default_values_property(self):
        """Test that the default_values property returns the correct defaults."""
        defaults = self.builder.default_values()
        self.assertEqual(defaults["gpu_power"].value, 400 * u.W)
        self.assertEqual(defaults["nb_gpus_per_instance"].value, 4 * u.dimensionless)

    @patch("efootprint.builders.hardware.gpu_server_builder.default_ssd")
    @patch("efootprint.builders.hardware.gpu_server_builder.OnPremise")
    def test_on_premise_generation_with_specific_values(self, mock_on_premise, mock_default_ssd):
        name = "Test GPU Server"
        average_carbon_intensity = SourceValue(0.5 * u.kg / u.kWh)
        nb_gpus_per_instance = SourceValue(4 * u.dimensionless)

        self.builder.generate_gpu_server(name, "OnPremise", average_carbon_intensity, nb_gpus_per_instance,
                                         fixed_nb_of_instances=SourceValue(5 * u.dimensionless))

        mock_on_premise.assert_called_once_with(
            name,
            carbon_footprint_fabrication=(
                    SourceValue(2500 * u.kg) + SourceValue(4 * (150 * u.kg))
            ).set_label("default"),
            power=SourceValue(400 * u.W * 4).set_label("default"),
            lifespan=self.builder.default_value('lifespan'),
            idle_power=SourceValue(50 * u.W * 4).set_label("default"),
            ram=SourceValue(80 * u.GB * 4).set_label("default"),
            cpu_cores=SourceValue(4 * (1 * u.core)).set_label("default"),
            power_usage_effectiveness=self.builder.default_value('power_usage_effectiveness'),
            average_carbon_intensity=average_carbon_intensity,
            server_utilization_rate=self.builder.default_value('server_utilization_rate'),
            base_cpu_consumption=self.builder.default_value('base_cpu_consumption'),
            base_ram_consumption=self.builder.default_value('base_ram_consumption'),
            storage=mock_on_premise.call_args[1]['storage'],
            fixed_nb_of_instances=SourceValue(5 * u.dimensionless)
        )
        mock_default_ssd.assert_called_with(
            data_replication_factor=self.builder.default_value('data_replication_factor'),
            base_storage_need=self.builder.default_value('base_storage_need'),
            data_storage_duration=self.builder.default_value('data_storage_duration')
        )


if __name__ == "__main__":
    unittest.main()
