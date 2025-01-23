from typing import List

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class Hardware(ModelingObject):
    @classmethod
    def default_values(cls):
        return {
            "carbon_footprint_fabrication": SourceValue(150 * u.kg),
            "power": SourceValue(50 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day)
        }

    @classmethod
    def smartphone(cls, name="Default smartphone", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(30 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(1 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(3 * u.year, Sources.HYPOTHESIS),
            "fraction_of_usage_time": SourceValue(3.6 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def laptop(cls, name="Default laptop", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(156 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(50 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def box(cls, name="Default box", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(78 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(10 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
            "fraction_of_usage_time": SourceValue(24 * u.hour / u.day, Sources.HYPOTHESIS)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def screen(cls, name="Default screen", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(222 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(30 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day, Sources.HYPOTHESIS)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.smartphone, cls.laptop, cls.box, cls.screen]

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity, fraction_of_usage_time: ExplainableQuantity):
        super().__init__(name)
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.lifespan = lifespan.set_label(f"Lifespan of {self.name}")
        self.fraction_of_usage_time = fraction_of_usage_time.set_label(f"{self.name} fraction of usage time")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return self.modeling_obj_containers

    @property
    def systems(self) -> List:
        return list(set(sum([mod_obj.systems for mod_obj in self.modeling_obj_containers], start=[])))

