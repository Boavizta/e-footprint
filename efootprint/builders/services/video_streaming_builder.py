from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.constants.units import u
from efootprint.core.usage.job import Job

BITS_PER_PIXEL = ExplainableQuantity(
    24 * u.dimensionless, "bits per pixel (standard for video compression)", source=Sources.HYPOTHESIS)
FRAMES_PER_SECOND = ExplainableQuantity(
    30 * u.dimensionless, "frames per second for video playback", source=Sources.HYPOTHESIS)
BUFFER_SIZE_PER_USER = ExplainableQuantity(
    50 * u.MB, "buffer size per user", source=Sources.HYPOTHESIS)
STATIC_DELIVERY_CPU_COST = ExplainableQuantity(4 * u.core / (u.GB / u.s), "CPU cost per static stream",
                                               source=Sources.HYPOTHESIS)
OS_AND_STREAMING_SOFTWARE_BASE_RAM = ExplainableQuantity(
    2 * u.GB, "OS and streaming software base RAM consumption", source=Sources.HYPOTHESIS)


class VideoStreaming:
    def __init__(self, server, install_on_server=True):
        self.server = server

        if install_on_server:
            # Update server's base RAM consumption
            self.server.base_ram_consumption = (
                    self.server.base_ram_consumption + OS_AND_STREAMING_SOFTWARE_BASE_RAM
            ).set_label(f"{self.server.name} base RAM after video streaming service installation")

    def job(self, resolution: str, video_watch_duration: SourceValue):
        """
        Create a Job object for a streaming request based on the duration of the video watched.
        The bitrate is dynamically computed based on the resolution.

        Args:
            resolution (str): Resolution of the video stream (e.g., "1920x1080").
            video_watch_duration (SourceValue): Duration of the video watched in seconds.

        Returns:
            Job: An object that represents the resources needed for the streaming job.
        """
        # Dynamically calculate the bitrate based on resolution
        width, height = map(int, resolution.split('x'))
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless,f"pixel count for resolution {resolution}", source=Sources.USER_DATA)
        dynamic_bitrate = (pixel_count * BITS_PER_PIXEL * FRAMES_PER_SECOND).to(u.MB / u.s)

        # Assume stream duration equals video watch duration
        stream_duration = video_watch_duration

        # Calculate data transferred based on dynamic bitrate and duration
        data_transfer = stream_duration * dynamic_bitrate
        cpu_needed = STATIC_DELIVERY_CPU_COST * dynamic_bitrate

        return Job(
            f"streaming job for {self.resolution} resolution", self.server,
            data_upload=SourceValue(0 * u.kB),
            data_stored=data_transfer.to(u.GB).set_label("data stored during streaming"),
            data_download=data_transfer.to(u.GB).set_label("data downloaded during streaming"),
            request_duration=stream_duration,
            cpu_needed=cpu_needed.to(u.core),
            ram_needed=BUFFER_SIZE_PER_USER.to(u.GB))
