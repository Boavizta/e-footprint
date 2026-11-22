"""The narrative of an edit of a live model: what the engine does between an assignment and the next read.

Its page is drawn from this run (`npm run comprehension:render`, then
`specs/comprehension_harness/mechanisms/`). The steps are recorded, not asserted: each test asserts what the
edit gives, as any test does.
"""
import pytest

from comprehension_harness.python.declare import narrative
from efootprint.abstract_modeling_classes.reactive_core import instance_slot_registry
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern


@pytest.fixture
def pattern():
    """A usage pattern whose UTC occurrences were read once: the value is cached, with the edges of that read."""
    pattern = UsagePattern(
        "pattern", [UsageJourney("journey", uj_steps=[])], [Device.from_defaults("laptop")],
        Network.from_defaults("network"), Countries.FRANCE(), create_source_hourly_values_from_list([1, 2, 3]))
    pattern.utc_hourly_occurrences
    return pattern


def is_cached(mod_obj, attribute: str) -> bool:
    return instance_slot_registry(mod_obj)[attribute].has_cached_value


@narrative.mechanism("An edit voids what read it and recomputes what is asked")
class TestModelEdit:
    """A live assignment is one transaction. Its changes are normalized and applied together, the deletion wave
    voids every value that read them, and the guards run. Everything else waits to be read. A failure puts the
    model back as it was."""

    def test_a_numerical_input_change_voids_its_readers_until_they_are_read(self, pattern):
        before = pattern.utc_hourly_occurrences

        pattern.hourly_occurrences = create_source_hourly_values_from_list([4, 5, 6])

        assert not is_cached(pattern, "utc_hourly_occurrences")
        after = pattern.utc_hourly_occurrences
        assert after is not before and is_cached(pattern, "utc_hourly_occurrences")
        # The same occurrences, shifted to UTC: the new input was read.
        assert sorted(after.value.magnitude.tolist()) == [4, 5, 6]

    def test_a_relationship_change_voids_what_read_through_the_link(self, pattern):
        france = pattern.country

        pattern.country = Countries.JAPAN()

        assert not is_cached(pattern, "utc_hourly_occurrences")
        assert pattern not in france.modeling_obj_containers
        assert pattern in pattern.country.modeling_obj_containers

    def test_a_rejected_edit_puts_the_model_back(self):
        server = Server.from_defaults("server", storage=Storage.from_defaults("storage"))
        server_type = server.server_type

        with pytest.raises(ValueError, match="All changes have been reset"):
            server.server_type = SourceObject("unknown")

        assert server.server_type is server_type
