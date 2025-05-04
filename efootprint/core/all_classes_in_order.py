from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.hardware.device import Device
from efootprint.core.country import Country
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.usage.job import Job, JobBase, GPUJob
from efootprint.core.hardware.network import Network
from efootprint.core.system import System


SERVICE_CLASSES = [WebApplication, VideoStreaming, GenAIModel]
SERVICE_JOB_CLASSES = [WebApplicationJob, VideoStreamingJob, GenAIJob]
SERVER_CLASSES = [Server, GPUServer]
SERVER_BUILDER_CLASSES = [BoaviztaCloudServer]


ALL_EFOOTPRINT_CLASSES = (
        [UsageJourneyStep, UsageJourney, Device, Country, UsagePattern] + SERVICE_CLASSES + SERVER_BUILDER_CLASSES
        + [Job, GPUJob] + SERVICE_JOB_CLASSES + [Network] + SERVER_CLASSES + [Storage, System])

CANONICAL_COMPUTATION_ORDER = [UsageJourneyStep, UsageJourney, Device, Country, UsagePattern, Service, JobBase,
                               Network, ServerBase, Storage, System]
