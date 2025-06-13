import unittest
from datetime import timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.usage.job import Job
from efootprint.constants.units import u


class TestJob(TestCase):
    def setUp(self):
        self.server = MagicMock(spec=Server, id="server")
        self.server.class_as_simple_str = "Autoscaling"
        self.server.name = "server"

        self.job = Job(
            "test job", server=self.server, data_transferred=SourceValue(300 * u.MB),
             data_stored=SourceValue(300 * u.MB), ram_needed=SourceValue(400 * u.MB),
              compute_needed=SourceValue(2 * u.cpu_core), request_duration=SourceValue(2 * u.min))
        self.job.trigger_modeling_updates = False

    def test_data_stored_can_have_negative_value(self):
        Job.from_defaults("test job", server=self.server, data_stored=SourceValue(-300 * u.MB))

    def test_data_transferred_raises_error_if_negative_value(self):
        with self.assertRaises(ValueError):
            Job.from_defaults("test job", server=self.server, data_transferred=SourceValue(-300 * u.MB))

    def test_self_delete_should_raise_error_if_self_has_associated_uj_step(self):
        uj_step = MagicMock()
        uj_step.name = "uj_step"
        self.job.contextual_modeling_obj_containers = [ContextualModelingObjectAttribute(self.job, uj_step, "jobs")]
        with self.assertRaises(PermissionError):
            self.job.self_delete()

    def test_self_delete_removes_backward_links_and_recomputes_server_and_network(self):
        network = MagicMock(spec=Network, id="network")
        network.efootprint_class = Network
        network.set_modeling_obj_container = MagicMock()
        server = MagicMock(spec=Server, id="server")
        server.efootprint_class = Server
        server.name = "server"
        server.mod_objs_computation_chain = [server, network]
        server.set_modeling_obj_container = MagicMock()
        job = Job.from_defaults("test job", server=server)
        server.contextual_modeling_obj_containers = [ContextualModelingObjectAttribute(server, job, "server")]
        with patch.object(Job, "mod_obj_attributes", new_callable=PropertyMock) as mock_mod_obj_attributes:
            mock_mod_obj_attributes.return_value = [server]
            job.trigger_modeling_updates = True
            job.self_delete()
            server.set_modeling_obj_container.assert_called_once_with(None, None)
            server.compute_calculated_attributes.assert_called_once()
            network.compute_calculated_attributes.assert_called_once()

    def test_self_delete_removes_backward_links_and_doesnt_recompute_server_and_network(self):
        network = MagicMock(spec=Network, id="network")
        network.class_as_simple_str = "Network"
        network.set_modeling_obj_container = MagicMock()
        server = MagicMock(spec=Server, id="server")
        server.class_as_simple_str = "Server"
        server.name = "server"
        server.mod_objs_computation_chain = [server, network]
        server.set_modeling_obj_container = MagicMock()
        job = Job.from_defaults("test job", server=server)
        server.contextual_modeling_obj_containers = [ContextualModelingObjectAttribute(server, job, "server")]
        with patch.object(Job, "mod_obj_attributes", new_callable=PropertyMock) as mock_mod_obj_attributes:
            mock_mod_obj_attributes.return_value = [server]
            job.trigger_modeling_updates = False
            job.self_delete()
            server.set_modeling_obj_container.assert_called_once_with(None, None)
            server.compute_calculated_attributes.assert_not_called()
            network.compute_calculated_attributes.assert_not_called()

    def test_duration_in_full_hours(self):
        self.assertEqual(1 * u.dimensionless, self.job.duration_in_full_hours.value)

    def test_compute_hourly_job_occurrences_simple_case(self):
        uj1 = MagicMock()
        uj_step11 = MagicMock()
        uj1.uj_steps = [uj_step11]
        uj_step11.jobs = [self.job]
        uj_step11.user_time_spent = SourceValue(90 * u.min)
        usage_pattern = MagicMock()
        usage_pattern.usage_journey = uj1
        hourly_uj_starts = create_source_hourly_values_from_list([1, 2, 5, 7])
        usage_pattern.utc_hourly_usage_journey_starts = hourly_uj_starts
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

        self.job.update_dict_element_in_hourly_occurrences_per_usage_pattern(usage_pattern)
        job_occurrences = self.job.hourly_occurrences_per_usage_pattern[usage_pattern]
        self.assertEqual(hourly_uj_starts.start_date, job_occurrences.start_date)
        self.assertEqual(hourly_uj_starts.value_as_float_list, job_occurrences.value_as_float_list)
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

    def test_compute_hourly_job_occurrences_uj_lasting_less_than_an_hour_before(self):
        uj1 = MagicMock()
        uj_step11 = MagicMock()
        uj_step12 = MagicMock()
        job2 = MagicMock()
        uj1.uj_steps = [uj_step11, uj_step12]
        uj_step11.jobs = [job2]
        uj_step11.user_time_spent = SourceValue(40 * u.min)
        uj_step12.jobs = [self.job]
        uj_step12.user_time_spent = SourceValue(4 * u.min)
        usage_pattern = MagicMock()
        usage_pattern.usage_journey = uj1
        hourly_uj_starts = create_source_hourly_values_from_list([1, 2, 5, 7])
        usage_pattern.utc_hourly_usage_journey_starts = hourly_uj_starts
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

        self.job.update_dict_element_in_hourly_occurrences_per_usage_pattern(usage_pattern)
        job_occurrences = self.job.hourly_occurrences_per_usage_pattern[usage_pattern]
        self.assertEqual(hourly_uj_starts.start_date, job_occurrences.start_date)
        self.assertEqual(hourly_uj_starts.value_as_float_list, job_occurrences.value_as_float_list)
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

    def test_compute_hourly_job_occurrences_uj_lasting_more_than_an_hour_before(self):
        uj1 = MagicMock()
        uj_step11 = MagicMock()
        uj_step12 = MagicMock()
        job2 = MagicMock()
        uj1.uj_steps = [uj_step11, uj_step12]
        uj_step11.jobs = [job2]
        uj_step11.user_time_spent = SourceValue(61 * u.min)
        uj_step12.jobs = [self.job]
        uj_step12.user_time_spent = SourceValue(4 * u.min)
        usage_pattern = MagicMock()
        usage_pattern.usage_journey = uj1
        hourly_uj_starts = create_source_hourly_values_from_list([1, 2, 5, 7])
        usage_pattern.utc_hourly_usage_journey_starts = hourly_uj_starts
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

        self.job.update_dict_element_in_hourly_occurrences_per_usage_pattern(usage_pattern)
        job_occurrences = self.job.hourly_occurrences_per_usage_pattern[usage_pattern]
        self.assertEqual(hourly_uj_starts.start_date + timedelta(hours=1),
        job_occurrences.start_date)
        self.assertEqual(hourly_uj_starts.value_as_float_list, job_occurrences.value_as_float_list)
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

    def test_compute_hourly_job_occurrences_uj_steps_sum_up_to_more_than_one_hour(self):
        uj1 = MagicMock()
        uj_step11 = MagicMock()
        uj_step12 = MagicMock()
        uj_step13 = MagicMock()
        job2 = MagicMock()
        uj1.uj_steps = [uj_step11, uj_step12, uj_step13]
        uj_step11.jobs = [job2]
        uj_step11.user_time_spent = SourceValue(59 * u.min)
        uj_step12.jobs = [job2]
        uj_step12.user_time_spent = SourceValue(4 * u.min)
        uj_step13.jobs = [self.job, self.job]
        uj_step13.user_time_spent = SourceValue(1 * u.min)
        usage_pattern = MagicMock()
        usage_pattern.usage_journey = uj1
        hourly_uj_starts = create_source_hourly_values_from_list([1, 2, 5, 7])
        usage_pattern.utc_hourly_usage_journey_starts = hourly_uj_starts
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

        self.job.update_dict_element_in_hourly_occurrences_per_usage_pattern(usage_pattern)
        job_occurrences = self.job.hourly_occurrences_per_usage_pattern[usage_pattern]
        self.assertEqual(
            hourly_uj_starts.start_date + timedelta(hours=1),
            job_occurrences.start_date)
        self.assertEqual([elt * 2 for elt in hourly_uj_starts.value_as_float_list],
                         job_occurrences.value_as_float_list)
        self.job.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()

    def test_compute_job_hourly_data_exchange_simple_case(self):
        data_exchange = "data_stored"
        usage_pattern = MagicMock()
        hourly_occs_per_up = ExplainableObjectDict(
            {usage_pattern: create_source_hourly_values_from_list([1, 3, 5])})

        with patch.object(self.job, "hourly_occurrences_per_usage_pattern", hourly_occs_per_up), \
                patch.object(self.job, "data_stored", SourceValue(1 * u.GB)), \
                patch.object(Job, "duration_in_full_hours", new_callable=PropertyMock) as mock_full_hour_duration:
            mock_full_hour_duration.return_value = SourceValue(1 * u.dimensionless)
            job_hourly_data_exchange = self.job.compute_hourly_data_exchange_for_usage_pattern(
                usage_pattern, data_exchange)

            self.assertEqual([1, 3, 5], job_hourly_data_exchange.value_as_float_list)

    def test_compute_job_hourly_data_exchange_complex_case(self):
        data_exchange = "data_stored"
        usage_pattern = MagicMock()
        hourly_occs_per_up = ExplainableObjectDict(
            {usage_pattern: create_source_hourly_values_from_list([1, 3, 5])})

        with patch.object(self.job, "hourly_occurrences_per_usage_pattern", hourly_occs_per_up), \
                patch.object(self.job, "data_stored", SourceValue(1 * u.GB)), \
                patch.object(Job, "duration_in_full_hours", new_callable=PropertyMock) as mock_full_hour_duration:
            mock_full_hour_duration.return_value = SourceValue(2 * u.dimensionless)
            job_hourly_data_exchange = self.job.compute_hourly_data_exchange_for_usage_pattern(
                usage_pattern, data_exchange)

            self.assertEqual([0.5, 2, 4, 2.5], job_hourly_data_exchange.value_as_float_list)
            
    def test_compute_calculated_attribute_summed_across_usage_patterns_per_job(self):
        usage_pattern1 = MagicMock()
        usage_pattern2 = MagicMock()
        hourly_calc_attr_per_up = ExplainableObjectDict({
            usage_pattern1: create_source_hourly_values_from_list([1, 2, 5]),
            usage_pattern2: create_source_hourly_values_from_list([3, 2, 4])})
        self.job.hourly_calc_attr_per_up = hourly_calc_attr_per_up

        with patch.object(Job, "usage_patterns", new_callable=PropertyMock) as mock_ups:
            mock_ups.return_value = [usage_pattern1, usage_pattern2]
            result = self.job.sum_calculated_attribute_across_usage_patterns("hourly_calc_attr_per_up", "my calc attr")

            self.assertEqual([4, 4, 9], result.value_as_float_list)
            self.assertEqual("Hourly test job my calc attr across usage patterns", result.label)

        del self.job.hourly_calc_attr_per_up


if __name__ == "__main__":
    unittest.main()
