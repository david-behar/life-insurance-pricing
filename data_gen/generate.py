"""Generate the synthetic input data for the savings pricing demo.

All data is synthetic. Run: python data_gen/generate.py  -> writes CSVs to data_gen/out/
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(42)

# Model points: 500 new single-premium contracts
n = 500
model_points = pd.DataFrame({
    "contract_id": np.arange(1, n + 1),
    "age": rng.integers(25, 76, n),
    "sex": rng.choice(["M", "F"], n),
    "single_premium": np.round(rng.lognormal(np.log(40000), 0.8, n).clip(5000, 500000), -2),
})
model_points.to_csv(OUT / "model_points.csv", index=False)

# Mortality: Gompertz curve, females at 60% of males, q=1 at the last age
ages = np.arange(0, 121)
rows = []
for sex, factor in [("M", 1.0), ("F", 0.6)]:
    q = np.minimum(factor * 0.00003 * np.exp(0.095 * ages), 1.0)
    q[-1] = 1.0
    rows.append(pd.DataFrame({"age": ages, "sex": sex, "qx": np.round(q, 6)}))
pd.concat(rows).to_csv(OUT / "mortality_table.csv", index=False)

# Economic and product assumptions: one row per parameter (edited in DSS as an editable dataset)
pd.DataFrame([
    ("guaranteed_rate", 0.005, "rate", "Minimum annual rate credited to the account value"),
    ("profit_sharing_rate", 0.90, "share", "Share of the asset yield credited to policyholders"),
    ("asset_yield", 0.030, "rate", "Annual yield earned on the assets backing the account value"),
    ("discount_rate", 0.030, "rate", "Annual rate used to discount profits"),
    ("entry_fee_rate", 0.02, "share", "Fee deducted from each premium"),
    ("commission_rate", 0.01, "share", "Distributor commission on premiums"),
    ("acquisition_expense", 150.0, "EUR", "Expense per new contract"),
    ("maintenance_expense", 40.0, "EUR/year", "Expense per contract in force, before inflation"),
    ("expense_inflation", 0.02, "rate", "Annual inflation of maintenance expenses"),
    ("projection_years", 30, "years", "Projection horizon; remaining account value is paid out at the end"),
], columns=["parameter", "value", "unit", "description"]).to_csv(OUT / "assumptions.csv", index=False)

# Pricing options: annual management fee on account value
fees = [0.005, 0.006, 0.007, 0.008, 0.009, 0.010]
pd.DataFrame({"fee_label": ["{:.1f}%".format(f * 100) for f in fees], "management_fee": fees}).to_csv(
    OUT / "fee_grid.csv", index=False)

# Sensitivities
pd.DataFrame([
    ("base", 1.00, 1.0, 0.00, "Best-estimate assumptions"),
    ("mortality_up_15pct", 1.15, 1.0, 0.00, "Mortality rates x 1.15"),
    ("lapse_up_50pct", 1.00, 1.5, 0.00, "Lapse rates x 1.5"),
    ("lapse_down_50pct", 1.00, 0.5, 0.00, "Lapse rates x 0.5"),
    ("rates_down_1pct", 1.00, 1.0, -0.01, "Asset yield and discount rate - 1%"),
], columns=["sensitivity", "mortality_factor", "lapse_factor", "rate_shift", "description"]).to_csv(
    OUT / "sensitivities.csv", index=False)

# Surrender experience: one row per contract and policy year.
# True behaviour: low lapses early, a spike in policy year 9 (after the 8-year
# tax threshold), higher lapses when competitors pay more (rate_spread > 0).
rows = []
for cid in range(1, 4001):
    age = rng.integers(25, 76)
    av = rng.lognormal(np.log(40000), 0.8)
    start_year = rng.integers(1, 15)
    for year in range(start_year, min(start_year + 6, 21)):
        spread = rng.normal(0.0, 0.005)
        logit = (-3.6 + 0.08 * min(year, 8) + 1.3 * (year == 9) + 0.5 * (year >= 9)
                 - 0.01 * (age - 50) + 80 * spread)
        p = 1 / (1 + np.exp(-logit))
        surrendered = int(rng.random() < p)
        rows.append((cid, int(age), year, round(av, 2), round(spread, 5), surrendered))
        av *= 1.02
        if surrendered:
            break
pd.DataFrame(rows, columns=["contract_id", "age", "policy_year", "account_value",
                            "rate_spread", "surrendered"]).to_csv(
    OUT / "lapse_experience.csv", index=False)

for f in sorted(OUT.glob("*.csv")):
    print(f.name, len(pd.read_csv(f)))
