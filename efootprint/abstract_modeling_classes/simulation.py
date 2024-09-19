from datetime import datetime

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities
from efootprint.core.usage.usage_pattern import UsagePattern


class Simulation:
    def __init__(self, simulation_date: datetime, old_value, new_value):
        if type(old_value) != type(new_value):
            raise ValueError(f"In simulations old and new values should have same type, got "
                             f"{type(old_value)} and {type(new_value)}")
        if issubclass(type(old_value), ExplainableObject):
            if old_value.modeling_obj_container.id != self.id:
                raise ValueError(f"{old_value.label} belongs to {old_value.modeling_obj_container.name} so it can’t be"
                                 f" affected by a simulation from {self.name}")
            old_value_computation_chain = old_value.update_computation_chain
            all_values_to_recompute_ancestors = set(sum(
                [value.all_ancestors_with_id for value in old_value_computation_chain], start=[]))
            old_value_computation_chain_ids = [elt.id for elt in old_value_computation_chain]
            ancestors_not_in_computation_chain = [ancestor for ancestor in all_values_to_recompute_ancestors
                                                  if ancestor.id not in old_value_computation_chain_ids]
            hourly_quantities_ancestors_not_in_computation_chain = [
                ancestor for ancestor in ancestors_not_in_computation_chain
                if isinstance(ancestor, ExplainableHourlyQuantities)]

            happens_during_a_simulation_period = False
            hourly_quantities_to_filter = []
            simulation_date_as_hourly_freq = pd.Timestamp(simulation_date).to_period(freq="h")
            for ancestor in hourly_quantities_ancestors_not_in_computation_chain:
                if simulation_date_as_hourly_freq in ancestor.value.index:
                    hourly_quantities_to_filter.append(ancestor)
                    if isinstance(ancestor.modeling_obj_container, UsagePattern):
                        happens_during_a_simulation_period = True

            if not happens_during_a_simulation_period:
                raise ValueError(f"Can’t start a simulation on the {simulation_date} for {self.name} because the date "
                                 f"doesn’t belong to an existing modeling period")

            for hourly_quantities in hourly_quantities_to_filter:
                pass

