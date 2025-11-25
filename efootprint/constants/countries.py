from copy import copy
import csv
import os

import pytz

from efootprint.constants.units import u
from efootprint.constants.sources import Source,Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceTimezone
from efootprint.core.country import Country

root_dir = os.path.dirname(os.path.abspath(__file__))
countries_data_file = os.path.join(
    root_dir, "countries_computations", "countries_elec_carbon_intensity_and_timezone.csv")


def tz(timezone: str):
    return SourceTimezone(pytz.timezone(timezone), Sources.USER_DATA)


def country_generator(country_name, country_short_name, country_avg_carbon_int, timezone):
    def return_country():
        return Country(country_name, country_short_name, copy(country_avg_carbon_int), copy(timezone))

    return return_country


def country_generator_from_csv(country_name):
    with open(countries_data_file, newline="", encoding="utf-8") as f:
        countries_data_dict = csv.DictReader(f)
        for row in countries_data_dict:
            if row["Entity"] == country_name:
                country_short_name = row["Code"]
                source = Source(f"Our world in data ({row["Year"]})",
                                "https://ourworldindata.org/grapher/carbon-intensity-electricity")
                country_carbon_int = SourceValue(
                    int(float(row["Carbon intensity of electricity - gCO2/kWh"])) * u.g / u.kWh, source)
                timezone = tz(row["Timezone"])
                break

    return country_generator(country_name, country_short_name, copy(country_carbon_int), copy(timezone))


class Countries:
    # All countries with more than 5 million population in 2024
    AFGHANISTAN = country_generator_from_csv("Afghanistan")
    ALGERIA = country_generator_from_csv("Algeria")
    ANGOLA = country_generator_from_csv("Angola")
    ARGENTINA = country_generator_from_csv("Argentina")
    AUSTRALIA = country_generator_from_csv("Australia")
    AUSTRIA = country_generator_from_csv("Austria")
    AZERBAIJAN = country_generator_from_csv("Azerbaijan")
    BANGLADESH = country_generator_from_csv("Bangladesh")
    BELARUS = country_generator_from_csv("Belarus")
    BELGIUM = country_generator_from_csv("Belgium")
    BENIN = country_generator_from_csv("Benin")
    BOLIVIA = country_generator_from_csv("Bolivia")
    BRAZIL = country_generator_from_csv("Brazil")
    BULGARIA = country_generator_from_csv("Bulgaria")
    BURKINA_FASO = country_generator_from_csv("Burkina Faso")
    BURUNDI = country_generator_from_csv("Burundi")
    CAMBODIA = country_generator_from_csv("Cambodia")
    CAMEROON = country_generator_from_csv("Cameroon")
    CANADA = country_generator_from_csv("Canada")
    CENTRAL_AFRICAN_REPUBLIC = country_generator_from_csv("Central African Republic")
    CHAD = country_generator_from_csv("Chad")
    CHILE = country_generator_from_csv("Chile")
    CHINA = country_generator_from_csv("China")
    COLOMBIA = country_generator_from_csv("Colombia")
    CONGO = country_generator_from_csv("Congo")
    COSTA_RICA = country_generator_from_csv("Costa Rica")
    COTE_D_IVOIRE = country_generator_from_csv("Cote d\'Ivoire")
    CUBA = country_generator_from_csv("Cuba")
    CZECHIA = country_generator_from_csv("Czechia")
    DEMOCRATIC_REPUBLIC_OF_CONGO = country_generator_from_csv("Democratic Republic of Congo")
    DENMARK = country_generator_from_csv("Denmark")
    DOMINICAN_REPUBLIC = country_generator_from_csv("Dominican Republic")
    ECUADOR = country_generator_from_csv("Ecuador")
    EGYPT = country_generator_from_csv("Egypt")
    EL_SALVADOR = country_generator_from_csv("El Salvador")
    ETHIOPIA = country_generator_from_csv("Ethiopia")
    FINLAND = country_generator_from_csv("Finland")
    FRANCE = country_generator_from_csv("France")
    GERMANY = country_generator_from_csv("Germany")
    GHANA = country_generator_from_csv("Ghana")
    GREECE = country_generator_from_csv("Greece")
    GUATEMALA = country_generator_from_csv("Guatemala")
    GUINEA = country_generator_from_csv("Guinea")
    HAITI = country_generator_from_csv("Haiti")
    HONDURAS = country_generator_from_csv("Honduras")
    HONG_KONG = country_generator_from_csv("Hong Kong")
    HUNGARY = country_generator_from_csv("Hungary")
    INDIA = country_generator_from_csv("India")
    INDONESIA = country_generator_from_csv("Indonesia")
    IRAN = country_generator_from_csv("Iran")
    IRAQ = country_generator_from_csv("Iraq")
    IRELAND = country_generator_from_csv("Ireland")
    ISRAEL = country_generator_from_csv("Israel")
    ITALY = country_generator_from_csv("Italy")
    JAPAN = country_generator_from_csv("Japan")
    JORDAN = country_generator_from_csv("Jordan")
    KAZAKHSTAN = country_generator_from_csv("Kazakhstan")
    KENYA = country_generator_from_csv("Kenya")
    KYRGYZSTAN = country_generator_from_csv("Kyrgyzstan")
    LAOS = country_generator_from_csv("Laos")
    LEBANON = country_generator_from_csv("Lebanon")
    LIBERIA = country_generator_from_csv("Liberia")
    LIBYA = country_generator_from_csv("Libya")
    MADAGASCAR = country_generator_from_csv("Madagascar")
    MALAWI = country_generator_from_csv("Malawi")
    MALAYSIA = country_generator_from_csv("Malaysia")
    MALI = country_generator_from_csv("Mali")
    MAURITANIA = country_generator_from_csv("Mauritania")
    MEXICO = country_generator_from_csv("Mexico")
    MOROCCO = country_generator_from_csv("Morocco")
    MOZAMBIQUE = country_generator_from_csv("Mozambique")
    MYANMAR = country_generator_from_csv("Myanmar")
    NEPAL = country_generator_from_csv("Nepal")
    NETHERLANDS = country_generator_from_csv("Netherlands")
    NEW_ZEALAND = country_generator_from_csv("New Zealand")
    NICARAGUA = country_generator_from_csv("Nicaragua")
    NIGER = country_generator_from_csv("Niger")
    NIGERIA = country_generator_from_csv("Nigeria")
    NORTH_KOREA = country_generator_from_csv("North Korea")
    NORWAY = country_generator_from_csv("Norway")
    OMAN = country_generator_from_csv("Oman")
    PAKISTAN = country_generator_from_csv("Pakistan")
    PALESTINE = country_generator_from_csv("Palestine")
    PAPUA_NEW_GUINEA = country_generator_from_csv("Papua New Guinea")
    PARAGUAY = country_generator_from_csv("Paraguay")
    PERU = country_generator_from_csv("Peru")
    PHILIPPINES = country_generator_from_csv("Philippines")
    POLAND = country_generator_from_csv("Poland")
    PORTUGAL = country_generator_from_csv("Portugal")
    ROMANIA = country_generator_from_csv("Romania")
    RUSSIA = country_generator_from_csv("Russia")
    RWANDA = country_generator_from_csv("Rwanda")
    SAUDI_ARABIA = country_generator_from_csv("Saudi Arabia")
    SENEGAL = country_generator_from_csv("Senegal")
    SERBIA = country_generator_from_csv("Serbia")
    SIERRA_LEONE = country_generator_from_csv("Sierra Leone")
    SINGAPORE = country_generator_from_csv("Singapore")
    SLOVAKIA = country_generator_from_csv("Slovakia")
    SOMALIA = country_generator_from_csv("Somalia")
    SOUTH_AFRICA = country_generator_from_csv("South Africa")
    SOUTH_KOREA = country_generator_from_csv("South Korea")
    SOUTH_SUDAN = country_generator_from_csv("South Sudan")
    SPAIN = country_generator_from_csv("Spain")
    SRI_LANKA = country_generator_from_csv("Sri Lanka")
    SUDAN = country_generator_from_csv("Sudan")
    SWEDEN = country_generator_from_csv("Sweden")
    SWITZERLAND = country_generator_from_csv("Switzerland")
    SYRIA = country_generator_from_csv("Syria")
    TAJIKISTAN = country_generator_from_csv("Tajikistan")
    TANZANIA = country_generator_from_csv("Tanzania")
    THAILAND = country_generator_from_csv("Thailand")
    TOGO = country_generator_from_csv("Togo")
    TUNISIA = country_generator_from_csv("Tunisia")
    TURKEY = country_generator_from_csv("Turkey")
    TURKMENISTAN = country_generator_from_csv("Turkmenistan")
    UGANDA = country_generator_from_csv("Uganda")
    UKRAINE = country_generator_from_csv("Ukraine")
    UNITED_ARAB_EMIRATES = country_generator_from_csv("United Arab Emirates")
    UNITED_KINGDOM = country_generator_from_csv("United Kingdom")
    UNITED_STATES = country_generator_from_csv("United States")
    UZBEKISTAN = country_generator_from_csv("Uzbekistan")
    VENEZUELA = country_generator_from_csv("Venezuela")
    VIETNAM = country_generator_from_csv("Vietnam")
    YEMEN = country_generator_from_csv("Yemen")
    ZAMBIA = country_generator_from_csv("Zambia")
    ZIMBABWE = country_generator_from_csv("Zimbabwe")
