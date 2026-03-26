# Unified Quantity Display Plan

## Goal

Create a single, centralized mechanism for displaying quantities with human-readable units based on magnitude.
For example, `22000 kg` should display as `22 t`, and `0.003 kWh` as `3 Wh`.

Currently this logic is scattered, inconsistent, and limited to CO2 kg→tonne conversion only.


## Current State

### e-footprint

| File | Line(s) | What it does | Problem |
|---|---|---|---|
| `efootprint/utils/tools.py` | 33-50 | `format_co2_amount()` / `display_co2_amount()`: threshold at 501 kg, hardcoded kg→tonne | Only handles CO2 mass, threshold is arbitrary, returns raw strings not Pint quantities |
| `explainable_quantity.py` | 210-214 | `__str__`: `round(self.value, 2)` with Pint default formatting | No magnitude-aware unit scaling |
| `explainable_hourly_quantities.py` | 444-460 | `__str__`: `{:~}` compact unit + round 2 decimals per element | No magnitude-aware unit scaling |
| `explainable_recurrent_quantities.py` | 188-203 | `__str__`: same as hourly | No magnitude-aware unit scaling |
| `core/system.py` | 317-348 | Bar chart: hardcoded `magnitude_kg / 1000`, uses `format_co2_amount` | Hardcoded conversion |
| `utils/impact_repartition/sankey.py` | 581-710 | Uses `format_co2_amount` / `display_co2_amount` | Hardcoded CO2-only conversion |
| `utils/plot_baseline_and_simulation_data.py` | 65 | `plt.ylabel(f"{baseline_q.units:~}")` | No magnitude-aware unit scaling |

### e-footprint-interface

| File | Line(s) | What it does | Problem |
|---|---|---|---|
| `explainable_objects_web.py` | 72-79 | `ExplainableQuantityWeb.rounded_value`: `round(self.value, 2)`, `.unit` returns raw Pint unit | No magnitude-aware scaling |
| `model_web_utils.py` | 42-43 | `get_reindexed_array_from_dict`: hardcoded `.to(u.tonne)` and `* u.tonne` | Hardcoded tonne assumption |
| `emissions_calculation_service.py` | 46-105 | Calls `get_reindexed_array_from_dict` (which hardcodes tonnes), then `to_rounded_daily_values` | Inherits hardcoded tonne |
| `sankey_views.py` | 162-323 | Uses `display_co2_amount(format_co2_amount(kg))` | Hardcoded CO2-only conversion |
| `form_field_generator.py` | 156 | `f"{default.value.units:~P}"` for form unit labels | Not magnitude-aware (but OK here since it's the input unit, not a display of a computed value) |
| `views.py` | 231-232 | Excel export: raw `magnitude` + `str(units)` | No scaling |
| `result_graph.html` | 20, 36 | Hardcoded `<p class="h8">t CO<sub>2</sub>-eq</p>` | Hardcoded tonne label |
| `tooltip.js` | 79-122 | Hardcoded `.toFixed(2) + " t CO₂-eq"` | Hardcoded tonne label and unit |
| `calculated_attribute_chart.html` | 6 | `data-unit="{{ web_ehq.unit }}"` passes raw Pint unit | No scaling |
| `source_table.html` | 31-32 | Raw `{{ value.magnitude }}` / `{{ value.units }}` | No scaling |
| `explainable_quantity.html` | 7 | `{{ item.rounded_value }}` | No scaling |


## Design

### New module: `efootprint/utils/display.py`

This module provides two public functions:

#### 1. `best_display_unit(quantity: Quantity) -> Unit`

Given a Pint `Quantity` (scalar or numpy array), returns the most human-readable `Unit` from its
unit family. This is the only unit-selection primitive.

- For **scalar** quantities: uses `abs(magnitude)` to select the unit.
- For **array** quantities (numpy): uses `mean(abs(magnitude))` to select the unit. This covers
  timeseries where the mean represents the typical value the user reads.

Algorithm:
- If the magnitude is an ndarray, compute `representative = mean(abs(magnitude))`; otherwise
  `representative = abs(magnitude)`
- If representative is 0, return the quantity's current unit unchanged
- Look up the unit family for the quantity's dimension (via `is_compatible_with`)
- If no family matches (e.g. `cpu_core`, `occurrence`), return the quantity's current unit
- Iterate the family from largest to smallest unit
- Return the first unit where `representative` converted to that unit is `>= 1`
- Fallback: return the smallest unit in the family

#### 2. `format_quantity_for_display(quantity: Quantity, rounding: int = 2) -> Quantity`

Convenience wrapper: converts to best display unit and rounds. Returns a `Quantity` with the
appropriate unit and rounded magnitude (scalar or array). Callers can extract `.magnitude` and
`.units` as needed.

#### `display_quantity` and `display_unit` properties on Explainable classes

`ExplainableQuantity`, `ExplainableHourlyQuantities`, and `ExplainableRecurrentQuantities` each
get two new properties in e-footprint:

```python
@property
def display_quantity(self):
    return format_quantity_for_display(self.value)

@property
def display_unit(self):
    return self.display_quantity.units
```

`display_unit` returns a Pint `Unit` object, consistent with the existing `unit` property.
Formatting to a human-readable string is a separate concern handled by the
`human_readable_unit(unit)` helper in `display.py`.

#### `human_readable_unit(unit: Unit) -> str` helper

A simple helper in `display.py` that wraps the non-intuitive Pint format spec:

```python
def human_readable_unit(unit: Unit) -> str:
    return f"{unit:~P}"
```

Templates and other display code call this when they need a string (e.g.
`human_readable_unit(obj.display_unit)` → `"kg"`).

These live on the core classes so both e-footprint and the interface can use them directly.
`ExplainableQuantityWeb` (interface) no longer needs its own display logic — it delegates to the
upstream properties.

#### Call site strategies

While `best_display_unit` handles both scalars and arrays, **charts and diagrams with multiple
series** still need to pick a single reference quantity to determine the shared axis unit:

- **Result charts** (`EmissionsCalculationService`): Pass `system.total_footprint.value` (the sum
  timeseries) to `best_display_unit`. Its mean represents the y-axis magnitude.

- **Sankey diagrams** (`sankey_views.py`, `sankey.py`): Pass `total_system_kg * u.kg` (scalar).
  This is the root total, which equals `System`'s total unless classes are excluded.

- **`system.py` bar chart**: Same as result charts — use `total_footprint`.

- **Single timeseries `__str__`**: Pass `self.value` directly — `best_display_unit` computes
  the mean internally.

- **Single scalar `__str__`** (`ExplainableQuantity`): Pass `self.value` directly.

#### Unit families

Defined as an ordered list (smallest to largest) of preferred display units per dimension.
Pint automatically handles decimal prefixes (kilo, mega, giga, etc.) for custom units like
`byte_ram`, so we don't need to manually define `kB_ram`, `GB_ram`, etc.:

```python
UNIT_FAMILIES: List[List[Unit]] = [
    [u.mg, u.g, u.kg, u.tonne],                          # mass
    [u.mWh, u.Wh, u.kWh, u.MWh],                         # energy
    [u.mW, u.W, u.kW, u.MW],                              # power
    [u.byte, u.kB, u.MB, u.GB, u.TB],                    # data transfer
    [u.byte_ram, u.kB_ram, u.MB_ram, u.GB_ram, u.TB_ram], # RAM
]
```

> **Verify at implementation time**: confirm that Pint prefix composition works for `byte_ram`
> (i.e. `u.kB_ram` resolves correctly). If not, add explicit definitions to `custom_units.txt`.

Units not in any family (e.g. `cpu_core`, `gpu`, `occurrence`, `concurrent`, `billion`) pass through
unchanged — `best_display_unit` returns their current unit.


## Patch Steps

### Step 1. Verify RAM unit prefixes work in Pint

File: `efootprint/constants/custom_units.txt`

Verify that `u.kB_ram`, `u.MB_ram`, `u.GB_ram`, `u.TB_ram` resolve via Pint prefix composition.
If not, add explicit definitions.


### Step 2. Create `efootprint/utils/display.py`

New file with:

```python
import math
from typing import Optional, List
import numpy as np
from pint import Quantity, Unit
from efootprint.constants.units import u

UNIT_FAMILIES: List[List[Unit]] = [
    [u.mg, u.g, u.kg, u.tonne],
    [u.mWh, u.Wh, u.kWh, u.MWh],
    [u.mW, u.W, u.kW, u.MW],
    [u.byte, u.kB, u.MB, u.GB, u.TB],
    [u.byte_ram, u.kB_ram, u.MB_ram, u.GB_ram, u.TB_ram],
]


def _get_unit_family(quantity: Quantity) -> Optional[List[Unit]]:
    for family in UNIT_FAMILIES:
        if quantity.is_compatible_with(family[0]):
            return family
    return None


def best_display_unit(quantity: Quantity) -> Unit:
    """Return the most human-readable unit for a Quantity (scalar or numpy array).

    For arrays, uses mean(abs(magnitude)) as the representative value.
    """
    magnitude = quantity.magnitude
    if isinstance(magnitude, np.ndarray):
        representative = np.mean(np.abs(magnitude))
    else:
        representative = abs(magnitude)
    if representative == 0:
        return quantity.units
    family = _get_unit_family(quantity)
    if family is None:
        return quantity.units
    for unit in reversed(family):
        if representative * quantity.units.to(unit) >= 1:
            return unit
    return family[0]


def _round_to_sig_figs(value: float, sig_figs: int = 3) -> float:
    if value == 0:
        return 0.0
    digits = sig_figs - int(math.floor(math.log10(abs(value)))) - 1
    return round(value, digits)


def format_quantity_for_display(quantity: Quantity, sig_figs: int = 3) -> Quantity:
    """Convert a Quantity (scalar or array) to its best display unit and round to significant figures."""
    display_unit = best_display_unit(quantity)
    converted = quantity.to(display_unit)
    magnitude = converted.magnitude
    if isinstance(magnitude, np.ndarray):
        rounded = np.vectorize(lambda v: _round_to_sig_figs(v, sig_figs))(magnitude)
    else:
        rounded = _round_to_sig_figs(magnitude, sig_figs)
    return rounded * display_unit


def human_readable_unit(unit: Unit) -> str:
    """Format a Pint Unit as a compact human-readable string (e.g. kg, MWh, t)."""
    return f"{unit:~P}"
```


### Step 3. Add tests for `efootprint/utils/display.py`

File: `tests/test_display.py` (or `tests/test_display_utils.py`)

Test cases for `best_display_unit`:
- Scalar quantities: `22000 * u.kg` → `u.tonne`, `300 * u.g` → `u.g`, `4500 * u.kWh` → `u.MWh`
- Zero: `0 * u.kg` → keeps `u.kg`
- No family: `42 * u.cpu_core` → `u.cpu_core`
- Very small values: `0.005 * u.kg` → `u.g`
- Boundary: `1000 * u.kg` → `u.tonne`, `999 * u.kg` → `u.kg`
- Array (mean selects unit): `np.array([100, 200, 50000]) * u.kg` → mean is ~16733 kg → `u.tonne`
- Array mostly small: `np.array([1, 2, 3]) * u.kg` → mean is 2 kg → `u.kg`
- Array all zeros: `np.zeros(10) * u.kg` → keeps `u.kg`

Test cases for `format_quantity_for_display` (3 significant figures):
- `22000 * u.kg` → `22.0 * u.tonne`
- `123456 * u.kg` → `123 * u.tonne`
- `300 * u.g` → `300.0 * u.g`
- `4500 * u.kWh` → `4.5 * u.MWh`
- `1.2345 * u.kg` → `1.23 * u.kg`
- `np.array([1000, 2000, 3000]) * u.kg` → `np.array([1.0, 2.0, 3.0]) * u.tonne`


### Step 4. Add `display_quantity` and `display_unit` properties to Explainable classes

Add to `ExplainableQuantity`, `ExplainableHourlyQuantities`, and `ExplainableRecurrentQuantities`:

```python
from efootprint.utils.display import format_quantity_for_display

@property
def display_quantity(self):
    return format_quantity_for_display(self.value)

@property
def display_unit(self):
    return self.display_quantity.units
```

These properties are the canonical way to get a display-ready value from any Explainable object,
used by both `__str__` (next steps) and the interface templates.


### Step 5. Update `ExplainableQuantity.__str__` to use auto-scaling

File: `efootprint/abstract_modeling_classes/explainable_quantity.py`

Before:
```python
def __str__(self):
    if isinstance(self.value, Quantity):
        return f"{round(self.value, 2)}"
    else:
        return str(self.value)
```

After:
```python
def __str__(self):
    if isinstance(self.value, Quantity):
        return str(self.display_quantity)
    else:
        return str(self.value)
```


### Step 6. Update `ExplainableHourlyQuantities.__str__` to use auto-scaling

File: `efootprint/abstract_modeling_classes/explainable_hourly_quantities.py`

The timeseries `__str__` should pick the best display unit, then display all sampled values in that
unit. `best_display_unit` handles the mean-of-abs logic internally for arrays.

Before:
```python
compact_unit = "{:~}".format(self.unit)
# ... rounds individual magnitudes to 2 decimals
```

After:
```python
display_unit = best_display_unit(self.value)
compact_unit = human_readable_unit(display_unit)
converted_values = self.value.to(display_unit)
# ... rounds individual magnitudes of converted_values to 2 decimals
```


### Step 7. Update `ExplainableRecurrentQuantities.__str__` (same pattern as Step 6)

File: `efootprint/abstract_modeling_classes/explainable_recurrent_quantities.py`

Same pattern: `best_display_unit(self.value)`, convert, display.


### Step 8. Delete `format_co2_amount` and `display_co2_amount`

File: `efootprint/utils/tools.py`

No need for backward compatibility — there are no external callers.

Delete both `format_co2_amount` and `display_co2_amount` entirely. All callers should use
`format_quantity_for_display` and `human_readable_unit` from `efootprint/utils/display.py` directly.

> **Note**: The kg→tonne threshold changes from 501 to 1000 (natural boundary at magnitude >= 1 in
> tonnes). This is the correct behavior.


### Step 9. Update `system.py` bar chart generation

File: `efootprint/core/system.py`

Remove hardcoded `magnitude_kg / 1000`. Use the system's `total_footprint` to determine the
display unit — this is the same reference the result charts will use.

Before:
```python
value_colname = "tonnes CO2 emissions"
magnitude_kg = quantity.magnitude
magnitude_tonnes = magnitude_kg / 1000
```

After:
```python
# Determine display unit from total footprint (best_display_unit handles array mean internally)
chart_unit = best_display_unit(self.total_footprint.value)
chart_unit_str = human_readable_unit(chart_unit)
value_colname = f"{chart_unit_str} CO2 emissions"

# In the loop — keep quantity as-is, just convert to chart_unit:
converted_magnitude = quantity.to(chart_unit).magnitude
```


### Step 10. Refactor `sankey.py` in e-footprint

File: `efootprint/utils/impact_repartition/sankey.py`

#### 10a. Remove `_get_value_kg` — keep Pint quantities throughout

Currently `_get_value_kg` extracts a raw float in kg from ExplainableQuantity/ExplainableHourlyQuantities.
This loses the Pint quantity early and forces all downstream code to work with raw floats + implicit
"kg" assumption. Instead, keep values as Pint quantities as long as possible.

Replace `_get_value_kg` with a `_get_total_value` that returns a Pint `Quantity`:

```python
@staticmethod
def _get_total_value(value: Any) -> Quantity:
    if isinstance(value, EmptyExplainableObject):
        return 0.0 * u.kg
    if isinstance(value, ExplainableHourlyQuantities):
        return value.sum().value
    return value.value
```

Update `_ResolvedFootprintSource` to hold a `Quantity` instead of `float`:
```python
@dataclass(frozen=True)
class _ResolvedFootprintSource:
    source: ModelingObject
    value: Quantity  # was value_kg: float
```

Propagate this through `_iter_resolved_sources`, `_sum_leaf_values`, `_traverse`,
`_handle_impact_source`, etc. Internal arithmetic (comparisons, scaling) works the same with Pint
quantities. `_total_system_kg` becomes `_total_system_value: Quantity`.

Link values (currently stored in tonnes as floats) should be stored as Pint quantities too.

#### 10b. Use `best_display_unit` from root total for all display formatting

Once `_total_system_value` is a Quantity, determining the display unit is trivial:

```python
root_display_unit = best_display_unit(self._total_system_value)
```

All hover labels and link labels convert to this unit:
```python
display_val = format_quantity_for_display(node_value)
amount_str = f"{display_val.magnitude} {human_readable_unit(display_val.units)}"
```

But since we want a consistent unit across the whole diagram, use the root display unit explicitly:
```python
magnitude = round(node_value.to(root_display_unit).magnitude, 2)
amount_str = f"{magnitude} {human_readable_unit(root_display_unit)}"
```

#### 10c. Update `figure()` default title

Update the default title in `figure()` to use `format_quantity_for_display` and
`human_readable_unit` instead of the deleted `format_co2_amount`/`display_co2_amount`.

The interface computes its own title freely in `sankey_views.py` (with UI-specific labels and
formatting), so no need to expose a `title` property.

This ensures all values in the sankey share the same unit (driven by the root total), which is
consistent with how the user reads the diagram.


### Step 11. Update `plot_baseline_and_simulation_data.py`

File: `efootprint/utils/plot_baseline_and_simulation_data.py`

The y-axis label should reflect the auto-scaled unit.

```python
# Before:
plt.ylabel(f"{baseline_q.units:~}")

# After (best_display_unit handles array mean internally):
display_unit = best_display_unit(baseline_q)
plt.ylabel(human_readable_unit(display_unit))
# Also convert plot data to display_unit before plotting
```


### Step 12. Run e-footprint tests, fix any failures from `__str__` changes

The `__str__` changes (Steps 5-7) will affect any test that asserts on string representations of
`ExplainableQuantity`, `ExplainableHourlyQuantities`, or `ExplainableRecurrentQuantities`.

Run `poetry run pytest` and update assertions to match the new auto-scaled format.


---

### Interface changes (after e-footprint changes are on a branch or installed as editable)

### Step 13. Update `model_web_utils.py` — remove hardcoded `.to(u.tonne)`

File: `e-footprint-interface/model_builder/domain/entities/web_core/model_web_utils.py`

`get_reindexed_array_from_dict` currently hardcodes `.to(u.tonne)`. Make it unit-agnostic — keep
data in its original unit and let the display layer handle conversion.

```python
def get_reindexed_array_from_dict(key, d, global_start, total_hours):
    val = d.get(key)
    if isinstance(val, EmptyExplainableObject):
        return np.zeros(total_hours, dtype=np.float32) * u.kg  # base unit
    return reindex_array(val, global_start, total_hours)  # no .to(u.tonne)
```


### Step 14. Update `EmissionsCalculationService` to determine display unit from `total_footprint`

File: `e-footprint-interface/model_builder/domain/services/emissions_calculation_service.py`

The display unit for result charts is determined by `System.total_footprint` — the mean of its
daily sums represents what the user sees on the y-axis.

```python
from efootprint.utils.display import best_display_unit

class EmissionsCalculationService:
    def calculate_daily_emissions(self, system) -> EmissionsResult:
        # ... existing reindexing logic (now in kg, not tonnes) ...

        # Determine display unit from total_footprint (handles array mean internally)
        display_unit = best_display_unit(system.total_footprint.value)

        # Convert all reindexed arrays to display_unit before calling to_rounded_daily_values
        # ... array.to(display_unit) ...

        display_unit_str = human_readable_unit(display_unit)
        return EmissionsResult(dates=dates, values=values, display_unit=display_unit_str)
```

Update `EmissionsResult` to include the display unit string:
```python
@dataclass
class EmissionsResult:
    dates: List[str]
    values: Dict[str, List[float]]
    display_unit: str  # e.g. "t", "kg"
```


### Step 15. Update `result_graph.html` to use dynamic unit label

File: `e-footprint-interface/model_builder/templates/model_builder/result/result_graph.html`

Before:
```html
<p class="h8">t CO<sub>2</sub>-eq</p>
```

After:
```html
<p class="h8">{{ display_unit }} CO<sub>2</sub>-eq</p>
```

The view that renders this template must pass `display_unit` in the context (from
`EmissionsResult.display_unit`).


### Step 16. Update `tooltip.js` to use dynamic unit

File: `e-footprint-interface/theme/static/scripts/result_charts/tooltip.js`

Before:
```js
fabricationTotal.toFixed(2) + " t CO₂-eq"
```

After — read the unit from a data attribute or from `window.emissions.display_unit`:
```js
const unit = window.emissions.display_unit || "t";
fabricationTotal.toFixed(2) + ` ${unit} CO₂-eq`
```

This requires the view that passes `window.emissions` to also include `display_unit`.


### Step 17. Simplify `ExplainableQuantityWeb`

File: `e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/explainable_objects_web.py`

Since `display_quantity` and `display_unit` now live on the upstream `ExplainableQuantity` class
(Step 4), `ExplainableQuantityWeb` can simply delegate:

```python
class ExplainableQuantityWeb(ExplainableObjectWeb):
    @property
    def rounded_value(self):
        return self.display_quantity.magnitude

    @property
    def unit(self):
        return self.value.units
```

`display_quantity` and `display_unit` are inherited from the upstream class. `rounded_value` is
kept as a convenience for templates that use `{{ item.rounded_value }}`.

> **Note**: `rounded_value` now returns a magnitude in the auto-scaled unit (e.g. 22 instead of
> 22000). Any template using `{{ item.rounded_value }}` alongside `{{ item.unit }}` must switch to
> `{{ item.display_unit }}` to stay consistent.


### Step 18. Update templates using Explainable display properties

Files:
- `model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_quantity.html`
- `model_builder/templates/model_builder/result/source_table.html`

Replace raw `{{ item.unit }}` or `{{ value.units }}` with `{{ item.display_unit }}` where the
corresponding magnitude uses `rounded_value`.

For `source_table.html` which uses `{{ explainable_quantity.value.magnitude }}` directly, switch to
`{{ explainable_quantity.rounded_value }}` + `{{ explainable_quantity.display_unit }}`.


### Step 19. Update `calculated_attribute_chart.html` unit label

File: `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/calculated_attribute_chart.html`

Currently passes `data-unit="{{ web_ehq.unit }}"` (raw Pint unit). Switch to
`data-unit="{{ web_ehq.display_unit }}"` to use the auto-scaled unit.


### Step 20. Update Excel export to use `format_quantity_for_display`

File: `e-footprint-interface/model_builder/adapters/views/views.py`

Before:
```python
attr_value.value.magnitude
str(attr_value.value.units)
```

After:
```python
display = format_quantity_for_display(attr_value.value)
display.magnitude
human_readable_unit(display.units)
```


### Step 21. Update `sankey_views.py` in the interface

File: `e-footprint-interface/model_builder/adapters/views/sankey_views.py`

The interface keeps its own title formatting (UI-specific labels, em dash, "CO₂eq"). Use
`sankey.total_system_value` (the new Pint quantity from Step 10a) for the amount display:

```python
from efootprint.utils.display import format_quantity_for_display, human_readable_unit

total_display = format_quantity_for_display(sankey.total_system_value)
total_co2 = f"{total_display.magnitude} {human_readable_unit(total_display.units)}"
title = f"{system.name} — {lifecycle_info}impact repartition{excluded_info} (total {total_co2} CO₂eq)"
```

Remove `display_co2_amount` / `format_co2_amount` imports.

The `_build_node_tooltip` and `_build_link_tooltip` helpers build HTML tooltips for the JS-rendered
sankey. They currently call `format_co2_amount(kg)` on raw floats — update them to use
`format_quantity_for_display` instead. After Step 10a, the sankey's public API exposes Pint
quantities (`total_system_value`, `node_total_values`, etc.), so the tooltip helpers can use those
directly.


### Step 22. Run interface tests, fix failures

Run `poetry run pytest` in `e-footprint-interface/` and update any assertions affected by the
new display formatting.


## Out of Scope

- **Form input fields**: The unit shown next to form inputs (`form_field_generator.py:156`) should
  remain the *input* unit, not auto-scaled. Users enter values in the unit defined by the model.

