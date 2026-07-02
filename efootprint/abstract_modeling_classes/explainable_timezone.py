import pytz

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


@ExplainableObject.register_subclass(lambda d: "zone" in d)
class ExplainableTimezone(ExplainableObject):
    __slots__ = ()

    @classmethod
    def from_json_dict(cls, d):
        return cls(pytz.timezone(d["zone"]), label=d["label"])

    def to_json(self, with_formula=False):
        output_dict = {"zone": self.value.zone}
        output_dict.update(super().to_json(with_formula))

        return output_dict
