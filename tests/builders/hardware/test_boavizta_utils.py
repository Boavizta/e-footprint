from unittest import TestCase

from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi_from_package_dependency, \
    call_boaviztapi_from_web_request
from efootprint.logger import logger


class TestBoaviztaUtils(TestCase):
    def test_web_api_and_package_dependency_calls_return_same_results(self):
        """
        This test checks that the results from the web API and the package dependency are the same.
        It does this by comparing the results of a call to the Boavizta API using both methods.
        """
        for url, params in [
            ("https://api.boavizta.org/v1/cloud/instance/all_providers", {}),
            ("https://api.boavizta.org/v1/cloud/instance/all_instances", {"provider": "aws"}),
            ("https://api.boavizta.org/v1/cloud/instance", {"provider": "aws", "instance_type": "t2.micro"}),
            ("https://api.boavizta.org/v1/server/archetypes", {}),
            ("https://api.boavizta.org/v1/server/archetype_config", {"archetype": "platform_compute_low"}),
        ]:
            logger.info(f"Testing URL: {url} with params: {params} from package dependency")
            package_dependency_result = call_boaviztapi_from_package_dependency(url, params=params)
            web_request_result = call_boaviztapi_from_web_request(url, params=params)

            self.maxDiff = None

            if (isinstance(web_request_result, dict) and "verbose" in web_request_result.keys()
                    and "params" in web_request_result["verbose"]["CPU-1"].keys()):
                web_request_result["verbose"]["CPU-1"].pop("params")
                package_dependency_result["verbose"]["CPU-1"].pop("params")

            self.assertEqual(package_dependency_result, web_request_result)
