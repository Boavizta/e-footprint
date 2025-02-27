from efootprint.logger import logger


def upgrade_version_9_to_10(system_dict):
    if "Hardware" in system_dict.keys():
        logger.info(f"Upgrading system dict from version 9 to 10, changing 'Hardware' key to 'Device'")
        system_dict["Device"] = system_dict.pop("Hardware")

    return system_dict


VERSION_UPGRADE_HANDLERS = {
    9: upgrade_version_9_to_10
}
