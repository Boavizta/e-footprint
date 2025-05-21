from efootprint.logger import logger


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


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10
}
