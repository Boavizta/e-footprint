from unittest import TestCase

import numpy as np

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from tests.utils import attach_input, recompute_attribute


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

            @computed_attribute
            def raw_nb_of_instances(self):
                return create_source_hourly_values_from_list([1.5, 3])

            @computed_attribute
            def nb_of_instances(self):
                return create_source_hourly_values_from_list([2, 3])

            @computed_attribute
            def instances_energy(self):
                return create_source_hourly_values_from_list([2, 4], pint_unit=u.kWh)

        self.test_infra_hardware = InfraHardwareTestClass(
            "test_infra_hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_DATA),
            power=SourceValue(2 * u.W, Sources.USER_DATA), lifespan=SourceValue(6 * u.years))

    def test_instances_fabrication_footprint(self):
        recompute_attribute(self.test_infra_hardware, "nb_of_instances")
        recompute_attribute(self.test_infra_hardware, "instances_fabrication_footprint")
        self.assertEqual(u.kg, self.test_infra_hardware.instances_fabrication_footprint.unit)
        self.assertTrue(
            np.allclose([round(2 * 20 / (365.25 * 24), 3), round(3 * 20 / (365.25 * 24), 3)],
            round(self.test_infra_hardware.instances_fabrication_footprint, 3).magnitude))

    def test_energy_footprints(self):
        attach_input(
            self.test_infra_hardware, "average_carbon_intensity", SourceValue(100 * u.g / u.kWh))
        recompute_attribute(self.test_infra_hardware, "instances_energy")
        recompute_attribute(self.test_infra_hardware, "energy_footprint")
        self.assertEqual(u.kg, self.test_infra_hardware.energy_footprint.unit)
        self.assertTrue(np.allclose([0.2, 0.4],
                         self.test_infra_hardware.energy_footprint.magnitude))
        del self.test_infra_hardware.average_carbon_intensity
        self.assertIsNone(getattr(self.test_infra_hardware, "average_carbon_intensity", None))
