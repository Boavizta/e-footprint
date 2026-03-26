from datetime import timedelta
from typing import Dict, List, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
from efootprint.builders.services.service_base_class import Service
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.job import JobBase
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.logger import logger
from efootprint.utils.display import best_display_unit, human_readable_unit


class System(ModelingObject):
    def __init__(self, name: str, usage_patterns: List[UsagePattern], edge_usage_patterns: List[EdgeUsagePattern],):
        super().__init__(name)
        self.total_footprint = EmptyExplainableObject()
        self.usage_patterns = usage_patterns
        self.edge_usage_patterns = edge_usage_patterns
        self.check_no_object_to_link_is_already_linked_to_another_system()
        self.simulation = None
        self.set_initial_and_previous_footprints()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return self.countries + self.edge_usage_patterns + self.usage_patterns

    def set_initial_and_previous_footprints(self):
        self.previous_change = None
        self.previous_total_energy_footprints_sum_over_period = ExplainableObjectDict()
        self.previous_total_fabrication_footprints_sum_over_period = ExplainableObjectDict()
        self.all_changes = []
        self.initial_total_energy_footprints_sum_over_period = ExplainableObjectDict()
        self.initial_total_fabrication_footprints_sum_over_period = ExplainableObjectDict()

    def compute_calculated_attributes(self):
        self.check_no_object_to_link_is_already_linked_to_another_system()
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

    def check_no_object_to_link_is_already_linked_to_another_system(self):
        for mod_obj in self.all_linked_objects:
            mod_obj_systems = mod_obj.systems
            if mod_obj_systems and mod_obj_systems[0].id != self.id:
                raise PermissionError(f"{mod_obj.name} is already linked to {mod_obj_systems[0].name}, so it is "
                                      f"impossible to link it to {self.name}")
            if len(mod_obj_systems) > 1:
                raise ValueError(f"{mod_obj.name} is linked to 2 systems, this should never happen, please report an"
                                 f" e-footprint bug at https://github.com/Boavizta/e-footprint/issues")

    @property
    def systems(self) -> List:
        return [self]

    def after_init(self):
        from time import perf_counter
        start = perf_counter()
        logger.info(f"Starting computing {self.name} modeling")
        mod_obj_computation_chain_excluding_self = self.mod_objs_computation_chain[1:]
        optimized_chain = optimize_mod_objs_computation_chain(mod_obj_computation_chain_excluding_self)
        if len(optimized_chain) == 0 or optimized_chain[-1] != self:
            optimized_chain.append(self)
        self.launch_mod_objs_computation_chain(optimized_chain)
        all_objects = self.all_linked_objects
        nb_of_calculated_attributes = sum([len(obj.calculated_attributes) for obj in all_objects])
        if nb_of_calculated_attributes > 0:
            compute_duration = round((perf_counter() - start), 3)
            logger.info(
                f"Computed {nb_of_calculated_attributes} calculated attributes over {len(all_objects)} objects in "
                f"{compute_duration} seconds or {round(1000 * compute_duration / nb_of_calculated_attributes, 2)} "
                f"ms per computation")
        self.initial_total_energy_footprints_sum_over_period = self.total_energy_footprint_sum_over_period
        self.initial_total_fabrication_footprints_sum_over_period = self.total_fabrication_footprint_sum_over_period
        self.trigger_modeling_updates = True

    def get_objects_linked_to_usage_patterns(
            self, usage_patterns: List[UsagePattern]) -> List[ModelingObject]:
        output_list =  self.storages + usage_patterns
        usage_journeys = self.usage_journeys
        uj_steps = list(dict.fromkeys(sum([uj.uj_steps for uj in usage_journeys], start=[])))
        devices = list(dict.fromkeys(sum([up.devices for up in usage_patterns], start=[])))
        all_modeling_objects = output_list + usage_journeys + uj_steps + devices

        return all_modeling_objects

    def get_objects_linked_to_edge_usage_patterns(
            self, edge_usage_patterns: List[EdgeUsagePattern]) -> List[ModelingObject]:
        output_list = self.edge_storages + edge_usage_patterns
        edge_usage_journeys = self.edge_usage_journeys
        edge_functions = list(dict.fromkeys(sum([euj.edge_functions for euj in edge_usage_journeys], start=[])))
        recurrent_edge_device_needs = list(
            set(sum([ef.recurrent_edge_device_needs for ef in edge_functions], start=[])))
        recurrent_server_needs = list(
            set(sum([ef.recurrent_server_needs for ef in edge_functions], start=[])))
        recurrent_edge_component_needs = list(
            set(sum([redn.recurrent_edge_component_needs for redn in recurrent_edge_device_needs], start=[])))
        edge_devices = self.edge_devices
        edge_devices_components = list(dict.fromkeys(sum([ed.components for ed in edge_devices], start=[])))
        all_modeling_objects = (
                output_list + edge_usage_journeys + edge_functions + recurrent_edge_device_needs
                + recurrent_server_needs + recurrent_edge_component_needs
                + edge_devices + edge_devices_components)

        return all_modeling_objects

    @property
    def all_linked_objects(self):
        return (self.networks + self.jobs + self.servers + self.services + self.external_apis
                + self.external_api_servers + self.countries
                + self.get_objects_linked_to_usage_patterns(self.usage_patterns)
                + self.get_objects_linked_to_edge_usage_patterns(self.edge_usage_patterns))

    @property
    def usage_journeys(self) -> List[UsageJourney]:
        return list(dict.fromkeys([up.usage_journey for up in self.usage_patterns]))

    @property
    def edge_usage_journeys(self) -> List[EdgeUsageJourney]:
        return list(dict.fromkeys([eup.edge_usage_journey for eup in self.edge_usage_patterns]))

    @property
    def devices(self) -> List[Device]:
        return list(dict.fromkeys(sum([up.devices for up in self.usage_patterns], start=[])))

    @property
    def countries(self) -> List[Country]:
        countries = list(dict.fromkeys([up.country for up in self.usage_patterns]
                             + [eup.country for eup in self.edge_usage_patterns]))
        return countries

    @property
    def networks(self) -> List[Network]:
        return list(dict.fromkeys([up.network for up in self.usage_patterns] + [eup.network for eup in self.edge_usage_patterns]))

    @property
    def jobs(self) -> List[JobBase]:
        jobs_from_usage_patterns = sum([up.jobs for up in self.usage_patterns], start=[])
        jobs_from_edge_usage_patterns = sum([eup.jobs for eup in self.edge_usage_patterns], start=[])
        return list(dict.fromkeys(jobs_from_usage_patterns + jobs_from_edge_usage_patterns))

    @property
    def servers(self) -> List[Server]:
        return list(dict.fromkeys([job.server for job in self.jobs if hasattr(job, "server")
                         and isinstance(job.server, ServerBase)]))

    @property
    def services(self) -> List[Service]:
        return list(dict.fromkeys(sum([server.installed_services for server in self.servers], start=[])))

    @property
    def external_apis(self) -> List[ExternalAPI]:
        return list(dict.fromkeys([job.external_api for job in self.jobs if hasattr(job, "external_api")]))

    @property
    def external_api_servers(self) -> List[ExternalAPIServer]:
        return list(dict.fromkeys([external_api.server for external_api in self.external_apis]))

    @property
    def edge_devices(self) -> List[EdgeDevice]:
        return list(dict.fromkeys(sum([euj.edge_devices for euj in self.edge_usage_journeys], start=[])))

    @property
    def edge_computers(self) -> List[EdgeComputer]:
        return [hw for hw in self.edge_devices if isinstance(hw, EdgeComputer)]

    @property
    def storages(self) -> List[Storage]:
        return list(dict.fromkeys([server.storage for server in self.servers]))

    @property
    def edge_storages(self) -> List[EdgeStorage]:
        edge_storages = []
        for edge_device in self.edge_devices:
            for component in edge_device.components:
                if isinstance(component, EdgeStorage):
                    edge_storages.append(component)
        return list(dict.fromkeys(edge_storages))

    @staticmethod
    def get_efootprint_obj_by_name(
            efootprint_obj_name: str, efootprint_obj_list: List[ModelingObject]) -> Optional[ModelingObject]:
        for efootprint_obj in efootprint_obj_list:
            if efootprint_obj.name == efootprint_obj_name:
                return efootprint_obj
        return None

    def _objects_by_category(self):
        from efootprint.all_classes_in_order import OBJECT_CATEGORIES
        result = {category: [] for category in OBJECT_CATEGORIES}
        for obj in self.all_linked_objects:
            for category_name, category_classes in OBJECT_CATEGORIES.items():
                if any(isinstance(obj, cls) for cls in category_classes):
                    result[category_name].append(obj)
                    break
        return result

    @property
    def fabrication_footprints(self) -> Dict[str, Dict[str, ExplainableHourlyQuantities]]:
        return {category: {obj: obj.instances_fabrication_footprint for obj in objs
                           if hasattr(obj, "instances_fabrication_footprint")}
                for category, objs in self._objects_by_category().items()}

    @property
    def energy_footprints(self) -> Dict[str, Dict[str, ExplainableHourlyQuantities]]:
        return {category: {obj: obj.energy_footprint for obj in objs if hasattr(obj, "energy_footprint")}
                for category, objs in self._objects_by_category().items()}

    @property
    def total_fabrication_footprints(self) -> Dict[str, ExplainableHourlyQuantities]:
        return {category: sum(objs.values(), start=EmptyExplainableObject()).to(u.kg).set_label(
            f"{category} total fabrication footprint")
            for category, objs in self.fabrication_footprints.items()}

    @property
    def total_energy_footprints(self) -> Dict[str, ExplainableHourlyQuantities]:
        return {category: sum(objs.values(), start=EmptyExplainableObject()).to(u.kg).set_label(
            f"{category} total energy footprint")
            for category, objs in self.energy_footprints.items()}

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
                [sum(self.fabrication_footprints[key].values()) + sum(self.energy_footprints[key].values())
                for key in self.fabrication_footprints], start=EmptyExplainableObject()
            )
        ).to(u.kg).set_label(f"{self.name} total carbon footprint")

        self.total_footprint = round(total_footprint, 4)

    def plot_footprints_by_category_and_object(self, filename=None, height=400, width=800, notebook=True):
        import plotly.express as px
        import plotly

        fab_footprints = self.fabrication_footprint_sum_over_period
        energy_footprints = self.energy_footprint_sum_over_period

        rows_as_dicts = []
        chart_unit = best_display_unit(self.total_footprint.value)
        chart_unit_str = human_readable_unit(chart_unit)
        value_colname = f"{chart_unit_str} CO2 emissions"

        for category in fab_footprints:
            fab_objects = sorted(fab_footprints[category].items(), key=lambda x: x[0].name)
            energy_objects = sorted(energy_footprints[category].items(), key=lambda x: x[0].name)

            for objs, color in zip([energy_objects, fab_objects], ["Electricity", "Fabrication"]):
                for object, quantity in objs:
                    converted_magnitude = quantity.to(chart_unit).magnitude
                    amount_str = f"{round(converted_magnitude, 2)} {chart_unit_str}"

                    rows_as_dicts.append({
                        "Type": color, "Category": category, "Object": object.name, value_colname: converted_magnitude,
                        "Amount": amount_str})

        import pandas as pd
        df = pd.DataFrame.from_records(rows_as_dicts)

        total_co2 = df[value_colname].sum()
        total_footprint = self.total_footprint

        start_date = total_footprint.start_date
        end_date = start_date + timedelta(hours=len(total_footprint.value) - 1)
        total_amount = round(total_footprint.sum().value.to(chart_unit).magnitude, 2)

        fig = px.bar(
            df, x="Category", y=value_colname, color='Type', barmode='group',
            height=height, width=width,
            hover_data={"Type": False, "Category": False, "Object": True, value_colname: False, "Amount": True},
            template="plotly_white",
            title=f"Total CO2 emissions from {start_date.date()} to {end_date.date()}: "
                  f"{total_amount} {chart_unit_str}"
        )

        # Legend placement logic
        total_energy_servers = sum(energy_footprints["Servers"].values(), start=0)
        total_fab_servers = sum(fab_footprints["Servers"].values(), start=0)
        total_energy_devices = sum(energy_footprints["Devices"].values(), start=0)
        total_fab_devices = sum(fab_footprints["Devices"].values(), start=0)

        if (total_energy_servers + total_fab_servers) > (total_energy_devices + total_fab_devices):
            legend_alignment = "right"
            legend_x = 0.98
        else:
            legend_alignment = "left"
            legend_x = 0.02

        fig.update_layout(
            legend={"orientation": "v", "yanchor": "top", "y": 1.02, "xanchor": legend_alignment, "x": legend_x,
                    "title": ""},
            title={"x": 0.5, "y": 0.9, "xanchor": 'center', "yanchor": 'top'}
        )

        # Add annotations (percentages per category and type)
        total_by_cat_type = df.groupby(["Category", "Type"])[value_colname].sum()

        for (category, source_type), height_val in total_by_cat_type.items():
            x_shift = 30 if source_type == 'Fabrication' else -30
            percentage = int((height_val / total_co2) * 100)

            fig.add_annotation(
                x=category, y=height_val,
                text=f"{percentage}%",
                showarrow=False,
                yshift=10,
                xshift=x_shift
            )

        if notebook and filename is None:
            filename = f"{self.name} footprints.html"

        if filename is not None:
            plotly.offline.plot(fig, filename=filename, auto_open=False)

        if notebook:
            from IPython.display import HTML
            return HTML(filename)

        return fig

    def plot_emission_diffs(self, filepath=None, figsize=(10, 5), from_start=False, plt_show=False):
        import os
        import matplotlib
        if not plt_show and os.environ.get("MPLBACKEND") is None:
            matplotlib.use("Agg", force=True)
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
        from efootprint.utils.plot_emission_diffs import EmissionPlotter
        EmissionPlotter(
            ax, emissions_dict__old, emissions_dict__new, rounding_value=0).plot_emission_diffs()

        if filepath is not None:
            plt.savefig(filepath, bbox_inches='tight')

        if plt_show:
            plt.show()

        return fig, ax
