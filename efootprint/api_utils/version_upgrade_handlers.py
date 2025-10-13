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
        logger.info(f"Upgrading system dict from version 11 to 12, changing 'edge_device' attribute to 'edge_computer'")
        for usage_journey_key in system_dict["EdgeUsageJourney"]:
            if "edge_device" in system_dict["EdgeUsageJourney"][usage_journey_key]:
                rename_dict_key(system_dict["EdgeUsageJourney"][usage_journey_key], "edge_device", "edge_computer")

    return system_dict


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10,
    10: upgrade_version_10_to_11,
    11: upgrade_version_11_to_12,
}
