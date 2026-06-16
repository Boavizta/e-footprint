# How to model server-to-server interaction

> Load this scenario in the e-footprint interface:
> [E-commerce web/database scenario]({{ config.extra.interface_base_url }}/template/ecommerce/)

## How e-footprint models inter-server calls

There is no first-class primitive in e-footprint for "service A calls
service B." The modeling technique is simpler and worth stating outright:

**List every {class:Job} the user request triggers — direct or
transitive — as a job of the upstream {class:UsageJourneyStep}, each
pointing at the {class:Server} that actually handles it.**

The framework attributes each job's footprint to its server
automatically. The fan-out is captured by repetition: if one user
action triggers one frontend call and three database queries, the
journey step lists four jobs.

The same {class:Job} object can be referenced from several
{class:UsageJourneyStep} instances. When two user actions both hit the
same backend query, sharing the job rather than duplicating it keeps
per-call parameters in one place — easier to read, and robust to
later changes in the underlying numbers.

## Worked example: web server querying a database

Building on {doc:database_modeling}, suppose a user browses a product.
The action triggers an API call to a web server, which in turn queries
the PostgreSQL database from the previous page. The journey step lists
both jobs:

```python
# Reusing db_server, storage, read_query from {doc:database_modeling}.
web_server = Server(
    "Web application server",
    base_ram_consumption=SourceValue(1 * u.GB_ram),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core),
    storage=Storage("Web app local storage"),
)

serve_product_page = Job(
    "Serve product page", server=web_server,
    request_duration=SourceValue(50 * u.ms),
    compute_needed=SourceValue(0.3 * u.cpu_core),
    ram_needed=SourceValue(40 * u.MB_ram),
    data_transferred=SourceValue(30 * u.kB),
    data_stored=SourceValue(0 * u.kB),
)

browse_product = UsageJourneyStep(
    "Browse a product",
    user_time_spent=SourceValue(15 * u.s),
    jobs=[serve_product_page, read_query],  # two servers involved
)
```

The user's device only sees `serve_product_page` directly;
`read_query` is downstream. From e-footprint's point of view that
distinction does not matter — both are listed on the step, each is
processed on its own server.

If a single product page triggered three database queries (catalog
read, pricing read, inventory check), the step's `jobs` list would
contain `serve_product_page` plus three database jobs.

## Modeling granularity

The example above lists one {class:Job} per downstream call, but that
is a modeling choice, not a requirement. Aggregating several small
downstream calls into one composite job is fine when their individual
contributions do not change the order of magnitude of the result;
conversely, splitting a single call into several jobs is worth doing
only if the split changes the result meaningfully. e-footprint's
methodology is iterative ({doc:methodology}) — start coarse, then
refine the parts that turn out to dominate.

The interactive scenario is the same e-commerce web/database system used
by the database guide and the interface's introductory e-commerce card;
this page simply reads it from the server-to-server angle.
