import unittest
from unittest.mock import patch

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.hardware.gpu_server_builder import GPUServer
from efootprint.core.hardware.storage import Storage


class TestGPUServer(unittest.TestCase):
    def setUp(self):
        self.gpu_server = GPUServer.from_defaults(
            "Test GPU Server Builder", storage=Storage.from_defaults("default storage"))
        self.gpu_server.trigger_modeling_updates = False

    def test_update_carbon_footprint_fabrication(self):
        with patch.object(self.gpu_server, "nb_gpus_per_instance", SourceValue(4 * u.dimensionless)), \
                patch.object(self.gpu_server, "carbon_footprint_fabrication_without_gpu", SourceValue(2000 * u.kg)), \
                patch.object(self.gpu_server, "carbon_footprint_fabrication_one_gpu", SourceValue(250 * u.kg)):
            self.gpu_server.update_carbon_footprint_fabrication()
        self.assertEqual(self.gpu_server.carbon_footprint_fabrication.value, 3000 * u.kg)

    def test_update_power(self):
        with patch.object(self.gpu_server, "nb_gpus_per_instance", SourceValue(4 * u.dimensionless)), \
                patch.object(self.gpu_server, "gpu_power", SourceValue(400 * u.W)):
            self.gpu_server.update_power()
        self.assertEqual(self.gpu_server.power.value, 1600 * u.W)

    def test_update_idle_power(self):
        with patch.object(self.gpu_server, "nb_gpus_per_instance", SourceValue(4 * u.dimensionless)), \
                patch.object(self.gpu_server, "gpu_idle_power", SourceValue(50 * u.W)):
            self.gpu_server.update_idle_power()
        self.assertEqual(self.gpu_server.idle_power.value, 200 * u.W)

    def test_update_ram(self):
        with patch.object(self.gpu_server, "nb_gpus_per_instance", SourceValue(4 * u.dimensionless)), \
                patch.object(self.gpu_server, "ram_per_gpu", SourceValue(80 * u.GB)):
            self.gpu_server.update_ram()
        self.assertEqual(self.gpu_server.ram.value, 320 * u.GB)

    def test_update_cpu_cores(self):
        with patch.object(self.gpu_server, "nb_gpus_per_instance", SourceValue(4 * u.dimensionless)):
            self.gpu_server.update_cpu_cores()
        self.assertEqual(self.gpu_server.cpu_cores.value, 4 * u.core)


if __name__ == "__main__":
    unittest.main()
