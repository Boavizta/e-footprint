from collections import defaultdict
from functools import cached_property
from typing import List, TYPE_CHECKING


from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import divide_or_fallback
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.attribution import Atom
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.hardware.edge.edge_storage import EdgeStorage


class EdgeDevice(ModelingObject):
    """A piece of edge hardware (sensor, gateway, controller, embedded computer) made up of one or more {class:EdgeComponent}s plus a structural chassis. Aggregates fabrication and energy footprints of its components, then attributes them to the {class:RecurrentEdgeComponentNeed}s that load each one."""

    disambiguation = (
        "Use {class:EdgeDevice} to assemble bespoke hardware from individual {class:EdgeComponent}s. For "
        "appliance-style hardware modeled as a single workload curve, prefer {class:EdgeAppliance}. For "
        "computer-like hardware composed of CPU, RAM, and storage, prefer {class:EdgeComputer}.")

    pitfalls = (
        "{param:EdgeDevice.lifespan} must be longer than every {param:EdgeUsageJourney.usage_span} that uses "
        "the device. Otherwise the device cannot last the journey and the model raises an error.")

    param_descriptions = {
        "structure_carbon_footprint_fabrication": (
            "Embodied carbon of the chassis or structural envelope, separate from individual components."),
        "components": (
            "List of {class:EdgeComponent}s that make up the device (typically RAM, CPU, storage, or workload)."),
        "lifespan": (
            "Expected time before the device is replaced. Embodied carbon is amortised over this duration."),
    }

    default_values = {
        "structure_carbon_footprint_fabrication": SourceValue(50 * u.kg),
        "lifespan": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, structure_carbon_footprint_fabrication: ExplainableQuantity,
                 components: List[EdgeComponent], lifespan: ExplainableQuantity):
        super().__init__(name)
        self.lifespan = lifespan.set_label(f"Lifespan")
        self.structure_carbon_footprint_fabrication = structure_carbon_footprint_fabrication.set_label(
            f"Structure fabrication carbon footprint")
        self.components = components

        self.lifespan_validation = EmptyExplainableObject()
        self.component_needs_edge_device_validation = EmptyExplainableObject()
        self.total_nb_of_units = EmptyExplainableObject()
        self.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.fabrication_footprint_breakdown_by_source = ExplainableObjectDict()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    calculated_attributes = [
        "lifespan_validation", "component_needs_edge_device_validation",
        "total_nb_of_units",
        "structure_fabrication_footprint_per_usage_pattern",
        "instances_fabrication_footprint_per_usage_pattern",
        "instances_energy_per_usage_pattern", "energy_footprint_per_usage_pattern",
        "instances_fabrication_footprint", "fabrication_footprint_breakdown_by_source",
        "instances_energy", "energy_footprint"]

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
        return [elt for elt in self.modeling_obj_containers if isinstance(elt, RecurrentEdgeDeviceNeed)]

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
        return [elt for elt in self.modeling_obj_containers if isinstance(elt, RecurrentServerNeed)]

    @property
    def recurrent_needs(self) -> List["RecurrentEdgeDeviceNeed | RecurrentServerNeed"]:
        return self.recurrent_edge_device_needs + self.recurrent_server_needs

    @property
    def recurrent_edge_component_needs(self) -> List["RecurrentEdgeComponentNeed"]:
        return list(dict.fromkeys(sum(
            [need.recurrent_edge_component_needs for need in self.recurrent_edge_device_needs], start=[])))

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(dict.fromkeys(sum([need.edge_usage_journeys for need in self.recurrent_needs], start=[])))

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return list(dict.fromkeys(sum([need.edge_functions for need in self.recurrent_needs], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([need.edge_usage_patterns for need in self.recurrent_needs], start=[])))

    def _filter_component_by_type(self, component_type: type) -> List[EdgeComponent]:
        components_of_type = []
        for component in self.components:
            if isinstance(component, component_type):
                components_of_type.append(component)

        return components_of_type

    @property
    def storages(self) -> List["EdgeStorage"]:
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage
        return self._filter_component_by_type(EdgeStorage)

    @property
    def cpus(self):
        from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
        return self._filter_component_by_type(EdgeCPUComponent)

    def update_lifespan_validation(self):
        """Validates that the device lifespan is at least as long as every {class:EdgeUsageJourney} that uses it; raises otherwise."""
        result = EmptyExplainableObject().generate_explainable_object_with_logical_dependency(self.lifespan)
        for edge_usage_journey in self.edge_usage_journeys:
            if self.lifespan < edge_usage_journey.usage_span:
                raise InsufficientCapacityError(self, "lifespan", self.lifespan, edge_usage_journey.usage_span)
            result = result.generate_explainable_object_with_logical_dependency(edge_usage_journey.usage_span)
        self.lifespan_validation = result

    def update_component_needs_edge_device_validation(self):
        """Validates that every {class:RecurrentEdgeComponentNeed} loaded onto this device targets a component that actually belongs to it."""
        for component_need in self.recurrent_edge_component_needs:
            component_device = component_need.edge_component.edge_device
            if component_device is not None and component_device != self:
                raise ValueError(
                    f"RecurrentEdgeComponentNeed '{component_need.name}' points to component "
                    f"'{component_need.edge_component.name}' belonging to EdgeDevice '{component_device.name}', "
                    f"but RecurrentEdgeDeviceNeed '{self.name}' is linked to EdgeDevice '{self.name}'. "
                    f"All component needs must belong to the same edge device.")

        self.component_needs_edge_device_validation = EmptyExplainableObject()

    def _find_parent_groups(self):
        from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import (
            ContextualModelingObjectDictKey)

        return list(dict.fromkeys([
            contextual_container.modeling_obj_container
            for contextual_container in self.contextual_modeling_obj_containers
            if (
                isinstance(contextual_container, ContextualModelingObjectDictKey)
                and isinstance(contextual_container.modeling_obj_container, EdgeDeviceGroup)
            )
        ]))

    def _find_root_groups(self):
        parent_groups = self._find_parent_groups()
        root_groups = []
        for group in parent_groups:
            root_groups += group._find_root_groups()
        return list(dict.fromkeys(root_groups))

    def update_total_nb_of_units(self):
        """How many copies of the device are deployed in total once group hierarchies are unrolled. Defaults to 1 if the device is not in any {class:EdgeDeviceGroup}."""
        parent_groups = self._find_parent_groups()
        if not parent_groups:
            self.total_nb_of_units = ExplainableQuantity(
                1 * u.dimensionless, f"no group (default count = 1)")
            return

        # Sum contributions from all parent groups. When a device belongs to multiple
        # groups, its total count is the sum of its count in each group multiplied by
        # that group's effective number within the root, allowing a device to be shared
        # across independent group hierarchies with additive counts.
        total = sum(
            [group.edge_device_counts[self] * group.effective_nb_of_units_within_root
             for group in parent_groups],
            start=EmptyExplainableObject())
        self.total_nb_of_units = total.set_label(f"Total nb per ensemble")

    def self_delete(self):
        parent_groups = self._find_parent_groups()
        if parent_groups:
            raise PermissionError(
                f"You can’t delete {self.name} because it is referenced in edge_device_counts of "
                f"{','.join(parent.name for parent in parent_groups)}.")
        super().self_delete()

    def update_dict_element_in_structure_fabrication_footprint_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        structure_fabrication_intensity = self.structure_carbon_footprint_fabrication / self.lifespan
        nb_instances = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
            usage_pattern]
        self.structure_fabrication_footprint_per_usage_pattern[usage_pattern] = (
            self.total_nb_of_units * nb_instances * structure_fabrication_intensity * ExplainableQuantity(1 * u.hour, "one hour")
        ).to(u.kg).set_label(f"Hourly structure fabrication footprint for {usage_pattern.name}")

    def update_structure_fabrication_footprint_per_usage_pattern(self):
        """Hourly fabrication-phase emissions of the chassis (excluding components), broken down by usage pattern."""
        self.structure_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_structure_fabrication_footprint_per_usage_pattern(usage_pattern)

    def unused_component_fabrication_per_edge_device(self, component: EdgeComponent,
                                                     usage_pattern: "EdgeUsagePattern"):
        """Hourly fabrication footprint of a component with no needs at this pattern, booked as part of the
        chassis: the device is deployed there, so the unused component's embodied carbon amortizes with the
        deployment exactly like the structure's. Reads only the component's input attributes because need-less
        components never enter the calculated-attribute computation chain."""
        fabrication = component.carbon_footprint_fabrication_from_inputs
        if fabrication.magnitude == 0:
            return EmptyExplainableObject(
                left_parent=fabrication, label=f"No unused fabrication for zero-footprint {component.name}")
        if isinstance(component.lifespan, EmptyExplainableObject):
            raise ValueError(
                f"Cannot book the fabrication of unused component {component.name} at pattern "
                f"{usage_pattern.name}: its lifespan is a calculated attribute that was never computed because "
                f"the component has no needs. Give the component an input lifespan or link a need to it.")
        nb_instances = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
            usage_pattern]
        return (nb_instances * fabrication / component.lifespan * ExplainableQuantity(1 * u.hour, "one hour")
                ).to(u.kg).set_label(f"Hourly unused {component.name} fabrication footprint for {usage_pattern.name}")

    def update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        total_footprint = self.structure_fabrication_footprint_per_usage_pattern.get(
            usage_pattern, EmptyExplainableObject())
        for component in self.components:
            if usage_pattern in component.fabrication_footprint_per_edge_device_per_usage_pattern:
                total_footprint += (self.total_nb_of_units
                                    * component.fabrication_footprint_per_edge_device_per_usage_pattern[usage_pattern])
            else:
                total_footprint += (self.total_nb_of_units
                                    * self.unused_component_fabrication_per_edge_device(component, usage_pattern))

        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = total_footprint.to(
            u.kg).set_label(f"Hourly instances fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        """Hourly fabrication-phase emissions of the whole device (chassis plus all components), broken down by usage pattern. Components with no needs at a pattern count as part of the chassis there: their embodied carbon amortizes with the deployment."""
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    def update_dict_element_in_instances_energy_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # Sum energy from all components
        total_energy = EmptyExplainableObject()
        for component in self.components:
            if usage_pattern in component.energy_per_edge_device_per_usage_pattern:
                total_energy += component.energy_per_edge_device_per_usage_pattern[usage_pattern]

        self.instances_energy_per_usage_pattern[usage_pattern] = (
            self.total_nb_of_units * total_energy
        ).set_label(f"Hourly energy consumed by instances for {usage_pattern.name}")

    def update_instances_energy_per_usage_pattern(self):
        """Hourly energy consumed by the whole device, broken down by usage pattern. Equal to the sum of component-level energy multiplied by the device count."""
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_energy_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_footprint_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # Sum energy footprint from all components
        total_energy_footprint = EmptyExplainableObject()
        for component in self.components:
            if usage_pattern in component.energy_footprint_per_edge_device_per_usage_pattern:
                total_energy_footprint += component.energy_footprint_per_edge_device_per_usage_pattern[usage_pattern]

        self.energy_footprint_per_usage_pattern[usage_pattern] = (
            self.total_nb_of_units * total_energy_footprint
        ).set_label(
            f"Energy footprint for {usage_pattern.name}").to(u.kg)

    def update_energy_footprint_per_usage_pattern(self):
        """Hourly carbon emissions caused by device electricity use, broken down by usage pattern. Equal to component-level energy footprints summed and multiplied by the device count."""
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_footprint_per_usage_pattern(usage_pattern)

    def update_instances_energy(self):
        """Total hourly energy consumed by all instances of the device, summed across every usage pattern."""
        instances_energy = sum(
            self.instances_energy_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_energy = instances_energy.set_label(
            "Total energy consumed across usage patterns")

    def update_energy_footprint(self):
        """Total hourly energy-use carbon footprint, summed across every usage pattern."""
        energy_footprint = sum(
            self.energy_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.energy_footprint = energy_footprint.set_label(
            "Total energy footprint across usage patterns")

    def update_instances_fabrication_footprint(self):
        """Total hourly fabrication-phase carbon footprint, summed across every usage pattern."""
        instances_fabrication_footprint = sum(
            self.instances_fabrication_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            "Total fabrication footprint across usage patterns")

    def update_dict_element_in_fabrication_footprint_breakdown_by_source(self, component: EdgeComponent):
        structure_fabrication_total = sum(
            self.structure_fabrication_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        equal_structure_share = structure_fabrication_total / ExplainableQuantity(
            len(self.components) * u.dimensionless, label=f"Number of components")
        unused_fabrication = sum(
            [self.unused_component_fabrication_per_edge_device(component, usage_pattern)
             for usage_pattern in self.edge_usage_patterns
             if usage_pattern not in component.fabrication_footprint_per_edge_device_per_usage_pattern],
            start=EmptyExplainableObject())
        self.fabrication_footprint_breakdown_by_source[component] = (
            self.total_nb_of_units * (component.fabrication_footprint_per_edge_device + unused_fabrication)
            + equal_structure_share
        ).set_label(f"Fabrication footprint attributed to {component.name}")

    def update_fabrication_footprint_breakdown_by_source(self):
        """Per-component breakdown of the device's fabrication footprint, attributing each component's own embodied carbon (including the deployment-booked part at patterns where it has no needs) plus an even share of the chassis fabrication."""
        self.fabrication_footprint_breakdown_by_source = ExplainableObjectDict()
        if not self.components:
            return

        for component in self.components:
            self.update_dict_element_in_fabrication_footprint_breakdown_by_source(component)

    @property
    def energy_footprint_breakdown_by_source(self) -> ExplainableObjectDict:
        return ExplainableObjectDict({
            component: (self.total_nb_of_units * component.energy_footprint_per_edge_device).set_label(
                f"Energy footprint attributed to {component.name}")
            for component in self.components
        })

    @property
    def footprint_breakdown_by_source(self) -> dict[LifeCyclePhases, ExplainableObjectDict]:
        return {
            LifeCyclePhases.MANUFACTURING: self.fabrication_footprint_breakdown_by_source,
            LifeCyclePhases.USAGE: self.energy_footprint_breakdown_by_source,
        }

    # --- Attribution-only atom physics and builder (lazy cached properties / methods, consumed only by the
    # attribution layer, never by the eager calculated-attribute graph) ---

    @cached_property
    def demand_share_per_need_and_pattern(self) -> dict:
        """Each component need's hourly share of the capacity-occupying demand on its component in a pattern —
        CPU / RAM / workload by the hourly resource need, EdgeStorage by the need's own cumulative HELD volume
        (not the net write rate, which goes negative on delete hours). Hours where no need loads the component
        fall back to an explicit equal share across the component's needs present in the pattern (1/n — NOT
        divide_or_fallback(fallback=1), which would book the footprint once per need), so the shares always
        sum to 1."""
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage

        needs_per_component = defaultdict(list)
        for need in self.recurrent_edge_component_needs:
            needs_per_component[need.edge_component].append(need)

        shares = {}
        for component, needs in needs_per_component.items():
            is_storage = isinstance(component, EdgeStorage)
            for usage_pattern in component.edge_usage_patterns:
                needs_at_up = [need for need in needs if usage_pattern in need.unitary_hourly_need_per_usage_pattern]
                demand_per_need = {
                    need: (need.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern] if is_storage
                           else need.unitary_hourly_need_per_usage_pattern[usage_pattern])
                    for need in needs_at_up}
                total_demand = sum(demand_per_need.values(), start=EmptyExplainableObject())
                equal_share = 1 / len(needs_at_up)
                for need, demand in demand_per_need.items():
                    shares[(need, usage_pattern)] = divide_or_fallback(
                        demand, total_demand, fallback=equal_share).set_label(
                        f"{need.name} demand share of {component.name} in {usage_pattern.name}")

        return shares

    @cached_property
    def fabrication_pool_share_per_carrier_and_pattern(self) -> dict:
        """Chassis-pool rule: components unused at a pattern are part of the chassis. The
        pool at a pattern — every unused component's deployment-booked fabrication plus its equal chassis
        share (the full structure when the device has no components) — splits equally across the pattern's
        deployment carriers: the component needs at the pattern and the device's RecurrentServerNeeds reached
        there. Patterns where every component is used carry no entry. Raises when a deployed pattern has
        booked fabrication but no carriers (an empty RecurrentEdgeDeviceNeed)."""
        needs_at_pattern = defaultdict(list)
        for (need, usage_pattern) in self.demand_share_per_need_and_pattern:
            needs_at_pattern[usage_pattern].append(need)

        shares = {}
        for usage_pattern in self.edge_usage_patterns:
            used_component_ids = {need.edge_component.id for need in needs_at_pattern[usage_pattern]}
            unused_components = [c for c in self.components if c.id not in used_component_ids]
            if usage_pattern not in self.structure_fabrication_footprint_per_usage_pattern:
                # The device was never computed (e.g. deployed only through empty RecurrentEdgeDeviceNeeds):
                # nothing is booked eagerly, so there is nothing to attribute.
                continue
            structure_fabrication = self.structure_fabrication_footprint_per_usage_pattern[usage_pattern]
            if self.components:
                if not unused_components:
                    continue
                chassis_pool = structure_fabrication * ExplainableQuantity(
                    len(unused_components) / len(self.components) * u.dimensionless,
                    "Unused components' equal chassis shares")
            else:
                chassis_pool = structure_fabrication
            pool = sum(
                [self.total_nb_of_units * self.unused_component_fabrication_per_edge_device(
                    component, usage_pattern) for component in unused_components],
                start=chassis_pool)
            rsns_at_pattern = [rsn for rsn in self.recurrent_server_needs
                               if usage_pattern in rsn.edge_usage_patterns]
            nb_carriers = len(needs_at_pattern[usage_pattern]) + len(rsns_at_pattern)
            if nb_carriers == 0:
                raise ValueError(
                    f"{self.name} books fabrication at {usage_pattern.name} but has no component needs and no "
                    f"RecurrentServerNeeds there to attribute it to. Remove the empty RecurrentEdgeDeviceNeed "
                    f"deploying it or give it component needs.")
            shares[usage_pattern] = (pool / ExplainableQuantity(
                nb_carriers * u.dimensionless, "Number of deployment carriers")).to(u.kg).set_label(
                f"{self.name} unused-components chassis pool share per carrier in {usage_pattern.name}")

        return shares

    @cached_property
    def fabrication_atom_value_per_need_and_pattern(self) -> dict:
        """Fabrication atom value: (component fabrication + an equal 1/nb_components chassis share,
        matching the breakdown-by-source axis) × the need's demand share, plus the need's equal carrier share
        of the pattern's unused-components chassis pool."""
        nb_components = ExplainableQuantity(len(self.components) * u.dimensionless, "Number of components")
        pool_shares = self.fabrication_pool_share_per_carrier_and_pattern
        values = {}
        for (need, usage_pattern), share in self.demand_share_per_need_and_pattern.items():
            component_fabrication = (
                self.total_nb_of_units
                * need.edge_component.fabrication_footprint_per_edge_device_per_usage_pattern[usage_pattern])
            chassis_share = self.structure_fabrication_footprint_per_usage_pattern[usage_pattern] / nb_components
            value = (component_fabrication + chassis_share) * share
            if usage_pattern in pool_shares:
                value = value + pool_shares[usage_pattern]
            values[(need, usage_pattern)] = value.to(u.kg).set_label(
                f"{self.name} fabrication footprint attributed to {need.name} in {usage_pattern.name}")

        return values

    @cached_property
    def energy_atom_value_per_need_and_pattern(self) -> dict:
        """Energy atom value: the idle/base floor of the component's affine power curve — which no
        need's demand changes — split equally across the component's needs at every hour, plus the need's own
        dynamic marginal (the rest of the component's energy footprint, split by demand share — exact by
        linearity of the power curve). EdgeStorage draws no power, so its needs carry an empty energy value;
        the chassis carries no energy."""
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage

        one_hour = ExplainableQuantity(1 * u.hour, "one hour")
        nb_needs_per_component_and_pattern = defaultdict(int)
        for (need, usage_pattern) in self.demand_share_per_need_and_pattern:
            nb_needs_per_component_and_pattern[(need.edge_component, usage_pattern)] += 1

        values = {}
        for (need, usage_pattern), share in self.demand_share_per_need_and_pattern.items():
            component = need.edge_component
            if isinstance(component, EdgeStorage):
                values[(need, usage_pattern)] = EmptyExplainableObject(
                    label=f"{self.name} energy footprint attributed to {need.name} in {usage_pattern.name}")
                continue
            nb_journeys_in_parallel = (
                usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
                    usage_pattern])
            idle_and_base_floor = (
                self.total_nb_of_units * nb_journeys_in_parallel * component.unitary_power_at_zero_recurrent_need
                * one_hour * usage_pattern.country.average_carbon_intensity).to(u.kg)
            component_energy_footprint = (
                self.total_nb_of_units
                * component.energy_footprint_per_edge_device_per_usage_pattern[usage_pattern]).to(u.kg)
            equal_share = ExplainableQuantity(
                1 / nb_needs_per_component_and_pattern[(component, usage_pattern)] * u.dimensionless,
                f"Equal share among {component.name} needs in {usage_pattern.name}")
            values[(need, usage_pattern)] = (
                idle_and_base_floor * equal_share + (component_energy_footprint - idle_and_base_floor) * share
            ).to(u.kg).set_label(
                f"{self.name} energy footprint attributed to {need.name} in {usage_pattern.name}")

        return values

    def atom_value(self, need: "RecurrentEdgeComponentNeed", usage_pattern: "EdgeUsagePattern",
                   phase: LifeCyclePhases):
        """The per-(need, pattern) atom value — the need's footprint at the pattern across every
        bundle and function it sits in, before the slot-multiplicity split of attribution_atoms."""
        values = (self.fabrication_atom_value_per_need_and_pattern if phase == LifeCyclePhases.MANUFACTURING
                  else self.energy_atom_value_per_need_and_pattern)
        return values[(need, usage_pattern)]

    def attribution_atoms(self, phase: LifeCyclePhases):
        """Slot enumeration: for each pattern, walk the journey's edge functions (with multiplicity), each
        function's device-need bundles, each bundle's component needs — one atom per (need, bundle, function)
        slot, valued atom_value × slot count / total occurrences of the need in the journey, so the slots of a
        need partition its atom_value exactly: within-journey reuse splits across its bundles and functions by
        occurrence ratios; the common case is one slot with ratio 1. In the fabrication phase the device's
        RecurrentServerNeeds carry their equal share of the unused-components chassis pool through (rsn, ef)
        slots, split by the same occurrence ratios."""
        pool_shares = (self.fabrication_pool_share_per_carrier_and_pattern
                       if phase == LifeCyclePhases.MANUFACTURING else {})
        for usage_pattern in self.edge_usage_patterns:
            journey = usage_pattern.edge_usage_journey
            slot_counts = {}
            rsn_slot_counts = {}
            for edge_function in dict.fromkeys(journey.edge_functions):
                ef_count = journey.edge_functions.count(edge_function)
                for device_need in dict.fromkeys(edge_function.recurrent_edge_device_needs):
                    if device_need.edge_device != self:
                        continue
                    redn_count = edge_function.recurrent_edge_device_needs.count(device_need)
                    for component_need in dict.fromkeys(device_need.recurrent_edge_component_needs):
                        recn_count = device_need.recurrent_edge_component_needs.count(component_need)
                        slot_counts[(component_need, device_need, edge_function)] = (
                            ef_count * redn_count * recn_count)
                if usage_pattern in pool_shares:
                    for server_need in dict.fromkeys(edge_function.recurrent_server_needs):
                        if server_need.edge_device != self:
                            continue
                        rsn_slot_counts[(server_need, edge_function)] = (
                            ef_count * edge_function.recurrent_server_needs.count(server_need))
            occurrences_per_need = defaultdict(int)
            for (component_need, _, _), count in slot_counts.items():
                occurrences_per_need[component_need] += count
            for (component_need, device_need, edge_function), count in slot_counts.items():
                occurrence_share = ExplainableQuantity(
                    count / occurrences_per_need[component_need] * u.dimensionless,
                    f"{component_need.name} occurrence share via {device_need.name} in {edge_function.name}")
                yield Atom(
                    source=self, stream="single", up=usage_pattern, recn=component_need, redn=device_need,
                    ef=edge_function,
                    value=(self.atom_value(component_need, usage_pattern, phase) * occurrence_share).set_label(
                        f"{self.name} {phase.value.lower()} footprint via {component_need.name} through "
                        f"{device_need.name} in {edge_function.name} ({usage_pattern.name})"))
            occurrences_per_rsn = defaultdict(int)
            for (server_need, _), count in rsn_slot_counts.items():
                occurrences_per_rsn[server_need] += count
            for (server_need, edge_function), count in rsn_slot_counts.items():
                occurrence_share = ExplainableQuantity(
                    count / occurrences_per_rsn[server_need] * u.dimensionless,
                    f"{server_need.name} occurrence share in {edge_function.name}")
                yield Atom(
                    source=self, stream="single", up=usage_pattern, rsn=server_need, ef=edge_function,
                    value=(pool_shares[usage_pattern] * occurrence_share).set_label(
                        f"{self.name} {phase.value.lower()} footprint via {server_need.name} in "
                        f"{edge_function.name} ({usage_pattern.name})"))
