import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR
from tests.integration_tests.integration_complex_system_base import IntegrationTestComplexSystem


class IntegrationTestComplexSystemFromJson(IntegrationTestComplexSystem):
    @classmethod
    def setUpClass(cls):
        system, storage_1, storage_2, storage_3, server1, server2, server3, \
            streaming_job, upload_job, dailymotion_job, tiktok_job, tiktok_analytics_job, \
            streaming_step, upload_step, dailymotion_step, tiktok_step, \
            start_date, usage_pattern1, usage_pattern2, uj, network = cls.generate_complex_system()

        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "complex_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        # Load the system from the JSON file
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2, cls.server3, \
            cls.streaming_job, cls.upload_job, cls.dailymotion_job, cls.tiktok_job, cls.tiktok_analytics_job, \
            cls.streaming_step, cls.upload_step, cls.dailymotion_step, cls.tiktok_step, \
            cls.start_date, cls.usage_pattern1, cls.usage_pattern2, cls.uj, cls.network = \
        flat_obj_dict[system.id], flat_obj_dict[storage_1.id], flat_obj_dict[storage_2.id], flat_obj_dict[storage_3.id], \
        flat_obj_dict[server1.id], flat_obj_dict[server2.id], flat_obj_dict[server3.id], \
        flat_obj_dict[streaming_job.id], flat_obj_dict[upload_job.id], flat_obj_dict[dailymotion_job.id], \
        flat_obj_dict[tiktok_job.id], flat_obj_dict[tiktok_analytics_job.id], \
        flat_obj_dict[streaming_step.id], flat_obj_dict[upload_step.id], flat_obj_dict[dailymotion_step.id], \
        flat_obj_dict[tiktok_step.id], start_date, flat_obj_dict[usage_pattern1.id], \
        flat_obj_dict[usage_pattern2.id], flat_obj_dict[uj.id], flat_obj_dict[network.id]

        cls.initialize_footprints(cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2,
                                  cls.server3, cls.usage_pattern1, cls.usage_pattern2, cls.network)

        cls.ref_json_filename = "complex_system"
