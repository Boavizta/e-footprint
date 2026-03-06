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
    def __init__(self, system):
        self.system = system
        self.node_labels = []
        self.node_indices = {}
        self.node_color_keys = []  # object id or structural key, for consistent coloring
        self.node_objects = {}
        self.link_sources = []
        self.link_targets = []
        self.link_values = []
        self.node_total_kg = []
        self._built = False
        self._total_system_kg = 0

    def _add_node(self, label, key, color_key=None, obj=None):
        if key in self.node_indices:
            return self.node_indices[key]
        idx = len(self.node_labels)
        self.node_labels.append(label)
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

        expanded = set()
        queue = [idx for idx in self.node_objects]
        while queue:
            next_queue = []
            for node_idx in queue:
                if node_idx in expanded:
                    continue
                expanded.add(node_idx)
                obj = self.node_objects[node_idx]
                if not hasattr(obj, "impact_repartition"):
                    continue
                total_tonnes = self.node_total_kg[node_idx] / 1000
                footprint_type = self._get_footprint_type_for_node(node_idx)
                for child_obj, fraction in obj.impact_repartition.items():
                    frac_val = self._get_fraction_magnitude(fraction)
                    child_value = total_tonnes * frac_val
                    if child_value <= 0:
                        continue
                    child_key = (child_obj.id, footprint_type)
                    child_idx = self._add_node(child_obj.name, child_key, color_key=child_obj.id, obj=child_obj)
                    self._add_link(node_idx, child_idx, child_value)
                    if child_idx not in expanded:
                        next_queue.append(child_idx)
            queue = next_queue

    def _get_footprint_type_for_node(self, node_idx):
        for key, idx in self.node_indices.items():
            if idx == node_idx:
                return key[1]
        return "unknown"

    def _compute_node_colors(self):
        # Map each unique color_key to a consistent color
        unique_keys = list(dict.fromkeys(self.node_color_keys))
        key_to_color = {}
        # Fixed colors for structural nodes
        key_to_color["__system__"] = "rgba(100,100,100,0.8)"
        key_to_color["__fabrication__"] = "rgba(180,80,80,0.8)"
        key_to_color["__energy__"] = "rgba(80,120,180,0.8)"
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
            node_hover.append(f"{self.node_labels[idx]}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return node_hover

    def _build_link_labels(self):
        link_labels = []
        for i in range(len(self.link_values)):
            kg = self.link_values[i] * 1000
            amount_str = display_co2_amount(format_co2_amount(kg))
            pct = (kg / self._total_system_kg * 100) if self._total_system_kg > 0 else 0
            src_label = self.node_labels[self.link_sources[i]]
            tgt_label = self.node_labels[self.link_targets[i]]
            link_labels.append(f"{src_label} → {tgt_label}<br>{amount_str} CO2eq ({pct:.1f}%)")
        return link_labels

    def figure(self, title=None, width=1200):
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
        fig.update_layout(title_text=title, font_size=12, height=600, width=width)
        return fig


if __name__ == '__main__':
    from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass

    system, start_date = IntegrationTestServicesBaseClass.generate_system_with_services()

    sankey = ImpactRepartitionSankey(system)
    fig = sankey.figure()
    fig.show()
