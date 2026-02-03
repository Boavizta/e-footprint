from copy import deepcopy

from efootprint.api_utils.suppressed_efootprint_classes import ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT
from efootprint.logger import logger


def rename_dict_key(d, old_key, new_key):
    if old_key not in d:
        raise KeyError(f"{old_key} not found in dictionary")
    if new_key in d:
        raise KeyError(f"{new_key} already exists in dictionary")

    keys = list(d.keys())
    index = keys.index(old_key)
    value = d[old_key]

    # Remove old key
    del d[old_key]

    # Rebuild the dict by inserting the new key at the same position
    d_items = list(d.items())
    d_items.insert(index, (new_key, value))

    d.clear()
    d.update(d_items)


def upgrade_version_9_to_10(system_dict, efootprint_classes_dict=None):
    object_keys_to_delete = ["year", "job_type", "description"]
    for class_key in system_dict:
        if class_key == "efootprint_version":
            continue
        for efootprint_obj_key in system_dict[class_key]:
            for object_key_to_delete in object_keys_to_delete:
                if object_key_to_delete in system_dict[class_key][efootprint_obj_key]:
                    del system_dict[class_key][efootprint_obj_key][object_key_to_delete]
    if "Hardware" in system_dict:
        logger.info(f"Upgrading system dict from version 9 to 10, changing 'Hardware' key to 'Device'")
        system_dict["Device"] = system_dict.pop("Hardware")

    return system_dict


def upgrade_version_10_to_11(system_dict, efootprint_classes_dict=None):
    for system_key in system_dict["System"]:
        system_dict["System"][system_key]["edge_usage_patterns"] = []

    for server_type in ["Server", "GPUServer", "BoaviztaCloudServer"]:
        if server_type not in system_dict:
            continue
        for server_key in system_dict[server_type]:
            rename_dict_key(system_dict[server_type][server_key], "server_utilization_rate", "utilization_rate")

    return system_dict


def upgrade_version_11_to_12(system_dict, efootprint_classes_dict=None):
    if "EdgeDevice" in system_dict:
        system_dict["EdgeComputer"] = system_dict.pop("EdgeDevice")

    if "EdgeUsageJourney" in system_dict:
        logger.info(f"Upgrading system dict from version 11 to 12, upgrading EdgeUsageJourney structure "
                    f"and changing 'EdgeDevice' key to 'EdgeComputer'")
        # Create EdgeFunction entries from edge_processes
        if "EdgeFunction" not in system_dict:
            system_dict["EdgeFunction"] = {}

        for edge_usage_journey_id in system_dict["EdgeUsageJourney"]:
            journey = system_dict["EdgeUsageJourney"][edge_usage_journey_id]

            # Get the edge_device (now edge_computer) reference from the journey
            edge_computer_id = journey.get("edge_device")
            del journey["edge_device"]

            # Embed edge_processes into an edge_function
            edge_function_id = f"ef_{edge_usage_journey_id}"
            edge_process_ids = journey.get("edge_processes", [])
            system_dict["EdgeFunction"][edge_function_id] = {
                "name": f"Edge function for edge usage journey {journey["name"]}",
                "id": edge_function_id,
                "recurrent_edge_resource_needs": edge_process_ids
            }

            # Replace edge_processes with edge_functions
            rename_dict_key(journey, "edge_processes", "edge_functions")
            journey["edge_functions"] = [edge_function_id]

            for edge_process_id in edge_process_ids:
                # Add edge_computer reference to RecurrentEdgeProcess
                system_dict["RecurrentEdgeProcess"][edge_process_id]["edge_device"] = edge_computer_id

    return system_dict


def upgrade_version_12_to_13(system_dict, efootprint_classes_dict=None):
    """
    Upgrade from version 12 to 13: Replace dimensionless units with occurrence/concurrent,
    and byte units with byte_ram where appropriate in timeseries data.
    """
    from efootprint.api_utils.unit_mappings import (
        TIMESERIES_UNIT_MIGRATIONS, SCALAR_RAM_ATTRIBUTES_TO_MIGRATE, RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE
    )
    efootprint_classes_with_suppressed_classes = deepcopy(efootprint_classes_dict)
    efootprint_classes_with_suppressed_classes.update(ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT)
    logger.info("Upgrading system dict from version 12 to 13: migrating units in timeseries and RAM data")

    def migrate_timeseries_unit(obj_dict, attr_name, new_unit):
        """Migrate unit in timeseries (ExplainableHourlyQuantities or ExplainableRecurrentQuantities) stored in JSON."""
        if attr_name not in obj_dict:
            return

        attr_value = obj_dict[attr_name]

        # Check if it's a timeseries (has 'compressed_values', 'values', or 'recurring_values')
        if isinstance(attr_value, dict) and ('compressed_values' in attr_value or 'values' in attr_value or 'recurring_values' in attr_value):
            if 'unit' in attr_value and attr_value['unit'] in ['dimensionless', '']:
                old_unit = attr_value['unit']
                attr_value['unit'] = new_unit

        # Handle ExplainableObjectDict (dict of timeseries)
        elif isinstance(attr_value, dict):
            for key, sub_value in attr_value.items():
                if isinstance(sub_value, dict) and ('compressed_values' in sub_value or 'values' in sub_value or 'recurring_values' in sub_value):
                    if 'unit' in sub_value and sub_value['unit'] in ['dimensionless', '']:
                        old_unit = sub_value['unit']
                        sub_value['unit'] = new_unit

    def migrate_ram_timeseries_unit(obj_dict, attr_name):
        """Migrate unit in RAM timeseries (ExplainableHourlyQuantities or ExplainableRecurrentQuantities) by appending _ram."""
        if attr_name not in obj_dict:
            return

        attr_value = obj_dict[attr_name]

        # Check if it's a timeseries (has 'compressed_values', 'values', or 'recurring_values')
        if isinstance(attr_value, dict) and ('compressed_values' in attr_value or 'values' in attr_value or 'recurring_values' in attr_value):
            if 'unit' in attr_value:
                old_unit = attr_value['unit']
                # Only migrate if it's a byte unit (not already _ram)
                if '_ram' not in old_unit and any(byte_prefix in old_unit.lower() for byte_prefix in ['byte', 'b']):
                    # Append _ram to the existing unit to preserve power of ten
                    new_unit = old_unit + '_ram' if old_unit.endswith('byte') else old_unit.replace('B', 'B_ram')
                    attr_value['unit'] = new_unit

    def migrate_scalar_ram_unit(obj_dict, attr_name):
        """Migrate unit in scalar ExplainableQuantity stored in JSON by appending _ram."""
        if attr_name not in obj_dict:
            return

        attr_value = obj_dict[attr_name]

        # Check if it's a scalar ExplainableQuantity (has 'unit' but not timeseries keys)
        if isinstance(attr_value, dict) and 'unit' in attr_value:
            if 'compressed_values' not in attr_value and 'values' not in attr_value and 'recurring_values' not in attr_value:
                old_unit = attr_value['unit']
                # Only migrate if it's a byte unit (not already _ram)
                if '_ram' not in old_unit and any(byte_prefix in old_unit.lower() for byte_prefix in ['byte', 'b']):
                    # Append _ram to the existing unit to preserve power of ten
                    new_unit = old_unit + '_ram' if old_unit.endswith('byte') else old_unit.replace('B', 'B_ram')
                    attr_value['unit'] = new_unit

    # Iterate through all classes and objects
    for class_name in system_dict:
        if class_name == "efootprint_version":
            continue
        efootprint_class = efootprint_classes_with_suppressed_classes[class_name]

        for obj_id in system_dict[class_name]:
            obj_dict = system_dict[class_name][obj_id]

            # Apply timeseries unit migrations (dimensionless -> occurrence/concurrent)
            for (migration_class, attr_name), new_unit in TIMESERIES_UNIT_MIGRATIONS.items():
                if efootprint_class.is_subclass_of(migration_class):
                    migrate_timeseries_unit(obj_dict, attr_name, new_unit)

            # Apply RAM timeseries unit migrations (append _ram)
            for (migration_class, attr_name) in RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE:
                if efootprint_class.is_subclass_of(migration_class):
                    migrate_ram_timeseries_unit(obj_dict, attr_name)

            # Apply scalar RAM unit migrations (append _ram)
            for (migration_class, attr_name) in SCALAR_RAM_ATTRIBUTES_TO_MIGRATE:
                if efootprint_class.is_subclass_of(migration_class):
                    migrate_scalar_ram_unit(obj_dict, attr_name)

    return system_dict


def upgrade_version_13_to_14(system_dict, efootprint_classes_dict=None):
    if "EdgeComputer" in system_dict:
        for edge_computer_id in system_dict["EdgeComputer"]:
            del system_dict["EdgeComputer"][edge_computer_id]["power_usage_effectiveness"]
            del system_dict["EdgeComputer"][edge_computer_id]["utilization_rate"]
            system_dict["EdgeComputer"][edge_computer_id]["structure_carbon_footprint_fabrication"] = \
                system_dict["EdgeComputer"][edge_computer_id]["carbon_footprint_fabrication"]
    if "EdgeFunction" in system_dict:
        logger.info("Upgrading system dict from version 13 to 14: renaming recurrent_edge_resource_needs to "
                    "recurrent_edge_device_needs in EdgeFunctions and updating EdgeComputer attributes")
        for edge_function_id in system_dict["EdgeFunction"]:
            rename_dict_key(system_dict["EdgeFunction"][edge_function_id], "recurrent_edge_resource_needs",
                            "recurrent_edge_device_needs")

    return system_dict


def upgrade_version_14_to_15(system_dict, efootprint_classes_dict=None):
    if "EdgeUsagePattern" in system_dict:
        logger.info("Upgrading system dict from version 14 to 15: adding default wifi network to EdgeUsagePatterns"
                    " and empty recurrent_server_needs to EdgeFunctions")
        default_network_id = "default_wifi_network_for_edge"
        if "Network" not in system_dict:
            system_dict["Network"] = {}
        system_dict["Network"][default_network_id] = {
            "name": "Default wifi network for edge",
            "id": default_network_id,
            "bandwidth_energy_intensity": {
                "value": 0.05, "unit": "kilowatt_hour / gigabyte",
                "label": "bandwith energy intensity of Default wifi network from e-footprint hypothesis",
                "source": {"name": "e-footprint hypothesis", "link": None}
            }
        }
        for edge_usage_pattern_id in system_dict["EdgeUsagePattern"]:
            system_dict["EdgeUsagePattern"][edge_usage_pattern_id]["network"] = default_network_id

    if "EdgeFunction" in system_dict:
        for edge_function_id in system_dict["EdgeFunction"]:
            system_dict["EdgeFunction"][edge_function_id]["recurrent_server_needs"] = []

    return system_dict


def upgrade_version_15_to_16(system_dict, efootprint_classes_dict=None):
    """
    Upgrade from version 15 to 16:
    - WebApplication / WebApplicationJob services are removed:
        * suppress WebApplication services from the JSON
        * convert WebApplicationJobs into classic Jobs with Job.default_values inputs (server inferred from service)
    - GenAIModel / GenAIJob services are removed:
        * convert GenAIModel into EcoLogitsGenAIExternalAPI (keep provider + model_name)
        * convert GenAIJob into EcoLogitsGenAIExternalAPIJob (keep output_token_count, point to external API)
    """
    from efootprint.core.usage.job import Job
    did_upgrade = False

    # WebApplicationJob -> Job (defaults) + remove WebApplication services
    web_app_job_class_key = "WebApplicationJob"
    if web_app_job_class_key in system_dict:
        did_upgrade = True
        system_dict.setdefault("Job", {})
        web_app_services = system_dict.get("WebApplication", {})

        for web_app_job_id, web_app_job_dict in list(system_dict[web_app_job_class_key].items()):
            service_id = web_app_job_dict.get("service")
            server_id = web_app_services[service_id].get("server")
            new_job_id = web_app_job_id
            new_job_dict = {"name": web_app_job_dict.get("name"), "id": new_job_id, "server": server_id,
                            "data_transferred": web_app_job_dict["data_transferred"],
                            "data_stored": web_app_job_dict["data_stored"]}
            for attr_name, default_value in Job.default_values.items():
                if attr_name not in ["data_transferred", "data_stored"]:
                    new_job_dict[attr_name] = default_value.to_json()

            system_dict["Job"][new_job_id] = new_job_dict

        del system_dict[web_app_job_class_key]

    # Suppress WebApplication services from the JSON (they are removed in v16).
    if "WebApplication" in system_dict:
        del system_dict["WebApplication"]

    # GenAIModel -> EcoLogitsGenAIExternalAPI, GenAIJob -> EcoLogitsGenAIExternalAPIJob
    if "GenAIModel" in system_dict:
        did_upgrade = True
        system_dict.setdefault("EcoLogitsGenAIExternalAPI", {})

        for genai_model_id, genai_model_dict in list(system_dict["GenAIModel"].items()):
            new_external_api_id = genai_model_id
            new_external_api_dict = {
                "name": genai_model_dict.get("name"), "id": new_external_api_id,
                "provider": genai_model_dict["provider"], "model_name": genai_model_dict["model_name"]}

            system_dict["EcoLogitsGenAIExternalAPI"][new_external_api_id] = new_external_api_dict

        del system_dict["GenAIModel"]

    if "GenAIJob" in system_dict:
        did_upgrade = True
        system_dict.setdefault("EcoLogitsGenAIExternalAPIJob", {})

        for genai_job_id, genai_job_dict in list(system_dict["GenAIJob"].items()):
            external_api_id = genai_job_dict.get("service")

            new_job_id = genai_job_dict.get("id", genai_job_id)
            new_job_dict = {"name": genai_job_dict.get("name"), "id": new_job_id, "external_api": external_api_id}
            new_job_dict["output_token_count"] = genai_job_dict.get("output_token_count")
            system_dict["EcoLogitsGenAIExternalAPIJob"][new_job_id] = new_job_dict

        del system_dict["GenAIJob"]

    if did_upgrade:
        logger.info("Upgraded system dict from version 15 to 16: migrating WebApplication and GenAI services removal")

    return system_dict


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10,
    10: upgrade_version_10_to_11,
    11: upgrade_version_11_to_12,
    12: upgrade_version_12_to_13,
    13: upgrade_version_13_to_14,
    14: upgrade_version_14_to_15,
    15: upgrade_version_15_to_16,
}
