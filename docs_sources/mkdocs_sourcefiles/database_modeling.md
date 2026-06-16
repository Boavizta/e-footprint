# How to model a database

e-footprint does not have a first-class abstraction for databases. A
database is modeled by composing the primitives used for any backend
workload: a {class:Server}, a {class:Storage}, and a set of {class:Job}s.
A database-flavoured {class:Service}, plugged in through the server's
installed-services mechanism, would bundle a sensible engine baseline
and canonical query templates — that would be a welcome contribution.

> Load this scenario in the e-footprint interface:
> [E-commerce web/database scenario]({{ config.extra.interface_base_url }}/template/ecommerce/)

## How a database maps onto the primitives

- **Engine baseline.** Use {param:Server.base_ram_consumption} and
  {param:Server.base_compute_consumption} for the RAM and CPU the
  engine holds independently of queries — buffer pool, connection
  workers, background tasks. Both default to zero, so they are easy to
  forget.
- **On-disk footprint.** Use {param:Storage.base_storage_need} for
  existing tables and indexes at t=0, {param:Storage.data_storage_duration}
  for retention, {param:Storage.data_replication_factor} for replicas.
  {class:Storage} already accounts for both the fabrication and the
  operational energy of the persistent volumes; do not model them
  separately.
- **Query workload.** Use one {class:Job} *per kind of operation*, not
  one averaged job. Set {param:Job.compute_needed}, {param:Job.ram_needed},
  and {param:Job.request_duration} for what a single query holds;
  {param:Job.data_transferred} for the network payload;
  {param:Job.data_stored} for the net per-call storage growth.

## Python sketch

```python
storage = Storage(
    "PostgreSQL storage",
    base_storage_need=SourceValue(100 * u.GB_stored),
)

db_server = Server(
    "PostgreSQL server",
    base_ram_consumption=SourceValue(2 * u.GB_ram),
    base_compute_consumption=SourceValue(0.1 * u.cpu_core),
    storage=storage,
    # remaining params fall back to defaults
)

read_query = Job(
    "SELECT", server=db_server,
    request_duration=SourceValue(20 * u.ms),
    compute_needed=SourceValue(0.1 * u.cpu_core),
    ram_needed=SourceValue(20 * u.MB_ram),
    data_transferred=SourceValue(5 * u.kB),
    data_stored=SourceValue(0 * u.kB),
)

write_query = Job(
    "INSERT", server=db_server,
    request_duration=SourceValue(40 * u.ms),
    compute_needed=SourceValue(0.2 * u.cpu_core),
    ram_needed=SourceValue(50 * u.MB_ram),
    data_transferred=SourceValue(2 * u.kB),
    data_stored=SourceValue(0.5 * u.kB),
)
```

The values above sketch a modest PostgreSQL deployment under steady
load: a couple of gigabytes of shared buffers, continuous background
workers (checkpointer, autovacuum), and queries in the millisecond
range. They are illustrative, not measured — profile your own setup or
cite a credible source in a {class:Source}.

## Pitfalls

- **Averaging reads and writes into a single job.** They differ by
  orders of magnitude on `data_stored` and often on `compute_needed`.
  Model the mix via multiple {class:Job} instances.
- **Confusing transfer and storage.** {param:Job.data_transferred} is
  the per-call network payload; {param:Job.data_stored} is the per-call
  contribution to durable storage. Both can be non-zero on the same
  job.
- **Forgetting the engine baseline.** The defaults for
  {param:Server.base_ram_consumption} and
  {param:Server.base_compute_consumption} are zero. A database with no
  queries still consumes resources.

See {doc:server_to_server_interaction} for how to wire these jobs into
a usage journey alongside an upstream web server.

The interactive scenario uses an e-commerce journey so the same loaded
model can be read from three angles: the product journey, the database
server, and the server-to-server calls between them.
