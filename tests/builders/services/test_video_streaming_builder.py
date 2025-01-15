import unittest
from unittest.mock import Mock, patch
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.services.video_streaming import VideoStreamingService
from efootprint.core.hardware.servers.server_base_class import Server


class TestVideoStreamingService(unittest.TestCase):
    def setUp(self):
        self.mock_server = Mock(spec=Server)
        self.mock_server.contextual_modeling_obj_containers = []
        self.mock_server.name = "Test Server"

        self.streaming_builder = VideoStreamingService(name="Test Streaming", server=self.mock_server)

    def test_initialization(self):
        """Test that the VideoStreamingService initializes correctly."""
        self.assertEqual(self.streaming_builder.server, self.mock_server)
        self.assertEqual(self.streaming_builder.base_ram_consumption.value, 2 * u.GB)
        self.assertEqual(self.streaming_builder.bits_per_pixel.value, 24 * u.dimensionless)
        self.assertEqual(self.streaming_builder.static_delivery_cpu_cost.value, 4 * u.core / (u.GB / u.s))
        self.assertEqual(self.streaming_builder.ram_buffer_per_user.value, 50 * u.MB)

    def test_list_values(self):
        """Test the list_values method."""
        expected_resolutions = [
            "480p (640 x 480)", "720p (1280 x 720)", "1080p (1920 x 1080)", "1440p (2560 x 1440)",
            "2K (2048 x 1080)", "4K (3840 x 2160)", "8K (7680 x 4320)"
        ]
        self.assertEqual(self.streaming_builder.list_values()["resolution"], expected_resolutions)

    def test_generate_job_valid_resolution(self):
        """Test generating a job with a valid resolution."""
        resolution = "1080p (1920 x 1080)"
        video_watch_duration = SourceValue(3600 * u.s)
        frames_per_second = SourceValue(30 * u.dimensionless / u.s)

        with patch("efootprint.builders.services.video_streaming.Job") as mock_job:
            self.streaming_builder.generate_job(resolution, video_watch_duration, frames_per_second)
            pixel_count = SourceValue(1920 * 1080 * u.dimensionless)
            dynamic_bitrate = (pixel_count * SourceValue(24 * u.dimensionless) * frames_per_second).to(u.MB / u.s)
            data_transfer = video_watch_duration * dynamic_bitrate
            cpu_needed = SourceValue(4 * u.core / (u.GB / u.s)) * dynamic_bitrate

            mock_job.assert_called_once_with(
                f"{resolution} streaming", self.mock_server,
                data_upload=SourceValue(0 * u.kB),
                data_stored=data_transfer.to(u.GB).set_label("data stored during streaming"),
                data_download=data_transfer.to(u.GB).set_label("data downloaded during streaming"),
                request_duration=video_watch_duration,
                cpu_needed=cpu_needed.to(u.core),
                ram_needed=SourceValue(50 * u.MB)
            )

    def test_generate_job_invalid_resolution(self):
        """Test that an invalid resolution raises a ValueError."""
        invalid_resolution = "invalid resolution"
        video_watch_duration = SourceValue(3600 * u.s)

        with self.assertRaises(ValueError):
            self.streaming_builder.generate_job(invalid_resolution, video_watch_duration)


if __name__ == "__main__":
    unittest.main()
