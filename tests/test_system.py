import os.path
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock
import unittest

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject, ExplainableQuantity
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.core.system import System
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues, SourceValue
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.core.usage.usage_pattern import UsagePattern

root_dir = os.path.dirname(os.path.abspath(__file__))


class TestSystem(TestCase):
    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)

        self.usage_pattern = MagicMock(spec=UsagePattern)
        self.usage_pattern.name = "usage_pattern"
        self.usage_pattern.id = "usage_pattern_id"
        self.usage_pattern.systems = []
        device = MagicMock()
        self.usage_pattern.devices = [device]
        device.systems = []
        self.usage_pattern.country = MagicMock()
        self.usage_pattern.country.systems = []
        self.usage_pattern.usage_journey = MagicMock()
        self.usage_pattern.usage_journey.systems = []
        uj_step = MagicMock()
        self.usage_pattern.usage_journey.uj_steps = [uj_step]
        uj_step.systems = []
        job = MagicMock()
        uj_step.jobs = [job]
        job.systems = []
        self.usage_pattern.usage_journey.systems = []
        self.server = MagicMock()
        self.server.name = "server"
        self.server.id = "server_id"
        self.server.systems = []
        self.storage = MagicMock()
        self.storage.name = "storage"
        self.storage.id = "storage_id"
        self.storage.systems = []
        self.network = MagicMock()
        self.network.name = "network"
        self.network.id = "network_id"
        self.network.systems = []

        self.usage_pattern.usage_journey.servers = {self.server}
        self.usage_pattern.usage_journey.storages = {self.storage}
        self.usage_pattern.network = self.network

        self.server.instances_fabrication_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        self.storage.instances_fabrication_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        self.usage_pattern.instances_fabrication_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))

        self.server.energy_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        self.storage.energy_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        self.usage_pattern.energy_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        self.network.energy_footprint = SourceHourlyValues(
            create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))

        self.system = System(
            "Non cloud system",
            usage_patterns=[self.usage_pattern]
        )
        self.system.trigger_modeling_updates = False

    def test_servers(self):
        self.assertEqual([self.server], self.system.servers)

    def test_storages(self):
        self.assertEqual([self.storage], self.system.storages)

    def test_networks(self):
        self.assertEqual([self.network], self.system.networks)

    def test_check_no_object_to_link_is_already_linked_to_another_system_pass_case(self):
        obj1 = MagicMock()
        mock_system = MagicMock()
        mock_system.id = self.system.id
        obj1.systems = [mock_system]

        obj2 = MagicMock()
        obj2.systems = []

        usage_patterns = MagicMock()

        with patch.object(System, "get_objects_linked_to_usage_patterns", new_callable=PropertyMock) \
            as mock_get_objects_linked_to_usage_patterns:
            mock_get_objects_linked_to_usage_patterns.return_value = lambda x: [obj1, obj2]
            self.system.check_no_object_to_link_is_already_linked_to_another_system(usage_patterns)

    def test_check_no_object_to_link_is_already_linked_to_another_system_fail_case(self):
        obj1 = MagicMock()
        mock_system = MagicMock()
        mock_system.id = "other id"
        obj1.systems = [mock_system]

        obj2 = MagicMock()
        obj2.systems = []

        usage_patterns = MagicMock()

        with patch.object(System, "get_objects_linked_to_usage_patterns", new_callable=PropertyMock) \
            as mock_get_objects_linked_to_usage_patterns:
            mock_get_objects_linked_to_usage_patterns.return_value = lambda x: [obj1, obj2]
            with self.assertRaises(PermissionError):
                self.system.check_no_object_to_link_is_already_linked_to_another_system(usage_patterns)

    def test_an_object_cant_be_linked_to_several_systems(self):
        new_server = MagicMock()
        other_system = MagicMock()
        other_system.id = "other id"
        new_server.systems = [other_system]

        with patch.object(System, "get_objects_linked_to_usage_patterns", new_callable=PropertyMock) \
                as mock_get_objects_linked_to_usage_patterns:
            mock_get_objects_linked_to_usage_patterns.return_value = lambda x: [new_server]
            with self.assertRaises(PermissionError):
                new_system = System("new system", usage_patterns=[self.usage_pattern])

    @patch.object(System, "get_objects_linked_to_usage_patterns", new_callable=PropertyMock)
    def test_cant_compute_calculated_attributes_with_usage_patterns_already_linked_to_another_system(
            self, mock_get_objects_linked_to_usage_patterns):
        mock_get_objects_linked_to_usage_patterns.return_value = lambda x: [new_up]
        new_up = MagicMock(spec=UsagePattern)
        new_up.name = "new up"
        other_system = MagicMock(spec=System)
        other_system.id = "other id"
        other_system.name = "other system"
        new_up.systems = [other_system]

        with self.assertRaises(PermissionError):
            self.system.usage_patterns = [new_up]
            self.system.compute_calculated_attributes()
        
    def test_fabrication_footprints(self):
        expected_dict = {
            "Servers": {"server_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"networks": EmptyExplainableObject()},
            "Devices": {"usage_pattern_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))}
        }
        
        self.assertDictEqual(expected_dict, self.system.fabrication_footprints)

    def test_energy_footprints(self):
        expected_dict = {
            "Servers": {"server_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Devices": {"usage_pattern_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"network_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))}
        }

        self.assertDictEqual(expected_dict, self.system.energy_footprints)

    def test_total_fabrication_footprints(self):
        expected_dict = {
            "Servers": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Storage": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Devices": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Network": EmptyExplainableObject()
        }
        self.assertDictEqual(expected_dict, self.system.total_fabrication_footprints)

    def test_total_energy_footprints(self):
        energy_footprints = self.system.total_energy_footprints
        expected_dict = {
            "Servers": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Storage": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Devices": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg)),
            "Network": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))
        }

        self.assertDictEqual(expected_dict, energy_footprints)

    def test_fabrication_footprint_sum_over_period(self):
        test_footprints = {
            "Servers": {"server_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Devices": {"usage_pattern_id": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"networks_id": EmptyExplainableObject()}
        }
        expected_dict = {
            "Servers": {"server_id": ExplainableQuantity(6 * u.kg, label="server")},
            "Storage": {"storage_id": ExplainableQuantity(6 * u.kg, label="storage")},
            "Devices": {"usage_pattern_id": ExplainableQuantity(6 * u.kg, label="devices")},
            "Network": {"networks_id": EmptyExplainableObject()},
        }

        with patch.object(System, "fabrication_footprints", new_callable=PropertyMock) as fab_mock:
            fab_mock.return_value = test_footprints
            fabrication_footprint_sum_over_period = self.system.fabrication_footprint_sum_over_period
            for category in expected_dict:
                for item in expected_dict[category]:
                    self.assertEqual(expected_dict[category][item].value, fabrication_footprint_sum_over_period[category][item].value)

    def test_energy_footprint_sum_over_period(self):
        test_footprints = {
            "Servers": {"server": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Devices": {"usage_pattern": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"networks": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))}
        }
        expected_dict = {
            "Servers": {"server": ExplainableQuantity(6 * u.kg, label="server")},
            "Storage": {"storage": ExplainableQuantity(6 * u.kg, label="storage")},
            "Devices": {"usage_pattern": ExplainableQuantity(6 * u.kg, label="devices")},
            "Network": {"networks": ExplainableQuantity(6 * u.kg, label="devices")},
        }

        with patch.object(System, "energy_footprints", new_callable=PropertyMock) as eng_mock:
            eng_mock.return_value = test_footprints
            energy_footprint_sum_over_period = self.system.energy_footprint_sum_over_period
            for category in expected_dict:
                for item in expected_dict[category]:
                    self.assertEqual(expected_dict[category][item].value, energy_footprint_sum_over_period[category][item].value)

    def test_total_fabrication_footprint_sum_over_period(self):
        fab_footprints = {
            "Servers": {"server": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Devices": {"usage_pattern": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"networks": EmptyExplainableObject()}
        }

        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(0 * u.kg, "null value")
        }

        with patch.object(System, "fabrication_footprints", new_callable=PropertyMock) as fab_mock:
            fab_mock.return_value = fab_footprints
            total_fabrication_footprint_sum_over_period = self.system.total_fabrication_footprint_sum_over_period
            self.assertDictEqual(expected_dict, total_fabrication_footprint_sum_over_period)

    def test_total_energy_footprint_sum_over_period(self):
        energy_footprints = {
            "Servers": {"server": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Storage": {"storage": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Devices": {"usage_pattern": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))},
            "Network": {"networks": SourceHourlyValues(
                create_hourly_usage_df_from_list([1, 2, 3], pint_unit=u.kg))}
        }

        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(6 * u.kg, "null value")
        }

        with patch.object(System, "energy_footprints", new_callable=PropertyMock) as energy_mock:
            energy_mock.return_value = energy_footprints
            total_energy_footprint_sum_over_period = self.system.total_energy_footprint_sum_over_period
            self.assertDictEqual(expected_dict, total_energy_footprint_sum_over_period)

    @patch("efootprint.core.system.System.servers", new_callable=PropertyMock)
    @patch("efootprint.core.system.System.storages", new_callable=PropertyMock)
    def test_fabrication_footprints_has_as_many_values_as_nb_of_objects_even_if_some_objects_have_same_name(
            self, mock_storages, mock_servers):
        usage_pattern = MagicMock(spec=UsagePattern, instances_fabrication_footprint=SourceValue(1 * u.kg))
        usage_pattern.name = "usage pattern"
        usage_pattern.id = "usage pattern id"
        usage_pattern2 = MagicMock(spec=UsagePattern, instances_fabrication_footprint=SourceValue(1 * u.kg))
        usage_pattern2.name = "usage pattern2"
        usage_pattern2.id = "usage pattern2 id"
        server = MagicMock(instances_fabrication_footprint=SourceValue(1 * u.kg))
        server.name = "server"
        server.id = "server id"
        server2 = MagicMock(instances_fabrication_footprint=SourceValue(1 * u.kg))
        server2.name = "server2"
        server2.id = "server2 id"
        storage = MagicMock(instances_fabrication_footprint=SourceValue(1 * u.kg))
        storage.name = "storage"
        storage.id = "storage id"
        # same name
        storage2 = MagicMock(instances_fabrication_footprint=SourceValue(1 * u.kg))
        storage2.name = "storage"
        storage2.id = "storage2 id"

        mock_servers.return_value = [server, server2]
        mock_storages.return_value = [storage, storage2]

        system2 = System.__new__(System)
        system2.trigger_modeling_updates = False
        system2.usage_patterns = [usage_pattern, usage_pattern2]

        for category in ["Servers", "Storage", "Devices"]:
            self.assertEqual(
                len(list(system2.fabrication_footprints[category].values())), 2, f"{category} doesn’t have right len")

    @patch("efootprint.core.system.System.servers", new_callable=PropertyMock)
    @patch("efootprint.core.system.System.storages", new_callable=PropertyMock)
    @patch("efootprint.core.system.System.networks", new_callable=PropertyMock)
    def test_energy_footprints_has_as_many_values_as_nb_of_objects_even_if_some_objects_have_same_name(
            self, mock_networks, mock_storages, mock_servers):
        usage_pattern = MagicMock(spec=UsagePattern, energy_footprint=SourceValue(1 * u.kg))
        usage_pattern.name = "usage pattern"
        usage_pattern.id = "usage pattern id"
        usage_pattern2 = MagicMock(spec=UsagePattern, energy_footprint=SourceValue(1 * u.kg))
        usage_pattern2.name = "usage pattern2"
        usage_pattern2.id = "usage pattern2 id"
        server = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        server.name = "server"
        server.id = "server id"
        server2 = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        server2.name = "server2"
        server2.id = "server2 id"
        storage = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        storage.name = "storage"
        storage.id = "storage id"
        # same name
        storage2 = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        storage2.name = "storage"
        storage2.id = "storage2 id"
        network = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        network.name = "network"
        network.id = "network id"
        network2 = MagicMock(energy_footprint=SourceValue(1 * u.kg))
        network2.name = "network2"
        network2.id = "network2 id"

        mock_servers.return_value = [server, server2]
        mock_storages.return_value = [storage, storage2]
        mock_networks.return_value = [network, network2]

        system2 = System.__new__(System)
        system2.trigger_modeling_updates = False
        system2.usage_patterns = [usage_pattern, usage_pattern2]

        for category in ["Servers", "Storage", "Devices", "Network"]:
            self.assertEqual(
                len(list(system2.energy_footprints[category].values())), 2,
                f"{category} doesn’t have right len")

    def test_footprints_by_category_and_object(self):
        fab_footprints = {
            "Servers": {"server": ExplainableQuantity(6 * u.kg, "server")},
            "Storage": {"storage": ExplainableQuantity(6 * u.kg, "storage")},
            "Devices": {"usage_pattern": ExplainableQuantity(6 * u.kg, "usage_pattern")},
            "Network": {"networks": ExplainableQuantity(0 * u.kg, "network")}
        }

        energy_footprints = {
            "Servers": {"server": ExplainableQuantity(5 * u.kg, "server")},
            "Storage": {"storage": ExplainableQuantity(5 * u.kg, "storage")},
            "Devices": {"usage_pattern": ExplainableQuantity(5 * u.kg, "usage_pattern")},
            "Network": {"network": ExplainableQuantity(5 * u.kg, "network")},
        }

        with patch.object(System, "fabrication_footprint_sum_over_period", new_callable=PropertyMock) as fab_mock,\
            patch.object(System, "energy_footprint_sum_over_period", new_callable=PropertyMock) as en_mock:
            fab_mock.return_value = fab_footprints
            en_mock.return_value = energy_footprints
            self.system.plot_footprints_by_category_and_object(
                filename=os.path.join(root_dir, "footprints by category and object unit test.html"))

    def test_plot_emission_diffs(self):
        change_test = "changed energy footprint value"

        previous_fab_footprints = {
            "Servers": ExplainableQuantity(6 * u.kg, "server"),
            "Storage": ExplainableQuantity(6 * u.kg, "storage"),
            "Devices": ExplainableQuantity(6 * u.kg, "usage_pattern"),
            "Network": ExplainableQuantity(0 * u.kg, "network")
        }

        previous_energy_footprints = {
            "Servers": ExplainableQuantity(5 * u.kg, "server"),
            "Storage": ExplainableQuantity(5 * u.kg, "storage"),
            "Devices": ExplainableQuantity(5 * u.kg, "usage_pattern"),
            "Network": ExplainableQuantity(5 * u.kg, "network")
        }

        fab_footprints = {
           "Servers": ExplainableQuantity(6 * u.kg, "server"),
           "Storage": ExplainableQuantity(6 * u.kg, "storage"),
           "Devices": ExplainableQuantity(6 * u.kg, "usage_pattern"),
           "Network": ExplainableQuantity(0 * u.kg, "network")
        }

        energy_footprints = {
            "Servers": ExplainableQuantity(2 * u.kg, "server"),
            "Storage": ExplainableQuantity(10 * u.kg, "storage"),
            "Devices": ExplainableQuantity(15 * u.kg, "usage_pattern"),
            "Network": ExplainableQuantity(5 * u.kg, "network")
        }

        with patch.object(self.system, "previous_total_energy_footprints_sum_over_period", previous_energy_footprints),\
            patch.object(self.system, "previous_total_fabrication_footprints_sum_over_period", previous_fab_footprints), \
            patch.object(System, "total_energy_footprint_sum_over_period", new_callable=PropertyMock) as eneg, \
            patch.object(System, "total_fabrication_footprint_sum_over_period", new_callable=PropertyMock) as fab, \
            patch.object(self.system, "previous_change", change_test):
            eneg.return_value = energy_footprints
            fab.return_value = fab_footprints
            self.system.plot_emission_diffs(filepath=os.path.join(root_dir, "test_system_diff_plot.png"))

    def test_creating_system_with_empty_up_list_is_possible(self):
        system = System("Test system", usage_patterns=[])


if __name__ == '__main__':
    unittest.main()
