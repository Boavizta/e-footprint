import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR


class IntegrationTestServicesFromJson(IntegrationTestServicesBaseClass):
    @classmethod
    def setUpClass(cls):
        (system, storage, server, gpu_server, video_streaming_service, web_application_service,
         genai_service, video_streaming_job, web_application_job, genai_job, direct_gpu_job,
         network, uj, start_date, usage_pattern) = cls.generate_system_with_services()

        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "system_with_services_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        # Load the system from the JSON file
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)
        cls.system, cls.storage, cls.server, cls.gpu_server, \
            cls.video_streaming_service, cls.web_application_service, cls.genai_service, \
            cls.video_streaming_job, cls.web_application_job, cls.genai_job, cls.direct_gpu_job, \
            cls.network, cls.uj, start_date, cls.usage_pattern = \
            flat_obj_dict[system.id], flat_obj_dict[storage.id], flat_obj_dict[server.id], \
            flat_obj_dict[gpu_server.id], flat_obj_dict[video_streaming_service.id], \
            flat_obj_dict[web_application_service.id], flat_obj_dict[genai_service.id], \
            flat_obj_dict[video_streaming_job.id], flat_obj_dict[web_application_job.id], \
            flat_obj_dict[genai_job.id], flat_obj_dict[direct_gpu_job.id], \
            flat_obj_dict[network.id], flat_obj_dict[uj.id], start_date, flat_obj_dict[usage_pattern.id]

        cls.initialize_footprints(cls.system, cls.storage, cls.server, cls.gpu_server, cls.usage_pattern, cls.network)

        cls.ref_json_filename = "system_with_services"
    def test_system_to_json(self):
        self.run_test_system_to_json(self.system)

    def test_json_to_system(self):
        self.run_test_json_to_system(self.system)

    def test_variations_on_services_inputs(self):
        self.run_test_variations_on_services_inputs()

    def test_variations_on_services_inputs_after_json_to_system(self):
        self.run_test_variations_on_services_inputs_after_json_to_system()

    def test_update_service_servers(self):
        self.run_test_update_service_servers()

    def test_update_service_jobs(self):
        self.run_test_update_service_jobs()

    def test_install_new_service_on_server_and_make_sure_system_is_recomputed(self):
        self.run_test_install_new_service_on_server_and_make_sure_system_is_recomputed()
