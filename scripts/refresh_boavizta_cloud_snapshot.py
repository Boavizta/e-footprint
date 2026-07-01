"""Maintainer script: refresh the bundled Boavizta cloud-instance snapshot from the live API.

`BoaviztaCloudServer` validates its `provider` / `instance_type` inputs against this on-disk
snapshot instead of calling the API at import time (see specs/features/boavizta-import-time-fix).
Run this script periodically / before a release to pick up providers and instance types Boavizta
has added since the last refresh, and commit the resulting JSON diff. See RELEASE_PROCESS.md.

Usage:
    python scripts/refresh_boavizta_cloud_snapshot.py
"""
import json
from pathlib import Path

from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi_from_web_request

SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent
    / "efootprint" / "builders" / "hardware" / "boavizta_cloud_instances_snapshot.json")


def refresh_snapshot():
    providers = call_boaviztapi_from_web_request("https://api.boavizta.org/v1/cloud/instance/all_providers")
    instances_by_provider = {
        provider: call_boaviztapi_from_web_request(
            "https://api.boavizta.org/v1/cloud/instance/all_instances", params={"provider": provider})
        for provider in providers
    }

    snapshot = {"providers": providers, "instances_by_provider": instances_by_provider}
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")

    nb_instance_types = sum(len(instance_types) for instance_types in instances_by_provider.values())
    print(f"Wrote {SNAPSHOT_PATH} with {len(providers)} providers and {nb_instance_types} instance types.")


if __name__ == "__main__":
    refresh_snapshot()
