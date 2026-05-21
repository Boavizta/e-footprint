# Edge usage

The objects in this sub-bucket describe what a deployed fleet **does**
over its lifetime — not the visits a user pays to a centralized service,
but the recurring activity that runs while devices are in the field.

The shape is three layers deep.

An {class:EdgeUsagePattern} is the deployment schedule in a given
{class:Country}: an hourly timeseries of {class:EdgeUsageJourney}
*starts*, expressed in the country's local timezone. Each start is one
device entering service.

An {class:EdgeUsageJourney} is what that device does from the moment
it is deployed until it is retired — {param:EdgeUsageJourney.usage_span}
duration later. The journey is composed of {class:EdgeFunction}s, each
covering one coherent feature of the deployment (a telemetry loop, a
camera capture cycle, a control task).

An {class:EdgeFunction} expresses load in two directions. On the
device side it carries a list of {class:RecurrentEdgeDeviceNeed}s,
each bundling the per-component demand
({class:RecurrentEdgeComponentNeed}) that the function imposes on
one device; storage gets its own subclass,
{class:RecurrentEdgeStorageNeed}, because storage accumulates rather
than resets each hour. On the server side it carries
{class:RecurrentServerNeed}s — the bridge to centralized
infrastructure, where a typical-week pattern of {class:Job} triggers
is replayed and scaled by the deployed device count.

Together these layers replace the demand-driven web {class:UsagePattern}
with a deployment-driven one: impact comes from *what every device does
recurrently*, multiplied by *how many devices are in service*.

New to this paradigm? Start with {doc:web_vs_edge} for the mental model
that ties these objects to the rest of e-footprint.
