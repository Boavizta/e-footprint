from efootprint.api_utils.version_upgrade_handlers import upgrade_version_9_to_10, upgrade_version_10_to_11, \
    upgrade_version_11_to_12

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

    def test_upgrade_10_to_11(self):
        input_dict = {
            "System": {
                "syst_1": {"key": {"key": 1}},
                "syst_2": {"key": {"key": 2}},
            },
            "BoaviztaCloudServer": {
                "server1":{
                    "key": {"key": 3},
                    "server_utilization_rate": {"key": {"key": 4}},
                },
                "server2": {
                    "key": {"key": 3},
                    "server_utilization_rate": {"key": {"key": 4}},
                },
            },
            "GPUServer": {
                "server1":{
                    "key": {"key": 3},
                    "server_utilization_rate": {"key": {"key": 4}},
                },
            },
            # Server voluntarily missing
        }
        expected_output = {
            "System": {
                "syst_1": {"key": {"key": 1}, "edge_usage_patterns": []},
                "syst_2": {"key": {"key": 2}, "edge_usage_patterns": []},
            },
            "BoaviztaCloudServer": {
                "server1":{
                    "key": {"key": 3},
                    "utilization_rate": {"key": {"key": 4}},
                },
                "server2": {
                    "key": {"key": 3},
                    "utilization_rate": {"key": {"key": 4}},
                },
            },
            "GPUServer": {
                "server1":{
                    "key": {"key": 3},
                    "utilization_rate": {"key": {"key": 4}},
                },
            },
        }

        output_dict = upgrade_version_10_to_11(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_11_to_12(self):
        input_dict = {
            "EdgeDevice": {"key": {"key": 1}}, "a": {"key": {"key": 2}},
            "EdgeUsageJourney": {"key": {"edge_device": "uuid-EdgeDevice"}}
        }
        expected_output = {
            "EdgeComputer": {"key": {"key": 1}}, "a": {"key": {"key": 2}},
            "EdgeUsageJourney": {"key": {"edge_computer": "uuid-EdgeDevice"}}
        }
        output_dict = upgrade_version_11_to_12(input_dict)

        self.assertEqual(output_dict, expected_output)
