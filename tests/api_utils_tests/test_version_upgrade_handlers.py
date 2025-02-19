from efootprint.api_utils.version_upgrade_handlers import upgrade_version_9_to_10

from unittest import TestCase


class TestVersionUpgradeHandlers(TestCase):
    def test_upgrade_9_to_10(self):
        input_dict = {"a": 1, "Hardware": 2}
        expected_output = {"a": 1, "Device": 2}

        output_dict = upgrade_version_9_to_10(input_dict)

        self.assertEqual(output_dict, expected_output)