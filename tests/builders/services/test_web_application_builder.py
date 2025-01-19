import unittest
from unittest.mock import Mock, patch

import pandas as pd

from efootprint.builders.services.web_application import WebApplicationService
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server


class TestWebApplicationService(unittest.TestCase):
    def setUp(self):
        mock_server = Mock(spec=Server)
        mock_server.contextual_modeling_obj_containers = []
        self.server = mock_server
        self.builder = WebApplicationService("test", self.server, "php-symfony")

    @patch("efootprint.builders.services.web_application.default_request_duration")
    @patch("efootprint.builders.services.web_application.ECOBENCHMARK_DF")
    @patch("efootprint.builders.services.web_application.Job")
    def test_job_generation(self, mock_job, mock_ecobenchmark_df, mock_default_request_duration):
        mock_ecobenchmark_df.__getitem__.side_effect = pd.DataFrame.from_dict(
            {"service": ["php-symfony"], "use_case": ["default"],
             "avg_cpu_core_per_request": [0.5], "avg_ram_per_request_in_MB": [512]}).__getitem__
        mock_default_request_duration.return_value = SourceValue(1 * u.s)
        job = self.builder.generate_job("test job", SourceValue(1 * u.MB), SourceValue(1 * u.MB), SourceValue(1 * u.MB))
        mock_job.assert_called_once_with(
            "test job", self.server, SourceValue(1 * u.MB), SourceValue(1 * u.MB), SourceValue(1 * u.MB),
            request_duration=SourceValue(1 * u.s), cpu_needed=SourceValue(0.5 * u.core),
            ram_needed=SourceValue(512 * u.MB))

    def test_web_application_builder_raises_valueerror_if_technology_is_not_in_list(self):
        with self.assertRaises(ValueError):
            WebApplicationService("test", self.server, "not-in-list")
