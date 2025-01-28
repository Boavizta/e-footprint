from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.hardware.hardware import Hardware
from efootprint.core.country import Country
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.usage.job import Job
from efootprint.core.hardware.network import Network
from efootprint.core.system import System


SERVICE_CLASSES = [WebApplication, VideoStreaming, GenAIModel]
SERVICE_JOB_CLASSES = [WebApplicationJob, VideoStreamingJob, GenAIJob]
SERVER_CLASSES = [Server, GPUServer]
SERVER_BUILDER_CLASSES = [BoaviztaCloudServer]


ALL_CLASSES_IN_CANONICAL_COMPUTATION_ORDER = (
        [UsageJourneyStep, UsageJourney, Hardware, Country, UsagePattern] + SERVICE_CLASSES + SERVER_BUILDER_CLASSES
        + [Job] + SERVICE_JOB_CLASSES + [Network] + SERVER_CLASSES + [Storage, System])
