import re

from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.builders.services.service_base_class import Service
from efootprint.constants.units import u
from efootprint.core.usage.job import Job


class VideoStreamingService(Service):
    _default_values = {
        "bits_per_pixel": ExplainableQuantity(
    24 * u.dimensionless, "bits per pixel (standard for video compression)", source=Sources.HYPOTHESIS),
        "frames_per_second": ExplainableQuantity(
    30 * u.dimensionless / u.s, "frames per second for video playback", source=Sources.HYPOTHESIS),
        "ram_buffer_per_user": ExplainableQuantity(
    50 * u.MB, "buffer size per user", source=Sources.HYPOTHESIS),
        "static_delivery_cpu_cost": ExplainableQuantity(
            4 * u.core / (u.GB / u.s), "CPU cost per static stream", source=Sources.HYPOTHESIS),
        "base_ram_consumption": ExplainableQuantity(
    2 * u.GB, "OS and streaming software base RAM consumption", source=Sources.HYPOTHESIS)
    }

    @classmethod
    def list_values(cls):
        return {"resolution": [
            "480p (640 x 480)", "720p (1280 x 720)", "1080p (1920 x 1080)", "1440p (2560 x 1440)", "2K (2048 x 1080)",
            "4K (3840 x 2160)", "8K (7680 x 4320)"]
        }

    @classmethod
    def conditional_list_values(cls):
        return {}
    
    def __init__(self, name, server, base_ram_consumption: SourceValue = None, bits_per_pixel: SourceValue = None,
                 static_delivery_cpu_cost: SourceValue = None, ram_buffer_per_user: SourceValue = None):
        super().__init__(name, server)
        self.server = server
        self.base_ram_consumption = (base_ram_consumption or self.default_value("base_ram_consumption")).set_label(
            f"{self.name} OS and streaming software base RAM consumption")
        self.bits_per_pixel = (bits_per_pixel or self.default_value("bits_per_pixel")
                               ).set_label(f"{self.name} bits per pixel")
        self.static_delivery_cpu_cost = (static_delivery_cpu_cost or self.default_value("static_delivery_cpu_cost")
                                         ).set_label(f"{self.name} CPU cost per static stream")
        self.ram_buffer_per_user = (ram_buffer_per_user or self.default_value("ram_buffer_per_user")).set_label(
            f"{self.name} RAM buffer size per user")

    def generate_job(self, resolution: str, video_watch_duration: SourceValue,
                     frames_per_second: SourceValue = None):
        """
        Create a Job object for a streaming request based on the duration of the video watched.
        The bitrate is dynamically computed based on the resolution.

        Args:
            resolution (str): Resolution of the video stream (e.g., "1920x1080").
            video_watch_duration (SourceValue): Duration of the video watched in seconds.
            frames_per_second (SourceValue): Number of frames per second for video playback.

        Returns:
            Job: An object that represents the resources needed for the streaming job.
        """
        match = re.search(r"\((\d+)\s*x\s*(\d+)\)", resolution)
        if not match:
            raise ValueError(f"Invalid resolution format: {resolution}")
        width, height = map(int, match.groups())
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless,f"pixel count for resolution {resolution}", source=Sources.USER_DATA)

        frames_per_second = frames_per_second or self.default_value("frames_per_second")
        dynamic_bitrate = (pixel_count * self.bits_per_pixel * frames_per_second).to(u.MB / u.s)

        stream_duration = video_watch_duration

        data_transfer = stream_duration * dynamic_bitrate
        cpu_needed = self.static_delivery_cpu_cost * dynamic_bitrate

        return Job(
            f"{resolution} streaming", self.server,
            data_upload=SourceValue(0 * u.kB),
            data_stored=data_transfer.to(u.GB).set_label("data stored during streaming"),
            data_download=data_transfer.to(u.GB).set_label("data downloaded during streaming"),
            request_duration=stream_duration,
            cpu_needed=cpu_needed.to(u.core),
            ram_needed=self.ram_buffer_per_user.to(u.MB).copy())
