from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SankeyGraphSnapshot:
    node_keys_by_index: dict[int, Any]
    full_node_labels: list[str]
    node_color_keys: list[str]
    node_objects: dict[int, Any]
    links: list[tuple[int, int, float]]
    node_total_kg: list[float]


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
        self.link_values: list[float] = []
        self.link_index_by_edge: dict[tuple[int, int], int] = {}
        self.node_total_kg: list[float] = []

    def add_node(self, label: str, key: Any, color_key: str | None = None, obj: Any = None) -> int:
        if key in self.node_indices:
            return self.node_indices[key]
        idx = len(self.node_labels)
        self.node_labels.append(self._truncate_label(label))
        self.full_node_labels.append(label)
        self.node_indices[key] = idx
        self.node_color_keys.append(color_key or label)
        self.node_total_kg.append(0.0)
        if obj is not None:
            self.node_objects[idx] = obj
        return idx

    def add_link(self, source: int, target: int, value_tonnes: float) -> None:
        if value_tonnes <= 0:
            return
        edge = (source, target)
        existing_link_idx = self.link_index_by_edge.get(edge)
        if existing_link_idx is None:
            self.link_index_by_edge[edge] = len(self.link_sources)
            self.link_sources.append(source)
            self.link_targets.append(target)
            self.link_values.append(value_tonnes)
        else:
            self.link_values[existing_link_idx] += value_tonnes
        self.node_total_kg[target] += value_tonnes * 1000

    def snapshot(self) -> SankeyGraphSnapshot:
        return SankeyGraphSnapshot(
            node_keys_by_index={idx: key for key, idx in self.node_indices.items()},
            full_node_labels=list(self.full_node_labels),
            node_color_keys=list(self.node_color_keys),
            node_objects=dict(self.node_objects),
            links=list(zip(self.link_sources, self.link_targets, self.link_values)),
            node_total_kg=list(self.node_total_kg),
        )

    def reset_links_preserving_root_totals(self) -> list[tuple[int, int, float]]:
        original_links = list(zip(self.link_sources, self.link_targets, self.link_values))
        incoming_nodes = set(self.link_targets)
        root_total_kg = {
            idx: self.node_total_kg[idx]
            for idx in range(len(self.node_labels))
            if idx not in incoming_nodes and self.node_total_kg[idx] > 0
        }
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self.link_index_by_edge = {}
        self.node_total_kg = [0.0] * len(self.node_labels)
        for idx, kg in root_total_kg.items():
            self.node_total_kg[idx] = kg
        return original_links
