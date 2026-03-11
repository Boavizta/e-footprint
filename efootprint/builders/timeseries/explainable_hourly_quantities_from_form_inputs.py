from copy import deepcopy, copy
from datetime import datetime
import numpy as np
from pint import Quantity
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.constants.units import u


@ExplainableObject.register_subclass(lambda d: "form_inputs" in d and "initial_volume" in d["form_inputs"]
                                               and "net_growth_rate_in_percentage" in d["form_inputs"])
class ExplainableHourlyQuantitiesFromFormInputs(ExplainableHourlyQuantities):
    """
    ExplainableHourlyQuantities generated from simple form inputs:
    - start_date, modeling_duration, initial_volume, net_growth_rate

    Stores form inputs in JSON so they can be edited later.
    Computes timeseries lazily when .value is first accessed.
    """

    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None

        return cls(form_inputs=d["form_inputs"], label=d["label"], source=source)

    def __init__(self, form_inputs: dict, label: str = "no label",
                 left_parent=None, right_parent=None, operator: str = None, source: Source = None):
        """
        Initialize with form inputs dict containing:
        - start_date: str (YYYY-MM-DD)
        - modeling_duration_value: float
        - modeling_duration_unit: str ("month" or "year")
        - initial_volume: float
        - initial_volume_unit: str (unit string)
        - initial_volume_timespan: str ("day", "month", or "year")
        - net_growth_rate_in_percentage: float
        - net_growth_rate_timespan: str ("month" or "year")
        """
        self.form_inputs = form_inputs

        # Don't compute value yet - will be computed lazily
        # Initialize parent with None value, will be computed in property
        super().__init__(
            value={}, start_date=datetime.strptime(form_inputs["start_date"], "%Y-%m-%d"),
            label=label, left_parent=left_parent,
            right_parent=right_parent, operator=operator, source=source
        )
        # No need to handle json_compressed_value_data because form inputs are already a great compression in themselves
        del self.json_compressed_value_data

    @property
    def value(self):
        """Lazy computation of hourly timeseries from form inputs."""
        if self._value is None:
            self._value = self._compute_hourly_timeseries()

        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value

    @value.deleter
    def value(self):
        self._value = None

    def _compute_hourly_timeseries(self) -> Quantity:
        """
        Compute hourly timeseries from form inputs using exponential growth.
        Logic adapted from TimeseriesForm.generate_hourly_starts().
        """
        # Extract form inputs
        modeling_duration_value = float(self.form_inputs["modeling_duration_value"])
        modeling_duration_unit = self.form_inputs["modeling_duration_unit"]
        initial_volume = float(self.form_inputs["initial_volume"])
        initial_volume_timespan = self.form_inputs["initial_volume_timespan"]
        net_growth_rate_in_percentage = float(self.form_inputs["net_growth_rate_in_percentage"])
        net_growth_rate_timespan = self.form_inputs["net_growth_rate_timespan"]
        volume_unit = u.occurrence

        # Convert modeling duration to days
        unit_day_mapping = {"day": 1, "month": 30, "year": 365}
        modeling_duration_in_days = modeling_duration_value * unit_day_mapping[modeling_duration_unit]
        num_days = int(modeling_duration_in_days)

        # Convert growth rate to daily rate
        growth_timespan_in_days = unit_day_mapping[net_growth_rate_timespan]
        daily_growth_rate = (1 + net_growth_rate_in_percentage / 100) ** (1 / growth_timespan_in_days)

        # Convert initial volume to first daily volume
        volume_timespan_in_days = unit_day_mapping[initial_volume_timespan]
        if daily_growth_rate == 1:
            exponential_sum = volume_timespan_in_days
        else:
            exponential_sum = (daily_growth_rate ** volume_timespan_in_days - 1) / (daily_growth_rate - 1)

        first_daily_volume = initial_volume / exponential_sum

        # Compute daily values with exponential growth
        days = np.arange(num_days)
        daily_values = first_daily_volume * (daily_growth_rate ** days)

        # Convert to hourly values (constant within each day)
        hourly_values = np.repeat(daily_values / 24, 24).astype(np.float32)

        return Quantity(hourly_values, volume_unit)

    def to_json(self, save_calculated_attributes=False):
        output_dict = {"form_inputs": self.form_inputs}

        output_dict.update(super(ExplainableHourlyQuantities, self).to_json(save_calculated_attributes))

        return output_dict

    def __copy__(self):
        return ExplainableHourlyQuantitiesFromFormInputs(
            deepcopy(self.form_inputs), label=copy(self.label), source=copy(self.source))
