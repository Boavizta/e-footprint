# How to read a footprint per tenant or per provider

A loaded system's total footprint can be sliced two ways that are easy to
confuse:

- **Per tenant** — *who caused the impact?* Demand-side: attribute the
  footprint to the end users (a customer, a business unit, a country) who
  triggered it.
- **Per provider** — *where does it run?* Supply-side: group the
  infrastructure (servers and their storage) by the cloud or hosting
  provider that operates it.

The first is built into e-footprint; the second is a few lines of your
own grouping code.

## Per tenant (demand-side)

Model **one {class:UsagePattern} per tenant**. Each usage pattern already
carries its own attributed footprint across *all* tiers — end-user
devices, network, server, and storage — so there is nothing to assemble
by hand: you just read it.

```python
from efootprint.core.attribution import footprint_per_node
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.usage_pattern import UsagePattern

# system already built with one UsagePattern per tenant
for phase in (LifeCyclePhases.MANUFACTURING, LifeCyclePhases.USAGE):
    per_tenant = footprint_per_node(system, UsagePattern, phase)
    for tenant, footprint in per_tenant.items():
        print(phase.value, tenant.name, footprint.sum().to(u.kg))
```

`footprint_per_node(system, UsagePattern, phase)` returns one hourly
footprint per usage pattern, with every tier's contribution already
attributed to the tenant that drove it. Sum it over the modeling period
with `.sum()` to get a single number.

## Per provider (supply-side)

There is no provider attribute on {class:Server} or {class:Storage}, so
you decide the grouping and sum in plain Python. Each infrastructure
object's total attributed footprint, across every job and tenant that
uses it, is given by `attributed_footprint`:

```python
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.core.attribution import attributed_footprint
from efootprint.core.lifecycle_phases import LifeCyclePhases

infra_by_provider = {
    "AWS": [aws_server, aws_storage],
    "GCP": [gcp_server, gcp_storage],
}

for provider, infra in infra_by_provider.items():
    total = sum(
        (attributed_footprint(obj, phase)
         for obj in infra for phase in LifeCyclePhases),
        start=EmptyExplainableObject())
    print(provider, total.sum().to(u.kg))
```

### Boundary

Only infrastructure carries a provider. Network and end-user **device**
impacts are *not* attributed to a provider — a request crosses networks
and runs on devices that no single provider owns, and modeling that
allocation would be substantial work for little benefit. Per-provider
totals therefore cover the server and storage tiers only; the per-tenant
view above remains the way to see the full, all-tier footprint.
