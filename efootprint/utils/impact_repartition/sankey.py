import colorsys
import hashlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.impact_repartition._graph import SankeyGraph
from efootprint.utils.tools import display_co2_amount, format_co2_amount, time_it

ConfiguredClass: TypeAlias = type[ModelingObject] | str
NodeKey: TypeAlias = tuple[str, str | None] | tuple[str, str | int | None, int] | tuple[str, int, int, int]
ColumnInformation: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class _ResolvedFootprintSource:
    source: ModelingObject
    value_kg: float


class ImpactRepartitionSankey:
    _FIXED_KEY_COLORS = {
        "__system__": "rgba(100,100,100,0.8)",
        "__fabrication__": "rgba(180,80,80,0.8)",
        "__energy__": "rgba(80,120,180,0.8)",
    }

    def __init__(
            self,
            system: ModelingObject,
            aggregation_threshold_percent: float = 1.0,
            node_label_max_length: int | None = 15,
            skipped_impact_repartition_classes: Sequence[ConfiguredClass] | None = None,
            skip_phase_footprint_split: bool = False,
            skip_object_category_footprint_split: bool = False,
            skip_object_footprint_split: bool = False,
            excluded_object_types: Sequence[ConfiguredClass] | None = None,
            lifecycle_phase_filter: LifeCyclePhases | None = None,
            display_column_information: bool = True,
    ) -> None:
        self.system = system
        self.aggregation_threshold_percent = aggregation_threshold_percent
        self.node_label_max_length = node_label_max_length
        self.skipped_impact_repartition_classes: list[ConfiguredClass] = list(skipped_impact_repartition_classes or [])
        if "System" not in self.skipped_impact_repartition_classes:
            self.skipped_impact_repartition_classes.append("System")
        self.skip_phase_footprint_split = skip_phase_footprint_split
        self.skip_object_category_footprint_split = skip_object_category_footprint_split
        self.skip_object_footprint_split = skip_object_footprint_split
        self.excluded_object_types: list[ConfiguredClass] = list(excluded_object_types or [])
        self.lifecycle_phase_filter = lifecycle_phase_filter
        self.display_column_information = display_column_information
        self._graph = SankeyGraph(self._truncate_node_label)
        self.aggregated_node_members: dict[int, list[tuple[str, float]]] = {}
        self.aggregated_node_classes: dict[int, list[str]] = {}
        self._built: bool = False
        self._total_system_kg: float = 0
        self._manual_column_information: list[ColumnInformation] = []
        self._impact_repartition_start_column: int = 0
        self._node_columns: dict[int, int] = {}
        self._spacer_nodes: set[int] = set()
        self._spacer_original_source: dict[int, int] = {}
        self._category_node_indices: set[int] = set()
        self._leaf_node_indices: set[int] = set()
        self._breakdown_node_indices: set[int] = set()

    @property
    def node_labels(self) -> list[str]:
        return self._graph.node_labels

    @property
    def full_node_labels(self) -> list[str]:
        return self._graph.full_node_labels

    @property
    def node_indices(self) -> dict[Any, int]:
        return self._graph.node_indices

    @property
    def node_color_keys(self) -> list[str]:
        return self._graph.node_color_keys

    @property
    def node_objects(self) -> dict[int, ModelingObject]:
        return self._graph.node_objects

    @property
    def link_sources(self) -> list[int]:
        return self._graph.link_sources

    @property
    def link_targets(self) -> list[int]:
        return self._graph.link_targets

    @property
    def link_values(self) -> list[float]:
        return self._graph.link_values

    @property
    def node_total_kg(self) -> list[float]:
        return self._graph.node_total_kg

    @property
    def total_system_kg(self) -> float:
        return self._total_system_kg

    def _truncate_node_label(self, label: str) -> str:
        if self.node_label_max_length is None or len(label) <= self.node_label_max_length:
            return label
        return f"{label[:self.node_label_max_length].strip()}..."

    @staticmethod
    def _normalize_sankey_source(obj: ModelingObject) -> ModelingObject:
        from efootprint.builders.external_apis.external_api_base_class import ExternalAPIServer

        if isinstance(obj, ExternalAPIServer):
            return obj.external_api
        return obj

    def _matches_configured_class(self, obj: ModelingObject, configured_classes: Sequence[ConfiguredClass]) -> bool:
        def _resolve(cc):
            return ALL_EFOOTPRINT_CLASSES_DICT.get(cc) if isinstance(cc, str) else cc
        return any(isinstance(obj, cls) for cls in map(_resolve, configured_classes) if isinstance(cls, type))

    @staticmethod
    def _get_canonical_class_name(obj: ModelingObject) -> str:
        return obj.canonical_class.__name__

    @classmethod
    def _sort_class_names(cls, class_names: set[str]) -> list[str]:
        from efootprint.all_classes_in_order import CANONICAL_COMPUTATION_ORDER

        canonical_order = {
            canonical_class.__name__: index for index, canonical_class in enumerate(CANONICAL_COMPUTATION_ORDER)
        }
        return sorted(
            class_names,
            key=lambda class_name: (class_name not in canonical_order, canonical_order.get(class_name), class_name),
        )

    def _should_skip_object(self, obj: ModelingObject) -> bool:
        return self._matches_configured_class(obj, self.skipped_impact_repartition_classes)

    def _is_excluded(self, obj: ModelingObject) -> bool:
        return self._matches_configured_class(obj, self.excluded_object_types)

    def _reset_build_state(self) -> None:
        self._graph.reset()
        self.aggregated_node_members = {}
        self.aggregated_node_classes = {}
        self._total_system_kg = 0
        self._manual_column_information = []
        self._impact_repartition_start_column = 0
        self._node_columns = {}
        self._spacer_nodes = set()
        self._spacer_original_source = {}
        self._category_node_indices = set()
        self._leaf_node_indices = set()
        self._breakdown_node_indices = set()

    def _add_node(
            self, label: str, key: NodeKey, color_key: str | None = None, obj: ModelingObject | None = None) -> int:
        return self._graph.add_node(label, key, color_key=color_key, obj=obj)

    def _add_link(self, source: int, target: int, value_tonnes: float) -> None:
        self._graph.add_link(source, target, value_tonnes)

    @staticmethod
    def _get_value_kg(value: Any) -> float:
        if isinstance(value, EmptyExplainableObject):
            return 0.0
        if isinstance(value, ExplainableHourlyQuantities):
            return float(value.sum().magnitude)
        return float(value.magnitude)

    def _get_phases(self) -> list[LifeCyclePhases]:
        if self.lifecycle_phase_filter is not None:
            return [self.lifecycle_phase_filter]
        return [LifeCyclePhases.MANUFACTURING, LifeCyclePhases.USAGE]

    def _get_phase_context(self, phase: LifeCyclePhases) -> str | None:
        if self.skip_phase_footprint_split:
            return None
        return phase.value

    def _iter_resolved_sources(self, obj: ModelingObject, phase: LifeCyclePhases) -> Iterator[_ResolvedFootprintSource]:
        for original_source, value in obj.attributed_footprint_per_source[phase].items():
            source = self._normalize_sankey_source(original_source)
            if original_source is not source and self._is_excluded(original_source):
                continue
            if self._is_excluded(source):
                continue
            yield _ResolvedFootprintSource(source=source, value_kg=self._get_value_kg(value))

    def _get_phase_total_kg(
            self, root: ModelingObject, root_footprint: dict[LifeCyclePhases, dict[ModelingObject, Any]],
            phase: LifeCyclePhases) -> float:
        if self.excluded_object_types:
            return self._sum_leaf_values(root, phase, set())
        return sum(self._get_value_kg(value) for value in root_footprint[phase].values())

    def _sum_leaf_values(self, obj: ModelingObject, phase: LifeCyclePhases, visited: set[str]) -> float:
        if obj.id in visited:
            return 0
        next_visited = visited | {obj.id}
        total = 0
        for resolved_source in self._iter_resolved_sources(obj, phase):
            if resolved_source.source.is_impact_source:
                total += resolved_source.value_kg
                continue
            total += self._sum_leaf_values(resolved_source.source, phase, next_visited)
        return total

    def _add_flow_to_node(self, parent_idx: int | None, node_idx: int, value_kg: float) -> None:
        if parent_idx is not None:
            self._add_link(parent_idx, node_idx, value_kg / 1000)
        else:
            self.node_total_kg[node_idx] += value_kg

    def _traverse(
            self, obj: ModelingObject, phase: LifeCyclePhases, phase_context: str | None, parent_idx: int | None,
            visited: set[str]) -> None:
        if obj.id in visited:
            return
        next_visited = visited | {obj.id}
        for resolved_source in self._iter_resolved_sources(obj, phase):
            source = resolved_source.source
            value_kg = resolved_source.value_kg
            if self.excluded_object_types and not source.is_impact_source:
                value_kg = self._sum_leaf_values(source, phase, next_visited)
            if value_kg <= 0:
                continue
            if source.is_impact_source:
                self._handle_impact_source(source, value_kg, phase, phase_context, parent_idx)
                continue
            if self._should_skip_object(source):
                self._traverse(source, phase, phase_context, parent_idx, next_visited)
                continue
            source_idx = self._add_node(source.name, (source.id, phase_context), color_key=source.id, obj=source)
            self._add_flow_to_node(parent_idx, source_idx, value_kg)
            self._traverse(source, phase, phase_context, source_idx, next_visited)

    @staticmethod
    def _find_object_category_name(source: ModelingObject) -> str | None:
        from efootprint.all_classes_in_order import OBJECT_CATEGORIES

        for category_name, category_classes in OBJECT_CATEGORIES.items():
            if any(isinstance(source, cls) for cls in category_classes):
                return category_name
        return None

    @staticmethod
    def _get_source_phase_footprint(source: ModelingObject, phase: LifeCyclePhases) -> Any:
        if phase == LifeCyclePhases.MANUFACTURING:
            return source.instances_fabrication_footprint
        return source.energy_footprint

    @staticmethod
    def _get_footprint_breakdown_by_source(source: ModelingObject, phase: LifeCyclePhases) -> dict[ModelingObject, Any]:
        breakdown_by_source = getattr(source, "footprint_breakdown_by_source", None)
        if not isinstance(breakdown_by_source, dict):
            return {}
        return breakdown_by_source.get(phase, {})

    def _expand_impact_source_breakdown(
            self, source: ModelingObject, source_idx: int, phase: LifeCyclePhases, phase_context: str | None,
            value_kg: float) -> None:
        source_phase_footprint_kg = self._get_value_kg(self._get_source_phase_footprint(source, phase))
        if source_phase_footprint_kg <= 0:
            return

        for breakdown_source, breakdown_value in self._get_footprint_breakdown_by_source(source, phase).items():
            if breakdown_source is source or self._is_excluded(breakdown_source) or self._should_skip_object(breakdown_source):
                continue
            breakdown_value_kg = self._get_value_kg(breakdown_value) * value_kg / source_phase_footprint_kg
            if breakdown_value_kg <= 0:
                continue
            breakdown_idx = self._add_node(
                breakdown_source.name,
                (breakdown_source.id, phase_context),
                color_key=breakdown_source.id,
                obj=breakdown_source,
            )
            self._breakdown_node_indices.add(breakdown_idx)
            self._add_flow_to_node(source_idx, breakdown_idx, breakdown_value_kg)

    def _handle_impact_source(
            self, source: ModelingObject, value_kg: float, phase: LifeCyclePhases, phase_context: str | None,
            parent_idx: int | None) -> None:
        leaf_parent_idx = parent_idx
        if not self.skip_object_category_footprint_split:
            category_name = self._find_object_category_name(source)
            if category_name:
                category_label = f"{category_name} {phase_context}" if phase_context is not None else category_name
                cat_idx = self._add_node(category_label, (category_name, phase_context), color_key=f"__cat_{category_name}__")
                self._category_node_indices.add(cat_idx)
                self._add_flow_to_node(parent_idx, cat_idx, value_kg)
                leaf_parent_idx = cat_idx

        if self.skip_object_footprint_split:
            return

        if not self._should_skip_object(source):
            source_idx = self._add_node(source.name, (source.id, phase_context), color_key=source.id, obj=source)
            self._leaf_node_indices.add(source_idx)
            self._add_flow_to_node(leaf_parent_idx, source_idx, value_kg)
            self._expand_impact_source_breakdown(source, source_idx, phase, phase_context, value_kg)

    @time_it
    def build(self) -> None:
        if self._built:
            return
        self._reset_build_state()

        root = self.system
        phases = self._get_phases()
        root_footprint = root.attributed_footprint_per_source

        if self.excluded_object_types:
            self._total_system_kg = sum(self._sum_leaf_values(root, phase, set()) for phase in phases)
        else:
            self._total_system_kg = sum(
                self._get_value_kg(v) for phase in phases for v in root_footprint[phase].values())

        current_column_index = 1
        root_idx = None
        if not self._should_skip_object(root):
            root_idx = self._add_node(root.name, ("root", "total"), color_key="__system__", obj=root)
            self.node_total_kg[root_idx] = self._total_system_kg
            self._node_columns[root_idx] = current_column_index
            current_column_index += 1

        phase_parents = {}
        if not self.skip_phase_footprint_split and len(phases) > 1:
            for phase in phases:
                color_key = "__fabrication__" if phase == LifeCyclePhases.MANUFACTURING else "__energy__"
                phase_idx = self._add_node(phase.value, ("phase", phase.value), color_key=color_key)
                self._node_columns[phase_idx] = current_column_index
                self._add_flow_to_node(root_idx, phase_idx, self._get_phase_total_kg(root, root_footprint, phase))
                phase_parents[phase] = phase_idx
            self._manual_column_information.append({
                "column_index": current_column_index,
                "column_type": "manual_split",
                "description": "Life cycle phase",
            })
            current_column_index += 1
        else:
            for phase in phases:
                phase_parents[phase] = root_idx

        self._impact_repartition_start_column = current_column_index

        for phase in phases:
            self._traverse(root, phase, self._get_phase_context(phase), phase_parents[phase], visited=set())

        self._assign_columns()
        self._assign_category_leaf_and_breakdown_columns()
        self._aggregate_small_nodes_by_column()
        self._insert_spacer_nodes()
        self._built = True

    def _is_intermediate_node(self, node_idx: int) -> bool:
        """Intermediate traversal nodes: not root/phase (already in _node_columns) nor category/leaf/breakdown."""
        return (
            node_idx not in self._node_columns and node_idx not in self._category_node_indices
            and node_idx not in self._leaf_node_indices and node_idx not in self._breakdown_node_indices
        )

    def _assign_columns(self) -> None:
        from efootprint.all_classes_in_order import SANKEY_COLUMNS

        node_to_group = {}
        for node_idx, obj in self.node_objects.items():
            if not self._is_intermediate_node(node_idx):
                continue
            for group_idx, group in enumerate(SANKEY_COLUMNS):
                if any(isinstance(obj, cls) for cls in group):
                    node_to_group[node_idx] = group_idx
                    break

        unmatched = [
            self.node_objects[idx] for idx in self.node_objects
            if self._is_intermediate_node(idx) and idx not in node_to_group
        ]
        if unmatched:
            names = [f"{obj.name} ({type(obj).__name__})" for obj in unmatched]
            raise ValueError(f"Intermediate nodes not matching any SANKEY_COLUMNS group: {', '.join(names)}")

        used_groups = sorted(set(node_to_group.values()))
        group_to_column = {
            group_idx: self._impact_repartition_start_column + offset
            for offset, group_idx in enumerate(used_groups)
        }
        for node_idx, group_idx in node_to_group.items():
            self._node_columns[node_idx] = group_to_column[group_idx]

    def _assign_category_leaf_and_breakdown_columns(self) -> None:
        if not self._category_node_indices and not self._leaf_node_indices and not self._breakdown_node_indices:
            return
        max_column = max(self._node_columns.values()) if self._node_columns else self._impact_repartition_start_column - 1
        category_column = max_column + 1
        if self._category_node_indices:
            for category_idx in self._category_node_indices:
                self._node_columns[category_idx] = category_column
            self._manual_column_information.append({
                "column_index": category_column,
                "column_type": "manual_split",
                "description": "Object category",
            })
        leaf_column = category_column + 1 if self._category_node_indices else category_column
        breakdown_column = leaf_column + 1
        leaf_nodes_with_breakdown_children = {
            source for source, target in zip(self.link_sources, self.link_targets) if target in self._breakdown_node_indices
        }
        for leaf_idx in self._leaf_node_indices:
            if self._breakdown_node_indices and leaf_idx not in leaf_nodes_with_breakdown_children:
                self._node_columns[leaf_idx] = breakdown_column
            else:
                self._node_columns[leaf_idx] = leaf_column
        for node_idx in self._breakdown_node_indices:
            self._node_columns[node_idx] = breakdown_column

    def _insert_spacer_nodes(self) -> None:
        original_links = self._graph.reset_links_preserving_root_totals()
        for source, target, value in original_links:
            source_column = self._node_columns[source]
            target_column = self._node_columns[target]
            if target_column > source_column + 1:
                previous_idx = source
                for column in range(source_column + 1, target_column):
                    spacer_idx = self._add_node("", ("__spacer__", source, target, column), color_key=self.node_color_keys[source])
                    self._node_columns[spacer_idx] = column
                    self._spacer_nodes.add(spacer_idx)
                    self._spacer_original_source[spacer_idx] = source
                    self._add_link(previous_idx, spacer_idx, value)
                    previous_idx = spacer_idx
                self._add_link(previous_idx, target, value)
                continue
            self._add_link(source, target, value)

    def _aggregate_small_nodes_by_column(self) -> None:
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
        aggregate_groups = {column: group for column, group in aggregate_groups.items() if len(group) >= 2}
        if not aggregate_groups:
            return

        graph_snapshot = self._graph.snapshot()
        original_node_columns = dict(self._node_columns)
        nodes_to_aggregate = {node_idx for group in aggregate_groups.values() for node_idx in group}

        self._graph.reset()
        self.aggregated_node_members = {}
        self.aggregated_node_classes = {}
        self._node_columns = {}
        self._category_node_indices = set()
        self._leaf_node_indices = set()
        self._breakdown_node_indices = set()

        old_to_new_indices = {}
        for old_idx, label in enumerate(graph_snapshot.full_node_labels):
            if old_idx in nodes_to_aggregate:
                continue
            new_idx = self._add_node(
                label,
                graph_snapshot.node_keys_by_index[old_idx],
                color_key=graph_snapshot.node_color_keys[old_idx],
                obj=graph_snapshot.node_objects.get(old_idx),
            )
            old_to_new_indices[old_idx] = new_idx
            if old_idx in original_node_columns:
                self._node_columns[new_idx] = original_node_columns[old_idx]

        for column, group in aggregate_groups.items():
            group_members = sorted(group, key=lambda idx: graph_snapshot.node_total_kg[idx], reverse=True)
            aggregate_idx = self._add_node(
                f"Other ({len(group_members)})", ("__aggregated__", column), color_key=f"__aggregated__{column}")
            self.aggregated_node_members[aggregate_idx] = [
                (graph_snapshot.full_node_labels[idx], graph_snapshot.node_total_kg[idx]) for idx in group_members
            ]
            self.aggregated_node_classes[aggregate_idx] = self._sort_class_names({
                self._get_canonical_class_name(graph_snapshot.node_objects[idx])
                for idx in group_members
                if idx in graph_snapshot.node_objects
            })
            self._node_columns[aggregate_idx] = column
            for old_idx in group_members:
                old_to_new_indices[old_idx] = aggregate_idx

        combined_links = {}
        for source, target, value in graph_snapshot.links:
            new_source = old_to_new_indices[source]
            new_target = old_to_new_indices[target]
            if new_source == new_target:
                continue
            combined_links[(new_source, new_target)] = combined_links.get((new_source, new_target), 0) + value

        for (source, target), value in combined_links.items():
            self._add_link(source, target, value)

        # Restore node_total_kg for root nodes (no incoming links, so _add_link didn't accumulate their totals).
        # Uses snapshot targets so aggregated root nodes also get their total added to the aggregate.
        snapshot_targets = {target for _, target, _ in graph_snapshot.links}
        for old_idx, new_idx in old_to_new_indices.items():
            if old_idx not in snapshot_targets:
                self.node_total_kg[new_idx] += graph_snapshot.node_total_kg[old_idx]

    def _compute_node_colors(self) -> list[str]:
        return [self._compute_color_for_key(key) for key in self.node_color_keys]

    @classmethod
    def _compute_color_for_key(cls, key: str) -> str:
        if key in cls._FIXED_KEY_COLORS:
            return cls._FIXED_KEY_COLORS[key]
        if key.startswith("__aggregated__"):
            return "rgba(160,160,160,0.8)"
        digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
        hue = int.from_bytes(digest[:2], "big") % 360
        saturation = 0.34 + digest[2] / 255 * 0.16
        lightness = 0.43 + digest[3] / 255 * 0.14
        red, green, blue = colorsys.hls_to_rgb(hue / 360, lightness, saturation)
        return f"rgba({round(red * 255)},{round(green * 255)},{round(blue * 255)},0.8)"

    def _build_hover_labels(self) -> list[str]:
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
                    for label, member_kg in self.aggregated_node_members[idx]
                )
                node_hover.append(
                    f"{self.full_node_labels[idx]}<br>{amount_str} CO2eq ({pct:.1f}%)<br><br>Aggregated objects:<br>{members_str}")
                continue
            node_hover.append(f"{self.full_node_labels[idx]}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return node_hover

    def _build_link_labels(self) -> list[str]:
        incoming_by_target = {}
        outgoing_by_source = {}
        for source, target in zip(self.link_sources, self.link_targets):
            incoming_by_target.setdefault(target, []).append(source)
            outgoing_by_source.setdefault(source, []).append(target)

        def resolve_visible(node_idx, adjacency):
            current = node_idx
            while current in self._spacer_nodes:
                neighbors = adjacency.get(current, [])
                if not neighbors:
                    break
                current = neighbors[0]
            return current

        link_labels = []
        for link_idx in range(len(self.link_values)):
            kg = self.link_values[link_idx] * 1000
            amount_str = display_co2_amount(format_co2_amount(kg))
            pct = (kg / self._total_system_kg * 100) if self._total_system_kg > 0 else 0
            source_idx = resolve_visible(self.link_sources[link_idx], incoming_by_target)
            target_idx = resolve_visible(self.link_targets[link_idx], outgoing_by_source)
            link_labels.append(
                f"{self.full_node_labels[source_idx]} → {self.full_node_labels[target_idx]}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return link_labels

    def _column_x_center(self, column: int) -> float:
        min_col = min(self._node_columns.values())
        max_col = max(self._node_columns.values())
        if max_col == min_col:
            return 0.5
        return 0.006 + (column - min_col) / (max_col + 0.09 - min_col)

    def get_column_metadata(self) -> list[ColumnInformation]:
        if not self._built:
            self.build()
        if not self._node_columns:
            return []

        classes_by_column = {}
        for node_idx, column in self._node_columns.items():
            if node_idx in self._spacer_nodes:
                continue
            if node_idx in self.node_objects:
                classes_by_column.setdefault(column, set()).add(self._get_canonical_class_name(self.node_objects[node_idx]))
            if node_idx in self.aggregated_node_classes:
                classes_by_column.setdefault(column, set()).update(self.aggregated_node_classes[node_idx])

        return [{
            "column_index": column,
            "x_center": self._column_x_center(column),
            "class_names": self._sort_class_names(class_names),
        } for column, class_names in sorted(classes_by_column.items()) if class_names]

    def get_column_information(self) -> list[ColumnInformation]:
        if not self._built:
            self.build()
        manual = [{**info, "x_center": self._column_x_center(info["column_index"])} for info in self._manual_column_information]
        impact = [{
            "column_index": column_metadata["column_index"],
            "x_center": column_metadata["x_center"],
            "column_type": "impact_repartition",
            "class_names": column_metadata["class_names"],
        } for column_metadata in self.get_column_metadata()
            if column_metadata["column_index"] >= self._impact_repartition_start_column
            and not any(column_metadata["column_index"] == info["column_index"] for info in self._manual_column_information)]
        return manual + impact

    def _get_displayed_column_information(self) -> list[ColumnInformation]:
        return sorted(self.get_column_information(), key=lambda info: info["column_index"])

    @staticmethod
    def _format_column_header_text(column_info: ColumnInformation) -> str:
        if column_info["column_type"] == "manual_split":
            return column_info["description"]
        return "<br>".join(column_info["class_names"])

    def _build_column_header_annotations(self) -> tuple[list[dict[str, Any]], int]:
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
    def figure(
            self, title: str | None = None, filename: str | None = None, height: int = None, width: int = None,
            notebook: bool = False) -> Any:
        import plotly.graph_objects as go
        import plotly

        self.build()
        if title is None:
            lifecycle_info = ""
            if self.lifecycle_phase_filter:
                lifecycle_info = self.lifecycle_phase_filter.lower() + " "
            excluded_classes_info = ""
            if self.excluded_object_types:
                excluded_classes_info = " excluding " + ", ".join(
                    cls if isinstance(cls, str) else cls.__name__ for cls in self.excluded_object_types
                )
            title = (
                f"{self.system.name} {lifecycle_info}impact repartition{excluded_classes_info}: "
                f"{display_co2_amount(format_co2_amount(self._total_system_kg))} CO2eq"
            )

        node_hover = self._build_hover_labels()
        link_labels = self._build_link_labels()
        node_colors = self._compute_node_colors()
        link_colors = [
            node_colors[self._spacer_original_source.get(source, source)].replace("0.8)", "0.3)")
            for source in self.link_sources
        ]
        display_node_colors = [
            color.replace("0.8)", "0.3)") if idx in self._spacer_nodes else color
            for idx, color in enumerate(node_colors)
        ]
        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                label=self.node_labels, pad=20, thickness=20, color=display_node_colors, line=dict(width=0),
                customdata=node_hover, hovertemplate="%{customdata}<extra></extra>",
            ),
            link=dict(
                source=self.link_sources, target=self.link_targets, value=self.link_values,
                color=link_colors, customdata=link_labels, hovertemplate="%{customdata}<extra></extra>",
            ),
        )])
        top_margin = 100
        if self.display_column_information:
            column_annotations, max_line_count = self._build_column_header_annotations()
            if column_annotations:
                top_margin = 110 + 20 * max_line_count
                for annotation in column_annotations:
                    fig.add_annotation(**annotation)
        if height is None:
            height = 600 if notebook else 800
        if width is None:
            width = 1100 if notebook else 1800
        fig.update_layout(
            title=dict(text=title, pad=dict(b=24)),
            font_size=12, height=height, width=width, margin=dict(t=top_margin, b=100))
        if notebook and filename is None:
            filename = f"{self.system.name} impact repartition.html"
        if filename is not None:
            plotly.offline.plot(fig, filename=filename, auto_open=False)
        if notebook:
            from IPython.display import HTML
            return HTML(filename=filename)
        return fig


if __name__ == '__main__':
    test = "json"
    json_files = ["basic-model.json", "basic-2.json", "chatbot-efootprint-model.json",
                  "scenarioC_smart_building_system.json", "basic-edge.json", "curling.json", "smart building test.json"]
    skipped_impact_repartition_classes__full = [
        "System", "Country", "EdgeComponent", "JobBase", "RecurrentEdgeDeviceNeed", "RecurrentServerNeed",
        "RecurrentEdgeComponentNeed", "RecurrentEdgeWorkloadNeed"]
    skipped_impact_repartition_classes = [
        "System", "JobBase", "RecurrentEdgeDeviceNeed", "RecurrentServerNeed", "RecurrentEdgeComponentNeed"]
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
        with open(json_files[-2], "r") as f:
            json_data = json.load(f)
        class_obj_dict, flat_obj_dict = json_to_system(json_data)
        system = next(iter(class_obj_dict["System"].values()))
    sankey = ImpactRepartitionSankey(
        system, aggregation_threshold_percent=1,
        skipped_impact_repartition_classes=None,
        skip_phase_footprint_split=False, skip_object_category_footprint_split=False,
        skip_object_footprint_split=False, excluded_object_types=None, lifecycle_phase_filter=None,
        display_column_information=True
    )
    fig = sankey.figure()
    fig.show()
