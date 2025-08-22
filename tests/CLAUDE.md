When fixing tests, try to fix all tests at once.
When using patchs, favor the @patch syntax and make sure you use new_callable=PropertyMock when mocking properties.
If in one test changing a value of an object that is reused in other tests (i.e. objects linked to the class itself, like self.my_tested_efootprint_object), make sure to reset that value at the end of the test, or use a patch.

# Good to know
- default_values defined in ModelingObject classes don’t mean that the parameters can be omitted when defining a ModelingObject. It means that they can be omitted when creating the object from the ChildModelingObjectClass.from_defaults method.
- No need to test ModelingObject’s default values.
- No need to test ModelingObject’s calculated_attributes list.
- No need to test inheritance. In general, avoid implementing super obvious tests that don’t bring much value.
- ExplainableObjects without parents should have a label.

# Setting ExplainableObject parameters in ModelingObjects
When setting ExplainableObject parameters of ModelingObjects in tests, always use real ExplainableObjects (like ExplainableQuantity or ExplainableHourlyQuantity) instead of mocks so that e-footprint’s type checks don’t raise errors.

# Mocking ModelingObject parameters in ModelingObjects
When mocking a ModelingObject parameter in another ModelingObject, always specify the typing. For example, instead of doing
real_journey = EdgeUsageJourney(
            "test journey", 
            edge_processes=[], 
            edge_device=MagicMock(),
            usage_span=SourceValue(1 * u.year)
        )
do
real_journey = EdgeUsageJourney(
            "test journey", 
            edge_processes=[], 
            edge_device=MagicMock(spec=EdgeDevice),
            usage_span=SourceValue(1 * u.year)
        )

# Changing the value of a ModelingObject’s modeling_obj_containers property
It is not possible to directly set the modeling_obj_containers attribute of a ModelingObject when testing it, because modeling_obj_containers is a property:
@property
    def modeling_obj_containers(self):
        return list(set(
            [contextual_mod_obj_container.modeling_obj_container
             for contextual_mod_obj_container in self.contextual_modeling_obj_containers
             if contextual_mod_obj_container.modeling_obj_container is not None]))


Instead, you should use the set_modeling_obj_containers utils function from @tests/utils.py, like so:

mock_system = MagicMock(spec=ModelingObject)
set_modeling_obj_containers(self.edge_usage_pattern, [mock_system])