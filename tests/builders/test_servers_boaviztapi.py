import json
import os
import unittest
from unittest.mock import patch

from efootprint.builders.hardware.servers_boaviztapi import print_archetypes_and_their_configs, get_cloud_server, \
    on_premise_server_from_config
from efootprint.builders.hardware.storage_defaults import default_ssd
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

BUILDER_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestBoaviztapiBuilders(unittest.TestCase):
    def test_get_cloud_server(self):
        aws_server = get_cloud_server("aws", "m5.xlarge", SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        self.assertIsNotNone(aws_server)
        self.assertIsNotNone(aws_server.storage)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_get_cloud_server_with_specific_storage(self, mock_call_api):
        provider = 'aws'
        instance_type = 'a1.4xlarge'
        test_storage = default_ssd(name="Test storage", storage_capacity=SourceValue(2 * u.TB, Sources.HYPOTHESIS))
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_cloud.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        aws_server = get_cloud_server(provider, instance_type,  SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
                                      storage=test_storage)
        self.assertEqual(aws_server.name, f"{provider} {instance_type} instances")
        self.assertEqual(aws_server.storage.storage_capacity.value, 2 * u.TB)
        self.assertEqual(aws_server.storage.name, 'Test storage')
        self.assertEqual(aws_server.carbon_footprint_fabrication.value, 460 * u.kg)
        self.assertEqual(aws_server.ram.value, 32 * u.GB)
        self.assertEqual(aws_server.cpu_cores.value, 16 * u.core)
        self.assertEqual(round(aws_server.power.value, 2), 51.89 * u.W)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_get_cloud_server_with_no_storage(self, mock_call_api):
        provider = 'aws'
        instance_type = 'a1.4xlarge'
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_cloud.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        aws_server = get_cloud_server(provider, instance_type, SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        self.assertIn(provider, aws_server.name)
        self.assertIn(instance_type, aws_server.name)
        self.assertEqual(aws_server.storage.name, default_ssd().name)
        self.assertEqual(aws_server.storage.storage_capacity.value, 32 * u.GB)
        self.assertEqual(aws_server.storage.power.value, default_ssd().power.value * 0.032)
        self.assertEqual(aws_server.storage.carbon_footprint_fabrication.value,
                         default_ssd().carbon_footprint_fabrication.value * 0.032)
        self.assertEqual(aws_server.carbon_footprint_fabrication.value, 460 * u.kg)
        self.assertEqual(aws_server.ram.value, 32 * u.GB)
        self.assertEqual(aws_server.cpu_cores.value, 16 * u.core)
        self.assertEqual(round(aws_server.power.value, 2), 51.89 * u.W)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_on_premise_server_with_specific_storage(self, mock_call_api):
        test_storage = default_ssd(name="Test storage", storage_capacity=SourceValue(2 * u.TB, Sources.HYPOTHESIS))
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_ssd.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        on_prem_server = on_premise_server_from_config(
            "My server", 2, 24, 12, 32, average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            storage=test_storage)
        self.assertEqual(on_prem_server.storage.name, 'Test storage')
        self.assertEqual(on_prem_server.storage.storage_capacity.value, 2 * u.TB)
        self.assertEqual(on_prem_server.ram.value, 384 * u.GB)
        self.assertEqual(on_prem_server.cpu_cores.value, 48 * u.core)
        self.assertEqual(on_prem_server.carbon_footprint_fabrication.value, 1150 * u.kg)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_on_premise_server_with_no_storage_ssd_case(self, mock_call_api):
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_ssd.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        on_prem_server = on_premise_server_from_config(
            "My server", 2, 24, 12, 32, average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        self.assertEqual(on_prem_server.storage.name, f"{on_prem_server.name} SSD storage")
        self.assertEqual(on_prem_server.storage.storage_capacity.value, 500 * u.GB)
        self.assertEqual(on_prem_server.storage.fixed_nb_of_instances.value, 1 * u.dimensionless)
        self.assertEqual(on_prem_server.ram.value, 384 * u.GB)
        self.assertEqual(on_prem_server.cpu_cores.value, 48 * u.core)
        self.assertEqual(on_prem_server.carbon_footprint_fabrication.value, 1150 * u.kg)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_on_premise_server_with_no_storage_hdd_case(self, mock_call_api):
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_hdd.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        on_prem_server = on_premise_server_from_config(
            "My server", 2, 24, 12, 32, average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        self.assertEqual(on_prem_server.storage.name, f"{on_prem_server.name} HDD storage")
        self.assertEqual(on_prem_server.storage.storage_capacity.value, 500 * u.GB)
        self.assertEqual(on_prem_server.storage.fixed_nb_of_instances.value, 1 * u.dimensionless)
        self.assertEqual(on_prem_server.ram.value, 384 * u.GB)
        self.assertEqual(on_prem_server.cpu_cores.value, 48 * u.core)
        self.assertEqual(on_prem_server.carbon_footprint_fabrication.value, 1150 * u.kg)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_on_premise_server_compare_power(self,mock_call_api):
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_ssd.json"), "rb") as file:
            full_dict_ssd = json.load(file)
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_hdd.json"), "rb") as file:
            full_dict_hdd = json.load(file)
        mock_call_api.side_effect = [full_dict_ssd, full_dict_hdd]
        on_prem_server_ssd = on_premise_server_from_config(
            "My server", 2, 24, 12, 32, average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        on_prem_server_hdd = on_premise_server_from_config(
            "My server", 2, 24, 12, 32, average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS))
        self.assertNotEqual(on_prem_server_ssd.storage.power.value,
                            on_prem_server_hdd.storage.power.value)

    @patch('efootprint.builders.hardware.servers_boaviztapi.call_boaviztapi')
    def test_on_premise_server_hybrid_storage(self, mock_call_api):
        with open(os.path.join(BUILDER_TEST_DIR, "mock_api_server_hybrid.json"), "rb") as file:
            full_dict = json.load(file)
        mock_call_api.return_value = full_dict

        with self.assertRaises(ValueError) as context:
            on_prem_server_hybrid = on_premise_server_from_config(
                "My server", 2, 24, 12, 32,
                average_carbon_intensity=SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS)
            )
        self.assertIn(
            "Both SSD and HDD storage found in the server impact data ,this is not implemented yet",
            str(context.exception)
        )


    def test_print_archetypes_and_their_configs(self):
        # Too long and not very important so pass for now
        # print_archetypes_and_their_configs()
        pass
