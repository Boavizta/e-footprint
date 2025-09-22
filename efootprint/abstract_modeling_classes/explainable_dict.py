from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source


@ExplainableObject.register_subclass(lambda d: "value" in d and "unit" not in d and isinstance(d["value"], dict))
class ExplainableDict(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d["source"]) if "source" in d else None
        return cls(d["value"], label=d["label"], source=source)

    def to_json(self, save_calculated_attributes=False):
        output_dict = {"value": self.value}
        output_dict.update(super().to_json(save_calculated_attributes))

        return output_dict
