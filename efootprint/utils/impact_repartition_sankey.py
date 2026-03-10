from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.utils.tools import format_co2_amount, display_co2_amount

# Palette for consistent object coloring across fabrication/energy chains
_COLORS = [
    "rgba(31,119,180,0.8)", "rgba(255,127,14,0.8)", "rgba(44,160,44,0.8)", "rgba(214,39,40,0.8)",
    "rgba(148,103,189,0.8)", "rgba(140,86,75,0.8)", "rgba(227,119,194,0.8)", "rgba(127,127,127,0.8)",
    "rgba(188,189,34,0.8)", "rgba(23,190,207,0.8)", "rgba(174,199,232,0.8)", "rgba(255,187,120,0.8)",
    "rgba(152,223,138,0.8)", "rgba(255,152,150,0.8)", "rgba(197,176,213,0.8)", "rgba(196,156,148,0.8)",
]


class ImpactRepartitionSankey:
    def __init__(self, system, aggregation_threshold_percent=1, node_label_max_length=13):
        self.system = system
        self.aggregation_threshold_percent = aggregation_threshold_percent
        self.node_label_max_length = node_label_max_length
        self.node_labels = []
        self.full_node_labels = []
        self.node_indices = {}
        self.node_color_keys = []  # object id or structural key, for consistent coloring
        self.node_objects = {}
        self.aggregated_node_members = {}
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self.node_total_kg = []
        self._built = False
        self._total_system_kg = 0

    def _truncate_node_label(self, label):
        if self.node_label_max_length is None or len(label) <= self.node_label_max_length:
            return label
        return f"{label[:self.node_label_max_length].strip()}..."

    def _add_node(self, label, key, color_key=None, obj=None):
        if key in self.node_indices:
            return self.node_indices[key]
        idx = len(self.node_labels)
        self.node_labels.append(self._truncate_node_label(label))
        self.full_node_labels.append(label)
        self.node_indices[key] = idx
        self.node_color_keys.append(color_key or label)
        self.node_total_kg.append(0.0)
        if obj is not None:
            self.node_objects[idx] = obj
        return idx

    def _add_link(self, source, target, value_tonnes):
        if value_tonnes > 0:
            self.link_sources.append(source)
            self.link_targets.append(target)
            self.link_values.append(value_tonnes)
            self.node_total_kg[target] += value_tonnes * 1000

    @staticmethod
    def _get_fraction_magnitude(fraction):
        if isinstance(fraction, EmptyExplainableObject):
            return 0.0
        if isinstance(fraction, ExplainableHourlyQuantities):
            return float(fraction.mean().magnitude)
        return float(fraction.magnitude)

    def _expand_impact_repartition(self, node_idx, obj, total_tonnes, footprint_type, ancestor_ids=None):
        if not hasattr(obj, "impact_repartition"):
            return
        ancestor_ids = set() if ancestor_ids is None else ancestor_ids
        if obj.id in ancestor_ids:
            return
        next_ancestor_ids = ancestor_ids | {obj.id}
        for child_obj, fraction in obj.impact_repartition.items():
            child_value = total_tonnes * self._get_fraction_magnitude(fraction)
            if child_value <= 0:
                continue
            child_key = (child_obj.id, footprint_type)
            child_idx = self._add_node(child_obj.name, child_key, color_key=child_obj.id, obj=child_obj)
            self._add_link(node_idx, child_idx, child_value)
            self._expand_impact_repartition(
                child_idx, child_obj, child_value, footprint_type, ancestor_ids=next_ancestor_ids)

    def build(self):
        if self._built:
            return
        self._built = True
        system = self.system

        total_fab_dict = system.total_fabrication_footprint_sum_over_period
        total_energy_dict = system.total_energy_footprint_sum_over_period

        total_fab_kg = sum(
            v.magnitude for v in total_fab_dict.values() if not isinstance(v, EmptyExplainableObject))
        total_energy_kg = sum(
            v.magnitude for v in total_energy_dict.values() if not isinstance(v, EmptyExplainableObject))
        self._total_system_kg = total_fab_kg + total_energy_kg

        system_idx = self._add_node(system.name, ("system", "total"), color_key="__system__")
        self.node_total_kg[system_idx] = self._total_system_kg
        fab_idx = self._add_node("Fabrication", ("phase", "fabrication"), color_key="__fabrication__")
        energy_idx = self._add_node("Energy", ("phase", "energy"), color_key="__energy__")
        self._add_link(system_idx, fab_idx, total_fab_kg / 1000)
        self._add_link(system_idx, energy_idx, total_energy_kg / 1000)

        fab_by_obj = system.fabrication_footprint_sum_over_period
        energy_by_obj = system.energy_footprint_sum_over_period

        for phase_label, phase_idx, total_dict, obj_dict in [
            ("fabrication", fab_idx, total_fab_dict, fab_by_obj),
            ("energy", energy_idx, total_energy_dict, energy_by_obj),
        ]:
            for category, category_total in total_dict.items():
                cat_kg = category_total.magnitude if not isinstance(category_total, EmptyExplainableObject) else 0
                cat_tonnes = cat_kg / 1000
                if cat_tonnes <= 0:
                    continue
                cat_idx = self._add_node(
                    f"{category} {phase_label}", (category, phase_label), color_key=f"__cat_{category}__")
                self._add_link(phase_idx, cat_idx, cat_tonnes)

                for obj, obj_quantity in obj_dict[category].items():
                    obj_tonnes = obj_quantity.magnitude / 1000
                    if obj_tonnes <= 0:
                        continue
                    obj_key = (obj.id, phase_label)
                    obj_idx = self._add_node(obj.name, obj_key, color_key=obj.id, obj=obj)
                    self._add_link(cat_idx, obj_idx, obj_tonnes)
                    self._expand_impact_repartition(obj_idx, obj, obj_tonnes, phase_label)
        self._aggregate_small_nodes_by_column()

    def _get_footprint_type_for_node(self, node_idx):
        for key, idx in self.node_indices.items():
            if idx == node_idx:
                return key[1]
        return "unknown"

    def _compute_node_columns(self):
        if not self.link_sources:
            return {idx: 0 for idx in range(len(self.node_labels))}
        adjacency = {}
        incoming_count = {idx: 0 for idx in range(len(self.node_labels))}
        for source, target in zip(self.link_sources, self.link_targets):
            adjacency.setdefault(source, []).append(target)
            incoming_count[target] = incoming_count.get(target, 0) + 1
            incoming_count.setdefault(source, 0)
        root_nodes = [idx for idx, nb_incoming in incoming_count.items() if nb_incoming == 0]
        node_columns = {root_idx: 0 for root_idx in root_nodes}
        queue = list(root_nodes)
        while queue:
            node_idx = queue.pop(0)
            for child_idx in adjacency.get(node_idx, []):
                next_col = node_columns[node_idx] + 1
                if child_idx not in node_columns or next_col < node_columns[child_idx]:
                    node_columns[child_idx] = next_col
                    queue.append(child_idx)
        return node_columns

    def _aggregate_small_nodes_by_column(self):
        if self.aggregation_threshold_percent <= 0 or self._total_system_kg <= 0:
            return
        node_columns = self._compute_node_columns()
        threshold_kg = self._total_system_kg * self.aggregation_threshold_percent / 100
        aggregate_groups = {}
        for node_idx in self.node_objects:
            if self.node_total_kg[node_idx] >= threshold_kg:
                continue
            column = node_columns.get(node_idx)
            if column is None:
                continue
            aggregate_groups.setdefault(column, []).append(node_idx)
        aggregate_groups = {column: group for column, group in aggregate_groups.items() if len(group) >= 2}
        if not aggregate_groups:
            return

        original_node_keys = {idx: key for key, idx in self.node_indices.items()}
        original_full_labels = list(self.full_node_labels)
        original_color_keys = list(self.node_color_keys)
        original_node_objects = dict(self.node_objects)
        original_links = list(zip(self.link_sources, self.link_targets, self.link_values))
        original_node_total_kg = list(self.node_total_kg)
        nodes_to_aggregate = {node_idx for group in aggregate_groups.values() for node_idx in group}

        self.node_labels = []
        self.full_node_labels = []
        self.node_indices = {}
        self.node_color_keys = []
        self.node_objects = {}
        self.aggregated_node_members = {}
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self.node_total_kg = []

        old_to_new_indices = {}
        for old_idx, label in enumerate(original_full_labels):
            if old_idx in nodes_to_aggregate:
                continue
            new_idx = self._add_node(
                label, original_node_keys[old_idx], color_key=original_color_keys[old_idx], obj=original_node_objects.get(old_idx))
            old_to_new_indices[old_idx] = new_idx

        for column, group in aggregate_groups.items():
            group_members = sorted(group, key=lambda idx: original_node_total_kg[idx], reverse=True)
            aggregate_idx = self._add_node(
                f"Other ({len(group_members)})", ("__aggregated__", column), color_key=f"__aggregated__{column}")
            self.aggregated_node_members[aggregate_idx] = [
                (original_full_labels[idx], original_node_total_kg[idx]) for idx in group_members]
            for old_idx in group_members:
                old_to_new_indices[old_idx] = aggregate_idx

        combined_links = {}
        for source, target, value in original_links:
            new_source = old_to_new_indices[source]
            new_target = old_to_new_indices[target]
            if new_source == new_target:
                continue
            combined_links[(new_source, new_target)] = combined_links.get((new_source, new_target), 0) + value

        for (source, target), value in combined_links.items():
            self._add_link(source, target, value)

        for old_idx, new_idx in old_to_new_indices.items():
            if old_idx not in nodes_to_aggregate and original_node_total_kg[old_idx] > self.node_total_kg[new_idx]:
                self.node_total_kg[new_idx] = original_node_total_kg[old_idx]

    def _compute_node_colors(self):
        # Map each unique color_key to a consistent color
        unique_keys = list(dict.fromkeys(self.node_color_keys))
        key_to_color = {}
        # Fixed colors for structural nodes
        key_to_color["__system__"] = "rgba(100,100,100,0.8)"
        key_to_color["__fabrication__"] = "rgba(180,80,80,0.8)"
        key_to_color["__energy__"] = "rgba(80,120,180,0.8)"
        for key in unique_keys:
            if isinstance(key, str) and key.startswith("__aggregated__"):
                key_to_color[key] = "rgba(160,160,160,0.8)"
        color_idx = 0
        for key in unique_keys:
            if key not in key_to_color:
                key_to_color[key] = _COLORS[color_idx % len(_COLORS)]
                color_idx += 1
        return [key_to_color[k] for k in self.node_color_keys]

    def _build_hover_labels(self):
        node_hover = []
        for idx in range(len(self.node_labels)):
            kg = self.node_total_kg[idx]
            amount_str = display_co2_amount(format_co2_amount(kg))
            pct = (kg / self._total_system_kg * 100) if self._total_system_kg > 0 else 0
            if idx in self.aggregated_node_members:
                members_str = "<br>".join(
                    f"{label}: {display_co2_amount(format_co2_amount(member_kg))} CO2eq"
                    for label, member_kg in self.aggregated_node_members[idx])
                node_hover.append(
                    f"{self.full_node_labels[idx]}<br>{amount_str} CO2eq ({pct:.1f}%)<br><br>Aggregated objects:<br>{members_str}")
                continue
            node_hover.append(f"{self.full_node_labels[idx]}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return node_hover

    def _build_link_labels(self):
        link_labels = []
        for i in range(len(self.link_values)):
            kg = self.link_values[i] * 1000
            amount_str = display_co2_amount(format_co2_amount(kg))
            pct = (kg / self._total_system_kg * 100) if self._total_system_kg > 0 else 0
            src_label = self.full_node_labels[self.link_sources[i]]
            tgt_label = self.full_node_labels[self.link_targets[i]]
            link_labels.append(f"{src_label} → {tgt_label}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return link_labels

    def figure(self, title=None, width=1800):
        import plotly.graph_objects as go
        self.build()

        if title is None:
            title = (f"{self.system.name} impact repartition: "
                     f"{display_co2_amount(format_co2_amount(self._total_system_kg))} CO2eq")

        node_hover = self._build_hover_labels()
        link_labels = self._build_link_labels()
        node_colors = self._compute_node_colors()
        link_colors = [node_colors[src].replace("0.8)", "0.3)") for src in self.link_sources]

        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                label=self.node_labels, pad=20, thickness=20, color=node_colors,
                customdata=node_hover, hovertemplate="%{customdata}<extra></extra>",
            ),
            link=dict(
                source=self.link_sources, target=self.link_targets, value=self.link_values,
                color=link_colors, customdata=link_labels, hovertemplate="%{customdata}<extra></extra>",
            ),
        )])
        fig.update_layout(title_text=title, font_size=12, height=800, width=width)
        return fig


if __name__ == '__main__':
    test = "json"
    if test == "service":
        from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
        system, start_date = IntegrationTestServicesBaseClass.generate_system_with_services()
    elif test == "edge":
        from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass
        system, start_date = IntegrationTestSimpleEdgeSystemBaseClass.generate_simple_edge_system()
        print(system.edge_usage_patterns[0].attributed_fabrication_footprint.sum())
        print(system.edge_usage_patterns[0].attributed_energy_footprint.sum())
    elif test == "json":
        from efootprint.api_utils.json_to_system import json_to_system
        import json
        with open("scenarioC_smart_building_system.json", "r") as f:
            json_data = json.load(f)
        class_obj_dict, flat_obj_dict = json_to_system(json_data)
        system = next(iter(class_obj_dict["System"].values()))
    sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=1)
    fig = sankey.figure()
    fig.show()
