# How to model serverless / per-invocation workloads

> Load this scenario in the e-footprint interface:
> [E-commerce web/database scenario]({{ config.extra.interface_base_url }}/template/ecommerce/)

Functions-as-a-service (AWS Lambda, Cloud Run, edge functions) and other
pay-per-invocation backends have no first-class primitive in e-footprint,
and they don't need one. A serverless function is just a {class:Job}
running on a {class:Server} whose {param:Server.server_type} is set to
serverless.

## What "serverless" changes

The only thing that differs from an ordinary server is how provisioned
instances are counted, and that is captured entirely by
{param:Server.server_type}:

- **autoscaling** rounds hourly demand up to a whole number of instances,
  so a partially loaded instance is still billed in full;
- **serverless** attributes only the fractional instance-hours actually
  used — the pay-per-use model;
- **on-premise** holds a fixed fleet sized to peak demand over the whole
  period.

Picking serverless does **not** introduce a per-function cost model or
hide the compute. You still describe one invocation explicitly through
the {class:Job}: its {param:Job.compute_needed}, {param:Job.ram_needed},
{param:Job.request_duration}, and data parameters. Compute stays an
explicit input — it is the impact driver, so it is never inferred for you.

## Python sketch

```python
function_server = Server.from_defaults(
    "Image-resize function",
    server_type=ServerTypes.serverless(),
    storage=Storage.ssd("Function storage"),
)

resize_image = Job.from_defaults(
    "Resize uploaded image",
    server=function_server,
    request_duration=SourceValue(120 * u.ms),
    compute_needed=SourceValue(0.5 * u.cpu_core),
    ram_needed=SourceValue(256 * u.MB_ram),
    data_transferred=SourceValue(800 * u.kB),
    data_stored=SourceValue(0 * u.kB),
)
```

The function is wired into a system the same way as any other job: list
`resize_image` on the {class:UsageJourneyStep} that triggers it (see
{doc:server_to_server_interaction}). The serverless server type then makes
the instance count track demand fractionally, hour by hour, with no
always-on idle fleet.

## Granularity

Per the iterative methodology ({doc:methodology}), start with one
{class:Job} per kind of invocation and refine only the ones that turn out
to dominate. A serverless server with no traffic in a given hour
contributes no instance-hours in that hour — unlike an on-premise fleet,
which carries its provisioned footprint even while idle.

The interactive scenario models the same e-commerce system used by the
database and server-to-server guides, where the database is shown as a
managed serverless backend; this page reads it from the per-invocation
angle.
