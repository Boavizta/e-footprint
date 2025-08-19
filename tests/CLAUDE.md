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


For example, instead of doing self.edge_usage_pattern.modeling_obj_containers = mock_system, do something like:

mock_system = MagicMock(spec=ModelingObject)
mock_contextual_mod_obj_container = MagicMock()
mock_contextual_mod_obj_container.modeling_obj_container = mock_system
self.edge_usage_pattern.contextual_modeling_obj_containers = [mock_contextual_mod_obj_container]