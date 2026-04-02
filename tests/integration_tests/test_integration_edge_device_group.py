from tests.integration_tests.integration_edge_device_group_base_class import IntegrationEdgeDeviceGroupBaseClass
from tests.integration_tests.integration_test_base_class import AutoTestMethodsMeta


class IntegrationTestEdgeDeviceGroup(IntegrationEdgeDeviceGroupBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for EdgeDeviceGroup hierarchy created from code."""
