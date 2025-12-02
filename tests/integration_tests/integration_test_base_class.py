from collections import defaultdict
from copy import copy
from dataclasses import dataclass
import inspect
from typing import Callable, List, Optional, Dict, Sequence, Type, Union
from unittest import TestCase
import os
import json

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, get_instance_attributes
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.logger import logger

INTEGRATION_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ObjectLinkScenario:
    """Declarative description of a link-mutation test case."""

    name: str
    updates_builder: Union[Callable[["IntegrationTestBaseClass"], List[List[object]]], List[List[object]]]
    expected_changed: Sequence["ModelingObject"] = ()
    expected_unchanged: Sequence["ModelingObject"] = ()
    expect_total_change: bool = True
    expected_exception: Optional[Type[BaseException]] = None
    post_assertions: Optional[Callable[["IntegrationTestBaseClass"], None]] = None
    post_reset_assertions: Optional[Callable[["IntegrationTestBaseClass"], None]] = None


class AutoTestMethodsMeta(type):
    """Metaclass that auto-generates test_* methods from run_test_* methods in base classes.

    For each run_test_X method found in the class hierarchy, creates a test_X method
    that calls run_test_X(). This eliminates boilerplate like:
        def test_foo(self): self.run_test_foo()

    Special handling:
    - run_test_system_to_json and run_test_json_to_system pass self.system as argument
    - Skips generation if test_X is already defined in the class
    """
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect all run_test_* methods from the class and its bases
        run_test_methods = {}
        for klass in reversed(cls.__mro__):
            for method_name, method in inspect.getmembers(klass, predicate=inspect.isfunction):
                if method_name.startswith('run_test_'):
                    run_test_methods[method_name] = method

        # Generate test_* methods for each run_test_* method
        for run_method_name in run_test_methods:
            test_method_name = run_method_name.replace('run_test_', 'test_')

            # Skip if test method already exists in the class (not inherited)
            if test_method_name in namespace:
                continue

            # Create the test method
            if run_method_name in ('run_test_system_to_json', 'run_test_json_to_system'):
                # These methods need self.system as argument
                def make_test_with_system(run_name):
                    def test_method(self):
                        getattr(self, run_name)(self.system)
                    return test_method
                test_method = make_test_with_system(run_method_name)
            else:
                def make_test(run_name):
                    def test_method(self):
                        getattr(self, run_name)()
                    return test_method
                test_method = make_test(run_method_name)

            test_method.__name__ = test_method_name
            test_method.__qualname__ = f"{name}.{test_method_name}"
            setattr(cls, test_method_name, test_method)

        return cls


class SystemTestFixture:
    """Registry for test system objects providing convenient access patterns.

    Provides:
    - Access by name: fixture.get("Server 1")
    - Access by class: fixture.get_all(Server), fixture.get_first(Server)
    - Auto-initialization of footprint tracking dictionaries
    """
    def __init__(self, system: "System"):
        self.system = system
        self._by_name: Dict[str, ModelingObject] = {}
        self._by_class: Dict[str, List[ModelingObject]] = defaultdict(list)
        self._build_registry()

    def _build_registry(self):
        """Build lookup dictionaries from system's linked objects."""
        all_objects = [self.system] + self.system.all_linked_objects
        for obj in all_objects:
            self._by_name[obj.name] = obj
            # Use class_as_simple_str for consistent class name lookup
            self._by_class[obj.class_as_simple_str].append(obj)

    def get(self, name: str) -> ModelingObject:
        """Get object by its name."""
        if name not in self._by_name:
            available = list(self._by_name.keys())
            raise KeyError(f"No object named '{name}'. Available: {available}")
        return self._by_name[name]

    def get_first(self, class_type: Type) -> ModelingObject:
        """Get the first object of given class type."""
        class_name = class_type.__name__
        if class_name not in self._by_class or not self._by_class[class_name]:
            available = [k for k, v in self._by_class.items() if v]
            raise KeyError(f"No objects of type '{class_name}'. Available types: {available}")
        return self._by_class[class_name][0]

    def get_all(self, class_type: Type) -> List[ModelingObject]:
        """Get all objects of given class type."""
        class_name = class_type.__name__
        return self._by_class.get(class_name, [])

    def has(self, name: str) -> bool:
        """Check if an object with given name exists."""
        return name in self._by_name

    def has_class(self, class_type: Type) -> bool:
        """Check if any objects of given class type exist."""
        return bool(self._by_class.get(class_type.__name__))

    @property
    def class_names(self) -> List[str]:
        """Get list of all class types present in the system."""
        return [k for k, v in self._by_class.items() if v]

    def initialize_footprints(self) -> tuple:
        """Auto-initialize footprint tracking dictionaries.

        Returns:
            Tuple of (initial_footprint, initial_fab_footprints, initial_energy_footprints,
                     initial_system_total_fab_footprint, initial_system_total_energy_footprint)
        """
        initial_footprint = self.system.total_footprint
        initial_fab_footprints = {}
        initial_energy_footprints = {}

        for obj in self.system.all_linked_objects:
            if hasattr(obj, 'energy_footprint'):
                initial_energy_footprints[obj] = obj.energy_footprint
            if hasattr(obj, 'instances_fabrication_footprint'):
                initial_fab_footprints[obj] = obj.instances_fabrication_footprint
            # Handle UsagePattern special case with devices_fabrication_footprint
            if hasattr(obj, 'devices_fabrication_footprint'):
                initial_fab_footprints[obj] = obj.devices_fabrication_footprint
            if hasattr(obj, 'devices_energy_footprint'):
                initial_energy_footprints[obj] = obj.devices_energy_footprint

        initial_system_total_fab_footprint = self.system.total_fabrication_footprint_sum_over_period
        initial_system_total_energy_footprint = self.system.total_energy_footprint_sum_over_period

        return (initial_footprint, initial_fab_footprints, initial_energy_footprints,
                initial_system_total_fab_footprint, initial_system_total_energy_footprint)


class IntegrationTestBaseClass(TestCase):
    # Mapping of attribute names to object names in the system - override in subclasses
    OBJECT_NAMES_MAP: Dict[str, str] = {}
    REF_JSON_FILENAME: str = None

    @classmethod
    def setUpClass(cls):
        cls.initial_energy_footprints = {}
        cls.initial_fab_footprints = {}
        cls.ref_json_filename = None

    @classmethod
    def _setup_from_system(cls, system, start_date):
        """Common setup logic for both code-generated and JSON-loaded systems.

        Uses OBJECT_NAMES_MAP to extract objects from the fixture by name and assign
        them to class attributes.
        """
        cls.system = system
        cls.start_date = start_date
        cls.fixture = SystemTestFixture(system)

        # Extract objects by name using the mapping
        for attr_name, object_name in cls.OBJECT_NAMES_MAP.items():
            setattr(cls, attr_name, cls.fixture.get(object_name))

        # Auto-initialize footprints
        (cls.initial_footprint, cls.initial_fab_footprints, cls.initial_energy_footprints,
         cls.initial_system_total_fab_footprint, cls.initial_system_total_energy_footprint) = \
            cls.fixture.initialize_footprints()

        cls.ref_json_filename = cls.REF_JSON_FILENAME

    def footprint_has_changed(self, objects_to_test: List[ModelingObject], system=None):
        for obj in objects_to_test:
            try:
                initial_footprint = self.initial_energy_footprints[obj]
                new_footprint = obj.energy_footprint
                if obj.class_as_simple_str != "Network":
                    initial_footprint += self.initial_fab_footprints[obj]

                self.assertNotEqual(initial_footprint, new_footprint)
                logger.info(
                    f"{obj.name} footprint has changed from {str(initial_footprint)}"
                    f" to {str(new_footprint)}")
            except AssertionError:
                raise AssertionError(f"Footprint hasn’t changed for {obj.name}")
        if objects_to_test[0].systems:
            system = objects_to_test[0].systems[0]
        else:
            assert system is not None
        for prev_fp, initial_fp in zip(
                (system.previous_total_energy_footprints_sum_over_period,
                 system.previous_total_fabrication_footprints_sum_over_period),
                (self.initial_system_total_energy_footprint, self.initial_system_total_fab_footprint)):
            for key in ["Servers", "Storage", "Devices", "Network"]:
                self.assertEqual(round(initial_fp[key], 4), round(prev_fp[key], 4), f"{key} footprint is not equal")

    def footprint_has_not_changed(self, objects_to_test: List[ModelingObject]):
        for obj in objects_to_test:
            try:
                initial_energy_footprint = round(self.initial_energy_footprints[obj], 3)
                if obj.class_as_simple_str != "Network":
                    initial_fab_footprint = round(self.initial_fab_footprints[obj], 3)
                    self.assertEqual(initial_fab_footprint, round(obj.instances_fabrication_footprint, 3))
                self.assertEqual(initial_energy_footprint, round(obj.energy_footprint, 3))
                logger.info(f"{obj.name} footprint is the same as in setup")
            except AssertionError:
                raise AssertionError(f"Footprint has changed for {obj.name}")

    def run_test_system_to_json(self, input_system):
        tmp_filepath = os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}_tmp_file.json")
        system_to_json(input_system, save_calculated_attributes=False, output_filepath=tmp_filepath)

        with (open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), 'r') as ref_file,
              open(tmp_filepath, 'r') as tmp_file):
            ref_file_content = ref_file.read()
            tmp_file_content = tmp_file.read()

            self.assertEqual(ref_file_content, tmp_file_content)

        os.remove(tmp_filepath)

    def run_test_json_to_system(self, input_system):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)

        def retrieve_obj_by_name(name, mod_obj_list):
            for obj in mod_obj_list:
                if obj.name == name:
                    return obj

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        initial_mod_objs = input_system.all_linked_objects + [input_system]
        for obj_id, obj in flat_obj_dict.items():
            corresponding_obj = retrieve_obj_by_name(obj.name, initial_mod_objs)
            for attr_key, attr_value in obj.__dict__.items():
                if isinstance(attr_value, ExplainableQuantity) or isinstance(attr_value, ExplainableHourlyQuantities):
                    self.assertEqual(getattr(corresponding_obj, attr_key), attr_value,
                                     f"Attribute {attr_key} is not equal for {obj.name}")
                    self.assertEqual(getattr(corresponding_obj, attr_key).label,attr_value.label,
                                     f"Attribute {attr_key} label is not equal for {obj.name}")

            logger.info(f"All ExplainableQuantities have right values for generated object {obj.name}")

    def _test_input_change(
            self, expl_attr, expl_attr_new_value, input_object, expl_attr_name,
            calculated_attributes_that_should_be_updated:Optional[List[ExplainableObject]]=None):
        expl_attr_new_value.label = expl_attr.label
        logger.info(f"{expl_attr_new_value.label} changing from {expl_attr} to {expl_attr_new_value.value}")
        calc_attrs_that_should_change_metadata = []
        if calculated_attributes_that_should_be_updated is not None:
            for calc_attr in calculated_attributes_that_should_be_updated:
                calc_attrs_that_should_change_metadata.append(
                    {"mod_obj_container": calc_attr.modeling_obj_container,
                     "attr_name": calc_attr.attr_name_in_mod_obj_container,
                     "initial_calc_attr": calc_attr}
                )
        system = input_object.systems[0]
        input_object.__setattr__(expl_attr_name, expl_attr_new_value)
        new_footprint = system.total_footprint
        logger.info(f"system footprint went from \n{self.initial_footprint} to \n{new_footprint}")
        self.assertNotEqual(self.initial_footprint, new_footprint)
        for calc_attr_metadata in calc_attrs_that_should_change_metadata:
            new_calc_attr = getattr(calc_attr_metadata["mod_obj_container"], calc_attr_metadata["attr_name"])
            self.assertNotEqual(
                calc_attr_metadata["initial_calc_attr"], new_calc_attr,
                f"Calculated attribute {calc_attr_metadata['attr_name']} of "
                f"{calc_attr_metadata['mod_obj_container'].name} did not change")
            logger.info(f"Calculated attribute {calc_attr_metadata['attr_name']} of "
                        f"{calc_attr_metadata['mod_obj_container'].name} changed from "
                        f"{calc_attr_metadata['initial_calc_attr']} to {new_calc_attr}")
        logger.info(f"Setting back {expl_attr_new_value.label} to {expl_attr}")
        input_object.__setattr__(expl_attr_name, expl_attr)
        self.assertEqual(system.total_footprint, self.initial_footprint)

    def _test_variations_on_obj_inputs(self, input_object: ModelingObject, attrs_to_skip=None, special_mult=None):
        if attrs_to_skip is None:
            attrs_to_skip = []
        logger.warning(f"Testing input variations on {input_object.name}")
        for expl_attr_name, expl_attr in get_instance_attributes(input_object, ExplainableObject).items():
            if expl_attr_name not in attrs_to_skip and expl_attr_name not in input_object.calculated_attributes:
                expl_attr_new_value = copy(expl_attr)
                if special_mult and expl_attr_name in special_mult:
                    logger.info(f"Multiplying {expl_attr_name} by {special_mult[expl_attr_name]}")
                    expl_attr_new_value.value *= special_mult[expl_attr_name] * u.dimensionless
                else:
                    logger.info(f"Multiplying {expl_attr_name} by 100")
                    expl_attr_new_value.value *= 100 * u.dimensionless

                self._test_input_change(expl_attr, expl_attr_new_value, input_object, expl_attr_name)

    def _run_object_link_scenario(self, scenario: ObjectLinkScenario):
        """Apply link updates through ModelingUpdate and centralize assertions + rollback."""
        logger.warning(f"Running object link scenario '{scenario.name}'")
        updates = (scenario.updates_builder(self) if callable(scenario.updates_builder)
                   else scenario.updates_builder)
        modeling_update = None
        try:
            modeling_update = ModelingUpdate(updates)
            if scenario.expected_exception is not None:
                self.fail(
                    f"Scenario '{scenario.name}' expected exception "
                    f"{scenario.expected_exception.__name__} but none was raised"
                )

            if scenario.expect_total_change:
                self.assertNotEqual(self.initial_footprint, self.system.total_footprint)
            else:
                self.assertEqual(self.initial_footprint, self.system.total_footprint)

            if scenario.expected_changed:
                self.footprint_has_changed(list(scenario.expected_changed), system=self.system)
            if scenario.expected_unchanged:
                self.footprint_has_not_changed(list(scenario.expected_unchanged))
            if scenario.post_assertions:
                scenario.post_assertions(self)
        except Exception as exc:
            if scenario.expected_exception and isinstance(exc, scenario.expected_exception):
                self.assertEqual(self.initial_footprint, self.system.total_footprint)
                return
            raise
        finally:
            if modeling_update is not None:
                modeling_update.reset_values()
                if scenario.post_reset_assertions:
                    scenario.post_reset_assertions(self)
                self.footprint_has_not_changed(list(scenario.expected_changed) + list(scenario.expected_unchanged))
                self.assertEqual(self.initial_footprint, self.system.total_footprint)

    def check_semantic_units_in_calculated_attributes(self, system):
        """Test that all calculated attributes use correct semantic units (occurrence, concurrent, byte_ram).

        Args:
            system: The System object to check
        """
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        from efootprint.api_utils.unit_mappings import (
            TIMESERIES_UNIT_MIGRATIONS, SCALAR_RAM_ATTRIBUTES_TO_MIGRATE, RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE
        )

        errors = []

        def check_unit(calc_attr, mod_obj, calc_attr_name, key_str=""):
            """Check a single attribute's unit and append errors if incorrect.

            Args:
                calc_attr: The attribute to check
                mod_obj: The modeling object that contains this attribute
                calc_attr_name: The attribute name
                key_str: Optional string for dict keys (e.g., "[key_name]")
            """
            unit_str = str(calc_attr.unit)
            attr_path = f"{calc_attr_name}{key_str}"

            # Check occurrence/concurrent units
            for (mapping_class, mapping_attr), expected_unit in TIMESERIES_UNIT_MIGRATIONS.items():
                if mapping_attr == calc_attr_name and mod_obj.is_subclass_of(mapping_class):
                    if expected_unit not in unit_str:
                        errors.append(
                            f"{mod_obj.name}.{attr_path} should use '{expected_unit}' unit but has '{unit_str}'")
                    break

            # Check RAM units (should contain _ram)
            for (mapping_class, mapping_attr) in SCALAR_RAM_ATTRIBUTES_TO_MIGRATE | RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE:
                if mapping_attr == calc_attr_name and mod_obj.is_subclass_of(mapping_class):
                    if '_ram' not in unit_str:
                        errors.append(
                            f"{mod_obj.name}.{attr_path} should use byte_ram unit (e.g., gigabyte_ram) but has '{unit_str}'")
                    break

        for mod_obj in system.all_linked_objects + [system]:
            for calc_attr_name in mod_obj.calculated_attributes:
                calc_attr = getattr(mod_obj, calc_attr_name)

                # Handle ExplainableObjectDict
                if isinstance(calc_attr, ExplainableObjectDict):
                    for key, value in calc_attr.items():
                        check_unit(value, mod_obj, calc_attr_name, value.key_in_dict)
                elif isinstance(calc_attr, EmptyExplainableObject):
                    pass
                else:
                    check_unit(calc_attr, mod_obj, calc_attr_name)

        if errors:
            self.fail("Unit errors found:\n" + "\n".join(errors))
