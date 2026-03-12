from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.tools import format_co2_amount, display_co2_amount, time_it

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
            skipped_impact_repartition_classes=None,
            skip_phase_footprint_split=False, skip_object_category_footprint_split=False,
            skip_object_footprint_split=False, excluded_object_types=None, lifecycle_phase_filter=None,
            display_column_information=True):
        self.system = system
        self.aggregation_threshold_percent = aggregation_threshold_percent
        self.node_label_max_length = node_label_max_length
        self.skipped_impact_repartition_classes = skipped_impact_repartition_classes or []
        self.skip_phase_footprint_split = skip_phase_footprint_split
        self.skip_object_category_footprint_split = skip_object_category_footprint_split
        self.skip_object_footprint_split = skip_object_footprint_split
        self.excluded_object_types = excluded_object_types or []
        self.lifecycle_phase_filter = lifecycle_phase_filter
        self.display_column_information = display_column_information
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
        self._built = False
        self._total_system_kg = 0
        self._manual_column_information = []
        self._impact_repartition_start_column = 0
        self._node_columns = {}
        self._spacer_nodes = set()
        self._spacer_original_source = {}
        self._category_node_indices = set()
        self._leaf_node_indices = set()
        self._post_leaf_node_indices = set()

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

    @staticmethod
    def _normalize_sankey_source(obj):
        from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
        from efootprint.core.hardware.edge.edge_component import EdgeComponent
        from efootprint.core.hardware.edge.edge_device import EdgeDevice

        if isinstance(obj, ExternalAPIServer):
            external_api = getattr(obj, "external_api", None)
            if isinstance(external_api, ExternalAPI):
                return external_api
            for container in getattr(obj, "modeling_obj_containers", []):
                if isinstance(container, ExternalAPI):
                    return container
        if isinstance(obj, EdgeComponent):
            edge_device = getattr(obj, "edge_device", None)
            if isinstance(edge_device, EdgeDevice):
                return edge_device
        return obj

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

    def _is_excluded(self, obj):
        for excluded_class in self.excluded_object_types:
            if isinstance(excluded_class, str):
                obj_class_name = self._format_class_name(obj)
                if obj_class_name == excluded_class or obj.__class__.__name__ == excluded_class:
                    return True
                continue
            if isinstance(excluded_class, type) and isinstance(obj, excluded_class):
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
    def _get_value_kg(value):
        if isinstance(value, EmptyExplainableObject):
            return 0.0
        if isinstance(value, ExplainableHourlyQuantities):
            return float(value.sum().magnitude)
        return float(value.magnitude)

    def _get_phases(self):
        if self.lifecycle_phase_filter is not None:
            return [self.lifecycle_phase_filter]
        return [LifeCyclePhases.MANUFACTURING, LifeCyclePhases.USAGE]

    def _get_phase_context(self, phase):
        if self.skip_phase_footprint_split:
            return None
        return phase.value

    def _get_phase_total_kg(self, root, root_footprint, phase):
        if self.excluded_object_types:
            return self._sum_leaf_values(root, phase, set())
        return sum(self._get_value_kg(v) for s, v in root_footprint[phase].items() if not self._is_excluded(s))

    def _sum_leaf_values(self, obj, phase, visited):
        if obj.id in visited:
            return 0
        next_visited = visited | {obj.id}
        total = 0
        for original_source, value in obj.attributed_footprint_per_source[phase].items():
            source = self._normalize_sankey_source(original_source)
            if original_source is not source and self._is_excluded(original_source):
                continue
            if self._is_excluded(source):
                continue
            value_kg = self._get_value_kg(value)
            if source.is_impact_source:
                total += value_kg
            else:
                total += self._sum_leaf_values(source, phase, next_visited)
        return total

    def _traverse(self, obj, phase, phase_context, parent_idx, visited):
        if obj.id in visited:
            return
        next_visited = visited | {obj.id}
        footprint_dict = obj.attributed_footprint_per_source[phase]
        for original_source, value in footprint_dict.items():
            source = self._normalize_sankey_source(original_source)
            if original_source is not source and self._is_excluded(original_source):
                continue
            if self._is_excluded(source):
                continue
            value_kg = self._get_value_kg(value)
            if self.excluded_object_types and not source.is_impact_source:
                value_kg = self._sum_leaf_values(source, phase, next_visited)
            if value_kg <= 0:
                continue
            if source.is_impact_source:
                self._handle_impact_source(source, value_kg, phase_context, parent_idx, original_source=original_source)
                continue
            if self._should_skip_object(source):
                self._traverse(source, phase, phase_context, parent_idx, next_visited)
                continue
            source_key = (source.id, phase_context)
            source_idx = self._add_node(source.name, source_key, color_key=source.id, obj=source)
            if parent_idx is not None:
                self._add_link(parent_idx, source_idx, value_kg / 1000)
            else:
                self.node_total_kg[source_idx] += value_kg
            self._traverse(source, phase, phase_context, source_idx, next_visited)

    def _handle_impact_source(self, source, value_kg, phase_context, parent_idx, original_source=None):
        from efootprint.core.hardware.edge.edge_component import EdgeComponent
        from efootprint.core.hardware.edge.edge_device import EdgeDevice
        from efootprint.all_classes_in_order import OBJECT_CATEGORIES
        leaf_parent_idx = parent_idx
        if not self.skip_object_category_footprint_split:
            category_name = None
            for cat_name, cat_classes in OBJECT_CATEGORIES.items():
                if any(isinstance(source, cls) for cls in cat_classes):
                    category_name = cat_name
                    break
            if category_name:
                category_label = f"{category_name} {phase_context}" if phase_context is not None else category_name
                cat_key = (category_name, phase_context)
                cat_idx = self._add_node(
                    category_label, cat_key, color_key=f"__cat_{category_name}__")
                self._category_node_indices.add(cat_idx)
                if parent_idx is not None:
                    self._add_link(parent_idx, cat_idx, value_kg / 1000)
                else:
                    self.node_total_kg[cat_idx] += value_kg
                leaf_parent_idx = cat_idx
        skip_source = self._should_skip_object(source)
        if not self.skip_object_footprint_split:
            source_idx = leaf_parent_idx
            if not skip_source:
                source_key = (source.id, phase_context)
                source_idx = self._add_node(source.name, source_key, color_key=source.id, obj=source)
                self._leaf_node_indices.add(source_idx)
                if leaf_parent_idx is not None:
                    self._add_link(leaf_parent_idx, source_idx, value_kg / 1000)
                else:
                    self.node_total_kg[source_idx] += value_kg
            if (
                original_source is not None and original_source is not source
                and isinstance(original_source, EdgeComponent) and isinstance(source, EdgeDevice)
                and not self._should_skip_object(original_source)
            ):
                component_key = (original_source.id, phase_context)
                component_idx = self._add_node(
                    original_source.name, component_key, color_key=original_source.id, obj=original_source)
                self._post_leaf_node_indices.add(component_idx)
                if source_idx is not None:
                    self._add_link(source_idx, component_idx, value_kg / 1000)
                else:
                    self.node_total_kg[component_idx] += value_kg

    @time_it
    def build(self):
        if self._built:
            return
        self._built = True
        self._manual_column_information = []
        self._node_columns = {}
        self._spacer_nodes = set()
        self._spacer_original_source = {}
        self._category_node_indices = set()
        self._leaf_node_indices = set()
        self._post_leaf_node_indices = set()

        root = self.system
        phases = self._get_phases()
        root_footprint = root.attributed_footprint_per_source

        # Compute total (excluding excluded types via recursive leaf sum)
        if self.excluded_object_types:
            self._total_system_kg = sum(self._sum_leaf_values(root, phase, set()) for phase in phases)
        else:
            self._total_system_kg = 0
            for phase in phases:
                for source, value in root_footprint[phase].items():
                    self._total_system_kg += self._get_value_kg(value)

        current_column_index = 1
        root_is_skipped = self._should_skip_object(root)
        root_idx = None
        if not root_is_skipped:
            root_idx = self._add_node(root.name, ("root", "total"), color_key="__system__", obj=root)
            self.node_total_kg[root_idx] = self._total_system_kg
            self._node_columns[root_idx] = current_column_index
            current_column_index += 1

        # Phase split
        phase_parents = {}
        if not self.skip_phase_footprint_split and len(phases) > 1:
            for phase in phases:
                color_key = "__fabrication__" if phase == LifeCyclePhases.MANUFACTURING else "__energy__"
                phase_idx = self._add_node(phase.value, ("phase", phase.value), color_key=color_key)
                self._node_columns[phase_idx] = current_column_index
                phase_kg = self._get_phase_total_kg(root, root_footprint, phase)
                if root_idx is not None:
                    self._add_link(root_idx, phase_idx, phase_kg / 1000)
                else:
                    self.node_total_kg[phase_idx] = phase_kg
                phase_parents[phase] = phase_idx
            self._manual_column_information.append({
                "column_index": current_column_index,
                "column_type": "manual_split",
                "description": "Manufacturing / usage footprint",
            })
            current_column_index += 1
        else:
            for phase in phases:
                phase_parents[phase] = root_idx

        self._impact_repartition_start_column = current_column_index

        # Traverse from root for each phase
        for phase in phases:
            parent_idx = phase_parents[phase]
            phase_context = self._get_phase_context(phase)
            self._traverse(root, phase, phase_context, parent_idx, visited=set())

        self._assign_columns()
        self._assign_category_and_leaf_columns()
        self._aggregate_small_nodes_by_column()
        self._insert_spacer_nodes()

    def _assign_columns(self):
        from efootprint.all_classes_in_order import SANKEY_COLUMNS

        node_to_group = {}
        for node_idx, obj in self.node_objects.items():
            if node_idx in self._node_columns:
                continue
            if (node_idx in self._category_node_indices or node_idx in self._leaf_node_indices
                    or node_idx in self._post_leaf_node_indices):
                continue
            for group_idx, group in enumerate(SANKEY_COLUMNS):
                if any(isinstance(obj, cls) for cls in group):
                    node_to_group[node_idx] = group_idx
                    break

        used_groups = sorted(set(node_to_group.values()))
        group_to_column = {g: self._impact_repartition_start_column + i for i, g in enumerate(used_groups)}
        for node_idx, group_idx in node_to_group.items():
            self._node_columns[node_idx] = group_to_column[group_idx]

        # Fallback for nodes not matching any SANKEY_COLUMNS group
        for node_idx in range(len(self.node_labels)):
            if node_idx in self._node_columns:
                continue
            if (node_idx in self._category_node_indices or node_idx in self._leaf_node_indices
                    or node_idx in self._post_leaf_node_indices):
                continue
            parent_cols = [
                self._node_columns[src]
                for src, tgt in zip(self.link_sources, self.link_targets)
                if tgt == node_idx and src in self._node_columns]
            if parent_cols:
                self._node_columns[node_idx] = max(parent_cols) + 1
            else:
                self._node_columns[node_idx] = self._impact_repartition_start_column

    def _assign_category_and_leaf_columns(self):
        if not self._category_node_indices and not self._leaf_node_indices and not self._post_leaf_node_indices:
            return
        max_col = max(self._node_columns.values()) if self._node_columns else self._impact_repartition_start_column - 1
        category_col = max_col + 1
        if self._category_node_indices:
            for cat_idx in self._category_node_indices:
                self._node_columns[cat_idx] = category_col
            self._manual_column_information.append({
                "column_index": category_col,
                "column_type": "manual_split",
                "description": "Per object category footprint",
            })
        leaf_col = (category_col + 1) if self._category_node_indices else category_col
        post_leaf_col = leaf_col + 1
        leaf_nodes_with_post_leaf_children = {
            source for source, target in zip(self.link_sources, self.link_targets) if target in self._post_leaf_node_indices
        }
        if self._leaf_node_indices:
            for leaf_idx in self._leaf_node_indices:
                if self._post_leaf_node_indices and leaf_idx not in leaf_nodes_with_post_leaf_children:
                    self._node_columns[leaf_idx] = post_leaf_col
                else:
                    self._node_columns[leaf_idx] = leaf_col
        if self._post_leaf_node_indices:
            for node_idx in self._post_leaf_node_indices:
                self._node_columns[node_idx] = post_leaf_col

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

    def _aggregate_small_nodes_by_column(self):
        if self.aggregation_threshold_percent <= 0 or self._total_system_kg <= 0:
            return
        threshold_kg = self._total_system_kg * self.aggregation_threshold_percent / 100
        aggregate_groups = {}
        for node_idx in range(len(self.node_labels)):
            if self.node_total_kg[node_idx] >= threshold_kg:
                continue
            column = self._node_columns.get(node_idx)
            if column is None:
                continue
            aggregate_groups.setdefault(column, []).append(node_idx)
        aggregate_groups = {group_key: group for group_key, group in aggregate_groups.items() if len(group) >= 2}
        if not aggregate_groups:
            return

        original_node_keys = {idx: key for key, idx in self.node_indices.items()}
        original_full_labels = list(self.full_node_labels)
        original_color_keys = list(self.node_color_keys)
        original_node_objects = dict(self.node_objects)
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
                label, original_node_keys[old_idx], color_key=original_color_keys[old_idx],
                obj=original_node_objects.get(old_idx))
            old_to_new_indices[old_idx] = new_idx
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
        incoming_by_target = {}
        outgoing_by_source = {}
        for source, target in zip(self.link_sources, self.link_targets):
            incoming_by_target.setdefault(target, []).append(source)
            outgoing_by_source.setdefault(source, []).append(target)

        def resolve_visible_source(node_idx):
            current = node_idx
            visited = set()
            while current in self._spacer_nodes and current not in visited:
                visited.add(current)
                incoming = incoming_by_target.get(current, [])
                if not incoming:
                    break
                current = incoming[0]
            return current

        def resolve_visible_target(node_idx):
            current = node_idx
            visited = set()
            while current in self._spacer_nodes and current not in visited:
                visited.add(current)
                outgoing = outgoing_by_source.get(current, [])
                if not outgoing:
                    break
                current = outgoing[0]
            return current

        link_labels = []
        for i in range(len(self.link_values)):
            kg = self.link_values[i] * 1000
            amount_str = display_co2_amount(format_co2_amount(kg))
            pct = (kg / self._total_system_kg * 100) if self._total_system_kg > 0 else 0
            src_idx = resolve_visible_source(self.link_sources[i])
            tgt_idx = resolve_visible_target(self.link_targets[i])
            src_label = self.full_node_labels[src_idx]
            tgt_label = self.full_node_labels[tgt_idx]
            link_labels.append(f"{src_label} → {tgt_label}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return link_labels

    def _column_x_center(self, column):
        min_col = min(self._node_columns.values())
        max_col = max(self._node_columns.values())
        if max_col == min_col:
            return 0.5
        return 0.006 + (column - min_col) / (max_col + 0.09 - min_col)

    def get_column_metadata(self):
        if not self._built:
            self.build()
        if not self._node_columns:
            return []

        classes_by_column = {}
        for node_idx, column in self._node_columns.items():
            if node_idx in self._spacer_nodes:
                continue
            if node_idx in self.node_objects:
                classes_by_column.setdefault(column, set()).add(self._format_class_name(self.node_objects[node_idx]))
            if node_idx in self.aggregated_node_classes:
                classes_by_column.setdefault(column, set()).update(self.aggregated_node_classes[node_idx])

        if not classes_by_column:
            return []

        return [{
            "column_index": column,
            "x_center": self._column_x_center(column),
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
            if column_metadata["column_index"] >= self._impact_repartition_start_column
            and not any(column_metadata["column_index"] == info["column_index"]
                        for info in self._manual_column_information)]

    def _build_column_information_text(self):
        column_information = sorted(
            self.get_column_information(), key=lambda column_info: column_info["column_index"])
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

    def _get_displayed_column_information(self):
        if not self._built:
            self.build()
        manual_columns = {
            info["column_index"]: dict(info) for info in self._manual_column_information}
        displayed_columns = {}
        for column_index, info in manual_columns.items():
            displayed_columns[column_index] = {
                "column_index": column_index,
                "column_type": info["column_type"],
                "description": info["description"],
            }
        for metadata in self.get_column_metadata():
            if metadata["column_index"] in displayed_columns:
                continue
            displayed_columns[metadata["column_index"]] = {
                "column_index": metadata["column_index"],
                "column_type": "impact_repartition",
                "class_names": metadata["class_names"],
            }
        return [displayed_columns[column_index] for column_index in sorted(displayed_columns)]

    @staticmethod
    def _format_column_header_text(column_info):
        if column_info["column_type"] == "manual_split":
            return column_info["description"]
        return "<br>".join(column_info["class_names"])

    def _build_column_header_annotations(self):
        annotations = []
        max_line_count = 0
        for column_info in self._get_displayed_column_information():
            text = self._format_column_header_text(column_info)
            max_line_count = max(max_line_count, text.count("<br>") + 1)
            annotations.append(dict(
                x=self._column_x_center(column_info["column_index"]), y=1.03, xref="paper", yref="paper",
                xanchor="center", yanchor="bottom", align="center", showarrow=False, text=text,
                font=dict(size=11), bordercolor="rgba(210,210,210,1)", borderwidth=1, borderpad=4,
                bgcolor="rgba(250,250,250,0.95)",
            ))
        return annotations, max_line_count

    @time_it
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
        top_margin = 100
        if column_information_text is not None:
            column_annotations, max_line_count = self._build_column_header_annotations()
            top_margin = 110 + 20 * max_line_count
            for annotation in column_annotations:
                fig.add_annotation(**annotation)
        fig.update_layout(
            title=dict(text=title, pad=dict(b=24)),
            font_size=12, height=800, width=width, margin=dict(t=top_margin, b=100))
        return fig


if __name__ == '__main__':
    from efootprint.core.hardware.edge.edge_component import EdgeComponent
    from efootprint.core.usage.job import JobBase
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkloadNeed
    from efootprint.core.system import System
    from efootprint.core.country import Country
    from efootprint.core.hardware.device import Device
    from efootprint.core.hardware.edge.edge_device import EdgeDevice
    test = "json"
    json_files = ["basic-model.json", "basic-2.json", "chatbot-efootprint-model.json",
                  "scenarioC_smart_building_system.json", "basic-edge.json", "curling.json", "smart building test.json"]
    skipped_impact_repartition_classes__full = [
        System, Country, EdgeComponent, JobBase, RecurrentEdgeDeviceNeed, RecurrentServerNeed,
        RecurrentEdgeComponentNeed, RecurrentEdgeWorkloadNeed]
    skipped_impact_repartition_classes = [
        System, JobBase, RecurrentEdgeDeviceNeed, RecurrentServerNeed, RecurrentEdgeComponentNeed]
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
        with open(json_files[-1], "r") as f:
            json_data = json.load(f)
        class_obj_dict, flat_obj_dict = json_to_system(json_data)
        system = next(iter(class_obj_dict["System"].values()))
    sankey = ImpactRepartitionSankey(
        system, aggregation_threshold_percent=1,
        skipped_impact_repartition_classes=[System],
        skip_phase_footprint_split=False, skip_object_category_footprint_split=False,
        skip_object_footprint_split=False, excluded_object_types=None, lifecycle_phase_filter=LifeCyclePhases.USAGE,
        display_column_information=True
    )
    fig = sankey.figure()
    fig.show()
