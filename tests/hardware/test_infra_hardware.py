from unittest import TestCase

import numpy as np

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list


class TestInfraHardware(TestCase):
    def setUp(self):
        class InfraHardwareTestClass(InfraHardware):
            default_values = {
                    "carbon_footprint_fabrication": SourceValue(100 * u.kg),
                    "power": SourceValue(100 * u.W),
                    "lifespan": SourceValue(5 * u.year)
                }

            def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                         power: ExplainableQuantity, lifespan: ExplainableQuantity):
                super().__init__(name, carbon_footprint_fabrication, power, lifespan)

            def update_raw_nb_of_instances(self):
                self.raw_nb_of_instances = create_source_hourly_values_from_list([1.5, 3])

            def update_nb_of_instances(self):
                self.nb_of_instances = create_source_hourly_values_from_list([2, 3])

            def update_instances_energy(self):
                self.instances_energy = create_source_hourly_values_from_list([2, 4], pint_unit=u.kWh)

            def after_init(self):
                self.trigger_modeling_updates = False

        self.test_infra_hardware = InfraHardwareTestClass(
            "test_infra_hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years))

    def test_instances_fabrication_footprint(self):
        self.test_infra_hardware.update_nb_of_instances()
        self.test_infra_hardware.update_instances_fabrication_footprint()
        self.assertEqual(u.kg, self.test_infra_hardware.instances_fabrication_footprint.unit)
        self.assertTrue(
            np.allclose([round(2 * 20 / (365.25 * 24), 3), round(3 * 20 / (365.25 * 24), 3)],
            round(self.test_infra_hardware.instances_fabrication_footprint, 3).magnitude))

    def test_energy_footprints(self):
        self.test_infra_hardware.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        self.test_infra_hardware.update_instances_energy()
        self.test_infra_hardware.update_energy_footprint()
        self.assertEqual(u.kg, self.test_infra_hardware.energy_footprint.unit)
        self.assertTrue(np.allclose([0.2, 0.4],
                         self.test_infra_hardware.energy_footprint.magnitude))
        del self.test_infra_hardware.average_carbon_intensity
        self.assertIsNone(getattr(self.test_infra_hardware, "average_carbon_intensity", None))
