from time import time
start = time()
from efootprint.logger import logger
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
logger.info(f"Imported BoaviztaCloudServer in {time() - start:.5f} seconds.")
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.hardware.device import Device
from efootprint.core.country import Country
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.gpu_server import GPUServer
logger.info(f"Imported up to Storage and GPUServer in {time() - start:.5f} seconds.")
from efootprint.core.hardware.server import Server
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
logger.info(f"Imported up to Server and GenAIModel in {time() - start:.5f} seconds.")
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.usage.job import Job, JobBase
from efootprint.core.hardware.network import Network
logger.info(f"Imported up to Job, Network in {time() - start:.5f} seconds.")
from efootprint.core.system import System
logger.info(f"Imported all classes in {time() - start:.5f} seconds.")


SERVICE_CLASSES = [WebApplication, VideoStreaming, GenAIModel]
SERVICE_JOB_CLASSES = [WebApplicationJob, VideoStreamingJob, GenAIJob]
SERVER_CLASSES = [Server, GPUServer]
SERVER_BUILDER_CLASSES = [BoaviztaCloudServer]


ALL_EFOOTPRINT_CLASSES = (
        [UsageJourneyStep, UsageJourney, Device, Country, UsagePattern] + SERVICE_CLASSES + SERVER_BUILDER_CLASSES
        + [Job] + SERVICE_JOB_CLASSES + [Network] + SERVER_CLASSES + [Storage, System])

CANONICAL_COMPUTATION_ORDER = [UsageJourneyStep, UsageJourney, Device, Country, UsagePattern, Service, JobBase,
                               Network, ServerBase, Storage, System]
