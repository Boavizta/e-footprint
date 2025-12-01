from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass
from tests.integration_tests.integration_test_base_class import AutoTestMethodsMeta


class IntegrationTestSimpleEdgeSystem(IntegrationTestSimpleEdgeSystemBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for simple edge system created from code.

    Test methods are auto-generated from run_test_* methods in the base class.
    """
    def test_system_calculation_graph_right_after_json_to_system(self):
        # Placeholder - this test only makes sense for the FromJson variant
        pass
