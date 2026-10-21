# Improved autoscaling modeling

**Status:** parked for later specification and implementation.

## Need

An autoscaling server can currently scale from zero by rounding its raw hourly resource demand up to whole instances. Real deployments may instead keep a minimum number of instances running continuously, then autoscale above that floor. Modeling the production deployment of e-footprint-interface needs a minimum of one instance throughout the modeling period.

The intended capability is an autoscaling-only `minimum_nb_of_instances` input, with zero as the default:

```text
provisioned instances = max(minimum instances, ceil(raw resource demand))
```

The minimum must affect provisioned manufacturing and idle-energy footprints. Dynamic load energy must continue to follow raw job demand rather than the minimum-instance floor. Attribution must also account for the baseline footprint during hours with no job demand.

This remains distinct from the existing on-premise fixed-instance setting: the floor does not cap autoscaling above the minimum.

## Temporary workaround

Until this capability exists, the e-footprint-interface study will model one continuous logical keep-alive thread as contiguous one-hour job segments carrying minimal non-zero resource demand. This causes the autoscaling instance count to round up to one in otherwise idle hours. A single job spanning the full multi-year period is unsuitable because the concurrency convolution extends the output horizon and introduces FFT noise at this duration. The segmented synthetic load must be kept negligible and disclosed because it slightly reduces available capacity and adds a small dynamic-load footprint.
