import os.path
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock
import unittest

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.server import Server
from efootprint.core.system import System
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from tests import root_test_dir


class TestSystem(TestCase):
    @staticmethod
    def _hourly_kg(values=(1, 2, 3)):
        return create_source_hourly_values_from_list(list(values), pint_unit=u.kg)

    @staticmethod
    def _set_systems_empty(*objects):
        for obj in objects:
            obj.systems = []

    def _base_fabrication_footprints(self):
        return {
            "Servers": {self.server: self._hourly_kg()},
            "ExternalAPIs": {},
            "Storage": {self.storage: self._hourly_kg()},
            "Network": {},
            "Devices": {self.usage_pattern: self._hourly_kg()},
            "EdgeDevices": {}
        }

    def _base_energy_footprints(self):
        return {
            "Servers": {self.server: self._hourly_kg()},
            "ExternalAPIs": {},
            "Storage": {self.storage: self._hourly_kg()},
            "Devices": {self.usage_pattern: self._hourly_kg()},
            "Network": {self.network: self._hourly_kg()},
            "EdgeDevices": {}
        }

    def _make_edge_device(
        self,
        *,
        fab=None,
        energy=None,
        storage_fab=None,
        storage_energy=None,
        with_ids=False
    ):
        edge_computer = MagicMock(spec=EdgeComputer)
        edge_storage = MagicMock(spec=EdgeStorage)
        if with_ids:
            edge_computer.name = "edge_computer"
            edge_computer.id = "edge_computer_id"
            edge_storage.name = "storage_from_edge"
            edge_storage.id = "storage_from_edge_id"
            self._set_systems_empty(edge_computer, edge_storage)
        if fab is not None:
            edge_computer.instances_fabrication_footprint = fab
        if energy is not None:
            edge_computer.energy_footprint = energy
        if storage_fab is not None:
            edge_storage.instances_fabrication_footprint = storage_fab
        if storage_energy is not None:
            edge_storage.energy_footprint = storage_energy
        edge_computer.storage = edge_storage
        edge_computer.components = [edge_storage]
        return edge_computer, edge_storage

    def _make_edge_usage_pattern(
        self,
        *,
        with_server_need=False,
        with_job=False,
        with_ids=False,
        with_footprints=False,
        pattern_fab=None,
        pattern_energy=None,
        edge_fab=None,
        edge_energy=None,
        network_energy=None
    ):
        edge_usage_pattern = MagicMock(spec=EdgeUsagePattern)
        edge_usage_pattern.jobs = []
        edge_usage_journey = MagicMock(spec=EdgeUsageJourney)
        edge_function = MagicMock(spec=EdgeFunction)
        edge_resource_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        edge_computer, edge_storage = self._make_edge_device(with_ids=with_ids)

        edge_resource_need.edge_device = edge_computer
        edge_resource_need.recurrent_edge_component_needs = []
        edge_function.recurrent_edge_device_needs = [edge_resource_need]
        edge_function.recurrent_server_needs = []

        server_need = None
        job = None
        if with_server_need:
            server_need = MagicMock(spec=RecurrentServerNeed)
            server_need.edge_device = edge_computer
            server_need.jobs = []
            if with_job:
                job = MagicMock(spec=Job)
                server_need.jobs = [job]
                job.server = self.server
                edge_usage_pattern.jobs = [job]
            edge_function.recurrent_server_needs = [server_need]

        edge_usage_journey.edge_functions = [edge_function]
        edge_usage_journey.edge_devices = [edge_computer]
        edge_usage_pattern.edge_usage_journey = edge_usage_journey
        edge_usage_pattern.country = MagicMock()
        edge_usage_pattern.network = MagicMock()

        if with_ids:
            edge_usage_pattern.name = "edge_usage_pattern"
            edge_usage_pattern.id = "edge_usage_pattern_id"
            self._set_systems_empty(
                edge_usage_pattern,
                edge_usage_journey,
                edge_function,
                edge_resource_need,
                edge_usage_pattern.country,
                edge_usage_pattern.network,
            )
            if server_need is not None:
                self._set_systems_empty(server_need)
            if job is not None:
                self._set_systems_empty(job)

        if with_footprints:
            edge_usage_pattern.instances_fabrication_footprint = pattern_fab or self._hourly_kg()
            edge_usage_pattern.energy_footprint = pattern_energy or self._hourly_kg()
            edge_computer.instances_fabrication_footprint = edge_fab or self._hourly_kg(values=(2, 3, 4))
            edge_computer.energy_footprint = edge_energy or self._hourly_kg(values=(2, 3, 4))
            edge_storage.instances_fabrication_footprint = self._hourly_kg(values=(1, 1, 1))
            edge_storage.energy_footprint = self._hourly_kg(values=(1, 1, 1))
            edge_usage_pattern.network.energy_footprint = network_energy or self._hourly_kg(values=(2, 3, 4))

        return {
            "edge_usage_pattern": edge_usage_pattern,
            "edge_usage_journey": edge_usage_journey,
            "edge_function": edge_function,
            "edge_resource_need": edge_resource_need,
            "server_need": server_need,
            "job": job,
            "edge_computer": edge_computer,
            "edge_storage": edge_storage,
        }

    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)

        self.usage_pattern = MagicMock(spec=UsagePattern)
        self.usage_pattern.name = "usage_pattern"
        self.usage_pattern.id = self.usage_pattern
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
        self.usage_pattern.usage_journey.systems = []
        self.server = MagicMock(spec=Server)
        self.server.name = "server"
        self.server.id = "server_id"
        self.server.systems = []
        self.storage = MagicMock()
        self.storage.name = "storage"
        self.storage.id = "storage_id"
        self.storage.systems = []
        self.server.storage = self.storage
        job = MagicMock(spec=Job)
        uj_step.jobs = [job]
        job.systems = []
        job.server = self.server
        self.network = MagicMock()
        self.network.name = "network"
        self.network.id = "network_id"
        self.network.systems = []

        self.usage_pattern.network = self.network
        self.usage_pattern.jobs = [job]

        self.server.instances_fabrication_footprint = self._hourly_kg()
        self.storage.instances_fabrication_footprint = self._hourly_kg()
        self.usage_pattern.instances_fabrication_footprint = self._hourly_kg()

        self.server.energy_footprint = self._hourly_kg()
        self.storage.energy_footprint = self._hourly_kg()
        self.usage_pattern.energy_footprint = self._hourly_kg()
        self.network.energy_footprint = self._hourly_kg()

        self.system = System(
            "Test system",
            usage_patterns=[self.usage_pattern],
            edge_usage_patterns=[]
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

        with patch.object(System, "all_linked_objects", new_callable=PropertyMock) \
            as mock_all_linked_objects:
            mock_all_linked_objects.return_value = [obj1, obj2]
            self.system.check_no_object_to_link_is_already_linked_to_another_system()

    def test_check_no_object_to_link_is_already_linked_to_another_system_fail_case(self):
        obj1 = MagicMock()
        mock_system = MagicMock()
        mock_system.id = "other id"
        obj1.systems = [mock_system]

        obj2 = MagicMock()
        obj2.systems = []

        with patch.object(System, "all_linked_objects", new_callable=PropertyMock) \
            as mock_all_linked_objects:
            mock_all_linked_objects.return_value = [obj1, obj2]
            with self.assertRaises(PermissionError):
                self.system.check_no_object_to_link_is_already_linked_to_another_system()

    def test_an_object_cant_be_linked_to_several_systems(self):
        new_server = MagicMock()
        other_system = MagicMock()
        other_system.id = "other id"
        new_server.systems = [other_system]

        with patch.object(System, "all_linked_objects", new_callable=PropertyMock) \
                as mock_all_linked_objects:
            mock_all_linked_objects.return_value = [new_server]
            with self.assertRaises(PermissionError):
                new_system = System("new system", usage_patterns=[self.usage_pattern], edge_usage_patterns=[])

    def test_cant_compute_calculated_attributes_with_usage_patterns_already_linked_to_another_system(self):
        new_up = MagicMock(spec=UsagePattern)
        new_up.name = "new up"
        other_system = MagicMock(spec=System)
        other_system.id = "other id"
        other_system.name = "other system"
        new_up.systems = [other_system]

        with patch.object(System, "all_linked_objects", new_callable=PropertyMock) as mock_all_linked_objects:
            mock_all_linked_objects.return_value = [new_up]
            with self.assertRaises(PermissionError):
                self.system.usage_patterns = [new_up]
                self.system.compute_calculated_attributes()
        
    def test_fabrication_footprints(self):
        self.assertDictEqual(self._base_fabrication_footprints(), self.system.fabrication_footprints)

    def test_energy_footprints(self):
        self.assertDictEqual(self._base_energy_footprints(), self.system.energy_footprints)

    def test_external_apis_have_their_own_category_in_footprints(self):
        external_api = MagicMock()
        external_api.name = "external_api"
        external_api.systems = []
        external_api.instances_fabrication_footprint = self._hourly_kg(values=(4, 4, 4))
        external_api.energy_footprint = self._hourly_kg(values=(2, 2, 2))
        self.usage_pattern.jobs[0].external_api = external_api

        fab_footprints = self.system.fabrication_footprints
        energy_footprints = self.system.energy_footprints

        self.assertIn(external_api, fab_footprints["ExternalAPIs"])
        self.assertEqual(external_api.instances_fabrication_footprint, fab_footprints["ExternalAPIs"][external_api])
        self.assertIn(external_api, energy_footprints["ExternalAPIs"])
        self.assertEqual(external_api.energy_footprint, energy_footprints["ExternalAPIs"][external_api])

        self.assertEqual(external_api.instances_fabrication_footprint, self.system.total_fabrication_footprints["ExternalAPIs"])
        self.assertEqual(external_api.energy_footprint, self.system.total_energy_footprints["ExternalAPIs"])

    def test_total_fabrication_footprints(self):
        expected_dict = {
            "Servers":
                self._hourly_kg(),
            "ExternalAPIs": EmptyExplainableObject(),
            "Storage":
                self._hourly_kg(),
            "Devices":
                self._hourly_kg(),
            "Network": EmptyExplainableObject(),
            "EdgeDevices": EmptyExplainableObject()
        }
        self.assertDictEqual(expected_dict, self.system.total_fabrication_footprints)

    def test_total_energy_footprints(self):
        energy_footprints = self.system.total_energy_footprints
        expected_dict = {
            "Servers":
                self._hourly_kg(),
            "ExternalAPIs": EmptyExplainableObject(),
            "Storage":
                self._hourly_kg(),
            "Devices":
                self._hourly_kg(),
            "Network":
                self._hourly_kg(),
            "EdgeDevices": EmptyExplainableObject()
        }

        self.assertDictEqual(expected_dict, energy_footprints)

    def test_fabrication_footprint_sum_over_period(self):
        test_footprints = {
            "Servers": {self.server: 
                self._hourly_kg()},
            "Storage": {self.storage: 
                self._hourly_kg()},
            "Devices": {self.usage_pattern: 
                self._hourly_kg()},
            "Network": {"networks_id": EmptyExplainableObject()}
        }
        expected_dict = {
            "Servers": {self.server: ExplainableQuantity(6 * u.kg, label="server")},
            "Storage": {self.storage: ExplainableQuantity(6 * u.kg, label="storage")},
            "Devices": {self.usage_pattern: ExplainableQuantity(6 * u.kg, label="devices")},
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
            "Servers": {"server": 
                self._hourly_kg()},
            "Storage": {"storage": 
                self._hourly_kg()},
            "Devices": {"usage_pattern": 
                self._hourly_kg()},
            "Network": {"networks": 
                self._hourly_kg()}
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
            "Servers": {"server": 
                self._hourly_kg()},
            "Storage": {"storage": 
                self._hourly_kg()},
            "Devices": {"usage_pattern": 
                self._hourly_kg()},
            "Network": {"networks": EmptyExplainableObject()}
        }

        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "ExternalAPIs": ExplainableQuantity(0 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(0 * u.kg, "null value"),
            "EdgeDevices": ExplainableQuantity(0 * u.kg, "null value")
        }

        with patch.object(System, "fabrication_footprints", new_callable=PropertyMock) as fab_mock:
            fab_mock.return_value = fab_footprints
            total_fabrication_footprint_sum_over_period = self.system.total_fabrication_footprint_sum_over_period
            self.assertDictEqual(expected_dict, total_fabrication_footprint_sum_over_period)

    def test_total_energy_footprint_sum_over_period(self):
        energy_footprints = {
            "Servers": {"server": 
                self._hourly_kg()},
            "Storage": {"storage": 
                self._hourly_kg()},
            "Devices": {"usage_pattern": 
                self._hourly_kg()},
            "Network": {"networks": 
                self._hourly_kg()}
        }

        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "ExternalAPIs": ExplainableQuantity(0 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(6 * u.kg, "null value"),
            "EdgeDevices": ExplainableQuantity(0 * u.kg, "null value")
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
        system2.edge_usage_patterns = []

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
        system2.edge_usage_patterns = []

        for category in ["Servers", "Storage", "Devices", "Network"]:
            self.assertEqual(
                len(list(system2.energy_footprints[category].values())), 2,
                f"{category} doesn’t have right len")

    def test_footprints_by_category_and_object(self):
        fab_footprints = {
            "Servers": {self.server: ExplainableQuantity(6 * u.kg, "server")},
            "Storage": {self.storage: ExplainableQuantity(6 * u.kg, "storage")},
            "Devices": {self.usage_pattern: ExplainableQuantity(6 * u.kg, "usage_pattern")},
            "Network": {self.network: ExplainableQuantity(0 * u.kg, "network")}
        }

        energy_footprints = {
            "Servers": {self.server: ExplainableQuantity(5 * u.kg, "server")},
            "Storage": {self.storage: ExplainableQuantity(5 * u.kg, "storage")},
            "Devices": {self.usage_pattern: ExplainableQuantity(5 * u.kg, "usage_pattern")},
            "Network": {self.network: ExplainableQuantity(5 * u.kg, "network")},
        }

        with patch.object(System, "fabrication_footprint_sum_over_period", new_callable=PropertyMock) as fab_mock,\
            patch.object(System, "energy_footprint_sum_over_period", new_callable=PropertyMock) as en_mock:
            fab_mock.return_value = fab_footprints
            en_mock.return_value = energy_footprints
            self.system.plot_footprints_by_category_and_object(
                filename=os.path.join(root_test_dir, "footprints by category and object unit test.html"))

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
            self.system.plot_emission_diffs(filepath=os.path.join(root_test_dir, "test_system_diff_plot.png"))

    def test_creating_system_with_empty_up_list_is_possible(self):
        system = System("Test system", usage_patterns=[], edge_usage_patterns=[])

    def test_creating_system_with_edge_usage_patterns(self):
        edge_setup = self._make_edge_usage_pattern(
            with_server_need=True,
            with_job=True,
            with_ids=True,
            with_footprints=True
        )
        edge_usage_pattern = edge_setup["edge_usage_pattern"]
        edge_computer = edge_setup["edge_computer"]
        storage_from_edge = edge_setup["edge_storage"]
        edge_usage_journey = edge_setup["edge_usage_journey"]

        system = System("Test system with edge patterns", usage_patterns=[], edge_usage_patterns=[edge_usage_pattern])
        system.trigger_modeling_updates = False

        self.assertEqual([edge_usage_pattern], system.edge_usage_patterns)
        self.assertEqual([edge_computer], system.edge_computers)
        self.assertEqual([storage_from_edge], system.edge_storages)
        self.assertEqual([edge_usage_journey], system.edge_usage_journeys)

    def test_fabrication_footprints_includes_edge_devices(self):
        expected_dict = self._base_fabrication_footprints()
        self.assertDictEqual(expected_dict, self.system.fabrication_footprints)

        edge_computer, edge_storage = self._make_edge_device(
            fab=self._hourly_kg(values=(2, 3, 4)),
            storage_fab=self._hourly_kg(values=(1, 1, 1)),
            with_ids=True
        )

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            fab_footprints = self.system.fabrication_footprints

            expected_dict["EdgeDevices"] = {edge_computer: edge_computer.instances_fabrication_footprint}
            self.assertDictEqual(expected_dict, fab_footprints)

    def test_energy_footprints_includes_edge_devices(self):
        expected_dict = self._base_energy_footprints()
        self.assertDictEqual(expected_dict, self.system.energy_footprints)

        edge_computer, edge_storage = self._make_edge_device(
            energy=self._hourly_kg(values=(2, 3, 4)),
            storage_energy=self._hourly_kg(values=(1, 1, 1)),
            with_ids=True
        )
        edge_storage.id = "edge_storage_id"

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            energy_footprints = self.system.energy_footprints

            expected_dict["EdgeDevices"] = {edge_computer: edge_computer.energy_footprint}
            self.assertDictEqual(expected_dict, energy_footprints)

    def test_total_fabrication_footprints_includes_edge_devices(self):
        edge_computer, edge_storage = self._make_edge_device(
            fab=self._hourly_kg(values=(2, 3, 4)),
            storage_fab=self._hourly_kg(values=(1, 1, 1))
        )

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            total_fab_footprints = self.system.total_fabrication_footprints

            self.assertEqual("Edge devices total fabrication footprint", total_fab_footprints["EdgeDevices"].label)
            self.assertEqual(edge_computer.instances_fabrication_footprint, total_fab_footprints["EdgeDevices"])

    def test_total_energy_footprints_includes_edge_devices(self):
        edge_computer, edge_storage = self._make_edge_device(
            energy=self._hourly_kg(values=(2, 3, 4)),
            storage_energy=self._hourly_kg(values=(1, 1, 1))
        )

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            total_energy_footprints = self.system.total_energy_footprints

            self.assertEqual("Edge devices total energy footprint", total_energy_footprints["EdgeDevices"].label)
            self.assertEqual(edge_computer.energy_footprint, total_energy_footprints["EdgeDevices"])

    def test_total_fabrication_footprint_sum_over_period_includes_edge_devices(self):
        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "ExternalAPIs": ExplainableQuantity(0 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(0 * u.kg, "null value"),
            "EdgeDevices": ExplainableQuantity(0 * u.kg, "null value")
        }

        total_fab_sum = self.system.total_fabrication_footprint_sum_over_period
        self.assertDictEqual(expected_dict, total_fab_sum)

        edge_computer, edge_storage = self._make_edge_device(
            fab=self._hourly_kg(values=(2, 3, 4)),
            storage_fab=self._hourly_kg(values=(1, 1, 1))
        )

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            total_fab_sum = self.system.total_fabrication_footprint_sum_over_period

            self.assertIn("EdgeDevices", total_fab_sum)
            self.assertEqual(ExplainableQuantity(9 * u.kg, "sum"), total_fab_sum["EdgeDevices"])

    def test_total_energy_footprint_sum_over_period_includes_edge_computers(self):
        expected_dict = {
            "Servers": ExplainableQuantity(6 * u.kg, "null value"),
            "ExternalAPIs": ExplainableQuantity(0 * u.kg, "null value"),
            "Storage": ExplainableQuantity(6 * u.kg, "null value"),
            "Devices": ExplainableQuantity(6 * u.kg, "null value"),
            "Network": ExplainableQuantity(6 * u.kg, "null value"),
            "EdgeDevices": ExplainableQuantity(0 * u.kg, "null value")
        }

        total_energy_sum = self.system.total_energy_footprint_sum_over_period
        self.assertDictEqual(expected_dict, total_energy_sum)

        edge_computer, edge_storage = self._make_edge_device(
            energy=self._hourly_kg(values=(2, 3, 4)),
            storage_energy=self._hourly_kg(values=(1, 1, 1))
        )

        with patch.object(System, "edge_devices", new_callable=PropertyMock) as mock_edge_devices:
            mock_edge_devices.return_value = [edge_computer]
            total_energy_sum = self.system.total_energy_footprint_sum_over_period

            self.assertIn("EdgeDevices", total_energy_sum)
            self.assertEqual(ExplainableQuantity(9 * u.kg, "sum"), total_energy_sum["EdgeDevices"])

    def test_system_with_both_usage_patterns_and_edge_usage_patterns(self):
        edge_setup = self._make_edge_usage_pattern(
            with_ids=True,
            with_footprints=True,
            pattern_fab=self._hourly_kg(values=(2, 3, 4)),
            pattern_energy=self._hourly_kg(values=(2, 3, 4)),
            edge_fab=self._hourly_kg(values=(2, 3, 4)),
            edge_energy=self._hourly_kg(values=(2, 3, 4)),
            network_energy=self._hourly_kg(values=(2, 3, 4))
        )
        edge_usage_pattern = edge_setup["edge_usage_pattern"]
        edge_computer = edge_setup["edge_computer"]
        storage_from_edge = edge_setup["edge_storage"]

        system = System("Test system with both patterns",
                       usage_patterns=[self.usage_pattern],
                       edge_usage_patterns=[edge_usage_pattern])
        system.trigger_modeling_updates = False

        # Test that both regular and edge components are included
        self.assertEqual([self.usage_pattern], system.usage_patterns)
        self.assertEqual([edge_usage_pattern], system.edge_usage_patterns)
        self.assertEqual([self.server], system.servers)
        self.assertEqual([edge_computer], system.edge_computers)

        # Test combined storages
        combined_storages = system.storages + system.edge_storages
        self.assertIn(self.storage, combined_storages)
        self.assertIn(storage_from_edge, combined_storages)

        # Test footprints include both types
        fab_footprints = system.fabrication_footprints
        self.assertIn("Devices", fab_footprints)
        self.assertIn("EdgeDevices", fab_footprints)
        self.assertIn(self.usage_pattern, fab_footprints["Devices"])
        self.assertIn(edge_computer, fab_footprints["EdgeDevices"])

        energy_footprints = system.energy_footprints
        self.assertIn("Devices", energy_footprints)
        self.assertIn("EdgeDevices", energy_footprints)
        self.assertIn(self.usage_pattern, energy_footprints["Devices"])
        self.assertIn(edge_computer, energy_footprints["EdgeDevices"])

    def test_get_objects_linked_to_edge_usage_patterns(self):
        edge_setup = self._make_edge_usage_pattern(with_server_need=True, with_job=True)
        edge_usage_pattern = edge_setup["edge_usage_pattern"]
        edge_usage_journey = edge_setup["edge_usage_journey"]
        edge_function = edge_setup["edge_function"]
        edge_resource_need = edge_setup["edge_resource_need"]
        edge_computer = edge_setup["edge_computer"]
        storage = edge_setup["edge_storage"]
        server_need = edge_setup["server_need"]

        system = System.__new__(System)
        system.trigger_modeling_updates = False
        system.usage_patterns = []
        system.edge_usage_patterns = [edge_usage_pattern]

        linked_objects = system.get_objects_linked_to_edge_usage_patterns([edge_usage_pattern])

        # Check that all expected objects are in the linked objects list
        self.assertIn(edge_usage_pattern, linked_objects)
        self.assertIn(edge_usage_journey, linked_objects)
        self.assertIn(edge_function, linked_objects)
        self.assertIn(edge_resource_need, linked_objects)
        self.assertIn(edge_computer, linked_objects)
        self.assertIn(storage, linked_objects)
        self.assertIn(edge_resource_need, linked_objects)
        self.assertIn(server_need, linked_objects)
        self.assertEqual(8, len(linked_objects))


if __name__ == '__main__':
    unittest.main()
