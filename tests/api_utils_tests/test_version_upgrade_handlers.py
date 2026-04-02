from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.api_utils.version_upgrade_handlers import upgrade_version_9_to_10, upgrade_version_10_to_11, \
    upgrade_version_11_to_12, upgrade_version_12_to_13, upgrade_version_13_to_14, upgrade_version_14_to_15, \
    upgrade_version_15_to_16, upgrade_version_16_to_17, upgrade_version_18_to_19
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

from unittest import TestCase


class TestVersionUpgradeHandlers(TestCase):
    def test_upgrade_18_to_19(self):
        input_dict = {
            "EdgeCPUComponent": {
                "cpu_1": {
                    "carbon_footprint_fabrication": {"value": 20.0},
                    "power": {"value": 50.0},
                    "idle_power": {"value": 10.0},
                    "compute": {"value": 8.0},
                    "base_compute_consumption": {"value": 1.0},
                }
            },
            "EdgeRAMComponent": {
                "ram_1": {
                    "carbon_footprint_fabrication": {"value": 10.0},
                    "power": {"value": 0.0},
                    "idle_power": {"value": 0.0},
                    "ram": {"value": 16.0},
                    "base_ram_consumption": {"value": 2.0},
                }
            },
            "EdgeWorkloadComponent": {
                "workload_1": {
                    "carbon_footprint_fabrication": {"value": 100.0},
                    "power": {"value": 50.0},
                    "idle_power": {"value": 5.0},
                }
            },
            "EdgeStorage": {
                "storage_1": {
                    "carbon_footprint_fabrication_per_storage_capacity": {"value": 160.0},
                    "storage_capacity": {"value": 1.0},
                    "base_storage_need": {"value": 100.0},
                }
            },
        }
        expected_output = {
            "EdgeCPUComponent": {
                "cpu_1": {
                    "carbon_footprint_fabrication_per_unit": {"value": 20.0},
                    "power_per_unit": {"value": 50.0},
                    "idle_power_per_unit": {"value": 10.0},
                    "compute_per_unit": {"value": 8.0},
                    "base_compute_consumption": {"value": 1.0},
                    "nb_of_units": SourceValue(1 * u.dimensionless).to_json(),
                }
            },
            "EdgeRAMComponent": {
                "ram_1": {
                    "carbon_footprint_fabrication_per_unit": {"value": 10.0},
                    "power_per_unit": {"value": 0.0},
                    "idle_power_per_unit": {"value": 0.0},
                    "ram_per_unit": {"value": 16.0},
                    "base_ram_consumption": {"value": 2.0},
                    "nb_of_units": SourceValue(1 * u.dimensionless).to_json(),
                }
            },
            "EdgeWorkloadComponent": {
                "workload_1": {
                    "carbon_footprint_fabrication_per_unit": {"value": 100.0},
                    "power_per_unit": {"value": 50.0},
                    "idle_power_per_unit": {"value": 5.0},
                    "nb_of_units": SourceValue(1 * u.dimensionless).to_json(),
                }
            },
            "EdgeStorage": {
                "storage_1": {
                    "carbon_footprint_fabrication_per_storage_capacity": {"value": 160.0},
                    "storage_capacity_per_unit": {"value": 1.0},
                    "base_storage_need": {"value": 100.0},
                    "nb_of_units": SourceValue(1 * u.dimensionless).to_json(),
                }
            },
        }

        output_dict = upgrade_version_18_to_19(input_dict)

        self.assertEqual(output_dict, expected_output)

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

    def test_upgrade_12_to_13(self):
        """Test version 12 to 13 upgrade with inheritance checking for occurrence/concurrent/byte_ram units."""
        input_dict = {
            # UsagePattern base class - should apply to subclasses
            "UsagePattern": {
                "pattern_1": {
                    "name": "Basic Pattern",
                    "id": "pattern_1",
                    "hourly_usage_journey_starts": {
                        "compressed_values": [1, 2, 3],
                        "unit": "dimensionless",
                        "label": "hourly usage"
                    }
                }
            },
            # EdgeUsagePattern - separate from UsagePattern
            "EdgeUsagePattern": {
                "edge_pattern_1": {
                    "name": "Edge Pattern",
                    "id": "edge_pattern_1",
                    "hourly_edge_usage_journey_starts": {
                        "compressed_values": [10, 20],
                        "unit": "dimensionless",
                        "label": "edge starts"
                    }
                }
            },
            # JobBase - should apply to Job and GPUJob subclasses
            "Job": {
                "job_1": {
                    "name": "My Job",
                    "id": "job_1",
                    "ram_needed": {
                        "value": 512.0,
                        "unit": "MB",
                        "label": "RAM needed"
                    },
                }
            },
            "GPUJob": {
                "gpu_job_1": {
                    "name": "GPU Job",
                    "id": "gpu_job_1",
                    "ram_needed": {
                        "value": 1024.0,
                        "unit": "megabyte",
                        "label": "RAM needed"
                    }
                }
            },
            # ServerBase - should apply to Server, GPUServer subclasses
            "Server": {
                "server_1": {
                    "name": "My Server",
                    "id": "server_1",
                    "ram": {
                        "value": 64.0,
                        "unit": "GB",
                        "label": "Server RAM"
                    },
                    "base_ram_consumption": {
                        "value": 300.0,
                        "unit": "megabyte",
                        "label": "Base RAM"
                    }
                }
            },
            "GPUServer": {
                "gpu_server_1": {
                    "name": "GPU Server",
                    "id": "gpu_server_1",
                    "ram": {
                        "value": 128.0,
                        "unit": "gigabyte",
                        "label": "GPU Server RAM"
                    },
                    "ram_per_gpu": {
                        "value": 16.0,
                        "unit": "GB",
                        "label": "RAM per GPU"
                    }
                }
            },
            # Storage - not inheriting from ServerBase
            "Storage": {
                "storage_1": {
                    "name": "Storage",
                    "id": "storage_1"
                }
            },
            # RecurrentEdgeProcess
            "RecurrentEdgeProcess": {
                "process_1": {
                    "name": "Edge Process",
                    "id": "process_1",
                    "recurrent_ram_needed": {
                        "recurring_values": [512, 1024],
                        "unit": "megabyte",
                        "label": "recurrent RAM"
                    }
                }
            },
            # EdgeComputer
            "EdgeComputer": {
                "edge_comp_1": {
                    "name": "Edge Computer",
                    "id": "edge_comp_1",
                    "ram": {
                        "value": 4.0,
                        "unit": "GB",
                        "label": "Edge RAM"
                    },
                    "base_ram_consumption": {
                        "value": 100.0,
                        "unit": "MB",
                        "label": "Base RAM"
                    }
                }
            }
        }

        expected_output = {
            "UsagePattern": {
                "pattern_1": {
                    "name": "Basic Pattern",
                    "id": "pattern_1",
                    "hourly_usage_journey_starts": {
                        "compressed_values": [1, 2, 3],
                        "unit": "occurrence",
                        "label": "hourly usage"
                    },
                }
            },
            "EdgeUsagePattern": {
                "edge_pattern_1": {
                    "name": "Edge Pattern",
                    "id": "edge_pattern_1",
                    "hourly_edge_usage_journey_starts": {
                        "compressed_values": [10, 20],
                        "unit": "occurrence",
                        "label": "edge starts"
                    },
                }
            },
            "Job": {
                "job_1": {
                    "name": "My Job",
                    "id": "job_1",
                    "ram_needed": {
                        "value": 512.0,
                        "unit": "MB_ram",
                        "label": "RAM needed"
                    },
                }
            },
            "GPUJob": {
                "gpu_job_1": {
                    "name": "GPU Job",
                    "id": "gpu_job_1",
                    "ram_needed": {
                        "value": 1024.0,
                        "unit": "megabyte_ram",
                        "label": "RAM needed"
                    },
                }
            },
            "Server": {
                "server_1": {
                    "name": "My Server",
                    "id": "server_1",
                    "ram": {
                        "value": 64.0,
                        "unit": "GB_ram",
                        "label": "Server RAM"
                    },
                    "base_ram_consumption": {
                        "value": 300.0,
                        "unit": "megabyte_ram",
                        "label": "Base RAM"
                    },
                }
            },
            "GPUServer": {
                "gpu_server_1": {
                    "name": "GPU Server",
                    "id": "gpu_server_1",
                    "ram": {
                        "value": 128.0,
                        "unit": "gigabyte_ram",
                        "label": "GPU Server RAM"
                    },
                    "ram_per_gpu": {
                        "value": 16.0,
                        "unit": "GB_ram",
                        "label": "RAM per GPU"
                    },
                }
            },
            "Storage": {
                "storage_1": {
                    "name": "Storage",
                    "id": "storage_1",
                }
            },
            "RecurrentEdgeProcess": {
                "process_1": {
                    "name": "Edge Process",
                    "id": "process_1",
                    "recurrent_ram_needed": {
                        "recurring_values": [512, 1024],
                        "unit": "megabyte_ram",
                        "label": "recurrent RAM"
                    }
                }
            },
            "EdgeComputer": {
                "edge_comp_1": {
                    "name": "Edge Computer",
                    "id": "edge_comp_1",
                    "ram": {
                        "value": 4.0,
                        "unit": "GB_ram",
                        "label": "Edge RAM"
                    },
                    "base_ram_consumption": {
                        "value": 100.0,
                        "unit": "MB_ram",
                        "label": "Base RAM"
                    },
                }
            }
        }
        efootprint_classes_dict = {
            modeling_object_class.__name__: modeling_object_class
            for modeling_object_class in ALL_EFOOTPRINT_CLASSES
        }

        output_dict = upgrade_version_12_to_13(input_dict, efootprint_classes_dict)

        self.assertEqual(output_dict, expected_output)


    def test_upgrade_13_to_14(self):
        """Test version 13 to 14 upgrade."""
        input_dict = {
            "EdgeComputer": {
                "obj_1": {
                    "name": "Object 1",
                    "power_usage_effectiveness": "val",
                    "utilization_rate": "value",
                    "carbon_footprint_fabrication": "cff_val"
                },
                "obj_2": {
                    "power_usage_effectiveness": "val2",
                    "utilization_rate": "value2",
                    "carbon_footprint_fabrication": "cff_val"
                }
            },
            "EdgeFunction": {
                "func_1": {
                    "name": "Function 1",
                    "recurrent_edge_resource_needs": []
                },
                "func_2": {
                    "name": "Function 2",
                    "recurrent_edge_resource_needs": []
                }
            }
        }
        expected_output = {
            "EdgeComputer": {
                "obj_1": {
                    "name": "Object 1",
                    "carbon_footprint_fabrication": "cff_val",
                    "structure_carbon_footprint_fabrication": "cff_val"
                },
                "obj_2": {
                    "carbon_footprint_fabrication": "cff_val",
                    "structure_carbon_footprint_fabrication": "cff_val"
                }
            },
            "EdgeFunction": {
                "func_1": {
                    "name": "Function 1",
                    "recurrent_edge_device_needs": []
                },
                "func_2": {
                    "name": "Function 2",
                    "recurrent_edge_device_needs": []
                }
            }
        }

        output_dict = upgrade_version_13_to_14(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_14_to_15(self):
        """Test version 14 to 15: add default wifi network to EdgeUsagePatterns and recurrent_server_needs to EdgeFunctions."""
        input_dict = {
            "Network": {
                "existing_network": {"name": "Existing Network", "id": "existing_network"}},
            "EdgeUsagePattern": {
                "pattern_1": {"name": "Pattern 1", "id": "pattern_1"},
                "pattern_2": {"name": "Pattern 2", "id": "pattern_2"}},
            "EdgeFunction": {
                "func_1": {"name": "Function 1", "recurrent_edge_device_needs": []},
                "func_2": {"name": "Function 2", "recurrent_edge_device_needs": ["need_1"]}},
            "OtherClass": {"obj_1": {"name": "Object 1"}}}
        expected_output = {
            "Network": {
                "existing_network": {"name": "Existing Network", "id": "existing_network"},
                "default_wifi_network_for_edge": {
                    "name": "Default wifi network for edge",
                    "id": "default_wifi_network_for_edge",
                    "bandwidth_energy_intensity": {
                        "value": 0.05, "unit": "kilowatt_hour / gigabyte",
                        "label": "bandwith energy intensity of Default wifi network from e-footprint hypothesis",
                        "source": {"name": "e-footprint hypothesis", "link": None}
                    }}},
            "EdgeUsagePattern": {
                "pattern_1": {"name": "Pattern 1", "id": "pattern_1", "network": "default_wifi_network_for_edge"},
                "pattern_2": {"name": "Pattern 2", "id": "pattern_2", "network": "default_wifi_network_for_edge"}},
            "EdgeFunction": {
                "func_1": {"name": "Function 1", "recurrent_edge_device_needs": [], "recurrent_server_needs": []},
                "func_2": {"name": "Function 2", "recurrent_edge_device_needs": ["need_1"], "recurrent_server_needs": []}},
            "OtherClass": {"obj_1": {"name": "Object 1"}}}

        output_dict = upgrade_version_14_to_15(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_15_to_16_migrates_web_application_and_genai(self):
        from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources
        from efootprint.constants.units import u
        from efootprint.core.usage.job import Job

        input_dict = {
            "Server": {"srv_1": {"name": "Server 1", "id": "srv_1"}},
            "WebApplication": {"wa_1": {"name": "Web app", "id": "wa_1", "server": "srv_1"}},
            "WebApplicationJob": {"waj_1": {
                "name": "Fetch view", "id": "waj_1", "service": "wa_1",
                "data_transferred": SourceValue(1 * u.MB).to_json(), "data_stored": SourceValue(2 * u.MB).to_json(),
                "implementation_details": "php"}},
            "GenAIModel": {
                "gaim_1": {
                    "name": "LLM",
                    "id": "gaim_1",
                    "server": "srv_1",
                    "provider": "openai",
                    "model_name": "gpt-4o",
                }
            },
            "GenAIJob": {
                "gaij_1": {
                    "name": "LLM call",
                    "id": "gaij_1",
                    "service": "gaim_1",
                    "output_token_count": SourceValue(1234 * u.dimensionless, Sources.HYPOTHESIS).to_json(),
                }
            },
        }

        expected_job_defaults = {k: v.to_json() for k, v in Job.default_values.items()
                                 if k in ["request_duration", "compute_needed", "ram_needed"]}
        expected_output = {
            "Server": {"srv_1": {"name": "Server 1", "id": "srv_1"}},
            "Job": {"waj_1": {"name": "Fetch view", "id": "waj_1", "server": "srv_1",
                              "data_transferred": SourceValue(1 * u.MB).to_json(),
                              "data_stored": SourceValue(2 * u.MB).to_json(),
                              **expected_job_defaults}},
            "EcoLogitsGenAIExternalAPI": {
                "gaim_1": {
                    "name": "LLM",
                    "id": "gaim_1",
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "server": "gaim_1_server"
                }
            },
            "EcoLogitsGenAIExternalAPIServer": {
              "gaim_1_server": {
                  "name": "LLM server",
                  "id": "gaim_1_server"
              }
            },
            "EcoLogitsGenAIExternalAPIJob": {
                "gaij_1": {
                    "name": "LLM call",
                    "id": "gaij_1",
                    "external_api": "gaim_1",
                    "output_token_count": input_dict["GenAIJob"]["gaij_1"]["output_token_count"],
                    "data_transferred": SourceValue(0 * u.MB).to_json(),
                    "data_stored": SourceValue(0 * u.MB).to_json(),
                    "request_duration": SourceValue(0 * u.s).to_json(),
                    "compute_needed": SourceValue(0 * u.cpu_core).to_json(),
                    "ram_needed": SourceValue(0 * u.GB_ram).to_json()
                }
            },
        }

        output_dict = upgrade_version_15_to_16(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_16_to_17_clamps_negative_data_stored_and_removes_storage_power_attributes(self):
        input_dict = {
            "Job": {
                "job_1": {"id": "job_1", "data_stored": {"value": -1, "unit": "MB", "label": "data stored"}},
                "job_2": {"id": "job_2", "data_stored": {"value": 2, "unit": "MB", "label": "data stored"}},
            },
            "GPUJob": {
                "gpu_job_1": {"id": "gpu_job_1", "data_stored": {"value": -3.5, "unit": "MB", "label": "data stored"}},
            },
            "VideoStreamingJob": {
                "vs_job_1": {"id": "vs_job_1", "data_stored": {"value": 0, "unit": "MB", "label": "data stored"}},
            },
            "Storage": {
                "st_1": {
                    "id": "st_1",
                    "name": "Storage 1",
                    "power_per_storage_capacity": {"value": 1, "unit": "W / TB", "label": "deprecated"},
                    "idle_power": {"value": 2, "unit": "W", "label": "deprecated"},
                    "some_other_attr": "keep_me",
                },
                "st_2": {"id": "st_2", "name": "Storage 2", "some_other_attr": "keep_me_too"},
            },
        }
        expected_output = {
            "Job": {
                "job_1": {"id": "job_1", "data_stored": {"value": 0, "unit": "MB", "label": "data stored"}},
                "job_2": {"id": "job_2", "data_stored": {"value": 2, "unit": "MB", "label": "data stored"}},
            },
            "GPUJob": {
                "gpu_job_1": {"id": "gpu_job_1", "data_stored": {"value": 0, "unit": "MB", "label": "data stored"}},
            },
            "VideoStreamingJob": {
                "vs_job_1": {"id": "vs_job_1", "data_stored": {"value": 0, "unit": "MB", "label": "data stored"}},
            },
            "Storage": {
                "st_1": {"id": "st_1", "name": "Storage 1", "some_other_attr": "keep_me"},
                "st_2": {"id": "st_2", "name": "Storage 2", "some_other_attr": "keep_me_too"},
            },
        }

        output_dict = upgrade_version_16_to_17(input_dict)

        self.assertEqual(output_dict, expected_output)

    def test_upgrade_16_to_17_moves_edge_storage_component_needs_to_recurrent_edge_storage_needs(self):
        input_dict = {
            "EdgeStorage": {
                "edge_storage_1": {
                    "id": "edge_storage_1",
                    "name": "Edge storage 1",
                    "power_per_storage_capacity": {"value": 1, "unit": "W / TB", "label": "deprecated"},
                }
            },
            "EdgeRAMComponent": {
                "edge_ram_1": {"id": "edge_ram_1", "name": "Edge RAM 1"}
            },
            "RecurrentEdgeComponentNeed": {
                "storage_need_1": {
                    "id": "storage_need_1",
                    "name": "Storage need 1",
                    "edge_component": "edge_storage_1",
                    "recurrent_need": {"recurring_values": "[1.0]", "unit": "GB", "label": "need"},
                },
                "ram_need_1": {
                    "id": "ram_need_1",
                    "name": "RAM need 1",
                    "edge_component": "edge_ram_1",
                    "recurrent_need": {"recurring_values": "[2.0]", "unit": "GB_ram", "label": "need"},
                },
            },
        }
        expected_output = {
            "EdgeStorage": {
                "edge_storage_1": {"id": "edge_storage_1", "name": "Edge storage 1"}
            },
            "EdgeRAMComponent": {
                "edge_ram_1": {"id": "edge_ram_1", "name": "Edge RAM 1"}
            },
            "RecurrentEdgeComponentNeed": {
                "ram_need_1": {
                    "id": "ram_need_1",
                    "name": "RAM need 1",
                    "edge_component": "edge_ram_1",
                    "recurrent_need": {"recurring_values": "[2.0]", "unit": "GB_ram", "label": "need"},
                },
            },
            "RecurrentEdgeStorageNeed": {
                "storage_need_1": {
                    "id": "storage_need_1",
                    "name": "Storage need 1",
                    "edge_component": "edge_storage_1",
                    "recurrent_need": {"recurring_values": "[1.0]", "unit": "GB", "label": "need"},
                },
            },
        }

        output_dict = upgrade_version_16_to_17(input_dict)

        self.assertEqual(output_dict, expected_output)
