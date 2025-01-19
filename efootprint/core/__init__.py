from efootprint.core.system import System
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.hardware_base_classes import Hardware
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.job import Job
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.hardware.network import Network
from efootprint.core.country import Country


CORE_CLASSES = [System, Storage, Server, Hardware, UsagePattern, UserJourney, Job,
                UserJourneyStep, Network, Country]