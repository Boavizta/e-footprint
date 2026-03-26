from dataclasses import dataclass
from typing import Any

from pint import Quantity

from efootprint.constants.units import u


@dataclass(frozen=True)
class SankeyGraphSnapshot:
    node_keys_by_index: dict[int, Any]
    full_node_labels: list[str]
    node_color_keys: list[str]
    node_objects: dict[int, Any]
    links: list[tuple[int, int, Quantity]]
    node_total_values: list[Quantity]


class SankeyGraph:
    def __init__(self, truncate_label) -> None:
        self._truncate_label = truncate_label
        self.reset()

    def reset(self) -> None:
        self.node_labels: list[str] = []
        self.full_node_labels: list[str] = []
        self.node_indices: dict[Any, int] = {}
        self.node_color_keys: list[str] = []
        self.node_objects: dict[int, Any] = {}
        self.link_sources: list[int] = []
        self.link_targets: list[int] = []
        self.link_values: list[Quantity] = []
        self.link_index_by_edge: dict[tuple[int, int], int] = {}
        self.node_total_values: list[Quantity] = []

    def add_node(self, label: str, key: Any, color_key: str | None = None, obj: Any = None) -> int:
        if key in self.node_indices:
            return self.node_indices[key]
        idx = len(self.node_labels)
        self.node_labels.append(self._truncate_label(label))
        self.full_node_labels.append(label)
        self.node_indices[key] = idx
        self.node_color_keys.append(color_key or label)
        self.node_total_values.append(0 * u.kg)
        if obj is not None:
            self.node_objects[idx] = obj
        return idx

    def add_link(self, source: int, target: int, value: Quantity) -> None:
        if value.magnitude <= 0:
            return
        edge = (source, target)
        existing_link_idx = self.link_index_by_edge.get(edge)
        if existing_link_idx is None:
            self.link_index_by_edge[edge] = len(self.link_sources)
            self.link_sources.append(source)
            self.link_targets.append(target)
            self.link_values.append(value)
        else:
            self.link_values[existing_link_idx] += value
        self.node_total_values[target] += value

    def snapshot(self) -> SankeyGraphSnapshot:
        return SankeyGraphSnapshot(
            node_keys_by_index={idx: key for key, idx in self.node_indices.items()},
            full_node_labels=list(self.full_node_labels),
            node_color_keys=list(self.node_color_keys),
            node_objects=dict(self.node_objects),
            links=list(zip(self.link_sources, self.link_targets, self.link_values)),
            node_total_values=list(self.node_total_values),
        )

    def reset_links_preserving_root_totals(self) -> list[tuple[int, int, Quantity]]:
        original_links = list(zip(self.link_sources, self.link_targets, self.link_values))
        incoming_nodes = set(self.link_targets)
        root_total_values = {
            idx: self.node_total_values[idx]
            for idx in range(len(self.node_labels))
            if idx not in incoming_nodes and self.node_total_values[idx].magnitude > 0
        }
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self.link_index_by_edge = {}
        self.node_total_values = [0 * u.kg for _ in self.node_labels]
        for idx, value in root_total_values.items():
            self.node_total_values[idx] = value
        return original_links
