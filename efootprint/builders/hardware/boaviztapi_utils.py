import requests
import os

from efootprint.logger import logger


def call_boaviztapi_from_web_request(url, method="GET", params={}):
    logger.info(f"Calling Boavizta API with url {url}, method {method} and params {params}")
    headers = {'accept': 'application/json'}
    response = None
    if method == "GET":
        response = requests.get(url, headers=headers, params=params)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(
            f"{method} request to {url} with params {params} failed with status code {response.status_code}")


def call_boaviztapi_from_package_dependency(url, method="GET", params={}):
    import asyncio
    import inspect
    import warnings
    from scipy.optimize import OptimizeWarning

    warnings.simplefilter("ignore", ResourceWarning)
    warnings.simplefilter("ignore", OptimizeWarning)
    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.simplefilter("ignore", UserWarning)

    from boaviztapi.routers.cloud_router import instance_cloud_impact, server_get_all_provider_name, \
        server_get_all_archetype_name as server_get_all_archetype_name_cloud
    from boaviztapi.routers.server_router import (
        server_impact_from_model, server_get_all_archetype_name as server_get_all_archetype_name_server,
        get_archetype_config)

    url_method_mapping = {
        "https://api.boavizta.org/v1/cloud/instance/all_providers": server_get_all_provider_name,
        "https://api.boavizta.org/v1/cloud/instance/all_instances": server_get_all_archetype_name_cloud,
        "https://api.boavizta.org/v1/cloud/instance": instance_cloud_impact,
        "https://api.boavizta.org/v1/server/": server_impact_from_model,
        "https://api.boavizta.org/v1/server/archetypes": server_get_all_archetype_name_server,
        "https://api.boavizta.org/v1/server/archetype_config": get_archetype_config,
    }

    if url in url_method_mapping:
        method = url_method_mapping[url]
        if "criteria" in inspect.signature(method).parameters:
            params["criteria"] = params.get("criteria", ["gwp"])
        return asyncio.run(method(**params))
    else:
        raise ValueError(
            f"URL {url} is not in the list of available urls: {list(url_method_mapping.keys())}. Please provide a valid "
            f"URL, update the list of urls in call_boaviztapi_from_package_dependency or set environment variable "
            f"CALL_BOAVIZTAPI_VIA_WEB to True to use the web API.")


if not os.environ.get("CALL_BOAVIZTAPI_VIA_WEB"):
    call_boaviztapi = call_boaviztapi_from_package_dependency
else:
    call_boaviztapi = call_boaviztapi_from_web_request


def print_archetypes_and_their_configs():
    for archetype in call_boaviztapi('https://api.boavizta.org/v1/server/archetypes'):
        config = call_boaviztapi(
            url="https://api.boavizta.org/v1/server/archetype_config", params={"archetype": archetype})
        impact = call_boaviztapi(
            url="https://api.boavizta.org/v1/server/", params={"archetype": archetype})

        if "default" in config['CPU']['core_units']:
            nb_cpu_core_units = config['CPU']['core_units']['default']
        elif "core_units" in impact["verbose"]['CPU-1']:
            nb_cpu_core_units = impact["verbose"]['CPU-1']['core_units']['value']
        else:
            nb_cpu_core_units = 1

        nb_ssd_units = config['SSD']["units"].get('default', 0)
        nb_hdd_units = config['HDD']["units"].get('default', 0)

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
    from time import time
    start = time()
    print_archetypes_and_their_configs()
    print(f"Execution time: {time() - start} seconds")
