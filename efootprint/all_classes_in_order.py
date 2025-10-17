from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.edge_device_base import EdgeDeviceBase
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeed
from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload
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
RECURRENT_EDGE_NEEDS_CLASSES = [RecurrentEdgeProcess, RecurrentEdgeWorkload]


ALL_EFOOTPRINT_CLASSES = (
        [UsageJourneyStep, UsageJourney, Device, Country, UsagePattern]
        + [EdgeUsageJourney, EdgeFunction, EdgeUsagePattern, EdgeAppliance, EdgeComputer, EdgeStorage]
        + SERVICE_CLASSES + SERVER_BUILDER_CLASSES
        + [Job, GPUJob] + RECURRENT_EDGE_NEEDS_CLASSES + SERVICE_JOB_CLASSES + [Network] + SERVER_CLASSES
        + [Storage, System])

CANONICAL_COMPUTATION_ORDER = [
    UsageJourneyStep, UsageJourney, Device, Country, UsagePattern, EdgeUsageJourney, EdgeFunction,
    EdgeUsagePattern, RecurrentEdgeResourceNeed, EdgeDeviceBase, Service, JobBase,
    Network, ServerBase, Storage, System]
