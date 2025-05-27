from typing import Dict, List

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.logger import logger
from efootprint.utils.plot_emission_diffs import EmissionPlotter
from efootprint.utils.tools import format_co2_amount, display_co2_amount


class System(ModelingObject):
    def __init__(self, name: str, usage_patterns: List[UsagePattern]):
        super().__init__(name)
        self.total_footprint = EmptyExplainableObject()
        self.check_no_object_to_link_is_already_linked_to_another_system(usage_patterns)
        self.usage_patterns = usage_patterns
        self.simulation = None
        self.set_initial_and_previous_footprints()

    def set_initial_and_previous_footprints(self):
        self.previous_change = None
        self.previous_total_energy_footprints_sum_over_period = ExplainableObjectDict()
        self.previous_total_fabrication_footprints_sum_over_period = ExplainableObjectDict()
        self.all_changes = []
        self.initial_total_energy_footprints_sum_over_period = ExplainableObjectDict()
        self.initial_total_fabrication_footprints_sum_over_period = ExplainableObjectDict()

    def compute_calculated_attributes(self):
        self.check_no_object_to_link_is_already_linked_to_another_system(self.usage_patterns)
        super().compute_calculated_attributes()

    @property
    def calculated_attributes(self) -> List[str]:
        return ["total_footprint"]

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return (super().attributes_that_shouldnt_trigger_update_logic
                + ["all_changes", "previous_change", "previous_total_energy_footprints_sum_over_period",
                   "previous_total_fabrication_footprints_sum_over_period",
                   "initial_total_energy_footprints_sum_over_period",
                   "initial_total_fabrication_footprints_sum_over_period", "simulation"])

    def check_no_object_to_link_is_already_linked_to_another_system(self, usage_patterns: List[UsagePattern]):
        for mod_obj in self.get_objects_linked_to_usage_patterns(usage_patterns):
            mod_obj_systems = mod_obj.systems
            if mod_obj_systems and mod_obj_systems[0].id != self.id:
                raise PermissionError(f"{mod_obj.name} is already linked to {mod_obj_systems[0].name}, so it is "
                                      f"impossible to link it to {self.name}")
            if len(mod_obj_systems) > 1:
                raise ValueError(f"{mod_obj.name} is linked to 2 systems, this should never happen, please report an"
                                 f" e-footprint bug at https://github.com/Boavizta/e-footprint/issues")

    @property
    def usage_journeys(self) -> List[UsageJourney]:
        output_set = set()
        for usage_pattern in self.usage_patterns:
            output_set.update({usage_pattern.usage_journey})

        return list(output_set)

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return self.usage_patterns

    @property
    def systems(self) -> List:
        return [self]

    def after_init(self):
        from time import time
        start = time()
        logger.info(f"Starting computing {self.name} modeling")
        mod_obj_computation_chain_excluding_self = self.mod_objs_computation_chain[1:]
        self.launch_mod_objs_computation_chain(mod_obj_computation_chain_excluding_self)
        self.compute_calculated_attributes()
        logger.info(f"Finished computing {self.name} modeling in {round(time() - start, 3)} seconds")
        self.initial_total_energy_footprints_sum_over_period = self.total_energy_footprint_sum_over_period
        self.initial_total_fabrication_footprints_sum_over_period = self.total_fabrication_footprint_sum_over_period
        self.trigger_modeling_updates = True

    def get_objects_linked_to_usage_patterns(self, usage_patterns: List[UsagePattern]):
        output_list =  self.storages_from_usage_patterns(usage_patterns) + usage_patterns + \
                      self.networks_from_usage_patterns(usage_patterns)
        usage_journeys = list(set([up.usage_journey for up in usage_patterns]))
        uj_steps = list(set(sum([uj.uj_steps for uj in usage_journeys], start=[])))
        jobs = list(set(sum([uj_step.jobs for uj_step in uj_steps], start=[])))
        devices = list(set(sum([up.devices for up in usage_patterns], start=[])))
        countries = list(set([up.country for up in usage_patterns]))
        servers = self.servers_from_usage_patterns(usage_patterns)
        services = list(set(sum([server.installed_services for server in servers], start=[])))
        all_modeling_objects = output_list + usage_journeys + uj_steps + jobs + devices + countries + servers + services

        return all_modeling_objects

    @property
    def all_linked_objects(self):
        return self.get_objects_linked_to_usage_patterns(self.usage_patterns)

    @staticmethod
    def servers_from_usage_patterns(usage_patterns: List[UsagePattern]) -> List[Server]:
        output_set = set()
        for usage_pattern in usage_patterns:
            output_set.update(usage_pattern.usage_journey.servers)

        return list(output_set)

    @property
    def servers(self) -> List[Server]:
        return self.servers_from_usage_patterns(self.usage_patterns)

    @staticmethod
    def storages_from_usage_patterns(usage_patterns: List[UsagePattern]) -> List[Storage]:
        output_set = set()
        for usage_pattern in usage_patterns:
            output_set.update(usage_pattern.usage_journey.storages)

        return list(output_set)

    @property
    def storages(self) -> List[Storage]:
        return self.storages_from_usage_patterns(self.usage_patterns)

    @staticmethod
    def networks_from_usage_patterns(usage_patterns: List[UsagePattern]) -> List[Network]:
        output_set = set()
        for usage_pattern in usage_patterns:
            output_set.update({usage_pattern.network})

        return list(output_set)

    @property
    def networks(self) -> List[Network]:
        return self.networks_from_usage_patterns(self.usage_patterns)

    def get_storage_by_name(self, storage_name) -> Storage:
        for storage in self.storages:
            if storage.name == storage_name:
                return storage

    def get_server_by_name(self, server_name) -> Server:
        for server in self.servers:
            if server.name == server_name:
                return server

    def get_usage_pattern_by_name(self, usage_pattern_name) -> UsagePattern:
        for usage_pattern in self.usage_patterns:
            if usage_pattern.name == usage_pattern_name:
                return usage_pattern

    @property
    def fabrication_footprints(self) -> Dict[str, Dict[str, ExplainableHourlyQuantities]]:
        fab_footprints = {
            "Servers": {server.id: server.instances_fabrication_footprint for server in self.servers},
            "Storage": {storage.id: storage.instances_fabrication_footprint for storage in self.storages},
            "Network": {"networks": EmptyExplainableObject()},
            "Devices": {usage_pattern.id: usage_pattern.instances_fabrication_footprint
                        for usage_pattern in self.usage_patterns},
        }

        return fab_footprints

    @property
    def energy_footprints(self) -> Dict[str, Dict[str, ExplainableHourlyQuantities]]:
        energy_footprints = {
            "Servers": {server.id: server.energy_footprint for server in self.servers},
            "Storage": {storage.id: storage.energy_footprint for storage in self.storages},
            "Network": {network.id: network.energy_footprint for network in self.networks},
            "Devices": {usage_pattern.id: usage_pattern.energy_footprint
                        for usage_pattern in self.usage_patterns},
        }

        return energy_footprints

    @property
    def total_fabrication_footprints(self) -> Dict[str, ExplainableHourlyQuantities]:
        fab_footprints = {
            "Servers": sum([server.instances_fabrication_footprint for server in self.servers],
                           start=EmptyExplainableObject()).to(u.kg).set_label(
                "Servers total fabrication footprint"),
            "Storage": sum([storage.instances_fabrication_footprint for storage in self.storages],
                           start=EmptyExplainableObject()).to(u.kg).set_label(
                "Storage total fabrication footprint"),
            "Network": EmptyExplainableObject(),
            "Devices": sum([usage_pattern.instances_fabrication_footprint
                           for usage_pattern in self.usage_patterns], start=EmptyExplainableObject()).to(u.kg).set_label(
                "Devices total fabrication footprint")
        }

        return fab_footprints

    @property
    def total_energy_footprints(self) -> Dict[str, ExplainableHourlyQuantities]:
        energy_footprints = {
            "Servers": sum([server.energy_footprint for server in self.servers], start=EmptyExplainableObject()
                           ).to(u.kg).set_label("Servers total energy footprint"),
            "Storage": sum([storage.energy_footprint for storage in self.storages], start=EmptyExplainableObject()
                           ).to(u.kg).set_label("Storage total energy footprint"),
            "Network": sum([network.energy_footprint for network in self.networks], start=EmptyExplainableObject()
                           ).to(u.kg).set_label("Network total energy footprint"),
            "Devices": sum([usage_pattern.energy_footprint for usage_pattern in self.usage_patterns],
                           start=EmptyExplainableObject()).to(u.kg).set_label("Devices total energy footprint")
        }

        return energy_footprints

    @staticmethod
    def sum_and_remove_empty_explainable_object(expl_obj):
        tmp_sum = expl_obj.sum()
        if isinstance(tmp_sum, EmptyExplainableObject):
            tmp_sum = ExplainableQuantity(0 * u.kg, "null value")

        return tmp_sum

    @property
    def fabrication_footprint_sum_over_period(self) -> Dict[str, Dict[ModelingObject, ExplainableQuantity]]:
        fab_footprints_sum = {}
        for category_key, category_dict in self.fabrication_footprints.items():
            fab_footprints_sum[category_key] = {
                obj_key: self.sum_and_remove_empty_explainable_object(obj_value).to(u.kg).set_label(
                    f"{obj_key} fabrication footprints summed over modeling period")
                for obj_key, obj_value in category_dict.items()
            }

        return fab_footprints_sum

    @property
    def energy_footprint_sum_over_period(self) -> Dict[str, Dict[ModelingObject, ExplainableQuantity]]:
        energy_footprints_sum = {}
        for key, dict_value in self.energy_footprints.items():
            energy_footprints_sum[key] = {
                obj_key: self.sum_and_remove_empty_explainable_object(obj_value).to(u.kg).set_label(
                    f"{obj_key} energy footprints summed over modeling period")
                for obj_key, obj_value in dict_value.items()
            }

        return energy_footprints_sum

    @property
    def total_fabrication_footprint_sum_over_period(self) -> Dict[str, ExplainableQuantity]:
        fab_footprints = {
            object_category: self.sum_and_remove_empty_explainable_object(category_value).to(u.kg).set_label(
                f"{object_category} total fabrication footprints summed over modeling period")
            for object_category, category_value in self.total_fabrication_footprints.items()
        }

        return ExplainableObjectDict(fab_footprints)

    @property
    def total_energy_footprint_sum_over_period(self) -> Dict[str, ExplainableQuantity]:
        energy_footprints = {
            object_category: self.sum_and_remove_empty_explainable_object(category_value).to(u.kg).set_label(
                f"{object_category} total energy footprints summed over modeling period")
            for object_category, category_value in self.total_energy_footprints.items()
        }

        return ExplainableObjectDict(energy_footprints)

    def update_total_footprint(self):
        total_footprint = (
            sum(
                sum(self.fabrication_footprints[key].values()) + sum(self.energy_footprints[key].values())
                for key in self.fabrication_footprints
            )
        ).to(u.kg).set_label(f"{self.name} total carbon footprint")

        self.total_footprint = round(total_footprint, 4)

    def plot_footprints_by_category_and_object(self, filename=None, height=400, width=800, return_only_html=False):
        import plotly.express as px
        import plotly

        fab_footprints = self.fabrication_footprint_sum_over_period
        energy_footprints = self.energy_footprint_sum_over_period
        categories = list(fab_footprints.keys())

        rows_as_dicts = []

        value_colname = "tonnes CO2 emissions"
        for category in categories:
            fab_objects = sorted(fab_footprints[category].items(), key=lambda x: x[0])
            energy_objects = sorted(energy_footprints[category].items(), key=lambda x: x[0])

            for objs, color in zip([energy_objects, fab_objects], ["Electricity", "Fabrication"]):
                data_dicts = [
                    {"Type": color, "Category": category, "Object": obj[0],
                     value_colname: obj[1].value.magnitude / 1000,
                     "Amount": f"{display_co2_amount(format_co2_amount(obj[1].value.magnitude))}"}
                    for obj in objs]
                rows_as_dicts += data_dicts

        df = pd.DataFrame.from_records(rows_as_dicts)

        total_co2 = df[value_colname].sum()

        total_footprint = self.total_footprint

        fig = px.bar(
            df, x="Category", y=value_colname, color='Type', barmode='group', height=height, width=width,
            hover_data={"Type": False, "Category": False, "Object": True, value_colname: False, "Amount": True},
            template="plotly_white",
            title=f"Total CO2 emissions from "
                  f"{total_footprint.value.index.min().date()} "
                  f"to {total_footprint.value.index.max().date()}"
                  f": {display_co2_amount(format_co2_amount(total_co2 * 1000, rounding_value=0))}"
                  )

        if (max(sum(energy_footprints["Servers"].values()), sum(fab_footprints["Servers"].values())) >
                max(sum(energy_footprints["Devices"].values()), sum(fab_footprints["Devices"].values()))):
            legend_alignment = "right"
            legend_x = 0.98
        else:
            legend_alignment = "left"
            legend_x = 0.02

        fig.update_layout(
            legend={"orientation": "v", "yanchor": "top", "y": 1.02, "xanchor": legend_alignment, "x": legend_x,
                    "title": ""},
            title={"x": 0.5, "y": 0.9, "xanchor": 'center', "yanchor": 'top'})

        total_co2_per_category_and_type = df.groupby(["Category", "Type"])[value_colname].sum()

        for category, source_type in total_co2_per_category_and_type.keys():
            height = total_co2_per_category_and_type.loc[category, source_type]
            x_shift_direction = 1 if source_type == 'Fabrication' else -1

            fig.add_annotation(
                x=category,
                y=height,
                text=f"{int((height / total_co2) * 100)}%",  # Format the label as a percentage
                showarrow=False,
                yshift=10,  # Shift the label slightly above the stack
                xshift=30 * x_shift_direction
            )

        if return_only_html:
            return fig.to_html(full_html=False, include_plotlyjs=False)

        else:
            from IPython.display import HTML

            if filename is None:
                filename = f"{self.name} footprints.html"

            plotly.offline.plot(fig, filename=filename, auto_open=False)

            return HTML(filename)

    def plot_emission_diffs(self, filepath=None, figsize=(10, 5), from_start=False, plt_show=False):
        from matplotlib import pyplot as plt

        if self.previous_change is None:
            raise ValueError(
                f"There has been no change to the system yet so no diff to plot.\n"
                f"Use System.plot_footprints_by_category_and_object() to visualize footprints")

        if from_start and len(self.all_changes) > 1:
            emissions_dict__old = [self.initial_total_energy_footprints_sum_over_period,
                                   self.initial_total_fabrication_footprints_sum_over_period]
        else:
            emissions_dict__old = [self.previous_total_energy_footprints_sum_over_period,
                                   self.previous_total_fabrication_footprints_sum_over_period]

        emissions_dict__new = [self.total_energy_footprint_sum_over_period,
                               self.total_fabrication_footprint_sum_over_period]

        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)

        EmissionPlotter(
            ax, emissions_dict__old, emissions_dict__new, rounding_value=0).plot_emission_diffs()

        if filepath is not None:
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            plt.show()
