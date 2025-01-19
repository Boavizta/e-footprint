import re
from typing import List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceObject
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, EmptyExplainableObject
from efootprint.builders.services.service_base_class import Service
from efootprint.constants.units import u
from efootprint.core.hardware.servers.server_base_class import Server
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
    
    def __init__(self, name: str, server: Server, base_ram_consumption: SourceValue = None,
                 bits_per_pixel: SourceValue = None, static_delivery_cpu_cost: SourceValue = None,
                 ram_buffer_per_user: SourceValue = None):
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


class StreamingJob(Job):
    def __init__(self, service: VideoStreamingService, resolution: str, video_watch_duration: SourceValue,
                 frames_per_second: SourceValue):
        super().__init__(f"{resolution} streaming on {service.name}",
                         service.server, SourceValue(0 * u.kB), SourceValue(0 * u.kB), SourceValue(0 * u.kB),
                         video_watch_duration, SourceValue(0 * u.core), SourceValue(0 * u.GB))
        self.service = service
        self.resolution = SourceObject(resolution, Sources.USER_DATA, f"{self.name} resolution")
        self.frames_per_second = frames_per_second
        self.dynamic_bitrate = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return ["dynamic_bitrate", "data_download", "cpu_needed", "ram_needed"] + super().calculated_attributes

    def update_dynamic_bitrate(self):
        match = re.search(r"\((\d+)\s*x\s*(\d+)\)", self.resolution.value)
        if not match:
            raise ValueError(f"Invalid resolution format: {self.resolution.value}")
        width, height = map(int, match.groups())
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless, f"pixel count for resolution {self.resolution}",
            left_parent=self.resolution, operator="pixel count computation", source=Sources.USER_DATA)

        frames_per_second = self.frames_per_second

        self.dynamic_bitrate = (pixel_count * self.service.bits_per_pixel * frames_per_second).to(u.MB / u.s).set_label(
            f"{self.name} dynamic bitrate")

    def update_data_download(self):
        self.data_download = (self.request_duration * self.dynamic_bitrate).to(u.GB).set_label(
            f"{self.name} data download")

    def update_cpu_needed(self):
        self.cpu_needed = (self.service.static_delivery_cpu_cost * self.dynamic_bitrate).to(u.core).set_label(
            f"{self.name} CPU needed")

    def update_ram_needed(self):
        self.ram_needed = self.service.ram_buffer_per_user.copy().set_label(f"{self.name} RAM needed")