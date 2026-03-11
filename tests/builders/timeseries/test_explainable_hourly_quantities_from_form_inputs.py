from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.constants.countries import tz
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs


class CalculusGraphTest(TestCase):
    def test_calculus_graph_html_gen(self):
        self.mock_usage_journey = MagicMock(spec=UsageJourney, id="usage-journey-id")
        self.mock_devices = [MagicMock(spec=Device, id="device-id"), MagicMock(spec=Device, id="device-id2")]
        self.mock_network = MagicMock(spec=Network, id="network-id")
        self.mock_country = MagicMock(spec=Country, id="FR-id")
        self.mock_country.timezone = tz('Europe/Paris')
        self.default_hourly_starts = ExplainableHourlyQuantitiesFromFormInputs(
            {"start_date": "2024-01-01", "modeling_duration_value": 1, "modeling_duration_unit": "year",
             "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "month",
             "initial_volume": 1000, "initial_volume_timespan": "month"}
        )
        self.usage_pattern = UsagePattern.from_defaults(
            name="test_usage_pattern_from_form",
            hourly_usage_journey_starts=self.default_hourly_starts,
            usage_journey=self.mock_usage_journey,
            devices=self.mock_devices,
            network=self.mock_network,
            country=self.mock_country
        )

        # To get calculated attributes
        calculated_attributes = self.usage_pattern.calculated_attributes

        # To get calculus graph html
        self.usage_pattern.update_utc_hourly_usage_journey_starts()

        calculus_graph = build_calculus_graph(self.usage_pattern.utc_hourly_usage_journey_starts)
        calculus_graph.cdn_resources = "remote"
        html = calculus_graph.generate_html()
        self.assertGreater(len(html), 0)
