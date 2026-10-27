# Project euro-fund savings contracts with lifelib for every fee level x sensitivity.
# The actuarial engine lives in the project library: python/euro_fund_projection.py
import dataiku

import euro_fund_projection as engine


def read(name):
    return dataiku.Dataset(name).get_dataframe()


lapse_rates = read("lapse_rates")[["policy_year", "lapse_rate"]]

cashflows = engine.run_all(
    model_points=read("model_points"),
    mortality=read("mortality_table"),
    assumptions=read("assumptions"),
    lapse_rates=lapse_rates,
    fee_grid=read("fee_grid"),
    sensitivities=read("sensitivities"),
)

dataiku.Dataset("cashflows").write_with_schema(cashflows)
