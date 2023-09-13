from footprint_model.constants.countries import Country
from footprint_model.constants.physical_elements import InfraHardware, ObjectLinkedToUsagePatterns
from footprint_model.constants.explainable_quantities import ExplainableQuantity, ExplainableHourlyUsage
from footprint_model.constants.sources import SourceValue, Sources
from footprint_model.constants.units import u
from tests.utils import create_cpu_need, create_ram_need

from copy import deepcopy
from unittest import TestCase
from unittest.mock import MagicMock


class TestInfraHardware(TestCase):
    def setUp(self):
        class InfraHardwareTestClass(InfraHardware):
            def __init__(self, name: str, carbon_footprint_fabrication: SourceValue, power: SourceValue,
                         lifespan: SourceValue, country: Country):
                super().__init__(name, carbon_footprint_fabrication, power, lifespan, country)
                self.services__raw = set()

            def update_nb_of_instances(self):
                self.nb_of_instances = ExplainableQuantity(2 * u.dimensionless)

            def update_instances_power(self):
                self.instances_power = ExplainableQuantity(16 * u.W)

            @property
            def services(self):
                return self.services__raw

        test_country = MagicMock()
        test_country.average_carbon_intensity = ExplainableQuantity(100 * u.g / u.kWh)
        self.test_infra_hardware = InfraHardwareTestClass(
            "test_infra_hardware", carbon_footprint_fabrication=SourceValue(120 * u.kg, Sources.USER_INPUT),
            power=SourceValue(2 * u.W, Sources.USER_INPUT), lifespan=SourceValue(6 * u.years, Sources.HYPOTHESIS),
            country=test_country)

        self.usage_pattern_single_service = MagicMock()
        self.service1 = MagicMock()
        self.ram_needs_service1 = create_ram_need([[0, 8]])
        self.cpu_needs_service1 = create_cpu_need([[0, 8]])
        self.test_infra_hardware_single_service = deepcopy(self.test_infra_hardware)
        self.test_infra_hardware_single_service.usage_patterns = {self.usage_pattern_single_service}
        self.service1.hour_by_hour_ram_need = self.ram_needs_service1
        self.service1.hour_by_hour_cpu_need = self.cpu_needs_service1
        self.test_infra_hardware_single_service.services__raw = {self.service1}

        self.usage_pattern_multiple_services = MagicMock()
        self.service2 = MagicMock()
        self.service3 = MagicMock()
        self.ram_needs_service2 = create_ram_need([[6, 14]])
        self.ram_needs_service3 = create_ram_need([[8, 16]])
        self.cpu_needs_service2 = create_cpu_need([[6, 14]])
        self.cpu_needs_service3 = create_cpu_need([[8, 16]])
        self.test_infra_hardware_multiple_services = deepcopy(self.test_infra_hardware)
        self.test_infra_hardware_multiple_services.usage_patterns = {self.usage_pattern_multiple_services}
        self.service2.hour_by_hour_ram_need = self.ram_needs_service2
        self.service3.hour_by_hour_ram_need = self.ram_needs_service3
        self.service2.hour_by_hour_cpu_need = self.cpu_needs_service2
        self.service3.hour_by_hour_cpu_need = self.cpu_needs_service3
        self.test_infra_hardware_multiple_services.services__raw = {self.service2, self.service3}

    def test_update_all_services_ram_needs_single_service(self):
        expected_value = ExplainableHourlyUsage([ExplainableQuantity(0 * u.Go)] * 24)
        for i in range(8):
            expected_value.value[i] = ExplainableQuantity(100 * u.Go)

        self.test_infra_hardware_single_service.update_all_services_ram_needs()
        self.assertEqual(expected_value.value, self.test_infra_hardware_single_service.all_services_ram_needs.value)

    def test_all_services_infra_needs_multiple_services(self):
        expected_value = ExplainableHourlyUsage([ExplainableQuantity(0 * u.Go)] * 24)
        for i in range(6, 8):
            expected_value.value[i] = ExplainableQuantity(100 * u.Go)
        for i in range(8, 14):
            expected_value.value[i] = ExplainableQuantity(200 * u.Go)
        for i in range(14, 16):
            expected_value.value[i] = ExplainableQuantity(100 * u.Go)

        self.test_infra_hardware_multiple_services.update_all_services_ram_needs()
        self.assertEqual(expected_value.value, self.test_infra_hardware_multiple_services.all_services_ram_needs.value)

    def test_all_services_cpu_needs_single_service(self):
        expected_value = ExplainableHourlyUsage([ExplainableQuantity(0 * u.core)] * 24)
        for i in range(8):
            expected_value.value[i] = ExplainableQuantity(1 * u.core)

        self.test_infra_hardware_single_service.update_all_services_cpu_needs()
        self.assertEqual(expected_value.value, self.test_infra_hardware_single_service.all_services_cpu_needs.value)

    def test_all_services_cpu_needs_multiple_services(self):
        expected_value = ExplainableHourlyUsage([ExplainableQuantity(0 * u.core)] * 24)
        for i in range(6, 8):
            expected_value.value[i] = ExplainableQuantity(1 * u.core)
        for i in range(8, 14):
            expected_value.value[i] = ExplainableQuantity(2 * u.core)
        for i in range(14, 16):
            expected_value.value[i] = ExplainableQuantity(1 * u.core)

        self.test_infra_hardware_multiple_services.update_all_services_cpu_needs()
        self.assertEqual(expected_value.value, self.test_infra_hardware_multiple_services.all_services_cpu_needs.value)

    def test_fraction_of_time_in_use_single_service(self):
        expected_value = ExplainableQuantity(((24 - 16) / 24) * u.dimensionless, "fraction_of_time_in_use")
        self.test_infra_hardware_single_service.update_all_services_ram_needs()
        self.test_infra_hardware_single_service.update_all_services_cpu_needs()
        self.test_infra_hardware_single_service.update_fraction_of_time_in_use()
        self.assertEqual(expected_value.value, self.test_infra_hardware_single_service.fraction_of_time_in_use.value)

    def test_fraction_of_time_in_use_multiple_services_with_different_usage(self):
        expected_value = ExplainableQuantity(((24 - 14) / 24) * u.dimensionless, "fraction_of_time_in_use")
        self.test_infra_hardware_multiple_services.update_all_services_ram_needs()
        self.test_infra_hardware_multiple_services.update_all_services_cpu_needs()
        self.test_infra_hardware_multiple_services.update_fraction_of_time_in_use()
        self.assertEqual(expected_value.value, self.test_infra_hardware_multiple_services.fraction_of_time_in_use.value)

    def test_instances_fabrication_footprint(self):
        self.test_infra_hardware_single_service.update_nb_of_instances()
        self.test_infra_hardware_single_service.update_instances_fabrication_footprint()
        self.assertEqual(
            40 * u.kg / u.year, self.test_infra_hardware_single_service.instances_fabrication_footprint.value)

    def test_energy_footprints(self):
        self.test_infra_hardware_single_service.update_instances_power()
        self.test_infra_hardware_single_service.update_energy_footprint()
        self.assertEqual(
            round(16 * 24 * 365.25 * 100 * 1e-6 * u.kg / u.year, 2),
            round(self.test_infra_hardware_single_service.energy_footprint.value, 2))


class TestObjectLinkedToUsagePatterns(TestCase):
    def setUp(self):
        self.test_object_linked_to_usage_patterns = ObjectLinkedToUsagePatterns()

    def test_link_usage_pattern_should_return_same_set_if_usage_pattern_already_in_set(self):
        self.test_object_linked_to_usage_patterns.usage_patterns = {"usage_pattern_1"}
        self.test_object_linked_to_usage_patterns.link_usage_pattern("usage_pattern_1")
        self.assertEqual({"usage_pattern_1"}, self.test_object_linked_to_usage_patterns.usage_patterns)

    def test_link_usage_pattern_should_add_new_usage_pattern_to_usage_patterns_set(self):
        self.test_object_linked_to_usage_patterns.usage_patterns = {"usage_pattern_1"}
        self.test_object_linked_to_usage_patterns.link_usage_pattern("usage_pattern_2")
        self.assertEqual({"usage_pattern_1", "usage_pattern_2"}, self.test_object_linked_to_usage_patterns.usage_patterns)

    def test_unlink_usage_pattern(self):
        self.test_object_linked_to_usage_patterns.usage_patterns = {"usage_pattern_1"}
        self.test_object_linked_to_usage_patterns.unlink_usage_pattern("usage_pattern_1")
        self.assertEqual(set(), self.test_object_linked_to_usage_patterns.usage_patterns)