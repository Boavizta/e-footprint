import unittest
from unittest.mock import Mock, patch

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.core.hardware.server import Server


class TestVideoStreamingJob(unittest.TestCase):
    def setUp(self):
        self.service = Mock(spec=VideoStreaming)
        self.service.server = Mock()
        self.service.bits_per_pixel = EmptyExplainableObject()
        self.service.refresh_rate = EmptyExplainableObject()
        self.service.static_delivery_cpu_cost = EmptyExplainableObject()
        self.service.ram_buffer_per_user = EmptyExplainableObject()
        self.job = VideoStreamingJob.from_defaults("Test Job", service=self.service)
        self.job.trigger_modeling_updates = False

    def test_installable_on(self):
        self.assertEqual(VideoStreaming.installable_on(), [Server])

    def test_compatible_services(self):
        self.assertEqual(VideoStreamingJob.compatible_services(), [VideoStreaming])

    def test_compatible_jobs(self):
        self.assertEqual(VideoStreaming.compatible_jobs(), [VideoStreamingJob])

    def test_update_dynamic_bitrate(self):
        with patch.object(self.job, "resolution", SourceObject("1080p (1920 x 1080)")), \
            patch.object(self.service, "bits_per_pixel", SourceValue(24 * u.dimensionless)), \
                patch.object(self.service, "refresh_rate", SourceValue(30 * u.dimensionless / u.s)):
            self.job.update_dynamic_bitrate()
        self.job.update_dynamic_bitrate()
        self.assertEqual(self.job.dynamic_bitrate.value, 0 * u.dimensionless)

    def test_update_data_transferred(self):
        with patch.object(self.job, "dynamic_bitrate", SourceValue(30 * u.dimensionless / u.s)), \
            patch.object(self.job, "request_duration", SourceValue(1 * u.s)):
            self.job.update_data_transferred()
        self.assertTrue(abs(self.job.data_transferred.value - 30 * u.dimensionless) < 1e-5 * u.dimensionless)

    def test_update_compute_needed(self):
        with patch.object(self.job, "dynamic_bitrate", SourceValue(3 * u.GB / u.s)), \
            patch.object(self.service, "static_delivery_cpu_cost", SourceValue(4 * u.cpu_core / (u.GB / u.s))):
            self.job.update_compute_needed()
        self.assertTrue(self.job.compute_needed.value, 12 * u.cpu_core)

    def test_update_ram_needed(self):
        with patch.object(self.service, "ram_buffer_per_user", SourceValue(50 * u.MB_ram)):
            self.job.update_ram_needed()
        self.assertTrue(self.job.ram_needed.value, 50 * u.MB_ram)


if __name__ == "__main__":
    unittest.main()
