import requests
from urllib3.exceptions import RequestError

from efootprint.logger import logger
from efootprint.builders.hardware.storage_defaults import default_ssd, default_hdd
from efootprint.constants.sources import Source, Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.servers.autoscaling import Autoscaling
from efootprint.constants.units import u
from efootprint.core.hardware.servers.on_premise import OnPremise
from efootprint.core.hardware.storage import Storage


def call_boaviztapi(url, method="GET", **kwargs):
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
        raise RequestError(
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


def get_cloud_server(
        provider, instance_type, average_carbon_intensity, base_efootprint_class=Autoscaling,
        lifespan=None, idle_power=None, power_usage_effectiveness=None,
        server_utilization_rate=None, base_ram_consumption=None, base_cpu_consumption=None, storage: Storage=None
        ):
    if lifespan is None:
        lifespan = SourceValue(6 * u.year, Sources.HYPOTHESIS)
    if idle_power is None:
        idle_power = SourceValue(0 * u.W, Sources.HYPOTHESIS)
    if power_usage_effectiveness is None:
        power_usage_effectiveness = SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS)
    if server_utilization_rate is None:
        server_utilization_rate = SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS)
    if base_ram_consumption is None:
        base_ram_consumption = SourceValue(0 * u.GB, Sources.HYPOTHESIS)
    if base_cpu_consumption is None:
        base_cpu_consumption = SourceValue(0 * u.core, Sources.HYPOTHESIS)
    if storage is None:
        tmp_default_ssd = default_ssd()
        reference_storage_capacity = tmp_default_ssd.storage_capacity
        cloud_storage_capacity = SourceValue(32 * u.GB, source=Sources.HYPOTHESIS)
        ratio = (cloud_storage_capacity / reference_storage_capacity).to(u.dimensionless).set_label(
            "Ration of cloud server storage capacity to default storage capacity")
        storage = default_ssd(
            carbon_footprint_fabrication=tmp_default_ssd.carbon_footprint_fabrication * ratio,
            power=tmp_default_ssd.power * ratio,
            storage_capacity=cloud_storage_capacity)

    impact_url = "https://api.boavizta.org/v1/cloud/instance"
    params = {"provider": provider, "instance_type": instance_type}
    impact_source = Source(name="Boavizta API cloud instances",
                    link=f"{impact_url}?{'&'.join([key + '=' + params[key] for key in params.keys()])}")
    impact_data = call_boaviztapi(url=impact_url, params=params)
    impacts = impact_data["impacts"]
    cpu_spec = impact_data["verbose"]["CPU-1"]
    ram_spec = impact_data["verbose"]["RAM-1"]

    average_power_value = impact_data["verbose"]["avg_power"]["value"]
    average_power_unit = impact_data["verbose"]["avg_power"]["unit"]
    use_time_ratio = impact_data["verbose"]["use_time_ratio"]["value"]

    assert average_power_unit == "W"
    assert float(use_time_ratio) == 1

    return base_efootprint_class(
        f"{provider} {instance_type} instances",
        carbon_footprint_fabrication=SourceValue(impacts["gwp"]["embedded"]["value"] * u.kg, impact_source),
        power=SourceValue(average_power_value * u.W, impact_source),
        lifespan=lifespan,
        idle_power=idle_power,
        ram=SourceValue(ram_spec["units"]["value"] * ram_spec["capacity"]["value"] * u.GB, impact_source),
        cpu_cores=SourceValue(cpu_spec["units"]["value"] * cpu_spec["core_units"]["value"] * u.core, impact_source),
        power_usage_effectiveness=power_usage_effectiveness,
        average_carbon_intensity=average_carbon_intensity,
        server_utilization_rate=server_utilization_rate,
        base_ram_consumption=base_ram_consumption,
        base_cpu_consumption=base_cpu_consumption,
        storage=storage)


def on_premise_server_from_config(
        name: str, nb_of_cpu_units: int, nb_of_cores_per_cpu_unit: int, nb_of_ram_units: int,
        ram_quantity_per_unit_in_gb: int, average_carbon_intensity, lifespan=None, idle_power=None,
        power_usage_effectiveness=None, server_utilization_rate=None, fixed_nb_of_instances=None,
        base_ram_consumption=None, base_cpu_consumption=None, storage: Storage=None):
    impact_url = "https://api.boavizta.org/v1/server/"
    params = {"verbose": "true", "archetype": "platform_compute_medium", "criteria": ["gwp"]}
    data = {"model": {"type": "rack"},
            "configuration": {"cpu": {"units": nb_of_cpu_units, "core_units": nb_of_cores_per_cpu_unit},
                              "ram": [{"units": nb_of_ram_units, "capacity": ram_quantity_per_unit_in_gb}]}}

    impact_source = Source(name="Boavizta API servers",
                           link=f"{impact_url}?{'&'.join([key + '=' + str(params[key]) for key in params.keys()])}")
    impact_data = call_boaviztapi(url=impact_url, params=params, json=data, method="POST")

    if lifespan is None:
        lifespan = SourceValue(6 * u.year, Sources.HYPOTHESIS)
    if idle_power is None:
        idle_power = SourceValue(0 * u.W, Sources.HYPOTHESIS)
    if power_usage_effectiveness is None:
        power_usage_effectiveness = SourceValue(1.4 * u.dimensionless, Sources.HYPOTHESIS)
    if server_utilization_rate is None:
        server_utilization_rate = SourceValue(0.7 * u.dimensionless, Sources.HYPOTHESIS)
    if base_ram_consumption is None:
        base_ram_consumption = SourceValue(0 * u.GB, Sources.HYPOTHESIS)
    if base_cpu_consumption is None:
        base_cpu_consumption = SourceValue(0 * u.core, Sources.HYPOTHESIS)

    storage_type = None
    storage_spec = None
    if "SSD-1" in impact_data["verbose"].keys() and "HDD-1" in impact_data["verbose"].keys():
        raise ValueError("Both SSD and HDD storage found in the server impact data ,this is not implemented yet")
    elif "SSD-1" in impact_data["verbose"].keys():
        storage_type = "SSD"
        storage_spec = impact_data["verbose"]["SSD-1"]
    elif "HDD-1" in impact_data["verbose"].keys():
        storage_type = "HDD"
        storage_spec = impact_data["verbose"]["HDD-1"]

    full_storage_carbon_footprint_fabrication = SourceValue(
        storage_spec["impacts"]["gwp"]["embedded"]["value"] * u.kg, source=impact_source,
        label=f"Total {name} fabrication footprint")
    if storage is None:
        storage_unit = getattr(u, storage_spec["capacity"]["unit"])
        storage_capacity_from_api = SourceValue(
                    storage_spec["capacity"]["value"] * storage_unit, source=impact_source)
        nb_units = SourceValue(
            storage_spec["units"]["value"] * u.dimensionless, impact_source, f"Number of {name} storage instances")
        carbon_footprint_fabrication = (full_storage_carbon_footprint_fabrication / nb_units).set_label(
            f"Fabrication footprint of one {name} storage instance")
        if storage_type == 'SSD':
            reference_storage_capacity = default_ssd().storage_capacity
            ratio = (storage_capacity_from_api / reference_storage_capacity).to(u.dimensionless).set_label(
                "Ratio of on premise server storage capacity to default SSD storage capacity")
            storage = default_ssd(
                f"{name} SSD storage",
                storage_capacity=storage_capacity_from_api,
                fixed_nb_of_instances=nb_units,
                carbon_footprint_fabrication=carbon_footprint_fabrication,
                power=default_ssd().power * ratio,
            )
        elif storage_type == 'HDD':
            reference_storage_capacity = default_hdd().storage_capacity
            ratio = (storage_capacity_from_api / reference_storage_capacity).to(u.dimensionless).set_label(
                "Ration of on premise server storage capacity to default HDD storage capacity")
            storage = default_hdd(
                f"{name} HDD storage",
                storage_capacity=storage_capacity_from_api,
                fixed_nb_of_instances=nb_units,
                carbon_footprint_fabrication=carbon_footprint_fabrication,
                power=default_hdd().power * ratio,
            )
        else:
            raise ValueError(f"Storage type {storage_type} not yet implemented")

    average_power_value = impact_data["verbose"]["avg_power"]["value"]
    average_power_unit = impact_data["verbose"]["avg_power"]["unit"]
    use_time_ratio = impact_data["verbose"]["use_time_ratio"]["value"]

    assert average_power_unit == "W"
    assert float(use_time_ratio) == 1

    impacts = impact_data["impacts"]
    cpu_spec = impact_data["verbose"]["CPU-1"]
    ram_spec = impact_data["verbose"]["RAM-1"]

    total_fabrication_footprint_storage_included = SourceValue(
        impacts["gwp"]["embedded"]["value"] * u.kg, impact_source,
        f"Total {name} fabrication footprint storage included")
    total_fabrication_footprint_storage_excluded = (
            total_fabrication_footprint_storage_included - full_storage_carbon_footprint_fabrication)

    return OnPremise(
        name,
        carbon_footprint_fabrication=total_fabrication_footprint_storage_excluded,
        power=SourceValue(average_power_value * u.W, impact_source),
        lifespan=lifespan,
        idle_power=idle_power,
        ram=SourceValue(ram_spec["units"]["value"] * ram_spec["capacity"]["value"] * u.GB, impact_source),
        cpu_cores=SourceValue(cpu_spec["units"]["value"] * cpu_spec["core_units"]["value"] * u.core, impact_source),
        power_usage_effectiveness=power_usage_effectiveness,
        average_carbon_intensity=average_carbon_intensity,
        server_utilization_rate=server_utilization_rate,
        fixed_nb_of_instances=fixed_nb_of_instances,
        base_ram_consumption=base_ram_consumption,
        base_cpu_consumption=base_cpu_consumption,
        storage=storage
    )


if __name__ == "__main__":
    print_archetypes_and_their_configs()
