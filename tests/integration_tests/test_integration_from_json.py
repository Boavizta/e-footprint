import json

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_simple_system import IntegrationTestSimpleSystemBaseClass


class IntegrationTestSimpleSystemFromJson(IntegrationTestSimpleSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        (system, storage, server, streaming_job, streaming_step, upload_job, upload_step, uj, network, start_date,
         usage_pattern) = cls.generate_simple_system()

        cls.system_json_filepath = "system_with_calculated_attributes.json"
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        # Load the system from the JSON file
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        cls.system, cls.storage, cls.server, cls.streaming_job, cls.streaming_step, cls.upload_job, cls.upload_step, \
            cls.uj, cls.start_date, cls.network, cls.usage_pattern = \
            flat_obj_dict[system.id], flat_obj_dict[storage.id], flat_obj_dict[server.id], \
            flat_obj_dict[streaming_job.id], flat_obj_dict[streaming_step.id], flat_obj_dict[upload_job.id], \
            flat_obj_dict[upload_step.id], flat_obj_dict[uj.id], start_date, flat_obj_dict[network.id], \
            flat_obj_dict[usage_pattern.id]

        cls.initialize_footprints(cls.system, cls.storage, cls.server, cls.usage_pattern, cls.network)

        cls.ref_json_filename = "simple_system"
