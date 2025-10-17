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
            "EdgeDevice": {
                "edge_device_1": {
                    "name": "My Edge Device",
                    "id": "edge_device_1",
                    "some_attribute": "value"
                }
            },
            "RecurrentEdgeProcess": {
                "process_1": {
                    "name": "My Process",
                    "id": "process_1",
                    "recurrent_compute_needed": {}
                },
                "process_2": {
                    "name": "My Process 2",
                    "id": "process_2",
                    "recurrent_compute_needed": {}
                }
            },
            "EdgeUsageJourney": {
                "journey_1": {
                    "name": "My Journey",
                    "id": "journey_1",
                    "edge_device": "edge_device_1",
                    "edge_processes": ["process_1", "process_2"],
                    "usage_span": {}
                }
            },
            "OtherClass": {"key": {"key": 1}}
        }
        expected_output = {
            "EdgeComputer": {
                "edge_device_1": {
                    "name": "My Edge Device",
                    "id": "edge_device_1",
                    "some_attribute": "value"
                }
            },
            "RecurrentEdgeProcess": {
                "process_1": {
                    "name": "My Process",
                    "id": "process_1",
                    "recurrent_compute_needed": {},
                    "edge_device": "edge_device_1"
                },
                "process_2": {
                    "name": "My Process 2",
                    "id": "process_2",
                    "recurrent_compute_needed": {},
                    "edge_device": "edge_device_1"
                }
            },
            "EdgeFunction": {
                "ef_journey_1": {
                    "name": "Edge function for edge usage journey My Journey",
                    "id": "ef_journey_1",
                    "recurrent_edge_resource_needs": ["process_1", "process_2"]
                }
            },
            "EdgeUsageJourney": {
                "journey_1": {
                    "name": "My Journey",
                    "id": "journey_1",
                    "edge_functions": ["ef_journey_1"],
                    "usage_span": {}
                }
            },
            "OtherClass": {"key": {"key": 1}}
        }
        output_dict = upgrade_version_11_to_12(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_11_to_12_with_empty_edge_processes(self):
        input_dict = {
            "EdgeUsageJourney": {
                "journey_1": {
                    "name": "My Journey",
                    "id": "journey_1",
                    "edge_device": "edge_device_1",
                    "edge_processes": [],
                    "usage_span": {}
                }
            }
        }
        expected_output = {
            "EdgeFunction": {
                "ef_journey_1": {
                    "name": "Edge function for edge usage journey My Journey",
                    "id": "ef_journey_1",
                    "recurrent_edge_resource_needs": []
                }
            },
            "EdgeUsageJourney": {
                "journey_1": {
                    "name": "My Journey",
                    "id": "journey_1",
                    "edge_functions": ["ef_journey_1"],
                    "usage_span": {}
                }
            }
        }
        output_dict = upgrade_version_11_to_12(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_11_to_12_without_edge_usage_journey(self):
        input_dict = {
            "EdgeDevice": {
                "edge_device_1": {
                    "name": "My Edge Device",
                    "id": "edge_device_1"
                }
            }
        }
        expected_output = {
            "EdgeComputer": {
                "edge_device_1": {
                    "name": "My Edge Device",
                    "id": "edge_device_1"
                }
            }
        }
        output_dict = upgrade_version_11_to_12(input_dict)

        self.assertEqual(output_dict, expected_output)
