# Flexible usage-pattern timeseries — spec seed

Status: backlog seed · 2026-11-26 · scope to refine before planning.

## Need

Usage-pattern demand needs a richer editable timeseries form than a volume spread uniformly
across hours. Modelers should be able to express recurring activity and its evolution over time
without constructing custom hourly arrays.

## Proposed direction

- Support flexible typical-week profiles, similar to
  `ExplainableRecurrentQuantitiesFromWeeklyPattern`, with different activity by weekday and hour.
- Consider month-specific scaling to represent seasonal variation.
- Support exponential growth over the modeling period; consider an optional plateau and define
  whether it means a hard cap or a gradual approach to saturation.
- Support calendar-based occurrences such as exactly one training-run start each month. A
  repeated typical week or monthly scaling alone cannot express that schedule. Define the
  calendar rule and handling of short months when specifying the feature.

Keep profile shape, calendar occurrences, seasonal scaling and long-term growth understandable
as distinct controls. Refine how they combine and how volume is preserved before implementation;
the form must make the resulting hourly demand clear.

## Machine-learning how-to follow-up

Update the machine-learning workflow how-to introduced by
[executable-modeling-documentation](../../features/executable-modeling-documentation/plan.md#ml-guide)
to demonstrate genuinely scheduled retraining: one training-run start each calendar month,
with zero training starts in other hours, rather than 12 annual runs smoothed uniformly over
the year. Keep inference as a separate demand pattern. Update its generated presentations and
packaged example together, and explain the effect of concentrated training demand on results.

The current executable-documentation work can retain and disclose its smoothed approximation;
this backlog item owns replacing that approximation with the richer form.
