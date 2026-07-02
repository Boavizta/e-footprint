from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


@ExplainableObject.register_subclass(lambda d: "value" in d and "unit" not in d and isinstance(d["value"], dict))
class ExplainableDict(ExplainableObject):
    __slots__ = ()

    @classmethod
    def from_json_dict(cls, d):
        return cls(d["value"], label=d["label"])

    def to_json(self, with_formula=False):
        output_dict = {"value": self.value}
        output_dict.update(super().to_json(with_formula))

        return output_dict
