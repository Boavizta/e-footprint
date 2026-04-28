import uuid
from copy import deepcopy

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.suppressed_efootprint_classes import ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT
from efootprint.constants.units import u
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
        system_dict.setdefault("EcoLogitsGenAIExternalAPIServer", {})

        for genai_model_id, genai_model_dict in list(system_dict["GenAIModel"].items()):
            new_external_api_id = genai_model_id
            new_external_api_server_id = f"{new_external_api_id}_server"
            new_external_api_dict = {
                "name": genai_model_dict.get("name"), "id": new_external_api_id,
                "provider": genai_model_dict["provider"], "model_name": genai_model_dict["model_name"],
                "server": new_external_api_server_id}
            new_external_api_server_dict = {
                "name": f"{genai_model_dict.get('name')} server", "id": new_external_api_server_id}

            system_dict["EcoLogitsGenAIExternalAPI"][new_external_api_id] = new_external_api_dict
            system_dict["EcoLogitsGenAIExternalAPIServer"][new_external_api_server_id] = new_external_api_server_dict

        del system_dict["GenAIModel"]

    if "GenAIJob" in system_dict:
        did_upgrade = True
        system_dict.setdefault("EcoLogitsGenAIExternalAPIJob", {})

        for genai_job_id, genai_job_dict in list(system_dict["GenAIJob"].items()):
            external_api_id = genai_job_dict.get("service")

            new_job_id = genai_job_dict.get("id", genai_job_id)
            new_job_dict = {"name": genai_job_dict.get("name"), "id": new_job_id, "external_api": external_api_id}
            new_job_dict["output_token_count"] = genai_job_dict.get("output_token_count")
            new_job_dict["data_transferred"] = SourceValue(0 * u.MB).to_json()
            new_job_dict["data_stored"] = SourceValue(0 * u.MB).to_json()
            new_job_dict["request_duration"] = SourceValue(0 * u.s).to_json()
            new_job_dict["compute_needed"] = SourceValue(0 * u.cpu_core).to_json()
            new_job_dict["ram_needed"] = SourceValue(0 * u.GB_ram).to_json()
            system_dict["EcoLogitsGenAIExternalAPIJob"][new_job_id] = new_job_dict

        del system_dict["GenAIJob"]

    if did_upgrade:
        logger.info("Upgraded system dict from version 15 to 16: migrating WebApplication and GenAI services removal")

    return system_dict


def upgrade_version_16_to_17(system_dict, efootprint_classes_dict=None):
    log_upgrade = False
    for job_class in ["Job", "GPUJob", "VideoStreamingJob"]:
        if job_class in system_dict:
            for job_id in system_dict[job_class]:
                job_dict = system_dict[job_class][job_id]
                if job_dict["data_stored"]["value"] < 0:
                    job_dict["data_stored"]["value"] = 0
        log_upgrade = True
    for storage_key in ["Storage", "EdgeStorage"]:
        if storage_key in system_dict:
            for storage_id in system_dict[storage_key]:
                storage_dict = system_dict[storage_key][storage_id]
                for key in ["power_per_storage_capacity", "idle_power"]:
                    if key in storage_dict:
                        del storage_dict[key]
            log_upgrade = True
    if "RecurrentEdgeComponentNeed" in system_dict and "EdgeStorage" in system_dict:
        edge_storage_ids = set(system_dict["EdgeStorage"])
        storage_needs_to_move = {
            need_id: need_dict for need_id, need_dict in system_dict["RecurrentEdgeComponentNeed"].items()
            if need_dict.get("edge_component") in edge_storage_ids
        }
        if storage_needs_to_move:
            system_dict.setdefault("RecurrentEdgeStorageNeed", {})
            system_dict["RecurrentEdgeStorageNeed"].update(storage_needs_to_move)
            for need_id in storage_needs_to_move:
                del system_dict["RecurrentEdgeComponentNeed"][need_id]
            log_upgrade = True
    if log_upgrade:
        logger.info("Upgraded system dict from version 16 to 17: removed power_per_storage_capacity and idle_power "
                    "from Storage and EdgeStorage objects, set negative data stored by jobs to 0, and migrated "
                    "RecurrentEdgeComponentNeeds targeting EdgeStorage to RecurrentEdgeStorageNeeds.")
    return system_dict


def _append_stored_to_byte_unit(unit_str):
    """Convert a byte-based unit string to its _stored equivalent."""
    if '_stored' in unit_str or '_ram' in unit_str:
        return unit_str
    if '/' in unit_str:
        parts = unit_str.split('/')
        parts[-1] = _append_stored_to_byte_unit(parts[-1].strip())
        return ' / '.join(parts)
    if unit_str.endswith('byte'):
        return unit_str + '_stored'
    if unit_str.endswith('B'):
        return unit_str + '_stored'
    return unit_str


def upgrade_version_17_to_18(system_dict, efootprint_classes_dict=None):
    """Upgrade from version 17 to 18: migrate storage units from byte to byte_stored."""
    log_upgrade = False
    storage_scalar_attrs = ["base_storage_need", "storage_capacity", "carbon_footprint_fabrication_per_storage_capacity"]
    for storage_class in ["Storage", "EdgeStorage", "BoaviztaStorageFromConfig"]:
        if storage_class in system_dict:
            for obj_id, obj_dict in system_dict[storage_class].items():
                for attr in storage_scalar_attrs:
                    if attr in obj_dict and isinstance(obj_dict[attr], dict) and 'unit' in obj_dict[attr]:
                        old_unit = obj_dict[attr]['unit']
                        new_unit = _append_stored_to_byte_unit(old_unit)
                        if new_unit != old_unit:
                            obj_dict[attr]['unit'] = new_unit
                            log_upgrade = True

    if log_upgrade:
        logger.info("Upgraded system dict from version 17 to 18: migrated storage units from byte to byte_stored")
    return system_dict


def upgrade_version_18_to_19(system_dict, efootprint_classes_dict=None):
    log_upgrade = False
    base_edge_component_renames = {
        "carbon_footprint_fabrication": "carbon_footprint_fabrication_per_unit",
        "power": "power_per_unit",
        "idle_power": "idle_power_per_unit",
    }
    class_specific_renames = {
        "EdgeCPUComponent": {"compute": "compute_per_unit"},
        "EdgeComputerCPUComponent": {"compute": "compute_per_unit"},
        "EdgeRAMComponent": {"ram": "ram_per_unit"},
        "EdgeComputerRAMComponent": {"ram": "ram_per_unit"},
        "EdgeStorage": {"storage_capacity": "storage_capacity_per_unit"},
    }
    edge_component_classes = {
        "EdgeCPUComponent",
        "EdgeComputerCPUComponent",
        "EdgeRAMComponent",
        "EdgeComputerRAMComponent",
        "EdgeWorkloadComponent",
        "EdgeApplianceComponent",
        "EdgeStorage",
    }

    for class_name, objects_dict in system_dict.items():
        if class_name == "efootprint_version" or not isinstance(objects_dict, dict):
            continue

        renames = {}
        if class_name in edge_component_classes:
            renames.update(base_edge_component_renames)
        elif class_name == "EdgeStorage":
            renames.update({"power": "power_per_unit", "idle_power": "idle_power_per_unit"})
        renames.update(class_specific_renames.get(class_name, {}))

        for obj_dict in objects_dict.values():
            for old_attr, new_attr in renames.items():
                if old_attr in obj_dict and new_attr not in obj_dict:
                    rename_dict_key(obj_dict, old_attr, new_attr)
                    log_upgrade = True
            if class_name in edge_component_classes and "nb_of_units" not in obj_dict:
                obj_dict["nb_of_units"] = SourceValue(1 * u.dimensionless).to_json()
                log_upgrade = True

    if log_upgrade:
        logger.info(
            "Upgraded system dict from version 18 to 19: renamed edge component aggregate inputs to "
            "their per-unit counterparts, migrated EdgeStorage storage_capacity to "
            "storage_capacity_per_unit, and backfilled nb_of_units=1 on edge components."
        )
    return system_dict


def _append_suffix_to_byte_tokens(unit_str, suffix):
    """Append `_stored` or `_ram` to every byte/bit token in a (possibly compound) unit string.

    Skips tokens that already carry a `_stored`/`_ram` suffix so the operation is idempotent.
    """
    byte_token_suffixes = ("byte", "B", "bit")

    def _transform_token(token):
        stripped = token.strip()
        if "_stored" in stripped or "_ram" in stripped:
            return token
        for byte_suffix in byte_token_suffixes:
            if stripped.endswith(byte_suffix) and stripped != "gpu":
                return token.replace(stripped, stripped + f"_{suffix}")
        return token

    parts = unit_str.split("/")
    return "/".join(_transform_token(p) for p in parts)


def upgrade_version_19_to_20(system_dict, efootprint_classes_dict=None):
    """Append `_stored` / `_ram` to byte-unit attributes that weren't covered by earlier migrations.

    Motivated by the v20 dimensional split: `[information]`, `[information_ram]`, `[information_stored]`
    are now distinct dimensions, so `kWh/GB` for network bandwidth no longer simplifies away. Attributes
    that represent stored data or RAM must carry the matching semantic unit.
    """
    efootprint_classes_with_suppressed = deepcopy(efootprint_classes_dict) if efootprint_classes_dict else {}
    efootprint_classes_with_suppressed.update(ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT)

    scalar_stored_attrs = {
        ("JobBase", "data_stored"),
        ("Storage", "power_per_storage_capacity"),
        ("Storage", "storage_capacity"),
        ("Storage", "base_storage_need"),
        ("EdgeStorage", "power_per_storage_capacity"),
        ("BoaviztaStorageFromConfig", "power_per_storage_capacity"),
    }
    per_bit_attrs = {
        ("Network", "bandwidth_energy_intensity"),
    }
    per_stored_bit_attrs = {
        ("Storage", "carbon_footprint_fabrication_per_storage_capacity"),
    }
    timeseries_stored_attrs = {
        ("RecurrentEdgeProcess", "recurrent_storage_needed"),
    }
    scalar_ram_attrs = {
        ("ServerBase", "ram"),
        ("ServerBase", "base_ram_consumption"),
        ("GPUServer", "ram_per_gpu"),
        ("EdgeComputer", "ram"),
        ("EdgeComputer", "base_ram_consumption"),
        ("JobBase", "ram_needed"),
        ("Service", "base_ram_consumption"),
        ("Service", "ram_buffer_per_user"),
    }
    # Scalar attributes that used to carry a dimensionless value but semantically represent bits.
    # With bit now a distinct dimension, these must be upgraded so downstream `.to(MB/s)` conversions work.
    dimensionless_to_bit_attrs = {
        ("VideoStreaming", "bits_per_pixel"),
    }

    def _migrate_attr(obj_dict, attr_name, suffix):
        if attr_name not in obj_dict:
            return False
        attr_value = obj_dict[attr_name]
        if not (isinstance(attr_value, dict) and isinstance(attr_value.get("unit"), str)):
            return False
        old_unit = attr_value["unit"]
        new_unit = _append_suffix_to_byte_tokens(old_unit, suffix)
        if new_unit == old_unit:
            return False
        attr_value["unit"] = new_unit
        return True

    def _migrate_dimensionless_to_bit(obj_dict, attr_name):
        if attr_name not in obj_dict:
            return False
        attr_value = obj_dict[attr_name]
        if not (isinstance(attr_value, dict) and isinstance(attr_value.get("unit"), str)):
            return False
        if attr_value["unit"] != "dimensionless":
            return False
        attr_value["unit"] = "bit"
        return True

    def _strip_byte_suffix_from_denominator(unit_str):
        """Remove `_stored` / `_ram` suffix from byte/bit tokens so they fall back to the plain information dim."""
        parts = unit_str.split("/")
        def _transform(token):
            stripped = token.strip()
            for tag in ("_stored", "_ram"):
                if stripped.endswith(tag):
                    base = stripped[: -len(tag)]
                    return token.replace(stripped, base)
            return token
        return "/".join(_transform(p) for p in parts)

    def _migrate_per_info_attr(obj_dict, attr_name, target_suffix, default_denominator):
        """Normalize per-information denominators.

        `target_suffix` is "" for plain information, "stored" for information_stored.
        Happy path: if the unit has a `/` denominator, coerce the byte/bit token to the right dimension.
        Edge case: if the denominator was dropped (pint simplification on a zero value), reattach
        `default_denominator` so dimensional analysis still works downstream.
        """
        if attr_name not in obj_dict:
            return False
        attr_value = obj_dict[attr_name]
        if not (isinstance(attr_value, dict) and isinstance(attr_value.get("unit"), str)):
            return False
        old_unit = attr_value["unit"]
        if "/" in old_unit:
            if target_suffix:
                new_unit = _append_suffix_to_byte_tokens(old_unit, target_suffix)
            else:
                new_unit = _strip_byte_suffix_from_denominator(old_unit)
        elif attr_value.get("value") == 0:
            new_unit = f"{old_unit} / {default_denominator}"
        else:
            return False
        if new_unit == old_unit:
            return False
        attr_value["unit"] = new_unit
        return True

    edge_component_id_to_class = {}
    for class_name, objects_dict in system_dict.items():
        if class_name == "efootprint_version" or not isinstance(objects_dict, dict):
            continue
        efootprint_class = efootprint_classes_with_suppressed.get(class_name)
        if efootprint_class is None or not efootprint_class.is_subclass_of("EdgeComponent"):
            continue
        for obj_id in objects_dict:
            edge_component_id_to_class[obj_id] = efootprint_class

    log_upgrade = False
    for class_name, objects_dict in system_dict.items():
        if class_name == "efootprint_version" or not isinstance(objects_dict, dict):
            continue
        efootprint_class = efootprint_classes_with_suppressed.get(class_name)
        if efootprint_class is None:
            continue
        matching_stored_scalars = {
            attr for (migration_class, attr) in scalar_stored_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        matching_stored_ts = {
            attr for (migration_class, attr) in timeseries_stored_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        matching_ram_scalars = {
            attr for (migration_class, attr) in scalar_ram_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        matching_dimensionless_to_bit = {
            attr for (migration_class, attr) in dimensionless_to_bit_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        matching_per_bit = {
            attr for (migration_class, attr) in per_bit_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        matching_per_stored_bit = {
            attr for (migration_class, attr) in per_stored_bit_attrs
            if efootprint_class.is_subclass_of(migration_class)
        }
        is_recurrent_edge_component_need = efootprint_class.is_subclass_of("RecurrentEdgeComponentNeed")
        for obj_dict in objects_dict.values():
            for attr in matching_stored_scalars | matching_stored_ts:
                log_upgrade |= _migrate_attr(obj_dict, attr, "stored")
            for attr in matching_ram_scalars:
                log_upgrade |= _migrate_attr(obj_dict, attr, "ram")
            for attr in matching_dimensionless_to_bit:
                log_upgrade |= _migrate_dimensionless_to_bit(obj_dict, attr)
            for attr in matching_per_bit:
                log_upgrade |= _migrate_per_info_attr(obj_dict, attr, "", "gigabyte")
            for attr in matching_per_stored_bit:
                log_upgrade |= _migrate_per_info_attr(obj_dict, attr, "stored", "gigabyte_stored")
            if is_recurrent_edge_component_need:
                component_class = edge_component_id_to_class.get(obj_dict.get("edge_component"))
                if component_class is not None:
                    if component_class.is_subclass_of("EdgeRAMComponent"):
                        log_upgrade |= _migrate_attr(obj_dict, "recurrent_need", "ram")
                    elif component_class.is_subclass_of("EdgeStorage"):
                        log_upgrade |= _migrate_attr(obj_dict, "recurrent_need", "stored")

    if log_upgrade:
        logger.info("Upgraded system dict from version 19 to 20: appended `_stored`/`_ram` to byte-unit "
                    "attributes (data_stored, power_per_storage_capacity, recurrent_storage_needed, ram_per_gpu, "
                    "and RecurrentEdgeComponentNeed.recurrent_need based on the target component).")
    return system_dict


def upgrade_version_20_to_21(system_dict, efootprint_classes_dict=None):
    """Hoist inline ExplainableObject sources to a top-level "Sources" block keyed by id-ref.

    v20: every ExplainableObject payload carries `"source": {"name": ..., "link": ...}` inline.
    v21: payloads carry `"source": "<source_id>"`; the top-level `"Sources"` block holds
    `{source_id: {"id": ..., "name": ..., "link": ...}}`. Two sentinel ids — `"user_data"` and
    `"hypothesis"` — are reserved so the canonical `Sources.USER_DATA` / `Sources.HYPOTHESIS`
    re-identify with the live Python singletons across reloads.
    """
    sentinel_id_for_key = {
        ("user data", None): "user_data",
        ("e-footprint hypothesis", None): "hypothesis",
    }
    sources_block = {}
    sources_id_by_key = {}

    def _normalise_link(link):
        return link if link else None

    def _ensure_source_id(name, link):
        link = _normalise_link(link)
        key = (name, link)
        if key in sentinel_id_for_key:
            source_id = sentinel_id_for_key[key]
        elif key in sources_id_by_key:
            return sources_id_by_key[key]
        else:
            source_id = str(uuid.uuid4())[:6]
        sources_id_by_key[key] = source_id
        sources_block[source_id] = {"id": source_id, "name": name, "link": link}
        return source_id

    def _walk(node):
        if isinstance(node, dict):
            source_field = node.get("source")
            if isinstance(source_field, dict) and "name" in source_field:
                node["source"] = _ensure_source_id(source_field["name"], source_field.get("link"))
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    for class_key, class_dict in system_dict.items():
        if class_key in ("efootprint_version", "Sources") or not isinstance(class_dict, dict):
            continue
        _walk(class_dict)

    if sources_block:
        system_dict["Sources"] = sources_block
        # Re-order so Sources sits right after efootprint_version.
        ordered = {"efootprint_version": system_dict["efootprint_version"], "Sources": sources_block}
        for k, v in system_dict.items():
            if k in ordered:
                continue
            ordered[k] = v
        system_dict.clear()
        system_dict.update(ordered)
        logger.info(
            "Upgraded system dict from version 20 to 21: hoisted inline ExplainableObject sources to a "
            "top-level 'Sources' block keyed by id-ref.")

    return system_dict


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10,
    10: upgrade_version_10_to_11,
    11: upgrade_version_11_to_12,
    12: upgrade_version_12_to_13,
    13: upgrade_version_13_to_14,
    14: upgrade_version_14_to_15,
    15: upgrade_version_15_to_16,
    16: upgrade_version_16_to_17,
    17: upgrade_version_17_to_18,
    18: upgrade_version_18_to_19,
    19: upgrade_version_19_to_20,
    20: upgrade_version_20_to_21,
}
