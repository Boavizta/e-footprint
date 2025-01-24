from datetime import timedelta, datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.builders.services.video_streaming import VideoStreaming
from efootprint.builders.services.web_application import WebApplication
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues, SourceObject
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server, ServerTypes


class TestServer(TestCase):
    def setUp(self):
        self.country = MagicMock()
        self.server_base = Server(
            "Test server",
            server_type=ServerTypes.on_premise(),
            carbon_footprint_fabrication=SourceValue(0 * u.kg, Sources.BASE_ADEME_V19),
            power=SourceValue(0 * u.W, Sources.HYPOTHESIS),
            lifespan=SourceValue(0 * u.year, Sources.HYPOTHESIS),
            idle_power=SourceValue(0 * u.W, Sources.HYPOTHESIS),
            ram=SourceValue(0 * u.GB, Sources.HYPOTHESIS),
            compute=SourceValue(0 * u.cpu_core, Sources.HYPOTHESIS),
            power_usage_effectiveness=SourceValue(0 * u.dimensionless, Sources.HYPOTHESIS),
            average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
            server_utilization_rate=SourceValue(0 * u.dimensionless, Sources.HYPOTHESIS),
            base_ram_consumption=SourceValue(0 * u.GB, Sources.HYPOTHESIS),
            base_compute_consumption=SourceValue(0 * u.cpu_core, Sources.HYPOTHESIS),
            storage=MagicMock()
        )
        self.server_base.trigger_modeling_updates = False

    def test_installable_services(self):
        self.assertEqual(set(Server.installable_services()), {VideoStreaming, WebApplication})

    def test_update_hour_by_hour_compute_need(self):
        job1 = MagicMock()
        job2 = MagicMock()

        job1.hourly_avg_occurrences_across_usage_patterns = SourceHourlyValues(
            create_hourly_usage_df_from_list([10, 20, 1, 0]))
        job2.hourly_avg_occurrences_across_usage_patterns = SourceHourlyValues(
            create_hourly_usage_df_from_list([20, 15, 5, 3]))
        job1.compute_needed = SourceValue(2 * u.cpu_core)
        job2.compute_needed = SourceValue(3 * u.cpu_core)

        with patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = {job1, job2}
            self.server_base.update_hour_by_hour_compute_need()

        self.assertEqual([80, 85, 17, 9], self.server_base.hour_by_hour_compute_need.value_as_float_list)

    def test_update_hour_by_hour_ram_need(self):
        job1 = MagicMock()
        job2 = MagicMock()

        job1.hourly_avg_occurrences_across_usage_patterns = SourceHourlyValues(
            create_hourly_usage_df_from_list([10, 20, 1, 0]))
        job2.hourly_avg_occurrences_across_usage_patterns = SourceHourlyValues(
            create_hourly_usage_df_from_list([20, 15, 5, 3]))
        job1.ram_needed = SourceValue(2 * u.GB)
        job2.ram_needed = SourceValue(3 * u.GB)

        with patch.object(Server, "jobs", new_callable=PropertyMock) as mock_jobs:
            mock_jobs.return_value = {job1, job2}
            self.server_base.update_hour_by_hour_ram_need()

        self.assertEqual([80, 85, 17, 9], self.server_base.hour_by_hour_ram_need.value_as_float_list)


    def test_available_compute_per_instance(self):
        with patch.object(self.server_base, "occupied_compute_per_instance", SourceValue(2 * u.cpu_core)), \
                patch.object(self.server_base, "compute", SourceValue(24 * u.cpu_core)), \
                patch.object(self.server_base, "server_utilization_rate", SourceValue(0.7 * u.dimensionless)):
            self.server_base.update_available_compute_per_instance()
            expected_value = SourceValue((24 * 0.7 - 2) * u.cpu_core)

            self.assertEqual(expected_value.value, self.server_base.available_compute_per_instance.value)

    def test_available_ram_per_instance(self):
        with patch.object(self.server_base, "occupied_ram_per_instance", SourceValue(2 * u.GB)), \
                patch.object(self.server_base, "ram", SourceValue(24 * u.GB)), \
                patch.object(self.server_base, "server_utilization_rate", SourceValue(0.7 * u.dimensionless)):
            self.server_base.update_available_ram_per_instance()
            expected_value = SourceValue((24 * 0.7 - 2) * u.GB)

            self.assertEqual(expected_value.value, self.server_base.available_ram_per_instance.value)


    def test_available_ram_per_instance_should_raise_value_error_when_demand_exceeds_server_capacity(self):
        with patch.object(self.server_base, "ram", SourceValue(128 * u.GB)), \
            patch.object(self.server_base, "occupied_ram_per_instance", SourceValue(129 * u.GB)), \
            patch.object(self.server_base, "server_utilization_rate", SourceValue(0.7 * u.dimensionless)):
            with self.assertRaises(ValueError):
                self.server_base.update_available_ram_per_instance()

    def test_occupied_compute_per_instance(self):
        service_1 = MagicMock()
        service_2 = MagicMock()
        service_1.base_compute_consumption = SourceValue(2 * u.cpu_core)
        service_2.base_compute_consumption = SourceValue(3 * u.cpu_core)
        with patch.object(self.server_base, "base_compute_consumption", SourceValue(5 * u.cpu_core)), \
                patch.object(Server, "installed_services", [service_1, service_2]):
            self.server_base.update_occupied_compute_per_instance()
            expected_value = SourceValue(10 * u.cpu_core)

            self.assertEqual(expected_value.value, self.server_base.occupied_compute_per_instance.value)

    def test_occupied_ram_per_instance(self):
        service_1 = MagicMock()
        service_2 = MagicMock()
        service_1.base_ram_consumption = SourceValue(2 * u.GB)
        service_2.base_ram_consumption = SourceValue(3 * u.GB)
        with patch.object(self.server_base, "base_ram_consumption", SourceValue(5 * u.GB)), \
                patch.object(Server, "installed_services", [service_1, service_2]):
            self.server_base.update_occupied_ram_per_instance()
            expected_value = SourceValue(10 * u.GB)

            self.assertEqual(expected_value.value, self.server_base.occupied_ram_per_instance.value)

    def test_raw_nb_of_instances_autoscaling_simple_case(self):
        ram_need = SourceHourlyValues(create_hourly_usage_df_from_list([0, 1, 3, 3, 10], pint_unit=u.GB))
        cpu_need = SourceHourlyValues(create_hourly_usage_df_from_list([2, 4, 2, 6, 3], pint_unit=u.cpu_core))

        with patch.object(self.server_base, "hour_by_hour_ram_need", new=ram_need), \
                patch.object(self.server_base, "hour_by_hour_compute_need", new=cpu_need), \
                patch.object(self.server_base, "available_ram_per_instance", new=SourceValue(2 * u.GB)), \
                patch.object(self.server_base, "available_compute_per_instance", new=SourceValue(4 * u.cpu_core)):
            self.server_base.update_raw_nb_of_instances()

            self.assertEqual([0.5, 1, 1.5, 1.5, 5], self.server_base.raw_nb_of_instances.value_as_float_list)

    def test_raw_nb_of_instances_autoscaling_different_timespan_case(self):
        start_date_a = datetime.strptime("2025-01-01", "%Y-%m-%d")
        start_date_b = datetime.strptime("2025-01-02", "%Y-%m-%d")

        ram_need_a = SourceHourlyValues(
            create_hourly_usage_df_from_list([0, 1, 3, 3, 10], start_date_a, pint_unit=u.GB), label="ram_need_a")
        ram_need_b = SourceHourlyValues(
            create_hourly_usage_df_from_list([0, 1, 3, 3, 10], start_date_b, pint_unit=u.GB), label="ram_need_b")
        cpu_need_a = SourceHourlyValues(
            create_hourly_usage_df_from_list([2, 4, 2, 6, 3], start_date_a, pint_unit=u.cpu_core), label="cpu_need_a")
        cpu_need_b = SourceHourlyValues(
            create_hourly_usage_df_from_list([2, 4, 2, 6, 3], start_date_b, pint_unit=u.cpu_core), label="cpu_need_b")
        all_ram_need = (ram_need_a + ram_need_b).set_label("all_ram_need")
        all_cpu_need = (cpu_need_a + cpu_need_b).set_label("all_cpu_need")

        expected_data = [0.5, 1, 1.5, 1.5, 5, 0.5, 1, 1.5, 1.5, 5]
        expected_max_date = start_date_b + timedelta(hours=(len(ram_need_b)-1))

        with patch.object(self.server_base, "hour_by_hour_ram_need", new=all_ram_need), \
                patch.object(self.server_base, "hour_by_hour_compute_need", new=all_cpu_need), \
                patch.object(self.server_base, "available_ram_per_instance", new=SourceValue(2 * u.GB)), \
                patch.object(self.server_base, "available_compute_per_instance", new=SourceValue(4 * u.cpu_core)):
            self.server_base.update_raw_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.raw_nb_of_instances.value_as_float_list)
            self.assertEqual(start_date_a, self.server_base.raw_nb_of_instances.value.index.min().to_timestamp())
            self.assertEqual(expected_max_date, self.server_base.raw_nb_of_instances.value.index.max().to_timestamp())

    def test_compute_instances_energy_simple_case(self):
        with patch.object(self.server_base, "nb_of_instances",
                          SourceHourlyValues(create_hourly_usage_df_from_list([1, 0, 2]))), \
                patch.object(self.server_base, "raw_nb_of_instances",
                             SourceHourlyValues(create_hourly_usage_df_from_list([1, 0, 2]))), \
                patch.object(self.server_base, "power", SourceValue(300 * u.W)), \
                patch.object(self.server_base, "idle_power", SourceValue(50 * u.W)), \
                patch.object(self.server_base, "power_usage_effectiveness", SourceValue(3 * u.dimensionless)):
            self.server_base.update_instances_energy()
            self.assertEqual(u.kWh, self.server_base.instances_energy.unit)
            self.assertEqual([0.9, 0, 1.8], self.server_base.instances_energy.value_as_float_list)

    def test_compute_instances_energy_complex_case(self):
        with patch.object(self.server_base, "nb_of_instances",
                          SourceHourlyValues(create_hourly_usage_df_from_list([1, 0, 2]))), \
                patch.object(self.server_base, "raw_nb_of_instances",
                             SourceHourlyValues(create_hourly_usage_df_from_list([1, 0, 1.5]))), \
                patch.object(self.server_base, "power", SourceValue(300 * u.W)), \
                patch.object(self.server_base, "idle_power", SourceValue(50 * u.W)), \
                patch.object(self.server_base, "power_usage_effectiveness", SourceValue(3 * u.dimensionless)):
            self.server_base.update_instances_energy()
            self.assertEqual(u.kWh, self.server_base.instances_energy.unit)
            self.assertEqual([0.9, 0, 0.9 + 0.525], self.server_base.instances_energy.value_as_float_list)

    def test_energy_footprints(self):
        instance_energy = SourceHourlyValues(
            create_hourly_usage_df_from_list([0.9, 1.8, 2.7], pint_unit=u.kWh))
        average_carbon_intensity = SourceValue(100 * u.g / u.kWh)

        with patch.object(self.server_base, "instances_energy", new=instance_energy), \
                patch.object(self.server_base, "average_carbon_intensity", new=average_carbon_intensity):
            self.server_base.update_energy_footprint()

            expected_footprint = [0.09, 0.18, 0.27]  # in kg
            self.assertEqual(expected_footprint, self.server_base.energy_footprint.value_as_float_list)
            self.assertEqual(u.kg, self.server_base.energy_footprint.unit)

    def test_autoscaling_nb_of_instances(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5]
        expected_data = [1, 1, 2, 2, 5]

        hourly_raw_data = SourceHourlyValues(create_hourly_usage_df_from_list(raw_data, pint_unit=u.dimensionless))
        with patch.object(self.server_base, "raw_nb_of_instances", hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.autoscaling()):
            self.server_base.update_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_on_premise_rounds_up_to_next_integer(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5.5]
        expected_data = [6, 6, 6, 6, 6]

        hourly_raw_data = SourceHourlyValues(create_hourly_usage_df_from_list(raw_data, pint_unit=u.dimensionless))
        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()):
            self.server_base.update_nb_of_instances()
            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_takes_fixed_nb_of_instances_into_account(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5.5]
        expected_data = [12, 12, 12, 12, 12]

        hourly_raw_data = SourceHourlyValues(create_hourly_usage_df_from_list(raw_data, pint_unit=u.dimensionless))

        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()), \
                patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.dimensionless)):
            self.server_base.update_nb_of_instances()
            self.assertEqual(
                expected_data,
                self.server_base.nb_of_instances.value_as_float_list)

    def test_nb_of_instances_raises_error_if_fixed_number_of_instances_is_surpassed(self):
        raw_data = [0.5, 1, 1.5, 1.5, 14]

        hourly_raw_data = SourceHourlyValues(create_hourly_usage_df_from_list(raw_data, pint_unit=u.dimensionless))

        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()), \
                patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.dimensionless)):
            with self.assertRaises(ValueError):
                self.server_base.update_nb_of_instances()

    def test_nb_of_instances_returns_emptyexplainableobject_if_raw_nb_of_instances_is_emptyexplainableobject(self):
        with patch.object(self.server_base, "raw_nb_of_instances", new=EmptyExplainableObject()), \
                patch.object(self.server_base, "server_type", ServerTypes.on_premise()):
            self.server_base.update_nb_of_instances()
            self.assertIsInstance(self.server_base.nb_of_instances, EmptyExplainableObject)

    def test_nb_of_instances_serverless(self):
        raw_data = [0.5, 1, 1.5, 1.5, 5]
        expected_data = [0.5, 1, 1.5, 1.5, 5]

        hourly_raw_data = SourceHourlyValues(create_hourly_usage_df_from_list(raw_data, pint_unit=u.dimensionless))
        with patch.object(self.server_base, "raw_nb_of_instances", new=hourly_raw_data), \
                patch.object(self.server_base, "server_type", ServerTypes.serverless()):
            self.server_base.update_nb_of_instances()

            self.assertEqual(expected_data, self.server_base.nb_of_instances.value_as_float_list)

    def test_server_raises_error_if_server_type_is_not_supported(self):
        with self.assertRaises(ValueError):
            self.server_base.server_type = SourceObject("unsupported_server_type")

    def test_server_raises_error_if_fixed_nb_of_instances_is_defined_for_non_on_premise_server(self):
        with patch.object(self.server_base, "server_type", ServerTypes.serverless()):
            with self.assertRaises(ValueError):
                self.server_base.fixed_nb_of_instances = SourceValue(12 * u.dimensionless)

    def test_server_raises_error_if_fixed_nb_of_instances_is_defined_and_server_type_changes_for_non_on_premise_server(
            self):
        with patch.object(self.server_base, "fixed_nb_of_instances", SourceValue(12 * u.dimensionless)):
            with self.assertRaises(ValueError):
                self.server_base.server_type = ServerTypes.serverless()
