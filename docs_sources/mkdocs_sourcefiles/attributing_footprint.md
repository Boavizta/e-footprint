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
from efootprint.constants.units import u
from efootprint.core.attribution import footprint_per_node
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.usage_pattern import UsagePattern

# `system` is your already-built System, with one UsagePattern per tenant
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

Cloud servers modeled as {class:BoaviztaCloudServer} carry a `provider`
attribute whose value is the provider key (e.g. `aws`, `gcp`,
`scaleway`), so you can bucket them straight off the model — no
hand-maintained mapping. Each server's attached {class:Storage} rides
along with it. Each infrastructure object's total attributed footprint,
across every job and tenant that uses it, is given by
`attributed_footprint`:

```python
from collections import defaultdict

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.constants.units import u
from efootprint.core.attribution import attributed_footprint
from efootprint.core.lifecycle_phases import LifeCyclePhases

# `system` is your already-built System
infra_by_provider = defaultdict(list)
for server in system.servers:
    if isinstance(server, BoaviztaCloudServer):
        # the server carries its provider; its attached storage rides along
        infra_by_provider[server.provider.value] += [server, server.storage]

for provider, infra in infra_by_provider.items():
    total = sum(
        (attributed_footprint(obj, phase)
         for obj in infra for phase in LifeCyclePhases),
        start=EmptyExplainableObject())
    print(provider, total.sum().to(u.kg))
```

Each provider total here combines both life-cycle phases (manufacturing
and usage) into one figure — unlike the per-tenant read above, which
keeps the phases separate. Drop the `for phase in LifeCyclePhases` loop
to break a provider down per phase too.

### Boundary

The `provider` attribute lives on {class:BoaviztaCloudServer}, the
cloud-instance server type. A plain on-premise {class:Server} (and its
{class:Storage}) has no provider — it is hardware you operate yourself —
so the loop above skips it; group those under your own label if you want
them in the breakdown. Network and end-user **device** impacts carry no
provider either: a request crosses networks and runs on devices that no
single provider owns, and modeling that allocation would be substantial
work for little benefit. Per-provider totals therefore cover the cloud
server and storage tiers only; the per-tenant view above remains the way
to see the full, all-tier footprint.
