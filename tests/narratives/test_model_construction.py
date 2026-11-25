"""The construction narrative records the current success and failure paths, before agent-guidance changes errors."""
import pytest

from comprehension_harness.python.declare import narrative, titled, planned_test
from efootprint.abstract_modeling_classes.reactive_core import computed_slots
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_pattern(**server_inputs):
    server = Server.from_defaults("server", storage=Storage.from_defaults("storage"), **server_inputs)
    job = Job.from_defaults("job", server=server, request_duration=SourceValue(2 * u.s))
    step = UsageJourneyStep.from_defaults("step", jobs=[job])
    journey = UsageJourney("journey", uj_steps=[step])
    pattern = UsagePattern(
        "pattern", [journey], [Device.laptop()], Network.from_defaults("network"), Countries.FRANCE(),
        create_source_hourly_values_from_list([1, 2, 3]))
    return pattern, server, job


@narrative.mechanism("A model is constructed from inputs and linked into a system")
class TestModelConstruction:
    """Constructors attach checked inputs and relationship links while the object is passive. A System checks
    ownership and pulls the linked model's guards before becoming live; totals remain lazy. Failure releases
    the incomplete owner's links and caches, leaving surviving objects available for a valid construction."""

    def test_a_web_model_links_its_objects_and_computes_its_footprint_when_asked(self):
        pattern, server, job = build_pattern()
        system = System("system", [pattern], edge_usage_patterns=[])

        assert all(obj._is_live for obj in [system] + system.all_linked_objects)
        assert all(obj.systems == [system] for obj in system.all_linked_objects)
        assert job.request_duration.value == 2 * u.s
        assert job.server._value is server
        assert computed_slots(System)["total_footprint"].peek(system) is None
        assert system.total_footprint.sum().to(u.kg).magnitude > 0

    # @planned agent-guidance#trial-errors Replace the legacy exception assertion with the adjacent planned title's requirements; keep cleanup assertions.

    @titled("A plain job input currently fails during labeling, before input attachment can validate it")
    def test_a_plain_number_fails_before_quantity_validation(self):
        server = Server.from_defaults("server", storage=Storage.from_defaults("storage"))

        with pytest.raises(AttributeError, match="set_label"):
            Job.from_defaults("invalid job", server=server, data_transferred=1)

        assert server.jobs == []

    # Extend test_a_plain_number_fails_before_quantity_validation above to check the input name and quantity hint;
    # retitle it as below, accepting TypeError instead of AttributeError. No case is added.
    @planned_test("agent-guidance#trial-errors: A plain quantity input names its parameter and explains the unit-bearing value to pass [number-needs-a-unit]")
    def test_planned_quantity_error(self):
        pass

    # @planned agent-guidance#trial-errors Add the adjacent planned title's diagnostic assertion while retaining the original graph-preservation checks.

    def test_a_second_system_is_refused_and_leaves_the_first_model_linked(self):
        pattern, server, _ = build_pattern()
        original = System("original", [pattern], edge_usage_patterns=[])
        footprint = original.total_footprint

        with pytest.raises(PermissionError):
            System("second", [pattern], edge_usage_patterns=[])

        assert pattern.systems == [original]
        assert server.systems == [original]
        assert original.total_footprint == footprint

    # Extend test_a_second_system_is_refused_and_leaves_the_first_model_linked above to check the duplication hint;
    # retitle it as below. No case is added.
    @planned_test("agent-guidance#trial-errors: Reusing the first model's objects names duplicate_system and preserves its links [second-system-says-duplicate]")
    def test_planned_system_reuse_error(self):
        pass

    def test_a_failed_guard_detaches_the_incomplete_system(self):
        pattern, server, _ = build_pattern(base_ram_consumption=SourceValue(200 * u.GB_ram))

        with pytest.raises(InsufficientCapacityError):
            System("rejected", [pattern], edge_usage_patterns=[])

        assert pattern.systems == []
        assert server.systems == []
        assert server.base_ram_consumption.value == 200 * u.GB_ram
