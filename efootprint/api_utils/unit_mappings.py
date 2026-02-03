"""Unit mappings for semantic units migration from v12 to v13.

These mappings define which attributes should use which semantic units:
- occurrence: discrete events that are aggregated by sum
- concurrent: concurrent counts that are aggregated by mean
- byte_ram: RAM allocation that is aggregated by mean (vs byte for data transfer)
"""

# Define timeseries attribute mappings: (class_name, attribute_name) -> new_unit_str
# Defined at base class level - automatically applies to all subclasses
TIMESERIES_UNIT_MIGRATIONS = {
    # UsagePattern attributes (applies to all subclasses like EdgeUsagePattern)
    ("UsagePattern", "hourly_usage_journey_starts"): "occurrence",
    # EdgeUsagePattern specific attributes
    ("EdgeUsagePattern", "hourly_edge_usage_journey_starts"): "occurrence",
    # RecurrentEdgeWorkload attributes (uses ExplainableRecurrentQuantities)
    ("RecurrentEdgeWorkload", "recurrent_workload"): "concurrent",
}

# Define RAM timeseries attributes that need _ram appended (ExplainableHourlyQuantities or ExplainableRecurrentQuantities with byte units)
# Defined at base class level - automatically applies to all subclasses
RAM_TIMESERIES_ATTRIBUTES_TO_MIGRATE = {
    ("RecurrentEdgeProcess", "recurrent_ram_needed"),
}

# Define scalar RAM attribute names that need migration: (class_name, attribute_name)
# Defined at base class level - automatically applies to all subclasses
SCALAR_RAM_ATTRIBUTES_TO_MIGRATE = {
    # ServerBase and subclasses (Server, GPUServer, BoaviztaCloudServer, BoaviztaServerFromConfig)
    ("ServerBase", "ram"),
    ("ServerBase", "base_ram_consumption"),
    ("GPUServer", "ram_per_gpu"),  # Specific to GPUServer

    # EdgeComputer
    ("EdgeComputer", "ram"),
    ("EdgeComputer", "base_ram_consumption"),

    # JobBase (applies to Job, GPUJob, etc.)
    ("JobBase", "ram_needed"),

    # Services
    ("VideoStreaming", "base_ram_consumption"),
    ("VideoStreaming", "ram_buffer_per_user"),
}
