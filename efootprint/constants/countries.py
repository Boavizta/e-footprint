from copy import copy

import pytz

from efootprint.constants.units import u
from efootprint.constants.sources import Source,Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceTimezone
from efootprint.core.country import Country


def tz(timezone: str):
    return SourceTimezone(pytz.timezone(timezone), Sources.USER_DATA)


def country_generator(country_name, country_short_name, country_avg_carbon_int, timezone):
    def return_country():
        return Country(country_name, country_short_name, copy(country_avg_carbon_int), copy(timezone))

    return return_country


class Countries:
    # TODO: Add other countries and automate data retrieval
    source = Source("Our world in data", "https://ourworldindata.org/energy#country-profiles")
    FRANCE = country_generator("France", "FRA", SourceValue(85 * u.g / u.kWh, source), tz('Europe/Paris'))
    # EUROPE = country_generator("Europe", "EUR", SourceValue(278 * u.g / u.kWh, source), None)
    GERMANY = country_generator("Germany", "DEU", SourceValue(386 * u.g / u.kWh, source), tz('Europe/Berlin'))
    FINLAND = country_generator("Finland", "FIN", SourceValue(132 * u.g / u.kWh, source), tz('Europe/Helsinki'))
    AUSTRIA = country_generator("Austria", "AUT", SourceValue(158 * u.g / u.kWh, source), tz('Europe/Vienna'))
    POLAND = country_generator("Poland", "POL", SourceValue(635 * u.g / u.kWh, source), tz('Europe/Warsaw'))
    NORWAY = country_generator("Norway", "NOR", SourceValue(26 * u.g / u.kWh, source), tz('Europe/Oslo'))
    HUNGARY = country_generator("Hungary", "HUN", SourceValue(223 * u.g / u.kWh, source), tz('Europe/Budapest'))
    UNITED_KINGDOM = country_generator("United Kingdom", "GBR", SourceValue(268 * u.g / u.kWh, source), tz('Europe/London'))
    BELGIUM = country_generator("Belgium", "BEL", SourceValue(165 * u.g / u.kWh, source), tz('Europe/Brussels'))
    ITALY = country_generator("Italy", "IT", SourceValue(371 * u.g / u.kWh, source), tz('Europe/Rome'))
    ROMANIA = country_generator("Romania", "RO", SourceValue(264 * u.g / u.kWh, source), tz('Europe/Bucharest'))
    MALAYSIA = country_generator("Malaysia", "MY", SourceValue(549 * u.g / u.kWh, source), tz('Asia/Kuala_Lumpur'))
    MOROCCO = country_generator("Morocco", "MA", SourceValue(610 * u.g / u.kWh, source), tz('Africa/Casablanca'))
    TUNISIA = country_generator("Tunisia", "TN", SourceValue(468 * u.g / u.kWh, source), tz('Africa/Tunis'))
    ALGERIA = country_generator("Algeria", "DZ", SourceValue(488 * u.g / u.kWh, source), tz('Africa/Algiers'))
    SENEGAL = country_generator("Senegal", "SN", SourceValue(503 * u.g / u.kWh, source), tz('Africa/Dakar'))
    # UNITED_STATES = country_generator("United States", "US", SourceValue(379 * u.g / u.kWh, source), None)
    # BRAZIL = country_generator("Brazil", "BR", SourceValue(159 * u.g / u.kWh, source), None)
