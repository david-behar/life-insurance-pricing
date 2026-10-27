"""Euro-fund savings contract projection built on the lifelib savings model (CashValue_ME).

lifelib credits the full investment return to the account value. A euro fund instead
credits max(guaranteed rate, profit sharing x asset yield); the insurer keeps the rest as
its financial margin. The overrides below implement that, plus Dataiku-fed assumptions.
"""
import os

import lifelib
import modelx as mx
import numpy as np
import pandas as pd

OUTPUT_COLUMNS = [
    "run_id", "management_fee", "sensitivity", "contract_id", "projection_year",
    "credited_rate", "guaranteed_rate", "rate_above_guarantee", "policies_in_force", "account_value_end",
    "premiums", "entry_fees", "management_fees", "financial_margin",
    "death_claims", "surrender_claims", "maturity_claims", "expenses", "commissions",
    "profit", "premiums_pv", "profit_pv",
]


def load_model():
    """Read CashValue_ME straight from the installed lifelib package (read-only, no copy)."""
    path = os.path.join(os.path.dirname(lifelib.__file__), "libraries", "savings", "CashValue_ME")
    return mx.read_model(path, name="EuroFund")


def setup_model(model, model_points, mortality, assumptions, lapse_rates):
    """Plug the Dataiku inputs into the model and override the euro-fund formulas."""
    P = model.Projection
    a = assumptions.set_index("parameter")["value"].astype(float)
    n_years = int(a["projection_years"])

    # Model points: new single-premium business, death benefit = account value
    P.model_point_table = pd.DataFrame({
        "spec_id": "EURO",
        "age_at_entry": model_points["age"].astype(int).values,
        "sex": model_points["sex"].values,
        "policy_term": n_years,
        "policy_count": 1.0,
        "sum_assured": 0.0,
        "duration_mth": 0,
        "premium_pp": model_points["single_premium"].astype(float).values,
        "av_pp_init": 0.0,
        "accum_prem_init_pp": 0.0,
    }, index=pd.Index(model_points["contract_id"].values, name="point_id"))
    P.product_spec_table = pd.DataFrame({
        "premium_type": ["SINGLE"], "has_surr_charge": [False], "surr_charge_id": [np.nan],
        "load_prem_rate": [float(a["entry_fee_rate"])], "is_wl": [False],
    }, index=pd.Index(["EURO"], name="spec_id"))

    # Assumption references (the sensitivity loop changes some of these)
    P.mort_by_age_sex = mortality.set_index(["age", "sex"])["qx"].astype(float)
    P.lapse_by_year = lapse_rates.set_index("policy_year")["lapse_rate"].astype(float)
    P.guaranteed_rate = float(a["guaranteed_rate"])
    P.profit_sharing_rate = float(a["profit_sharing_rate"])
    P.base_asset_yield = float(a["asset_yield"])
    P.base_discount_rate = float(a["discount_rate"])
    P.commission_rate = float(a["commission_rate"])
    P.acq_expense = float(a["acquisition_expense"])
    P.maint_expense = float(a["maintenance_expense"])
    P.expense_inflation = float(a["expense_inflation"])
    P.management_fee = 0.008
    P.mortality_factor = 1.0
    P.lapse_factor = 1.0
    P.rate_shift = 0.0

    # Mortality by attained age and sex, shocked by the sensitivity factor
    def mort_rate(t):
        mi = pd.MultiIndex.from_arrays([np.minimum(age(t), 120), sex()])
        q = mort_by_age_sex.reindex(mi, fill_value=1.0).set_axis(model_point().index)
        return np.minimum(q * mortality_factor, 1.0)

    # Lapse by policy year (last available year used beyond the table)
    def lapse_rate(t):
        year = np.minimum(duration(t) + 1, lapse_by_year.index.max()).values
        rates = lapse_by_year.reindex(year).set_axis(model_point().index)
        return np.minimum(rates * lapse_factor, 1.0)

    def asset_yield():
        return base_asset_yield + rate_shift

    # Insurer earns the asset yield on the assets backing the account value
    def inv_return_mth(t):
        return (1 + asset_yield()) ** (1 / 12) - 1

    # Euro fund crediting: max(guarantee, profit sharing x yield), before fees
    def credited_rate():
        return max(guaranteed_rate, profit_sharing_rate * asset_yield())

    def credited_rate_mth():
        return (1 + credited_rate()) ** (1 / 12) - 1

    def interest_cr_pp(t):
        return credited_rate_mth() * av_pp_at(t, "BEF_INV")

    def interest_cr(t):
        return (interest_cr_pp(t) * pols_if_at(t + 1, "BEF_MAT")
                + 0.5 * interest_cr_pp(t) * (pols_death(t) + pols_lapse(t)))

    def av_pp_at(t, timing):
        if timing == "BEF_PREM":
            return av_pp_init() if t == 0 else av_pp_at(t - 1, "BEF_INV") + interest_cr_pp(t - 1)
        elif timing == "BEF_FEE":
            return av_pp_at(t, "BEF_PREM") + prem_to_av_pp(t)
        elif timing == "BEF_INV":
            return av_pp_at(t, "BEF_FEE") - maint_fee_pp(t) - coi_pp(t)
        elif timing == "MID_MTH":
            return av_pp_at(t, "BEF_INV") + 0.5 * interest_cr_pp(t)
        raise ValueError("invalid timing")

    def maint_fee_rate():
        return management_fee / 12

    def commissions(t):
        return commission_rate * premiums(t)

    def expense_acq():
        return acq_expense

    def expense_maint():
        return maint_expense

    def inflation_rate():
        return expense_inflation

    def disc_rate_mth():
        return np.full(max_proj_len(), (1 + base_discount_rate + rate_shift) ** (1 / 12) - 1)

    def disc_factors():
        return (1 + disc_rate_mth()) ** (-np.arange(max_proj_len()))

    for f in [mort_rate, lapse_rate, asset_yield, inv_return_mth, credited_rate,
              credited_rate_mth, interest_cr_pp, interest_cr, av_pp_at, maint_fee_rate,
              commissions, expense_acq, expense_maint, inflation_rate, disc_rate_mth,
              disc_factors]:
        if f.__name__ in P.cells:
            P.cells[f.__name__].set_formula(f)
        else:
            P.new_cells(formula=f)


def project(model, run_id, management_fee, sensitivity):
    """Run one projection and return annual cash flows per contract."""
    P = model.Projection
    P.management_fee = float(management_fee)
    P.mortality_factor = float(sensitivity["mortality_factor"])
    P.lapse_factor = float(sensitivity["lapse_factor"])
    P.rate_shift = float(sensitivity["rate_shift"])

    T = P.max_proj_len() - 1  # months projected (last month is maturity only)
    df = P.disc_factors()

    def monthly(fn):
        return np.column_stack([np.asarray(fn(t), dtype=float) for t in range(T)])

    def by_year(arr):
        return arr.reshape(arr.shape[0], -1, 12).sum(axis=2)

    premiums = monthly(P.premiums)
    flows = {
        "premiums": premiums,
        "entry_fees": monthly(lambda t: P.premiums(t) - P.prem_to_av(t)),
        "management_fees": monthly(P.maint_fee),
        "financial_margin": monthly(lambda t: P.inv_income(t) - P.interest_cr(t)),
        "death_claims": monthly(lambda t: P.claims(t, "DEATH")),
        "surrender_claims": monthly(lambda t: P.claims(t, "LAPSE")),
        "maturity_claims": monthly(lambda t: P.claims(t, "MATURITY")) + by_month_maturity(P, T),
        "expenses": monthly(P.expenses),
        "commissions": monthly(P.commissions),
        "profit": monthly(P.net_cf),
    }
    disc = df[:T]
    annual = {k: by_year(v) for k, v in flows.items()}
    annual["premiums_pv"] = by_year(premiums * disc)
    annual["profit_pv"] = by_year(flows["profit"] * disc)

    year_ends = np.arange(12, T + 1, 12)
    pols = np.column_stack([np.asarray(P.pols_if_at(t, "BEF_MAT")) for t in year_ends])
    av = np.column_stack([np.asarray(P.av_at(t, "BEF_MAT")) for t in year_ends])
    # Contracts still in force at the horizon are paid out at maturity
    pols[:, -1] = 0.0
    av[:, -1] = 0.0

    ids = P.model_point().index.values
    n_mp, n_years = annual["premiums"].shape
    out = pd.DataFrame({
        "run_id": run_id,
        "management_fee": float(management_fee),
        "sensitivity": sensitivity["sensitivity"],
        "contract_id": np.repeat(ids, n_years),
        "projection_year": np.tile(np.arange(1, n_years + 1), n_mp),
        "credited_rate": P.credited_rate(),
        "guaranteed_rate": P.guaranteed_rate,
        "rate_above_guarantee": P.credited_rate() - P.guaranteed_rate,
        "policies_in_force": pols.ravel(),
        "account_value_end": av.ravel(),
        **{k: v.ravel() for k, v in annual.items()},
    })
    return out[OUTPUT_COLUMNS]


def by_month_maturity(P, T):
    """Account value paid out at the horizon (month T), booked in the last projected month."""
    out = np.zeros((len(P.model_point()), T))
    out[:, -1] = np.asarray(P.claims(T, "MATURITY"), dtype=float)
    return out


def run_all(model_points, mortality, assumptions, lapse_rates, fee_grid, sensitivities):
    model = load_model()
    setup_model(model, model_points, mortality, assumptions, lapse_rates)
    results = []
    for _, sens in sensitivities.iterrows():
        for fee in fee_grid["management_fee"]:
            run_id = "fee_{:.1f}pct__{}".format(fee * 100, sens["sensitivity"])
            results.append(project(model, run_id, fee, sens))
    model.close()
    return pd.concat(results, ignore_index=True)
