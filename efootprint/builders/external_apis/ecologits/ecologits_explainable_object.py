from pint.registry import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import get_unit


@ExplainableObject.register_subclass(lambda d: "ancestors" in d and "formula" in d)
class EcoLogitsExplainableObject(ExplainableQuantity):
    @classmethod
    def from_json_dict(cls, d):
        value = {key: d[key] for key in ["value", "unit"]}
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        return cls(value, label=d["label"], ancestors=d["ancestors"], formula=d["formula"], source=source)

    def __init__(self, value: Quantity|dict, label: str, ancestors: dict[str, Quantity|dict],
                 formula: str, source: Source, parent: ExplainableObject=None):
        super().__init__(value, label, left_parent=parent, source=source)
        self._ancestors = ancestors
        self.formula = formula

    @property
    def ancestors(self):
        if isinstance(next(iter(self._ancestors.values())), Quantity):
            return self._ancestors
        else:
            converted_ancestors = {}
            for key, val in self._ancestors.items():
                converted_ancestors[key] = Quantity(float(val["value"]), get_unit(val["unit"]))
            self._ancestors = converted_ancestors
            return self._ancestors
