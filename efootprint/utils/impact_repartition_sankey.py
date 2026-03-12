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
    def __init__(
            self, system, aggregation_threshold_percent=1.0, node_label_max_length=15,
            skipped_impact_repartition_classes=None, skip_total_footprint_split=True,
            skip_phase_footprint_split=False, skip_object_category_footprint_split=False,
            skip_object_footprint_split=False,
            display_column_information=True):
        self.system = system
        self.aggregation_threshold_percent = aggregation_threshold_percent
        self.node_label_max_length = node_label_max_length
        self.skipped_impact_repartition_classes = skipped_impact_repartition_classes or []
        self.skip_total_footprint_split = skip_total_footprint_split
        self.skip_phase_footprint_split = skip_phase_footprint_split
        self.skip_object_category_footprint_split = skip_object_category_footprint_split
        self.skip_object_footprint_split = skip_object_footprint_split
        self.display_column_information = display_column_information
        self.node_labels = []
        self.full_node_labels = []
        self.node_indices = {}
        self.node_color_keys = []  # object id or structural key, for consistent coloring
        self.node_objects = {}
        self.aggregated_node_members = {}
        self.aggregated_node_classes = {}
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self._link_index_by_edge = {}
        self.node_total_kg = []
        self._built = False
        self._total_system_kg = 0
        self._manual_column_information = []
        self._impact_repartition_start_column = 0
        self._node_columns = {}
        self._spacer_nodes = set()
        self._spacer_original_source = {}

    def _truncate_node_label(self, label):
        if self.node_label_max_length is None or len(label) <= self.node_label_max_length:
            return label
        return f"{label[:self.node_label_max_length].strip()}..."

    @staticmethod
    def _format_class_name(obj):
        class_name = getattr(obj, "class_as_simple_str", None)
        if isinstance(class_name, str) and class_name:
            return class_name
        return obj.__class__.__name__.lstrip("_")

    def _should_skip_object(self, obj):
        obj_class_name = self._format_class_name(obj)
        for skipped_class in self.skipped_impact_repartition_classes:
            if isinstance(skipped_class, str):
                if obj_class_name == skipped_class or obj.__class__.__name__ == skipped_class:
                    return True
                continue
            if isinstance(skipped_class, type) and isinstance(obj, skipped_class):
                return True
        return False

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
            edge = (source, target)
            existing_link_idx = self._link_index_by_edge.get(edge)
            if existing_link_idx is None:
                self._link_index_by_edge[edge] = len(self.link_sources)
                self.link_sources.append(source)
                self.link_targets.append(target)
                self.link_values.append(value_tonnes)
            else:
                self.link_values[existing_link_idx] += value_tonnes
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
            self._add_object_impact_to_sankey(
                node_idx, child_obj, child_value, footprint_type, ancestor_ids=next_ancestor_ids)

    def _add_object_impact_to_sankey(
            self, source_idx, obj, total_tonnes, footprint_type, ancestor_ids=None, skip_current_object=False):
        if total_tonnes <= 0:
            return
        ancestor_ids = set() if ancestor_ids is None else ancestor_ids
        if obj.id in ancestor_ids:
            return
        if skip_current_object or self._should_skip_object(obj):
            self._expand_impact_repartition(source_idx, obj, total_tonnes, footprint_type, ancestor_ids=ancestor_ids)
            return

        obj_key = (obj.id, footprint_type)
        obj_idx = self._add_node(obj.name, obj_key, color_key=obj.id, obj=obj)
        self._add_link(source_idx, obj_idx, total_tonnes)
        self._expand_impact_repartition(obj_idx, obj, total_tonnes, footprint_type, ancestor_ids=ancestor_ids)

    def build(self):
        if self._built:
            return
        self._built = True
        self._manual_column_information = []
        self._node_columns = {}
        self._spacer_nodes = set()
        self._spacer_original_source = {}
        system = self.system

        total_fab_dict = system.total_fabrication_footprint_sum_over_period
        total_energy_dict = system.total_energy_footprint_sum_over_period

        total_fab_kg = sum(
            v.magnitude for v in total_fab_dict.values() if not isinstance(v, EmptyExplainableObject))
        total_energy_kg = sum(
            v.magnitude for v in total_energy_dict.values() if not isinstance(v, EmptyExplainableObject))
        self._total_system_kg = total_fab_kg + total_energy_kg

        phase_parents = {"fabrication": None, "energy": None}
        current_column_index = 1
        if not self.skip_total_footprint_split:
            system_idx = self._add_node(system.name, ("system", "total"), color_key="__system__")
            self.node_total_kg[system_idx] = self._total_system_kg
            self._node_columns[system_idx] = current_column_index
            phase_parents = {"fabrication": system_idx, "energy": system_idx}
            self._manual_column_information.append({
                "column_index": current_column_index,
                "column_type": "manual_split",
                "description": "Full system footprint",
            })
            current_column_index += 1

        if not self.skip_phase_footprint_split:
            fab_idx = self._add_node("Fabrication", ("phase", "fabrication"), color_key="__fabrication__")
            energy_idx = self._add_node("Energy", ("phase", "energy"), color_key="__energy__")
            self._node_columns[fab_idx] = current_column_index
            self._node_columns[energy_idx] = current_column_index
            if phase_parents["fabrication"] is not None:
                self._add_link(phase_parents["fabrication"], fab_idx, total_fab_kg / 1000)
            if phase_parents["energy"] is not None:
                self._add_link(phase_parents["energy"], energy_idx, total_energy_kg / 1000)
            phase_parents["fabrication"] = fab_idx
            phase_parents["energy"] = energy_idx
            self._manual_column_information.append({
                "column_index": current_column_index,
                "column_type": "manual_split",
                "description": "Fabrication / energy footprint",
            })
            current_column_index += 1

        fab_by_obj = system.fabrication_footprint_sum_over_period
        energy_by_obj = system.energy_footprint_sum_over_period
        category_nodes_created = False

        for phase_label, total_dict, obj_dict in [
            ("fabrication", total_fab_dict, fab_by_obj),
            ("energy", total_energy_dict, energy_by_obj),
        ]:
            phase_parent_idx = phase_parents[phase_label]
            for category, category_total in total_dict.items():
                cat_kg = category_total.magnitude if not isinstance(category_total, EmptyExplainableObject) else 0
                cat_tonnes = cat_kg / 1000
                if cat_tonnes <= 0:
                    continue
                object_parent_idx = phase_parent_idx
                if not self.skip_object_category_footprint_split:
                    cat_idx = self._add_node(
                        f"{category} {phase_label}", (category, phase_label), color_key=f"__cat_{category}__")
                    self._node_columns[cat_idx] = current_column_index
                    if phase_parent_idx is not None:
                        self._add_link(phase_parent_idx, cat_idx, cat_tonnes)
                    object_parent_idx = cat_idx
                    category_nodes_created = True

                for obj, obj_quantity in obj_dict[category].items():
                    obj_tonnes = obj_quantity.magnitude / 1000
                    if obj_tonnes <= 0:
                        continue
                    self._add_object_impact_to_sankey(
                        object_parent_idx, obj, obj_tonnes, phase_label,
                        skip_current_object=self.skip_object_footprint_split)
        if category_nodes_created:
            self._manual_column_information.append({
                "column_index": current_column_index,
                "column_type": "manual_split",
                "description": "Per object category footprint",
            })
            current_column_index += 1
        self._impact_repartition_start_column = current_column_index
        self._assign_columns()
        self._aggregate_small_nodes_by_column()
        self._insert_spacer_nodes()

    def _assign_columns(self):
        from efootprint.all_classes_in_order import SANKEY_COLUMNS

        # Find SANKEY_COLUMNS group for each impact repartition node
        node_to_group = {}
        for node_idx, obj in self.node_objects.items():
            if node_idx in self._node_columns:
                continue
            for group_idx, group in enumerate(SANKEY_COLUMNS):
                if any(isinstance(obj, cls) for cls in group):
                    node_to_group[node_idx] = group_idx
                    break

        # Compress: only used groups get column numbers
        used_groups = sorted(set(node_to_group.values()))
        group_to_column = {g: self._impact_repartition_start_column + i for i, g in enumerate(used_groups)}
        for node_idx, group_idx in node_to_group.items():
            self._node_columns[node_idx] = group_to_column[group_idx]

        # Fallback for nodes not matching any SANKEY_COLUMNS group (e.g. test _DummyObjects)
        for node_idx in range(len(self.node_labels)):
            if node_idx in self._node_columns:
                continue
            parent_cols = [
                self._node_columns[src]
                for src, tgt in zip(self.link_sources, self.link_targets)
                if tgt == node_idx and src in self._node_columns]
            if parent_cols:
                self._node_columns[node_idx] = max(parent_cols) + 1
            else:
                self._node_columns[node_idx] = self._impact_repartition_start_column

    def _insert_spacer_nodes(self):
        original_links = list(zip(self.link_sources, self.link_targets, self.link_values))
        incoming_nodes = set(self.link_targets)
        root_total_kg = {
            idx: self.node_total_kg[idx]
            for idx in range(len(self.node_labels))
            if idx not in incoming_nodes and self.node_total_kg[idx] > 0}

        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self._link_index_by_edge = {}
        self.node_total_kg = [0.0] * len(self.node_labels)
        for idx, kg in root_total_kg.items():
            self.node_total_kg[idx] = kg

        for source, target, value in original_links:
            src_col = self._node_columns.get(source)
            tgt_col = self._node_columns.get(target)
            if src_col is not None and tgt_col is not None and tgt_col > src_col + 1:
                prev_idx = source
                for col in range(src_col + 1, tgt_col):
                    spacer_key = ("__spacer__", source, target, col)
                    spacer_idx = self._add_node("", spacer_key, color_key=self.node_color_keys[source])
                    self._node_columns[spacer_idx] = col
                    self._spacer_nodes.add(spacer_idx)
                    self._spacer_original_source[spacer_idx] = source
                    self._add_link(prev_idx, spacer_idx, value)
                    prev_idx = spacer_idx
                self._add_link(prev_idx, target, value)
            else:
                self._add_link(source, target, value)

    def _compute_node_columns(self):
        return dict(self._node_columns)

    def _aggregate_small_nodes_by_column_once(self):
        if self.aggregation_threshold_percent <= 0 or self._total_system_kg <= 0:
            return False
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
        aggregate_groups = {group_key: group for group_key, group in aggregate_groups.items() if len(group) >= 2}
        if not aggregate_groups:
            return False

        original_node_keys = {idx: key for key, idx in self.node_indices.items()}
        original_full_labels = list(self.full_node_labels)
        original_color_keys = list(self.node_color_keys)
        original_node_objects = dict(self.node_objects)
        original_aggregated_node_members = dict(self.aggregated_node_members)
        original_aggregated_node_classes = dict(self.aggregated_node_classes)
        original_links = list(zip(self.link_sources, self.link_targets, self.link_values))
        original_node_total_kg = list(self.node_total_kg)
        original_node_columns = dict(self._node_columns)
        nodes_to_aggregate = {node_idx for group in aggregate_groups.values() for node_idx in group}

        self.node_labels = []
        self.full_node_labels = []
        self.node_indices = {}
        self.node_color_keys = []
        self.node_objects = {}
        self.aggregated_node_members = {}
        self.aggregated_node_classes = {}
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self._link_index_by_edge = {}
        self.node_total_kg = []
        self._node_columns = {}

        old_to_new_indices = {}
        for old_idx, label in enumerate(original_full_labels):
            if old_idx in nodes_to_aggregate:
                continue
            new_idx = self._add_node(
                label, original_node_keys[old_idx], color_key=original_color_keys[old_idx], obj=original_node_objects.get(old_idx))
            old_to_new_indices[old_idx] = new_idx
            if old_idx in original_aggregated_node_members:
                self.aggregated_node_members[new_idx] = list(original_aggregated_node_members[old_idx])
            if old_idx in original_aggregated_node_classes:
                self.aggregated_node_classes[new_idx] = list(original_aggregated_node_classes[old_idx])
            if old_idx in original_node_columns:
                self._node_columns[new_idx] = original_node_columns[old_idx]

        for column, group in aggregate_groups.items():
            group_members = sorted(group, key=lambda idx: original_node_total_kg[idx], reverse=True)
            aggregate_idx = self._add_node(
                f"Other ({len(group_members)})",
                ("__aggregated__", column),
                color_key=f"__aggregated__{column}")
            self.aggregated_node_members[aggregate_idx] = [
                (original_full_labels[idx], original_node_total_kg[idx]) for idx in group_members]
            self.aggregated_node_classes[aggregate_idx] = sorted({
                self._format_class_name(original_node_objects[idx])
                for idx in group_members
                if idx in original_node_objects
            })
            self._node_columns[aggregate_idx] = column
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
        return True

    def _aggregate_small_nodes_by_column(self):
        while self._aggregate_small_nodes_by_column_once():
            pass

    def _compute_node_colors(self):
        unique_keys = list(dict.fromkeys(self.node_color_keys))
        key_to_color = {
            "__system__": "rgba(100,100,100,0.8)",
            "__fabrication__": "rgba(180,80,80,0.8)",
            "__energy__": "rgba(80,120,180,0.8)",
        }
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
            if idx in self._spacer_nodes:
                node_hover.append("")
                continue
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

    def get_column_metadata(self):
        if not self._built:
            self.build()
        node_columns = self._compute_node_columns()
        if not node_columns:
            return []

        classes_by_column = {}
        for node_idx, column in node_columns.items():
            if node_idx in self._spacer_nodes:
                continue
            if node_idx in self.node_objects:
                classes_by_column.setdefault(column, set()).add(self._format_class_name(self.node_objects[node_idx]))
            if node_idx in self.aggregated_node_classes:
                classes_by_column.setdefault(column, set()).update(self.aggregated_node_classes[node_idx])

        if not classes_by_column:
            return []

        max_column = max(node_columns.values())
        return [{
            "column_index": column,
            "x_center": 0.5 if max_column == 0 else (column + 0.5) / (max_column + 1),
            "class_names": sorted(class_names),
        } for column, class_names in sorted(classes_by_column.items()) if class_names]

    def get_column_information(self):
        if not self._built:
            self.build()
        return list(self._manual_column_information) + [{
            "column_index": column_metadata["column_index"],
            "column_type": "impact_repartition",
            "class_names": column_metadata["class_names"],
        } for column_metadata in self.get_column_metadata()
            if column_metadata["column_index"] >= self._impact_repartition_start_column]

    def _build_column_information_text(self):
        column_information = self.get_column_information()
        if not column_information:
            return None
        return "<br>".join([
            (
                f"Column {column_info['column_index']}: {column_info['description']}"
                if column_info["column_type"] == "manual_split"
                else f"Column {column_info['column_index']}: {', '.join(column_info['class_names'])}"
            )
            for column_info in column_information
        ])

    def figure(self, title=None, width=1800):
        import plotly.graph_objects as go
        self.build()

        if title is None:
            title = (f"{self.system.name} impact repartition: "
                     f"{display_co2_amount(format_co2_amount(self._total_system_kg))} CO2eq")

        node_hover = self._build_hover_labels()
        link_labels = self._build_link_labels()
        node_colors = self._compute_node_colors()
        link_colors = [
            node_colors[self._spacer_original_source.get(src, src)].replace("0.8)", "0.3)")
            for src in self.link_sources]
        # Spacer nodes: same transparency as links
        display_node_colors = [
            c.replace("0.8)", "0.3)") if i in self._spacer_nodes else c for i, c in enumerate(node_colors)]
        column_information_text = self._build_column_information_text() if self.display_column_information else None

        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                label=self.node_labels, pad=20, thickness=20, color=display_node_colors,
                line=dict(width=0),
                customdata=node_hover, hovertemplate="%{customdata}<extra></extra>",
            ),
            link=dict(
                source=self.link_sources, target=self.link_targets, value=self.link_values,
                color=link_colors, customdata=link_labels, hovertemplate="%{customdata}<extra></extra>",
            ),
        )])
        bottom_margin = 100
        if column_information_text is not None:
            line_count = column_information_text.count("<br>") + 1
            bottom_margin = 100 + 18 * line_count
            fig.add_annotation(
                x=0,
                y=-0.12,
                xref="paper",
                yref="paper",
                xanchor="left",
                yanchor="top",
                align="left",
                showarrow=False,
                text=column_information_text,
                font=dict(size=11),
            )
        fig.update_layout(title_text=title, font_size=12, height=800, width=width, margin=dict(b=bottom_margin))
        return fig


if __name__ == '__main__':
    from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
    from efootprint.core.usage.job import JobBase
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkloadNeed
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.country import Country
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.hardware.edge.edge_component import EdgeComponent
    from efootprint.core.hardware.device import Device
    test = "json"
    json_files = ["basic-model.json", "basic-2.json", "chatbot-efootprint-model.json",
                  "scenarioC_smart_building_system.json", "basic-edge.json", "curling.json"]
    skipped_impact_repartition_classes__full = [
        JobBase, EdgeWorkloadComponent, RecurrentEdgeDeviceNeed, RecurrentServerNeed, RecurrentEdgeComponentNeed, RecurrentEdgeWorkloadNeed]
    skipped_impact_repartition_classes = [
        JobBase, RecurrentEdgeDeviceNeed, RecurrentServerNeed, RecurrentEdgeComponentNeed]
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
        with open(json_files[3], "r") as f:
            json_data = json.load(f)
        class_obj_dict, flat_obj_dict = json_to_system(json_data)
        system = next(iter(class_obj_dict["System"].values()))
    sankey = ImpactRepartitionSankey(
        system, aggregation_threshold_percent=1, skipped_impact_repartition_classes=[])
    fig = sankey.figure()
    fig.show()
