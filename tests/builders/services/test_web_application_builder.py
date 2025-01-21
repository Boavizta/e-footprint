import unittest
from unittest.mock import Mock, patch

import pandas as pd

from efootprint.builders.services.web_application import WebApplicationService, WebApplicationJob
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server


class TestWebApplicationService(unittest.TestCase):
    def setUp(self):
        mock_server = Mock(spec=Server)
        mock_server.contextual_modeling_obj_containers = []
        self.server = mock_server
        self.builder = WebApplicationService("test", self.server, SourceObject("php-symfony"))



    def test_web_application_builder_raises_valueerror_if_technology_is_not_in_list(self):
        with self.assertRaises(ValueError):
            WebApplicationService("test", self.server, SourceObject("not-in-list"))


class TestWebApplicationJob(unittest.TestCase):
    @patch("efootprint.builders.services.web_application.default_request_duration")
    @patch("efootprint.builders.services.web_application.ECOBENCHMARK_DF")
    def test_update_cpu_needed(self, mock_ecobenchmark_df, mock_default_request_duration):
        mock_ecobenchmark_df.__getitem__.side_effect = pd.DataFrame.from_dict(
            {"service": ["php-symfony"], "use_case": ["default"],
             "avg_cpu_core_per_request": [0.5], "avg_ram_per_request_in_MB": [512]}).__getitem__
        mock_default_request_duration.return_value = SourceValue(1 * u.s)
        service = Mock(spec=WebApplicationService)
        service.technology = SourceObject("php-symfony")
        service.contextual_modeling_obj_containers = []
        service.server = Mock()
        job = WebApplicationJob(
            "test job", service=service, data_upload=SourceValue(1 * u.MB),
            data_stored=SourceValue(1 * u.MB), data_download=SourceValue(1 * u.MB),
            implementation_details=SourceObject("default"))
        job.update_cpu_needed()
        self.assertEqual(job.cpu_needed, SourceValue(0.5 * u.core))

    @patch("efootprint.builders.services.web_application.default_request_duration")
    @patch("efootprint.builders.services.web_application.ECOBENCHMARK_DF")
    def test_update_ram_needed(self, mock_ecobenchmark_df, mock_default_request_duration):
        mock_ecobenchmark_df.__getitem__.side_effect = pd.DataFrame.from_dict(
            {"service": ["php-symfony"], "use_case": ["default"],
             "avg_cpu_core_per_request": [0.5], "avg_ram_per_request_in_MB": [512]}).__getitem__
        mock_default_request_duration.return_value = SourceValue(1 * u.s)
        service = Mock(spec=WebApplicationService)
        service.technology = SourceObject("php-symfony")
        service.contextual_modeling_obj_containers = []
        service.server = Mock()
        job = WebApplicationJob(
            "test job", service=service, data_upload=SourceValue(1 * u.MB),
            data_stored=SourceValue(1 * u.MB), data_download=SourceValue(1 * u.MB),
            implementation_details=SourceObject("default"))
        job.update_ram_needed()
        self.assertEqual(job.ram_needed, SourceValue(512 * u.MB))
