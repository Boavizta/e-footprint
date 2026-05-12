"""
Système d'illustration pour la tribune Alliancy "Avant le bilan carbone, le business plan environnemental".

Système mixte web + edge + IA volontairement générique (pas un client précis), avec un objet agrégé
par catégorie pour produire un Sankey lisible une fois chargé dans l'interface e-footprint.

Sortie : tribune_alliancy_system.json à côté de ce fichier, à charger dans https://e-footprint.boavizta.org.

Lancer depuis la racine du repo : poetry run python communications/articles/2026-05-tribune-alliancy/system.py
"""
import os
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.time_builders import create_hourly_usage_from_frequency
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

NB_YEARS = 5
START_DATE = datetime(2025, 1, 1)


def generate_tribune_system() -> System:
    # --- Backend cloud (un objet agrégé par catégorie) ----------------------------------------
    db_storage = Storage.ssd("Base de données")
    cloud_server = BoaviztaCloudServer.from_defaults(
        "Serveurs cloud", server_type=ServerTypes.autoscaling(), storage=db_storage,
        base_ram_consumption=SourceValue(2 * u.GB_ram))

    # --- Assistant IA (API externe, modélisée via EcoLogits) ----------------------------------
    genai_api = EcoLogitsGenAIExternalAPI.from_defaults(
        "Assistant IA (API)", provider=SourceObject("openai"), model_name=SourceObject("gpt-4o"))

    # --- Parcours utilisateur web : une visite-type d'un opérateur sur la plateforme ----------
    backend_job = Job.from_defaults(
        "Consultation de la plateforme", server=cloud_server,
        data_transferred=SourceValue(50 * u.MB), data_stored=SourceValue(5000 * u.kB_stored),
        request_duration=SourceValue(100 * u.s), compute_needed=SourceValue(2 * u.cpu_core),
        ram_needed=SourceValue(2500 * u.MB_ram))
    genai_job = EcoLogitsGenAIExternalAPIJob(
        "Résumé d'alertes et analyses IA", genai_api, output_token_count=SourceValue(5000 * u.dimensionless))

    consultation_step = UsageJourneyStep(
        "Consultation des données", user_time_spent=SourceValue(5 * u.min), jobs=[backend_job])
    ai_step = UsageJourneyStep(
        "Discussion des insights", user_time_spent=SourceValue(5 * u.min), jobs=[genai_job])

    user_journey = UsageJourney("Analyses quotidiennes", uj_steps=[consultation_step, ai_step])

    user_devices = Device(
        name="Smartphones et laptops",
        carbon_footprint_fabrication=SourceValue(120 * u.kg),
        power=SourceValue(15 * u.W),
        lifespan=SourceValue(5 * u.year),
        fraction_of_usage_time=SourceValue(4 * u.hour / u.day))

    web_network = Network("Réseau", SourceValue(0.08 * u("kWh/GB")))

    def make_user_pattern(label, country, weekly_visits):
        return UsagePattern(
            label, user_journey, [user_devices], web_network, country,
            create_hourly_usage_from_frequency(
                timespan=NB_YEARS * u.year, input_volume=weekly_visits, frequency="weekly",
                active_days=[0, 1, 2, 3, 4], hours=[8, 9, 10, 11, 14, 15, 16, 17],
                start_date=START_DATE))

    # Une seule instance par pays, réutilisée pour les patterns web et IoT.
    france, united_states, spain = Countries.FRANCE(), Countries.UNITED_STATES(), Countries.SPAIN()
    united_states.name = "États-Unis"
    spain.name = "Espagne"

    user_patterns = [
        make_user_pattern("Opérateurs en France", france, 10000),
        make_user_pattern("Opérateurs aux US", united_states, 10000),
        make_user_pattern("Opérateurs en Italie", spain, 10000),
    ]

    # --- Flotte IoT terrain : 1 objet agrégé représentant le parc ------------------------------
    iot_storage = EdgeStorage(
        "Stockage embarqué",
        carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored),
        lifespan=SourceValue(8 * u.year),
        storage_capacity_per_unit=SourceValue(64 * u.GB_stored),
        base_storage_need=SourceValue(1 * u.GB_stored))

    iot_device = EdgeComputer(
        "Capteurs IoT terrain",
        carbon_footprint_fabrication=SourceValue(45 * u.kg),
        power=SourceValue(14 * u.W),
        lifespan=SourceValue(8 * u.year),
        idle_power=SourceValue(1 * u.W),
        ram=SourceValue(2 * u.GB_ram),
        compute=SourceValue(2 * u.cpu_core),
        base_ram_consumption=SourceValue(0.2 * u.GB_ram),
        base_compute_consumption=SourceValue(0.05 * u.cpu_core),
        storage=iot_storage)

    iot_local_process = RecurrentEdgeProcess.from_defaults(
        "Mesures et calcul local", edge_device=iot_device)

    iot_telemetry_job = Job.from_defaults(
        "Remontée de télémétrie au cloud", server=cloud_server,
        data_transferred=SourceValue(600 * u.kB))
    iot_to_cloud = RecurrentServerNeed.from_defaults(
        "Télémétrie horaire vers le cloud", edge_device=iot_device, jobs=[iot_telemetry_job])

    iot_function = EdgeFunction(
        "Surveillance des équipements",
        recurrent_edge_device_needs=[iot_local_process],
        recurrent_server_needs=[iot_to_cloud])

    iot_journey = EdgeUsageJourney(
        "Usage d'un capteur", edge_functions=[iot_function],
        usage_span=SourceValue(8 * u.year))

    iot_network = Network("Réseau IoT (cellulaire)", SourceValue(0.1 * u("kWh/GB")))

    # Déploiement : 10 000 capteurs mis en service sur 5 ans, répartis entre les trois pays
    def make_iot_pattern(label, country, weekly_deployments):
        return EdgeUsagePattern(
            label, edge_usage_journey=iot_journey, network=iot_network, country=country,
            hourly_edge_usage_journey_starts=create_hourly_usage_from_frequency(
                timespan=NB_YEARS * u.year, input_volume=weekly_deployments, frequency="weekly",
                active_days=[0, 1, 2, 3, 4], hours=[10],
                start_date=START_DATE))

    iot_patterns = [
        make_iot_pattern("Flotte IoT en France", france, 7),
        make_iot_pattern("Flotte IoT aux US", united_states, 7),
        make_iot_pattern("Flotte IoT en Italie", spain, 7),
    ]

    return System(
        "Plateforme B2B de surveillance d'équipements industriels",
        usage_patterns=user_patterns, edge_usage_patterns=iot_patterns)


if __name__ == "__main__":
    system = generate_tribune_system()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tribune_alliancy_system.json")
    system_to_json(system, save_calculated_attributes=False, output_filepath=output_path)
    print(f"Système exporté : {output_path}")
    total_kg = float(system.total_footprint.value.sum().magnitude)
    print(f"Empreinte cumulée sur {NB_YEARS} ans : {total_kg / 1000:.1f} t CO₂eq "
          f"({total_kg / NB_YEARS / 1000:.1f} t/an en moyenne)")
