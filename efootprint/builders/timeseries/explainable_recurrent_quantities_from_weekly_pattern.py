from copy import copy, deepcopy
from numbers import Integral, Real
from typing import Literal

import numpy as np
from pint import Quantity
from pint.errors import UndefinedUnitError

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.utils.display import format_display_number

_FLOAT32_MAX = float(np.finfo(np.float32).max)


class WeeklyPatternValidationError(ValueError):
    """One or more invalid fields in authored weekly-pattern inputs."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("; ".join(f"{error['path']}: {error['message']}" for error in errors))


def _is_finite_float32_number(value) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and np.isfinite(value)
        and abs(value) <= _FLOAT32_MAX
    )


@ExplainableObject.register_subclass(
    lambda data: isinstance(data.get("form_inputs"), dict)
    and "unit" in data["form_inputs"]
    and "profiles" in data["form_inputs"]
)
class ExplainableRecurrentQuantitiesFromWeeklyPattern(ExplainableRecurrentQuantities):
    """Recurrent quantities composed from named day profiles and their hourly ranges."""

    @classmethod
    def from_json_dict(cls, data):
        return cls(form_inputs=data["form_inputs"], label=data["label"])

    def __init__(
        self,
        form_inputs: dict,
        label: str = "no label",
        left_parent=None,
        right_parent=None,
        operator: str = None,
        source: Source = None,
        confidence: Literal["low", "medium", "high"] | None = None,
        comment: str = None,
    ):
        self.form_inputs = deepcopy(form_inputs)
        self._validate_form_inputs()
        super().__init__(
            value=self._compose_week(),
            label=label,
            left_parent=left_parent,
            right_parent=right_parent,
            operator=operator,
            source=source,
            confidence=confidence,
            comment=comment,
        )

    def _validate_form_inputs(self) -> None:
        errors = []

        def add(path: str, code: str, message: str) -> None:
            errors.append({"path": path, "code": code, "message": message})

        if not isinstance(self.form_inputs, dict):
            raise WeeklyPatternValidationError(
                [{"path": "form_inputs", "code": "invalid_type", "message": "Form inputs must be an object."}]
            )

        unit = self.form_inputs.get("unit")
        if not isinstance(unit, str) or not unit.strip():
            add("unit", "invalid_unit", "Unit must be a non-empty Pint unit string.")
        else:
            try:
                parsed_unit = Quantity(1, unit)
            except (TypeError, ValueError, UndefinedUnitError):
                add("unit", "invalid_unit", f"'{unit}' is not a valid Pint unit.")
            else:
                if str(parsed_unit.units) == "dimensionless":
                    add("unit", "invalid_unit", "Unit must not be dimensionless.")

        profiles = self.form_inputs.get("profiles")
        if not isinstance(profiles, list):
            add("profiles", "invalid_type", "Profiles must be a list.")
            raise WeeklyPatternValidationError(errors)
        if not 1 <= len(profiles) <= 7:
            add("profiles", "profile_count", "A weekly pattern must contain between 1 and 7 profiles.")

        seen_names = set()
        day_owners = [None] * 7
        for profile_index, profile in enumerate(profiles):
            profile_path = f"profiles[{profile_index}]"
            if not isinstance(profile, dict):
                add(profile_path, "invalid_type", "Each profile must be an object.")
                continue

            name_path = f"{profile_path}.name"
            name = profile.get("name")
            if not isinstance(name, str) or not name.strip():
                add(name_path, "empty_profile_name", "Profile name must be a non-empty string.")
            elif name in seen_names:
                add(name_path, "duplicate_profile_name", f"Profile name '{name}' must be unique.")
            else:
                seen_names.add(name)

            baseline_path = f"{profile_path}.baseline"
            if not _is_finite_float32_number(profile.get("baseline")):
                add(baseline_path, "invalid_number", "Baseline must be a finite number representable as float32.")

            days = profile.get("days")
            if not isinstance(days, list):
                add(f"{profile_path}.days", "invalid_type", "Profile days must be a list.")
            else:
                for day_index, day in enumerate(days):
                    day_path = f"{profile_path}.days[{day_index}]"
                    if not isinstance(day, Integral) or isinstance(day, bool) or not 0 <= day <= 6:
                        add(day_path, "invalid_day", "Day must be an integer from 0 (Monday) to 6 (Sunday).")
                    elif day_owners[day] is not None:
                        add(day_path, "duplicate_day_assignment", f"Day {day} is already assigned to another profile.")
                    else:
                        day_owners[day] = profile_index

            ranges = profile.get("ranges")
            if not isinstance(ranges, list):
                add(f"{profile_path}.ranges", "invalid_type", "Profile ranges must be a list.")
                continue

            previous_start = None
            covered_until = 0
            for range_index, time_range in enumerate(ranges):
                range_path = f"{profile_path}.ranges[{range_index}]"
                if not isinstance(time_range, dict):
                    add(range_path, "invalid_type", "Each range must be an object.")
                    continue

                start = time_range.get("start")
                end = time_range.get("end")
                start_valid = isinstance(start, Integral) and not isinstance(start, bool) and 0 <= start <= 23
                end_valid = isinstance(end, Integral) and not isinstance(end, bool) and 1 <= end <= 24
                if not start_valid:
                    add(f"{range_path}.start", "invalid_start_hour", "Range start must be an integer from 0 to 23.")
                if not end_valid:
                    add(f"{range_path}.end", "invalid_end_hour", "Range end must be an integer from 1 to 24.")
                if not _is_finite_float32_number(time_range.get("value")):
                    add(
                        f"{range_path}.value",
                        "invalid_number",
                        "Range value must be a finite number representable as float32.",
                    )

                if not start_valid or not end_valid:
                    continue
                if start >= end:
                    add(f"{range_path}.start", "invalid_range", "Range start must be earlier than its end.")
                    continue
                if previous_start is not None and start < previous_start:
                    add(f"{range_path}.start", "ranges_not_ordered", "Ranges must be ordered by start hour.")
                    covered_until = end
                else:
                    if previous_start is not None and start < covered_until:
                        add(f"{range_path}.start", "ranges_overlap", "Ranges in a profile must not overlap.")
                    covered_until = max(covered_until, end)
                previous_start = start

        for day, owner in enumerate(day_owners):
            if owner is None:
                add("profiles", "missing_day_assignment", f"Day {day} must be assigned to exactly one profile.")

        if errors:
            raise WeeklyPatternValidationError(errors)

    def _compose_week(self) -> Quantity:
        week = np.empty((7, 24), dtype=np.float32)
        for profile in self.form_inputs["profiles"]:
            day_values = np.full(24, float(profile["baseline"]), dtype=np.float32)
            for time_range in profile["ranges"]:
                day_values[time_range["start"] : time_range["end"]] = float(time_range["value"])
            week[profile["days"]] = day_values
        return Quantity(week.reshape(168), self.form_inputs["unit"])

    @property
    def form_inputs_for_display(self):
        """Authored profile values as ordered, human-readable comparison parameters."""
        output = {"unit": self.form_inputs["unit"]}
        day_names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        unit = self.form_inputs["unit"]
        for profile_index, profile in enumerate(self.form_inputs["profiles"], start=1):
            prefix = f"profile {profile_index}"
            output[f"{prefix} name"] = profile["name"]
            output[f"{prefix} days"] = ", ".join(day_names[day] for day in profile["days"]) or "none"
            output[f"{prefix} baseline"] = f"{format_display_number(float(profile['baseline']))} {unit}"
            for range_index, time_range in enumerate(profile["ranges"], start=1):
                output[f"{prefix} range {range_index}"] = (
                    f"{time_range['start']:02d}:00–{time_range['end']:02d}:00 = "
                    f"{format_display_number(float(time_range['value']))} {unit}"
                )
        return output

    def to_json(self, with_formula=False):
        output_dict = {"form_inputs": deepcopy(self.form_inputs)}
        output_dict.update(super(ExplainableRecurrentQuantities, self).to_json(with_formula))
        return output_dict

    def __copy__(self):
        return ExplainableRecurrentQuantitiesFromWeeklyPattern(
            form_inputs=deepcopy(self.form_inputs),
            label=copy(self.label),
            source=copy(self.source),
            confidence=self.confidence,
            comment=self.comment,
        )
