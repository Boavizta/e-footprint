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
    """A video-streaming service installed on a {class:Server}. Provides the per-stream cost model that converts {class:VideoStreamingJob}s (defined by resolution and duration) into bandwidth, CPU, and RAM demand on the server."""

    interactions = (
        "Build {class:VideoStreaming} once per service tier, then attach {class:VideoStreamingJob}s for each "
        "specific resolution / duration combination. The server hosting the service is the one that bills for "
        "the streams.")

    param_descriptions = {
        "server": (
            "{class:Server} on which the streaming service is installed. Streams consume the server's CPU "
            "and RAM."),
        "base_ram_consumption": (
            "RAM occupied per server by the operating system and streaming software, independent of users."),
        "bits_per_pixel": (
            "Average compression density. Multiplied by pixel count and refresh rate to estimate the dynamic "
            "bitrate of one stream."),
        "static_delivery_cpu_cost": (
            "CPU per unit of bitrate served (cores per GB/s). Multiplied by the dynamic bitrate to estimate "
            "the CPU consumed by one concurrent stream."),
        "ram_buffer_per_user": (
            "RAM held by the streaming server for each concurrent user (read-ahead buffers, sockets)."),
    }

    default_values =  {
            "base_ram_consumption": SourceValue(2 * u.GB_ram, source=Sources.HYPOTHESIS),
            "bits_per_pixel": SourceValue(0.1 * u.bit, source=Sources.HYPOTHESIS),
            "static_delivery_cpu_cost": SourceValue(4 * u.cpu_core / (u.GB / u.s), source=Sources.HYPOTHESIS),
            "ram_buffer_per_user": SourceValue(50 * u.MB_ram, source=Sources.HYPOTHESIS),
            }

    def __init__(self, name: str, server: Server, base_ram_consumption: ExplainableQuantity,
                 bits_per_pixel: ExplainableQuantity, static_delivery_cpu_cost: ExplainableQuantity,
                 ram_buffer_per_user: ExplainableQuantity):
        super().__init__(name, server, base_ram_consumption=base_ram_consumption.set_label(
            "OS and streaming software base RAM consumption"))
        self.bits_per_pixel = bits_per_pixel.set_label("Bits per pixel")
        self.static_delivery_cpu_cost = static_delivery_cpu_cost.set_label("CPU cost per static stream")
        self.ram_buffer_per_user = ram_buffer_per_user.set_label("RAM buffer size per user")


class VideoStreamingJob(ServiceJob):
    """One streaming session of a given resolution and duration consumed against a {class:VideoStreaming} service. Bandwidth, CPU, and RAM are derived from the resolution, refresh rate, and the service-level cost coefficients."""

    param_descriptions = {
        "service": (
            "{class:VideoStreaming} service that hosts the stream."),
        "resolution": (
            "Display resolution as a label like \"1080p (1920 x 1080)\". The pixel count is parsed from the "
            "label and used to estimate the dynamic bitrate."),
        "video_duration": (
            "Duration of one streaming session, used as the request duration."),
        "refresh_rate": (
            "Frames-per-second rate of the stream. Higher refresh rates increase the bitrate proportionally."),
        "data_stored": (
            "Net change in stored data per session. Usually 0 for streamed video."),
    }

    default_values =  {
            "resolution": SourceObject("1080p (1920 x 1080)"),
            "video_duration": SourceValue(1 * u.hour),
            "refresh_rate": SourceValue(30 * u.dimensionless / u.s),
            "data_stored": SourceValue(0 * u.MB_stored),
        }

    list_values =  {"resolution": [
            SourceObject("480p (640 x 480)"), SourceObject("720p (1280 x 720)"), SourceObject("1080p (1920 x 1080)"),
            SourceObject("1440p (2560 x 1440)"), SourceObject("2K (2048 x 1080)"),
            SourceObject("4K (3840 x 2160)"), SourceObject("8K (7680 x 4320)")]
        }

    def __init__(self, name: str, service: VideoStreaming, resolution: ExplainableObject,
                 video_duration: ExplainableQuantity, refresh_rate: ExplainableQuantity,
                 data_stored: ExplainableQuantity):
        super().__init__(name or f"{resolution} streaming on {service.name}",
                         service, SourceValue(0 * u.kB), data_stored,
                         SourceValue(0 * u.s), SourceValue(0 * u.cpu_core), SourceValue(0 * u.GB_ram))
        self.video_duration = video_duration.set_label("Video duration")
        self.resolution = resolution.set_label("Resolution")
        self.refresh_rate = refresh_rate.set_label("Frames per second")
        self.dynamic_bitrate = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return (["request_duration", "dynamic_bitrate", "data_transferred", "compute_needed", "ram_needed"]
                + super().calculated_attributes)

    def update_request_duration(self):
        """Request duration of one streaming session, equal to the chosen video duration."""
        self.request_duration = self.video_duration.copy().set_label("Request duration")

    def update_dynamic_bitrate(self):
        """Estimated bitrate of the stream, equal to the pixel count parsed from the resolution times bits-per-pixel times refresh rate."""
        match = re.search(r"\((\d+)\s*x\s*(\d+)\)", self.resolution.value)
        if not match:
            raise ValueError(f"Invalid resolution format: {self.resolution.value}")
        width, height = map(int, match.groups())
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless, f"pixel count for resolution {self.resolution}",
            left_parent=self.resolution, operator="pixel count computation", source=Sources.USER_DATA)

        self.dynamic_bitrate = (pixel_count * self.service.bits_per_pixel * self.refresh_rate
                                ).to(u.MB / u.s).set_label("Dynamic bitrate")

    def update_data_transferred(self):
        """Data transferred per session, equal to the dynamic bitrate times the video duration."""
        self.data_transferred = (self.request_duration * self.dynamic_bitrate).to(u.GB).set_label(
            "Data transferred")

    def update_compute_needed(self):
        """CPU consumed per session, equal to the service's per-bitrate CPU cost times the dynamic bitrate."""
        self.compute_needed = (self.service.static_delivery_cpu_cost * self.dynamic_bitrate).to(u.cpu_core).set_label(
            "CPU needed")

    def update_ram_needed(self):
        """RAM consumed per session, equal to the service's per-user RAM buffer."""
        self.ram_needed = self.service.ram_buffer_per_user.copy().set_label("RAM needed")
