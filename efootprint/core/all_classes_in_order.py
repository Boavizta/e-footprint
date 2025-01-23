from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.hardware.hardware import Hardware
from efootprint.core.country import Country
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.storage import Storage
from efootprint.builders.hardware.gpu_server_builder import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.builders.services.web_application import WebApplication, WebApplicationJob
from efootprint.core.usage.job import Job
from efootprint.core.hardware.network import Network
from efootprint.core.system import System


SERVICES_CLASSES = [WebApplication, VideoStreaming, GenAIModel]
JOB_CLASSES = [Job, WebApplicationJob, VideoStreamingJob, GenAIJob]
SERVER_CLASSES = [Server, GPUServer]


ALL_CLASSES_IN_CANONICAL_COMPUTATION_ORDER = (
        [UserJourneyStep, UserJourney, Hardware, Country, UsagePattern] + SERVICES_CLASSES + JOB_CLASSES + [Network]
        + SERVER_CLASSES + [Storage, System])
