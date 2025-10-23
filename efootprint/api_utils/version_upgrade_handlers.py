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


def upgrade_version_9_to_10(system_dict):
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


def upgrade_version_10_to_11(system_dict):
    for system_key in system_dict["System"]:
        system_dict["System"][system_key]["edge_usage_patterns"] = []

    for server_type in ["Server", "GPUServer", "BoaviztaCloudServer"]:
        if server_type not in system_dict:
            continue
        for server_key in system_dict[server_type]:
            rename_dict_key(system_dict[server_type][server_key], "server_utilization_rate", "utilization_rate")

    return system_dict


def upgrade_version_11_to_12(system_dict):
    if "EdgeDevice" in system_dict:
        logger.info(f"Upgrading system dict from version 11 to 12, changing 'EdgeDevice' key to 'EdgeComputer'")
        system_dict["EdgeComputer"] = system_dict.pop("EdgeDevice")

    if "EdgeUsageJourney" in system_dict:
        logger.info(f"Upgrading system dict from version 11 to 12, upgrading EdgeUsageJourney structure")
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


def upgrade_version_12_to_13(system_dict):
    """
    Upgrade from version 12 to 13: Replace dimensionless units with occurrence/concurrent,
    and byte units with byte_ram where appropriate in timeseries data.
    """
    from efootprint.api_utils.unit_mappings import (
        TIMESERIES_UNIT_MIGRATIONS, SCALAR_RAM_ATTRIBUTES_TO_MIGRATE, RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE
    )
    from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES

    logger.info("Upgrading system dict from version 12 to 13: migrating units in timeseries and RAM data")

    # Build classes dict
    efootprint_classes_dict = {
        modeling_object_class.__name__: modeling_object_class
        for modeling_object_class in ALL_EFOOTPRINT_CLASSES
    }

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
                logger.info(f"  Migrated {attr_name}: {old_unit} → {new_unit}")

        # Handle ExplainableObjectDict (dict of timeseries)
        elif isinstance(attr_value, dict):
            for key, sub_value in attr_value.items():
                if isinstance(sub_value, dict) and ('compressed_values' in sub_value or 'values' in sub_value or 'recurring_values' in sub_value):
                    if 'unit' in sub_value and sub_value['unit'] in ['dimensionless', '']:
                        old_unit = sub_value['unit']
                        sub_value['unit'] = new_unit
                        logger.info(f"  Migrated {attr_name}[{key}]: {old_unit} → {new_unit}")

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
                    logger.info(f"  Migrated {attr_name}: {old_unit} → {new_unit}")

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
                    logger.info(f"  Migrated {attr_name}: {old_unit} → {new_unit}")

    # Iterate through all classes and objects
    for class_name in system_dict:
        if class_name == "efootprint_version":
            continue
        efootprint_class = efootprint_classes_dict[class_name]

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


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10,
    10: upgrade_version_10_to_11,
    11: upgrade_version_11_to_12,
    12: upgrade_version_12_to_13,
}
