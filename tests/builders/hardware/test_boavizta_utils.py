import os
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi_from_package_dependency, \
    call_boaviztapi_from_web_request
import efootprint.builders.hardware.boaviztapi_utils as boaviztapi_utils
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
            try:
                web_request_result = call_boaviztapi_from_web_request(url, params=params)
            except requests.RequestException as exc:
                self.skipTest(f"Boavizta API not reachable: {exc}")

            self.maxDiff = None

            if (isinstance(web_request_result, dict) and "verbose" in web_request_result.keys()
                    and "params" in web_request_result["verbose"]["CPU-1"].keys()):
                web_request_result["verbose"]["CPU-1"].pop("params")
                package_dependency_result["verbose"]["CPU-1"].pop("params")

            self.assertEqual(package_dependency_result, web_request_result)


class TestBoaviztaUtilsCache(TestCase):
    def setUp(self):
        boaviztapi_utils._boaviztapi_cache.clear()
        boaviztapi_utils._boaviztapi_cache_size_bytes = 0
        os.environ.pop("USE_BOAVIZTAPI_PACKAGE", None)

    def test_cache_hit_avoids_second_request(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch("efootprint.builders.hardware.boaviztapi_utils.requests.get", return_value=response) as get_mock:
            result_first = boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes")
            result_second = boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes")
        self.assertEqual(result_first, {"ok": True})
        self.assertEqual(result_second, {"ok": True})
        self.assertEqual(get_mock.call_count, 1)

    def test_cache_key_includes_json_payload(self):
        response = Mock(status_code=200)
        response.json.side_effect = [{"ok": "a"}, {"ok": "b"}]
        with patch("efootprint.builders.hardware.boaviztapi_utils.requests.post", return_value=response) as post_mock:
            result_first = boaviztapi_utils.call_boaviztapi(
                "https://api.boavizta.org/v1/server/", method="POST", json={"model": "a"})
            result_second = boaviztapi_utils.call_boaviztapi(
                "https://api.boavizta.org/v1/server/", method="POST", json={"model": "b"})
        self.assertEqual(result_first, {"ok": "a"})
        self.assertEqual(result_second, {"ok": "b"})
        self.assertEqual(post_mock.call_count, 2)

    def test_fifo_eviction_by_size(self):
        response = Mock(status_code=200)
        response.json.side_effect = [{"value": "first"}, {"value": "second"}, {"value": "third"}]
        with patch("efootprint.builders.hardware.boaviztapi_utils._BOAVIZTAPI_CACHE_MAX_BYTES", 250):
            with patch("efootprint.builders.hardware.boaviztapi_utils.requests.get", return_value=response):
                boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes", params={"k": "1"})
                boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes", params={"k": "2"})
                boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes", params={"k": "3"})
        key_first = boaviztapi_utils._make_cache_key(
            "https://api.boavizta.org/v1/server/archetypes", "GET", {"k": "1"}, None)
        key_second = boaviztapi_utils._make_cache_key(
            "https://api.boavizta.org/v1/server/archetypes", "GET", {"k": "2"}, None)
        key_third = boaviztapi_utils._make_cache_key(
            "https://api.boavizta.org/v1/server/archetypes", "GET", {"k": "3"}, None)
        self.assertNotIn(key_first, boaviztapi_utils._boaviztapi_cache)
        self.assertIn(key_second, boaviztapi_utils._boaviztapi_cache)
        self.assertIn(key_third, boaviztapi_utils._boaviztapi_cache)

    def test_ttl_expiry_forces_refresh(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch("efootprint.builders.hardware.boaviztapi_utils.requests.get", return_value=response) as get_mock:
            boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes")
            for key, (value, entry_size, _) in list(boaviztapi_utils._boaviztapi_cache.items()):
                boaviztapi_utils._boaviztapi_cache[key] = (value, entry_size, 0)
            boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes")
        self.assertEqual(get_mock.call_count, 2)

    def test_package_dependency_mode_bypasses_cache(self):
        os.environ["USE_BOAVIZTAPI_PACKAGE"] = "1"
        with patch("efootprint.builders.hardware.boaviztapi_utils.call_boaviztapi_from_package_dependency",
                   return_value={"ok": True}) as package_mock:
            result = boaviztapi_utils.call_boaviztapi("https://api.boavizta.org/v1/server/archetypes")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(package_mock.call_count, 1)
        self.assertEqual(len(boaviztapi_utils._boaviztapi_cache), 0)
