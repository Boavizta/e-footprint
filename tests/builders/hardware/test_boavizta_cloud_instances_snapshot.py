import json
import subprocess
import sys
import textwrap
import unittest

import requests

from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi_from_web_request
from efootprint.builders.hardware.boavizta_cloud_server import BOAVIZTA_CLOUD_SNAPSHOT_PATH


class TestBoaviztaCloudInstancesSnapshot(unittest.TestCase):
    def test_snapshot_file_exists_and_is_well_formed(self):
        snapshot = json.loads(BOAVIZTA_CLOUD_SNAPSHOT_PATH.read_text())

        self.assertIn("providers", snapshot)
        self.assertIn("instances_by_provider", snapshot)
        self.assertTrue(snapshot["providers"], "Snapshot has no providers")

        for provider in snapshot["providers"]:
            self.assertIn(provider, snapshot["instances_by_provider"], f"No instance types for provider {provider}")
            self.assertTrue(snapshot["instances_by_provider"][provider], f"Empty instance type list for {provider}")


class TestBoaviztaCloudInstancesSnapshotSyncedWithLiveApi(unittest.TestCase):
    def test_snapshot_matches_live_boaviztapi_data(self):
        """
        Guards against the bundled snapshot silently drifting from the live Boavizta API. Skipped
        when the API is unreachable; failures here mean scripts/refresh_boavizta_cloud_snapshot.py
        should be run and the resulting JSON diff committed.
        """
        try:
            live_providers = call_boaviztapi_from_web_request(
                "https://api.boavizta.org/v1/cloud/instance/all_providers")
        except requests.RequestException as exc:
            self.skipTest(f"Boavizta API not reachable: {exc}")

        snapshot = json.loads(BOAVIZTA_CLOUD_SNAPSHOT_PATH.read_text())
        self.assertEqual(
            sorted(snapshot["providers"]), sorted(live_providers),
            "Snapshot provider list is out of sync with the live Boavizta API. "
            "Run scripts/refresh_boavizta_cloud_snapshot.py to refresh it.")

        for provider in live_providers:
            live_instance_types = call_boaviztapi_from_web_request(
                "https://api.boavizta.org/v1/cloud/instance/all_instances", params={"provider": provider})
            self.assertEqual(
                sorted(snapshot["instances_by_provider"][provider]), sorted(live_instance_types),
                f"Snapshot instance types for provider {provider} are out of sync with the live Boavizta API. "
                f"Run scripts/refresh_boavizta_cloud_snapshot.py to refresh it.")


if __name__ == "__main__":
    unittest.main()
