import pytz

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source


@ExplainableObject.register_subclass(lambda d: "zone" in d)
class ExplainableTimezone(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d["source"]) if "source" in d else None
        return cls(pytz.timezone(d["zone"]), label=d["label"], source=source)

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {"zone": self.value.zone}
        output_dict.update(super().to_json(with_calculated_attributes_data))

        return output_dict
