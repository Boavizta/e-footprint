import inspect
import pkgutil
import importlib
from types import ModuleType
from typing import Type, List

from unittest import TestCase

from efootprint import core
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES


def get_subclasses_in_package(package: ModuleType, base_class: Type) -> List[Type]:
    subclasses = []
    for finder, name, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = importlib.import_module(name)
        except Exception as e:
            print(f"Skipping module {name} due to import error: {e}")
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            # Ensure the class is defined in this module, and is a subclass of the base (but not the base itself)
            if obj.__module__ == module.__name__ and issubclass(obj, base_class) and obj is not base_class:
                subclasses.append(obj)
    return subclasses


class TestAllEfootprintClasses(TestCase):
    def test_all_efootprint_classes(self):
        all_modeling_object_classes = get_subclasses_in_package(core, ModelingObject)

        for efootprint_class in all_modeling_object_classes:
            if not inspect.isabstract(efootprint_class):
                self.assertIn(efootprint_class, ALL_EFOOTPRINT_CLASSES,
                              f"{efootprint_class.__name__} is not in ALL_EFOOTPRINT_CLASSES")
