import inspect
from unittest import TestCase


def get_test_method_names(cls):
    return [
        name for name, member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if name.startswith('test_')
    ]

def get_run_method_names(cls):
    return [
        name.replace("run_", "") for name, member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if name.startswith('run_')
    ]

def compare_class_methods(implementation_class, base_class):
    methods1 = get_test_method_names(implementation_class)
    methods2 = get_run_method_names(base_class)

    only_in_implementation_class = set(methods1) - set(methods2)
    only_in_base_class = set(methods2) - set(methods1)

    if only_in_implementation_class:
        raise ValueError(f"❌ Methods only in {implementation_class.__name__} and not in {base_class.__name__}: "
                         f"{sorted(only_in_implementation_class)}")
    if only_in_base_class:
        raise ValueError(f"❌ Methods only in {base_class.__name__} and not in {implementation_class.__name__}: "
                         f"{sorted(only_in_base_class)}")

    print(f"{implementation_class.__name__} and {base_class.__name__}: implement the same methods")


class TestIntegrationTestFromJsonAndCodeImplementSameMethods(TestCase):
    def test_methods_integration_tests_from_json_and_code(self):
        from tests.integration_tests.integration_complex_system_base_class import IntegrationTestComplexSystemBaseClass
        from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
        from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass
        from tests.integration_tests.integration_simple_edge_system_base_class import (
            IntegrationTestSimpleEdgeSystemBaseClass)
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

        compare_class_methods(IntegrationTestSimpleSystem, IntegrationTestSimpleSystemBaseClass)
        compare_class_methods(IntegrationTestSimpleSystemFromJson, IntegrationTestSimpleSystemBaseClass)
        compare_class_methods(IntegrationTestSimpleEdgeSystem, IntegrationTestSimpleEdgeSystemBaseClass)
        compare_class_methods(IntegrationTestSimpleEdgeSystemFromJson, IntegrationTestSimpleEdgeSystemBaseClass)
        compare_class_methods(IntegrationTestServices, IntegrationTestServicesBaseClass)
        compare_class_methods(IntegrationTestServicesFromJson, IntegrationTestServicesBaseClass)
        compare_class_methods(IntegrationTestComplexSystem, IntegrationTestComplexSystemBaseClass)
        compare_class_methods(IntegrationTestComplexSystemFromJson, IntegrationTestComplexSystemBaseClass)

if __name__ == '__main__':
    from tests.integration_tests.integration_simple_edge_system_base_class import \
        IntegrationTestSimpleEdgeSystemBaseClass

    for meth in get_run_method_names(IntegrationTestSimpleEdgeSystemBaseClass):
        print(f"def {meth}(self):\n    self.{meth.replace('test_', 'run_test_')}()")
