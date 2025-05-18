from efootprint.api_utils.version_upgrade_handlers import upgrade_version_9_to_10

from unittest import TestCase


class TestVersionUpgradeHandlers(TestCase):
    def test_upgrade_9_to_10(self):
        input_dict = {"a": {"key": {"key": 1}}, "Hardware": {"key": {"key": 2}}}
        expected_output = {"a": {"key": {"key": 1}}, "Device": {"key": {"key": 2}}}

        output_dict = upgrade_version_9_to_10(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_9_to_10_doesnt_break_when_no_hardware(self):
        input_dict = {"a": {"key": {"key": 1}}}
        expected_output = {"a": {"key": {"key": 1}}}

        output_dict = upgrade_version_9_to_10(input_dict)

        self.assertEqual(output_dict, expected_output)
