import numpy as np
import pandas as pd
import pint_pandas

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities, EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.servers.server_base_class import Server
from efootprint.core.hardware.storage import Storage


class OnPremise(Server):
    def __init__(self, name: str, carbon_footprint_fabrication: SourceValue, power: SourceValue,
                 lifespan: SourceValue, idle_power: SourceValue, ram: SourceValue, cpu_cores: SourceValue,
                 power_usage_effectiveness: SourceValue, average_carbon_intensity: SourceValue,
                 server_utilization_rate: SourceValue, base_ram_consumption: SourceValue,
                 base_cpu_consumption: SourceValue, storage: Storage,
                 fixed_nb_of_instances: SourceValue | EmptyExplainableObject = None):
        super().__init__(
            name, carbon_footprint_fabrication, power, lifespan, idle_power, ram, cpu_cores, power_usage_effectiveness,
            average_carbon_intensity, server_utilization_rate, base_ram_consumption, base_cpu_consumption, storage)
        self.fixed_nb_of_instances = fixed_nb_of_instances
        if self.fixed_nb_of_instances is not None:
            if not fixed_nb_of_instances.value.check("[]"):
                raise ValueError("Variable 'fixed_nb_of_instances' shouldn’t have any dimensionality")
        else:
            self.fixed_nb_of_instances = EmptyExplainableObject()
        self.fixed_nb_of_instances.set_label(
            f"User defined number of {self.name} instances").to(u.dimensionless)

    def update_nb_of_instances(self):
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            self.nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
        else:
            max_nb_of_instances = self.raw_nb_of_instances.max().ceil().to(u.dimensionless)

            nb_of_instances_df = pd.DataFrame(
                {"value": pint_pandas.PintArray(
                        max_nb_of_instances.magnitude * np.ones(len(self.raw_nb_of_instances)), dtype=u.dimensionless)},
                index=self.raw_nb_of_instances.value.index
            )

            if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
                if max_nb_of_instances > self.fixed_nb_of_instances:
                    raise ValueError(
                        f"The number of {self.name} instances computed from its resources need is superior to the "
                        f"number of instances specified by the user "
                        f"({max_nb_of_instances.value} > {self.fixed_nb_of_instances})")
                else:
                    fixed_nb_of_instances_df = pd.DataFrame(
                        {"value": pint_pandas.PintArray(
                            np.full(len(self.raw_nb_of_instances), self.fixed_nb_of_instances.value),
                            dtype=u.dimensionless
                        )},
                        index=self.raw_nb_of_instances.value.index
                    )
                    nb_of_instances_re_calculate = ExplainableHourlyQuantities(
                        fixed_nb_of_instances_df,
                        "Nb of instances",
                        left_parent=self.raw_nb_of_instances,
                        right_parent=self.fixed_nb_of_instances
                    )
                    self.nb_of_instances = nb_of_instances_re_calculate.set_label(
                        f"Fixed number of {self.name} instances")
            else:
                self.nb_of_instances = ExplainableHourlyQuantities(
                    nb_of_instances_df,
                    f"Hourly number of {self.name} instances",
                    left_parent=self.raw_nb_of_instances,
                    right_parent=self.fixed_nb_of_instances,
                    operator="depending on not being empty"
                )
