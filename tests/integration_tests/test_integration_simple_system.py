from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass
from tests.integration_tests.integration_test_base_class import AutoTestMethodsMeta


class IntegrationTestSimpleSystem(IntegrationTestSimpleSystemBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for simple system created from code.

    Test methods are auto-generated from run_test_* methods in the base class.
    """
    def test_system_calculation_graph_right_after_json_to_system(self):
        # Placeholder - this test only makes sense for the FromJson variant
        pass
