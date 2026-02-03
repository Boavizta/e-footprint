from pint.registry import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING


@ExplainableObject.register_subclass(lambda d: "ancestors" in d and "formula" in d)
class EcoLogitsExplainableQuantity(ExplainableQuantity):
    @classmethod
    def from_json_dict(cls, d):
        value = {key: d[key] for key in ["value", "unit"]}
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        return cls(value, label=d["label"], ancestors=d["ancestors"], formula=d["formula"], source=source)

    def __init__(self, value: Quantity|dict, label: str, ancestors: dict[str, Quantity|dict],
                 formula: str, source: Source, parent: ExplainableObject=None, operator: str=None):
        super().__init__(value, label, left_parent=parent, source=source, operator=operator)
        self._ancestors = ancestors
        self.formula = formula

    def to_json(self, save_calculated_attributes=False):
        output_dict = super().to_json(save_calculated_attributes)
        output_dict["ancestors"] = self._ancestors
        output_dict["formula"] = self.formula

        return output_dict

    @property
    def ancestors(self):
        if isinstance(next(iter(self._ancestors.values())), Quantity):
            return self._ancestors
        else:
            converted_ancestors = {}
            for key, val in self._ancestors.items():
                converted_ancestors[key] = float(val) * ECOLOGITS_UNIT_MAPPING[key]
            self._ancestors = converted_ancestors
            return self._ancestors
