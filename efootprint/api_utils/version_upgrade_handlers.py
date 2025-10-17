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


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10,
    10: upgrade_version_10_to_11,
    11: upgrade_version_11_to_12,
}
