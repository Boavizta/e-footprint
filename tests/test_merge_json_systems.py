import unittest
from unittest import TestCase

import efootprint
from efootprint.utils.merge_json_systems import merge_json_systems


def _make_system_dict(system_id, usage_pattern_ids, extra_classes=None):
    system_dict = {
        "efootprint_version": efootprint.__version__,
        "System": {
            system_id: {
                "name": system_id,
                "id": system_id,
                "usage_patterns": list(usage_pattern_ids),
                "edge_usage_patterns": [],
            }
        },
    }
    if extra_classes:
        system_dict.update(extra_classes)
    return system_dict


class TestMergeJsonSystems(TestCase):
    def test_merges_usage_patterns_under_single_merged_system_entry(self):
        """Test usage patterns of all input systems are concatenated under a single 'Merged system' entry."""
        sys_a = _make_system_dict(
            "system-a", ["up-a"],
            extra_classes={"UsagePattern": {"up-a": {"id": "up-a", "name": "up a"}}})
        sys_b = _make_system_dict(
            "system-b", ["up-b"],
            extra_classes={"UsagePattern": {"up-b": {"id": "up-b", "name": "up b"}}})

        merged = merge_json_systems([sys_a, sys_b])

        self.assertEqual(efootprint.__version__, merged["efootprint_version"])
        self.assertEqual(1, len(merged["System"]))
        merged_system = next(iter(merged["System"].values()))
        self.assertEqual("Merged system", merged_system["name"])
        self.assertEqual(["up-a", "up-b"], merged_system["usage_patterns"])
        self.assertEqual([], merged_system["edge_usage_patterns"])
        self.assertEqual({"up-a", "up-b"}, set(merged["UsagePattern"].keys()))

        # Idempotency: merging the same inputs produces the same merged system id.
        self.assertEqual(merged["System"], merge_json_systems([sys_a, sys_b])["System"])

    def test_colliding_ids_are_suffixed_per_system_index_in_every_copy(self):
        """Test an id that appears in multiple input systems is suffixed with -X in every copy and in references."""
        sys_0 = _make_system_dict(
            "sys-0", ["up-0"],
            extra_classes={
                "UsagePattern": {"up-0": {"id": "up-0", "name": "up 0", "server": "shared-server"}},
                "Server": {"shared-server": {"id": "shared-server", "name": "shared server 0"}},
            })
        sys_1 = _make_system_dict(
            "sys-1", ["up-1"],
            extra_classes={
                "UsagePattern": {"up-1": {"id": "up-1", "name": "up 1", "server": "shared-server"}},
                "Server": {"shared-server": {"id": "shared-server", "name": "shared server 1"}},
            })

        merged = merge_json_systems([sys_0, sys_1])

        self.assertEqual({"shared-server-0", "shared-server-1"}, set(merged["Server"].keys()))
        self.assertEqual("shared-server-0", merged["Server"]["shared-server-0"]["id"])
        self.assertEqual("shared-server-1", merged["Server"]["shared-server-1"]["id"])
        self.assertEqual("shared-server-0", merged["UsagePattern"]["up-0"]["server"])
        self.assertEqual("shared-server-1", merged["UsagePattern"]["up-1"]["server"])
        # Non-colliding ids are left untouched.
        self.assertEqual({"up-0", "up-1"}, set(merged["UsagePattern"].keys()))


if __name__ == "__main__":
    unittest.main()
