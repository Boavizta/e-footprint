import unittest
from unittest.mock import Mock, patch

import pandas as pd

from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server


class TestWebApplication(unittest.TestCase):
    def setUp(self):
        mock_server = Mock(spec=Server)
        self.server = mock_server
        self.builder = WebApplication("test", self.server, SourceObject("php-symfony"))

    def test_installable_on(self):
        self.assertEqual(WebApplication.installable_on(), [Server])

    def test_compatible_jobs(self):
        self.assertEqual(WebApplication.compatible_jobs(), [WebApplicationJob])

    def test_web_application_builder_raises_valueerror_if_technology_is_not_in_list(self):
        with self.assertRaises(ValueError):
            WebApplication("test", self.server, SourceObject("not-in-list"))


class TestWebApplicationJob(unittest.TestCase):
    def test_compatible_services(self):
        self.assertEqual(WebApplicationJob.compatible_services(), [WebApplication])

    @patch("efootprint.builders.services.web_application.default_request_duration")
    @patch("efootprint.builders.services.web_application.ECOBENCHMARK_DF")
    def test_update_compute_needed(self, mock_ecobenchmark_df, mock_default_request_duration):
        mock_ecobenchmark_df.__getitem__.side_effect = pd.DataFrame.from_dict(
            {"service": ["php-symfony"], "use_case": ["default"],
             "avg_cpu_core_per_request": [0.5], "avg_ram_per_request_in_MB": [512]}).__getitem__
        mock_default_request_duration.return_value = SourceValue(1 * u.s)
        service = Mock(spec=WebApplication)
        service.technology = SourceObject("php-symfony")
        service.server = Mock()
        job = WebApplicationJob(
            "test job", service=service, data_upload=SourceValue(1 * u.MB),
            data_stored=SourceValue(1 * u.MB), data_download=SourceValue(1 * u.MB),
            implementation_details=SourceObject("default"))
        job.update_compute_needed()
        self.assertEqual(job.compute_needed, SourceValue(0.5 * u.cpu_core))

    @patch("efootprint.builders.services.web_application.default_request_duration")
    @patch("efootprint.builders.services.web_application.ECOBENCHMARK_DF")
    def test_update_ram_needed(self, mock_ecobenchmark_df, mock_default_request_duration):
        mock_ecobenchmark_df.__getitem__.side_effect = pd.DataFrame.from_dict(
            {"service": ["php-symfony"], "use_case": ["default"],
             "avg_cpu_core_per_request": [0.5], "avg_ram_per_request_in_MB": [512]}).__getitem__
        mock_default_request_duration.return_value = SourceValue(1 * u.s)
        service = Mock(spec=WebApplication)
        service.technology = SourceObject("php-symfony")
        service.server = Mock()
        job = WebApplicationJob(
            "test job", service=service, data_upload=SourceValue(1 * u.MB),
            data_stored=SourceValue(1 * u.MB), data_download=SourceValue(1 * u.MB),
            implementation_details=SourceObject("default"))
        job.update_ram_needed()
        self.assertEqual(job.ram_needed, SourceValue(512 * u.MB))
