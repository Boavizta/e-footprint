from unittest import TestCase
from unittest.mock import MagicMock

from footprint_model.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from footprint_model.constants.units import u
from footprint_model.constants.sources import SourceValue, Sources
from footprint_model.core.hardware.device_population import DevicePopulation


class TestDevicePopulation(TestCase):
    def setUp(self):
        country = MagicMock()
        country.average_carbon_intensity = ExplainableQuantity(100 * u.g / u.kWh)
        self.device1 = MagicMock()
        self.device1.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device1.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device1.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        self.device2 = MagicMock()
        self.device2.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device2.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device2.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)

        self.device_population = DevicePopulation("Population", 2000, country, [self.device1, self.device2])
        self.usage_pattern = MagicMock()
        self.device_population.usage_patterns = {self.usage_pattern}
        self.usage_pattern.user_journey_freq = ExplainableQuantity(365.25 * u.user_journey / u.year)
        self.usage_pattern.user_journey.duration = ExplainableQuantity(1 * u.hour / u.user_journey)

    def test_power(self):
        test_device1 = MagicMock()
        test_device1.power = ExplainableQuantity(5 * u.W)
        test_device2 = MagicMock()
        test_device2.power = ExplainableQuantity(10 * u.W)

        self.device_population.devices = [test_device1, test_device2]
        self.device_population.update_power()

        self.assertEqual(365.25 * 15 * 1e-3 * u.kWh / u.year, self.device_population.power.value)

    def test_energy_footprint(self):
        self.device_population.power = ExplainableQuantity(1000 * u.kWh / u.year)
        self.device_population.update_energy_footprint()
        self.assertEqual(100 * u.kg / u.year, self.device_population.energy_footprint.value)

    def test_fabrication_footprint(self):
        self.device_population.update_fabrication_footprint()
        self.assertEqual(2 * 5 * u.kg / u.year, round(self.device_population.fabrication_footprint.value, 2))
