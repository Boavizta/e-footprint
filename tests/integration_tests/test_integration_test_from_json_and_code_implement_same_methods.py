import inspect
from unittest import TestCase


def get_method_names(cls):
    return {
        name for name, member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith('__')
    }


def compare_class_methods(cls1, cls2):
    methods1 = get_method_names(cls1)
    methods2 = get_method_names(cls2)

    only_in_cls1 = methods1 - methods2
    only_in_cls2 = methods2 - methods1

    if only_in_cls1:
        raise ValueError(f"❌ Methods only in {cls1.__name__}: {sorted(only_in_cls1)}")
    if only_in_cls2:
        raise ValueError(f"❌ Methods only in {cls2.__name__}: {sorted(only_in_cls2)}")


class TestIntegrationTestFromJsonAndCodeImplementSameMethods(TestCase):
    def test_methods_integration_tests_from_json_and_code(self):
        from tests.integration_tests.test_integration_complex_system import IntegrationTestComplexSystem
        from tests.integration_tests.test_integration_complex_system_from_json import \
            IntegrationTestComplexSystemFromJson
        from tests.integration_tests.test_integration_services import IntegrationTestServices
        from tests.integration_tests.test_integration_services_from_json import IntegrationTestServicesFromJson
        from tests.integration_tests.test_integration_simple_system import IntegrationTestSimpleSystem
        from tests.integration_tests.test_integration_simple_system_from_json import IntegrationTestSimpleSystemFromJson

        compare_class_methods(IntegrationTestSimpleSystem, IntegrationTestSimpleSystemFromJson)
        compare_class_methods(IntegrationTestServices, IntegrationTestServicesFromJson)
        compare_class_methods(IntegrationTestComplexSystem, IntegrationTestComplexSystemFromJson)
