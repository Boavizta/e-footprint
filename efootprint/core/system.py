from datetime import timedelta
from typing import Dict, List, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
from efootprint.builders.external_apis.external_api_job_base_class import ExternalAPIJob
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
from efootprint.utils.display import human_readable_unit, display_quantity_as_str
from efootprint.abstract_modeling_classes.reactive_core import (
    ComputationPurpose, computed_attribute, computed_structure)
from efootprint.core.attribution import attribution_sources


class System(ModelingObject):
    """Top-level container of an e-footprint model. Aggregates one or more {class:UsagePattern}s and {class:EdgeUsagePattern}s and exposes the total fabrication and energy footprint of the modeled digital service."""

    interactions = (
        "Construct {class:System} last, once all {class:UsagePattern} and {class:EdgeUsagePattern} objects "
        "have been wired up. The system kicks off the calculation pipeline and is the entry point for "
        "footprint plots and serialization helpers.")

    param_descriptions = {
        "usage_patterns": (
            "List of {class:UsagePattern}s describing web-style traffic against the system's servers."),
        "edge_usage_patterns": (
            "List of {class:EdgeUsagePattern}s describing edge-side workloads. Pass an empty list for "
            "purely web systems."),
    }

    def __init__(self, name: str, usage_patterns: List[UsagePattern], edge_usage_patterns: List[EdgeUsagePattern],):
        super().__init__(name)
        self.usage_patterns = usage_patterns
        self.edge_usage_patterns = edge_usage_patterns
        self.check_no_object_to_link_is_already_linked_to_another_system()

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
        for mod_obj in dict.fromkeys([self] + self.all_linked_objects):
            mod_obj.pull_guard_attributes()

    def get_objects_linked_to_usage_patterns(
            self, usage_patterns: List[UsagePattern]) -> List[ModelingObject]:
        output_list =  self.storages + usage_patterns
        usage_journeys = self.usage_journeys
        uj_steps = list(dict.fromkeys(sum([list(uj.uj_steps) for uj in usage_journeys], start=[])))
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
        edge_device_groups = []
        for ed in edge_devices:
            for group in ed.parent_groups:
                if group not in edge_device_groups:
                    edge_device_groups.append(group)
                    for ancestor in group._find_all_ancestor_groups():
                        if ancestor not in edge_device_groups:
                            edge_device_groups.append(ancestor)
        all_modeling_objects = (
                output_list + edge_usage_journeys + edge_functions + recurrent_edge_device_needs
                + recurrent_server_needs + recurrent_edge_component_needs
                + edge_devices + edge_devices_components + edge_device_groups)

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
        # Every JobBase subclass exposes `server` (Job/GPUJob direct, ServiceJob and ExternalAPIJob via property).
        return list(dict.fromkeys([job.server for job in self.jobs if isinstance(job.server, ServerBase)]))

    @property
    def services(self) -> List[Service]:
        return list(dict.fromkeys(sum([server.installed_services for server in self.servers], start=[])))

    @property
    def external_apis(self) -> List[ExternalAPI]:
        return list(dict.fromkeys([job.external_api for job in self.jobs if isinstance(job, ExternalAPIJob)]))

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
                    f"{obj_key.name} fabrication footprints summed over modeling period")
                for obj_key, obj_value in category_dict.items()
            }

        return fab_footprints_sum

    @property
    def energy_footprint_sum_over_period(self) -> Dict[str, Dict[ModelingObject, ExplainableQuantity]]:
        energy_footprints_sum = {}
        for key, dict_value in self.energy_footprints.items():
            energy_footprints_sum[key] = {
                obj_key: self.sum_and_remove_empty_explainable_object(obj_value).to(u.kg).set_label(
                    f"{obj_key.name} energy footprints summed over modeling period")
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

    @computed_attribute(serialize=True, purposes={ComputationPurpose.FOOTPRINT})
    def total_footprint(self):
        """Total system carbon footprint as an hourly timeseries, summing fabrication and energy footprints across every category of object (servers, storages, devices, networks, edge components)."""
        # Relationship edits can change containment after construction, so validate again at the footprint boundary.
        self.check_no_object_to_link_is_already_linked_to_another_system()
        # Snapshot the category breakdown once. Without this, `self.fabrication_footprints` and
        # `self.energy_footprints` each rebuild `_objects_by_category()` (which walks `all_linked_objects`
        # and re-derives jobs/servers/etc. from scratch), and the `for key in self.fabrication_footprints`
        # iteration would do it a third time. Each rebuild costs ~3 ms on a system of ~200 objects.
        categories = self._objects_by_category()
        fab = {category: [obj.instances_fabrication_footprint for obj in objs
                          if hasattr(obj, "instances_fabrication_footprint")]
               for category, objs in categories.items()}
        energy = {category: [obj.energy_footprint for obj in objs
                             if hasattr(obj, "energy_footprint")]
                  for category, objs in categories.items()}
        total_footprint = sum(
            [sum(fab[key]) + sum(energy[key]) for key in fab],
            start=EmptyExplainableObject(),
        ).to(u.kg).set_label("Total carbon footprint")

        return round(total_footprint, 4)

    @computed_structure(serialize=True)
    def impact_repartition_matrix(self) -> tuple:
        """The condensed impact-repartition summary: one dict-encoded row per attribution atom of the
        system's impact sources — (source, stream, cell coordinate ids, usage pattern, phase) with the
        atom's value reduced to its period sum in kg. Sankey folds and repartition reads run over these
        summed scalars; the hourly attribution reads keep folding the live atoms."""
        rows = []
        for source in attribution_sources(self):
            rows += source.impact_repartition_rows
        return tuple(rows)

    def compare_to(self, other: "System"):
        """Return a {class:SystemComparison} of this system against ``other`` — the notebook entry point for the comparison capability (totals + deltas, per-(category, phase) decomposition, aligned/cumulative time-series, input diff)."""
        from efootprint.comparison.system_comparison import SystemComparison
        return SystemComparison(self, other)

    @property
    def has_version_baseline(self) -> bool:
        """True when this system was loaded from a file saved by another library version that stored
        computed values: those values are retained in memory as an "as computed by vX" baseline
        (never re-serialized) instead of being trusted as caches."""
        return self.__dict__.get("_version_baseline") is not None

    def compare_to_version_baseline(self):
        """Return a {class:SystemComparison} of this system (recomputed by the current library version on
        read) against its retained "as computed by vX" baseline, so methodology or upstream-data drift
        introduced by a library upgrade is quantified with the standard comparison machinery. Only
        available on systems loaded from a file saved by a different library version; the baseline is
        session-scoped — the old file itself is the durable record."""
        baseline = self.__dict__.get("_version_baseline")
        if baseline is None:
            raise ValueError(
                f"{self.name} carries no version baseline: baselines only exist on systems loaded from a "
                f"file saved by a different library version that stored computed values.")
        from copy import copy as copy_value
        from efootprint.abstract_modeling_classes.reactive_core import computed_slots, computed_structures
        from efootprint.api_utils.json_to_system import json_to_system
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.comparison.duplication import assign_fresh_system_id
        from efootprint.comparison.system_comparison import SystemComparison

        # Inputs-only duplicate: the baseline system must carry the stored vX values and nothing
        # computed by the current version.
        class_obj_dict, flat_obj_dict, _ = json_to_system(system_to_json(self, save_computed_state=False))
        baseline_system = assign_fresh_system_id(next(iter(class_obj_dict["System"].values())))
        baseline_system.name = f"{self.name} as computed by v{baseline['efootprint_version']}"

        for (container_id, attr_name, key_id), value in baseline["values"].items():
            container = flat_obj_dict.get(container_id)
            if container is None:
                # Upgrade handlers may drop objects entirely (e.g. suppressed classes); their stored
                # values have no current counterpart to compare against.
                continue
            declared_computed_slots = computed_slots(container.efootprint_class)
            declared_computed_structures = computed_structures(container.efootprint_class)
            if attr_name in declared_computed_slots:
                descriptor = declared_computed_slots[attr_name]
                if key_id is not None:
                    if key_id in flat_obj_dict:
                        descriptor.attach_element_cached_value(container, flat_obj_dict[key_id], copy_value(value))
                else:
                    descriptor.attach_cached_value(container, copy_value(value))
            elif attr_name in declared_computed_structures:
                declared_computed_structures[attr_name].attach_cached_value(
                    container, tuple(value) if isinstance(value, list) else value)

        return SystemComparison(baseline_system, self)

    def plot_footprints_by_category_and_object(self, filename=None, height=400, width=800, notebook=True):
        import plotly.express as px
        import plotly

        fab_footprints = self.fabrication_footprint_sum_over_period
        energy_footprints = self.energy_footprint_sum_over_period

        rows_as_dicts = []
        total_footprint_sum_display = self.total_footprint.sum().display_quantity
        chart_unit = total_footprint_sum_display.units
        chart_unit_str = human_readable_unit(chart_unit)
        value_colname = f"{chart_unit_str} CO2 emissions"

        for category in fab_footprints:
            fab_objects = sorted(fab_footprints[category].items(), key=lambda x: x[0].name)
            energy_objects = sorted(energy_footprints[category].items(), key=lambda x: x[0].name)

            for objs, color in zip([energy_objects, fab_objects], ["Electricity", "Fabrication"]):
                for object, expl_quantity in objs:
                    display_quantity = expl_quantity.display_quantity
                    amount_str = display_quantity_as_str(display_quantity)

                    rows_as_dicts.append({
                        "Type": color, "Category": category, "Object": object.name,
                        value_colname: display_quantity.magnitude, "Amount": amount_str})

        import pandas as pd
        df = pd.DataFrame.from_records(rows_as_dicts)

        total_co2 = df[value_colname].sum()
        total_footprint = self.total_footprint

        start_date = total_footprint.start_date
        end_date = start_date + timedelta(hours=len(total_footprint.value) - 1)
        total_amount_str = display_quantity_as_str(total_footprint_sum_display)

        fig = px.bar(
            df, x="Category", y=value_colname, color='Type', barmode='group',
            height=height, width=width,
            hover_data={"Type": False, "Category": False, "Object": True, value_colname: False, "Amount": True},
            template="plotly_white",
            title=f"Total CO2 emissions from {start_date.date()} to {end_date.date()}: {total_amount_str}"
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
            plotly.offline.plot(fig, filename=filename, auto_open=False, include_plotlyjs="cdn")

        if notebook:
            from IPython.display import HTML
            return HTML(filename)

        return fig
