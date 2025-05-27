import re
from typing import List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.services.service_base_class import Service
from efootprint.builders.services.service_job_base_class import ServiceJob
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server


class VideoStreaming(Service):
    @classmethod
    def default_values(cls):
        return {
            "base_ram_consumption": SourceValue(2 * u.GB, source=Sources.HYPOTHESIS),
            "bits_per_pixel": SourceValue(0.1 * u.dimensionless, source=Sources.HYPOTHESIS),
            "static_delivery_cpu_cost": SourceValue(4 * u.cpu_core / (u.GB / u.s), source=Sources.HYPOTHESIS),
            "ram_buffer_per_user": SourceValue(50 * u.MB, source=Sources.HYPOTHESIS),
            }

    def __init__(self, name: str, server: Server, base_ram_consumption: ExplainableQuantity,
                 bits_per_pixel: ExplainableQuantity, static_delivery_cpu_cost: ExplainableQuantity,
                 ram_buffer_per_user: ExplainableQuantity):
        super().__init__(name, server)
        self.base_ram_consumption = base_ram_consumption.set_label(
            f"{self.name} OS and streaming software base RAM consumption")
        self.bits_per_pixel = bits_per_pixel.set_label(f"{self.name} bits per pixel")
        self.static_delivery_cpu_cost = static_delivery_cpu_cost.set_label(f"{self.name} CPU cost per static stream")
        self.ram_buffer_per_user = ram_buffer_per_user.set_label(f"{self.name} RAM buffer size per user")


class VideoStreamingJob(ServiceJob):
    @classmethod
    def default_values(cls):
        return {
            "resolution": SourceObject("1080p (1920 x 1080)"),
            "video_duration": SourceValue(1 * u.hour),
            "refresh_rate": SourceValue(30 * u.dimensionless / u.s),
            "data_stored": SourceValue(0 * u.MB),
        }

    @classmethod
    def list_values(cls):
        return {"resolution": [
            SourceObject("480p (640 x 480)"), SourceObject("720p (1280 x 720)"), SourceObject("1080p (1920 x 1080)"),
            SourceObject("1440p (2560 x 1440)"), SourceObject("2K (2048 x 1080)"),
            SourceObject("4K (3840 x 2160)"), SourceObject("8K (7680 x 4320)")]
        }

    def __init__(self, name: str, service: VideoStreaming, resolution: ExplainableObject,
                 video_duration: ExplainableQuantity, refresh_rate: ExplainableQuantity,
                 data_stored: ExplainableQuantity):
        super().__init__(name or f"{resolution} streaming on {service.name}",
                         service, SourceValue(0 * u.kB), data_stored,
                         SourceValue(0 * u.s), SourceValue(0 * u.cpu_core), SourceValue(0 * u.GB))
        self.video_duration = video_duration.set_label(f"{self.name} video duration")
        self.resolution = resolution.set_label(f"{self.name} resolution")
        self.refresh_rate = refresh_rate.set_label(f"{self.name} frames per second")
        self.dynamic_bitrate = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return (["request_duration", "dynamic_bitrate", "data_transferred", "compute_needed", "ram_needed"]
                + super().calculated_attributes)

    def update_request_duration(self):
        self.request_duration = self.video_duration.copy().set_label(f"{self.name} request duration")

    def update_dynamic_bitrate(self):
        match = re.search(r"\((\d+)\s*x\s*(\d+)\)", self.resolution.value)
        if not match:
            raise ValueError(f"Invalid resolution format: {self.resolution.value}")
        width, height = map(int, match.groups())
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless, f"pixel count for resolution {self.resolution}",
            left_parent=self.resolution, operator="pixel count computation", source=Sources.USER_DATA)

        self.dynamic_bitrate = (pixel_count * self.service.bits_per_pixel * self.refresh_rate
                                ).to(u.MB / u.s).set_label(f"{self.name} dynamic bitrate")

    def update_data_transferred(self):
        self.data_transferred = (self.request_duration * self.dynamic_bitrate).to(u.GB).set_label(
            f"{self.name} data transferred")

    def update_compute_needed(self):
        self.compute_needed = (self.service.static_delivery_cpu_cost * self.dynamic_bitrate).to(u.cpu_core).set_label(
            f"{self.name} CPU needed")

    def update_ram_needed(self):
        self.ram_needed = self.service.ram_buffer_per_user.copy().set_label(f"{self.name} RAM needed")
