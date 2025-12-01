"""Validation test to ensure code and FromJson variants have identical test methods.

With the AutoTestMethodsMeta metaclass, test methods are auto-generated from run_test_*
methods in base classes, so this validation is now automatic. This test remains as a
sanity check.
"""
import inspect
from unittest import TestCase


def get_test_method_names(cls):
    return [
        name for name, member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if name.startswith('test_')
    ]


def compare_class_methods(class1, class2):
    """Verify two classes have the same test methods."""
    methods1 = set(get_test_method_names(class1))
    methods2 = set(get_test_method_names(class2))

    only_in_class1 = methods1 - methods2
    only_in_class2 = methods2 - methods1

    if only_in_class1:
        raise ValueError(f"Methods only in {class1.__name__}: {sorted(only_in_class1)}")
    if only_in_class2:
        raise ValueError(f"Methods only in {class2.__name__}: {sorted(only_in_class2)}")


class TestIntegrationTestFromJsonAndCodeImplementSameMethods(TestCase):
    def test_methods_integration_tests_from_json_and_code(self):
        from tests.integration_tests.test_integration_complex_system import IntegrationTestComplexSystem
        from tests.integration_tests.test_integration_complex_system_from_json import \
            IntegrationTestComplexSystemFromJson
        from tests.integration_tests.test_integration_services import IntegrationTestServices
        from tests.integration_tests.test_integration_services_from_json import IntegrationTestServicesFromJson
        from tests.integration_tests.test_integration_simple_system import IntegrationTestSimpleSystem
        from tests.integration_tests.test_integration_simple_system_from_json import IntegrationTestSimpleSystemFromJson
        from tests.integration_tests.test_integration_simple_edge_system import IntegrationTestSimpleEdgeSystem
        from tests.integration_tests.test_integration_simple_edge_system_from_json import (
            IntegrationTestSimpleEdgeSystemFromJson)

        compare_class_methods(IntegrationTestSimpleSystem, IntegrationTestSimpleSystemFromJson)
        compare_class_methods(IntegrationTestSimpleEdgeSystem, IntegrationTestSimpleEdgeSystemFromJson)
        compare_class_methods(IntegrationTestServices, IntegrationTestServicesFromJson)
        compare_class_methods(IntegrationTestComplexSystem, IntegrationTestComplexSystemFromJson)
