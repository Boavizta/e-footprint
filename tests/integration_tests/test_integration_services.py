from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
from tests.integration_tests.integration_test_base_class import AutoTestMethodsMeta


class IntegrationTestServices(IntegrationTestServicesBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for services system created from code.

    Test methods are auto-generated from run_test_* methods in the base class.
    """
    pass
