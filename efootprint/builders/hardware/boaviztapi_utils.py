import requests

from efootprint.logger import logger


def call_boaviztapi(url, method="GET", **kwargs):
    logger.info(f"Calling Boavizta API with url {url}, method {method} and params {kwargs}")
    headers = {'accept': 'application/json'}
    response = None
    if method == "GET":
        response = requests.get(url, headers=headers, **kwargs)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=headers, **kwargs)

    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(
            f"{method} request to {url} with params {kwargs} failed with status code {response.status_code}")


def get_archetypes_and_their_configs_and_impacts():
    output_dict = {}
    for archetype in call_boaviztapi('https://api.boavizta.org/v1/server/archetypes'):
        configuration = call_boaviztapi(
            url="https://api.boavizta.org/v1/server/archetype_config", params={"archetype": archetype})
        impact = call_boaviztapi(
            url="https://api.boavizta.org/v1/server/", params={"archetype": archetype})
        if impact is None:
            logger.info(f"No impact for archetype {archetype}")
        else:
            output_dict[archetype] = {}
            output_dict[archetype]["config"] = configuration
            output_dict[archetype]["impact"] = impact

    return output_dict


def print_archetypes_and_their_configs():
    archetypes_data = get_archetypes_and_their_configs_and_impacts()

    for archetype in archetypes_data.keys():
        config = archetypes_data[archetype]["config"]
        impact = archetypes_data[archetype]["impact"]
        if "default" in config['CPU']['core_units'].keys():
            nb_cpu_core_units = config['CPU']['core_units']['default']
        else:
            nb_cpu_core_units = impact["verbose"]['CPU-1']['core_units']['value']

        nb_ssd_units = config['SSD']["units"]['default']
        nb_hdd_units = config['HDD']["units"]['default']

        if nb_hdd_units > 0 and nb_ssd_units > 0:
            raise ValueError(
                f"Archetype {archetype} has both SSD and HDD, please check and delete this exception raising if ok")
        storage_type = "SSD"
        if nb_hdd_units > 0:
            storage_type = "HDD"
        nb_storage_units = config[storage_type]["units"]['default']

        print(
            f"{archetype}: type {config['CASE']['case_type']['default']},\n"
            f"    {config['CPU']['units']['default']} cpu units with {nb_cpu_core_units} core units,\n"
            f"    {config['RAM']['units']['default']} RAM units with {config['RAM']['capacity']['default']} GB capacity,\n"
            f"    {nb_storage_units} {storage_type} units with {config[storage_type]['capacity']['default']} GB capacity,")

        total_gwp_embedded_value = impact["impacts"]["gwp"]["embedded"]["value"]
        total_gwp_embedded_unit = impact["impacts"]["gwp"]["unit"]

        if nb_storage_units > 0:
            storage_gwp_embedded_value = impact["verbose"][f"{storage_type}-1"]["impacts"]["gwp"]["embedded"]["value"]
            storage_gwp_embedded_unit = impact["verbose"][f"{storage_type}-1"]["impacts"]["gwp"]["unit"]

            assert total_gwp_embedded_unit == storage_gwp_embedded_unit
        else:
            storage_gwp_embedded_value = 0
            storage_gwp_embedded_unit = "kg"

        average_power_value = impact["verbose"]["avg_power"]["value"]
        average_power_unit = impact["verbose"]["avg_power"]["unit"]

        print(
            f"    Impact fabrication compute: {total_gwp_embedded_value - storage_gwp_embedded_value} {total_gwp_embedded_unit},\n"
            f"    Impact fabrication storage: {storage_gwp_embedded_value} {storage_gwp_embedded_unit},\n"
            f"    Average power: {round(average_power_value, 1)} {average_power_unit}\n")


if __name__ == "__main__":
    print_archetypes_and_their_configs()
