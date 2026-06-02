# Edge hardware

The objects in this sub-bucket describe decentralized hardware fleets —
IoT sensors, industrial controllers, smartphones, any deployed unit
whose impact scales with how many are in the field rather than with
centralized demand.

The fleet is described in two passes.

A single deployed unit is an {class:EdgeDevice}: a chassis with
embodied carbon, plus a list of {class:EdgeComponent}s that carry their
own fabrication and operational impact. The available component types
are {class:EdgeRAMComponent}, {class:EdgeCPUComponent},
{class:EdgeStorage}, and {class:EdgeWorkloadComponent}, the last being
a linear whole-device utilisation curve used when the internal
hardware is not modeled in detail. For two common construction
patterns, e-footprint provides convenience builders that wire the
components for you: {class:EdgeComputer} (RAM + CPU + storage) and
{class:EdgeAppliance} (a single linear workload curve).

How many units are deployed is set in two places that multiply
together. {class:EdgeDeviceGroup} expresses the **fleet structure**:
a composition node that holds multiplicities for child
{class:EdgeDevice}s and child {class:EdgeDeviceGroup}s, with arbitrary
nesting — a building contains rooms contain devices, a vehicle
contains subsystems, and so on. {class:EdgeUsagePattern} then expresses
the **deployment schedule** — when copies of that fleet come online in
a given country (see {doc:usage_edge_index}). The total count of any
single device is the unrolled group multiplicity times the deployment
count from the pattern.

The fabrication and operational footprint of the fleet — typically
the dominant output of an edge model — comes out of this combination.

New to this paradigm? Start with {doc:web_vs_edge} for the mental model
that ties these objects to the rest of e-footprint.
