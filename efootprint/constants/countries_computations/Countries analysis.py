# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Jupyter AI
#     language: python
#     name: jupyter-ai
# ---

# %%
import pandas as pd

df = pd.read_csv("carbon-intensity-electricity.csv")
pop = pd.read_csv("world_population.csv")
pop = pop.rename(columns={'Country Code': 'Code', '2024': 'Population'})
df = df.merge(pop[['Code', 'Population']], on='Code', how='left')
# Keep only last year for each country
df = df.sort_values(["Entity", "Year"])
df = df.groupby("Entity").tail(1)
df_without_code = df[pd.isnull(df["Code"])]
df = df[~pd.isnull(df["Code"])]
df.head()

# %%
df_without_code.head()

# %%
# Entities with no population
df[pd.isnull(df["Population"])]

# %%
big_countries = df[df["Population"]>5000000].sort_values(by="Entity").copy()
big_countries

# %%
import pycountry
import pytz

def get_alpha2(country):
    """
    country: either alpha-3 code (e.g. 'FRA'), or full name ('France'),
             or short name ('United States'), etc.
    Returns: ISO alpha-2 code (e.g. 'FR')
    """
    # If this looks like an alpha-3 code
    if len(country) == 3 and country.isalpha():
        try:
            c = pycountry.countries.get(alpha_3=country.upper())
            if c:
                return c.alpha_2
        except KeyError:
            pass

    # Try exact name match
    try:
        c = pycountry.countries.lookup(country)
        return c.alpha_2
    except LookupError:
        return None



# %%
def country_timezones(country):
    alpha2 = get_alpha2(country)
    if not alpha2:
        raise ValueError(f"No alpha2 found for {country}")

    tzens = pytz.country_timezones.get(alpha2)
    if not tzens:
        raise ValueError(f"No tz found for {country}")

    return tzens



# %%
countries_with_multiple_timezones = {}
for index, row in big_countries.iterrows():
    tzens = country_timezones(row["Code"])
    if len(tzens) > 1:
        countries_with_multiple_timezones[row["Code"]] = tzens

# %%
capitals_timezones_dict = {
    "ARG": "America/Argentina/Buenos_Aires",
    "AUS": "Australia/Sydney",
    "BRA": "America/Sao_Paulo",
    "CAN": "America/Toronto",
    "CHL": "America/Santiago",
    "CHN": "Asia/Shanghai",
    "COD": "Africa/Kinshasa",
    "ECU": "America/Guayaquil",
    "DEU": "Europe/Berlin",
    "IDN": "Asia/Jakarta",
    "KAZ": "Asia/Almaty",
    "MYS": "Asia/Kuala_Lumpur",
    "MEX": "America/Mexico_City",
    "PNG": "Pacific/Port_Moresby",
    "PRT": "Europe/Lisbon",
    "RUS": "Europe/Moscow",
    "ESP": "Europe/Madrid",
    "UKR": "Europe/Kyiv",
    "USA": "America/New_York",
    "UZB": "Asia/Tashkent"
}

# %%
for capital, timezone in capitals_timezones_dict.items():
    assert timezone in countries_with_multiple_timezones[capital]


# %%
def country_timezone(country_code: str):
    if country_code in capitals_timezones_dict:
        return capitals_timezones_dict[country_code]
    else:
        return country_timezones(country_code)[0]


# %%
big_countries["Timezone"] = big_countries["Code"].apply(country_timezone)

# %%
big_countries

# %%
assert not big_countries.isnull().values.any(), "Null values detected in big_countries"

# %%
big_countries.drop("Population", axis=1).to_csv("countries_elec_carbon_intensity_and_timezone.csv", index=False)

# %%
# automatically generate Countries class attributes
for country in big_countries["Entity"]:
    print(f"{country.replace(" ", "_").upper()} = country_generator_from_csv(\"{country}\")")

# %%
