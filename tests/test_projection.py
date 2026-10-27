"""Local check: lifelib projection vs an independent hand calculation for one contract."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "python"))
import euro_fund_projection as projection  # noqa: E402

D = Path(__file__).parent.parent / "data_gen" / "out"
mp = pd.read_csv(D / "model_points.csv")
mort = pd.read_csv(D / "mortality_table.csv")
assm = pd.read_csv(D / "assumptions.csv")
exp = pd.read_csv(D / "lapse_experience.csv")
lapse = exp.groupby("policy_year", as_index=False)["surrendered"].mean().rename(
    columns={"surrendered": "lapse_rate"})
fees = pd.read_csv(D / "fee_grid.csv")
sens = pd.read_csv(D / "sensitivities.csv")


def hand_calc(age, sex, prem, fee, a, q_tab, l_tab, mort_f=1.0, lapse_f=1.0, shift=0.0):
    """Monthly recursion written from scratch (no lifelib)."""
    y = a.asset_yield + shift
    cr = (1 + max(a.guaranteed_rate, a.profit_sharing_rate * y)) ** (1 / 12) - 1
    iy = (1 + y) ** (1 / 12) - 1
    v = (1 + a.discount_rate + shift) ** (-1 / 12)
    n, av, pv = 1.0, 0.0, 0.0
    for t in range(12 * int(a.projection_years)):
        yr, att_age = t // 12, min(age + t // 12, 120)
        q = min(q_tab[(att_age, sex)] * mort_f, 1.0)
        qm = 1 - (1 - q) ** (1 / 12)
        lm = 1 - (1 - min(l_tab[min(yr + 1, max(l_tab))] * lapse_f, 1.0)) ** (1 / 12)
        p = prem if t == 0 else 0.0
        av_fee = av + p * (1 - a.entry_fee_rate)
        fee_amt = av_fee * fee / 12
        av_inv = av_fee - fee_amt
        dth, lps = n * qm, (n - n * qm) * lm
        n_end = n - dth - lps
        av_end = av_inv * (1 + cr)
        # insurer: entry fee + mgmt fee + (asset yield - credited) on assets - costs
        fin = (iy - cr) * av_inv * (n_end + 0.5 * (dth + lps))
        exp_ = (a.acquisition_expense if t == 0 else 0) + n * a.maintenance_expense / 12 * (
            1 + a.expense_inflation) ** (t / 12)
        profit = p * a.entry_fee_rate + fee_amt * n + fin - exp_ - a.commission_rate * p
        pv += profit * v ** t
        n, av = n_end, av_end
    return pv


if __name__ == "__main__":
    t0 = time.time()
    model = projection.load_model()
    projection.setup_model(model, mp, mort, assm, lapse)
    base = sens.iloc[0]
    out = projection.project(model, "test", 0.008, base)
    print("one run:", round(time.time() - t0, 1), "s", out.shape)

    a = assm.set_index("parameter")["value"].astype(float)
    q_tab = mort.set_index(["age", "sex"])["qx"].to_dict()
    l_tab = lapse.set_index("policy_year")["lapse_rate"].to_dict()
    for cid in [1, 2, 3]:
        c = mp[mp.contract_id == cid].iloc[0]
        mine = hand_calc(c.age, c.sex, c.single_premium, 0.008, a, q_tab, l_tab)
        lib = out[out.contract_id == cid]["profit_pv"].sum()
        print(f"contract {cid}: lifelib PV profit={lib:,.2f}  hand={mine:,.2f}  diff={lib - mine:.4f}")

    g = out.groupby("projection_year")[["policies_in_force", "account_value_end", "profit"]].sum()
    print(g.head(10).round(0))
    print("margin:", out.profit_pv.sum() / out.premiums_pv.sum())
    print(out.isna().sum().sum(), "NaNs;", (out.account_value_end < 0).sum(), "negative AV")
    if "--quick" in sys.argv:
        sys.exit()

    t0 = time.time()
    allres = projection.run_all(mp, mort, assm, lapse, fees, sens)
    print("all runs:", round(time.time() - t0, 1), "s", allres.shape)
    r = allres.groupby(["sensitivity", "management_fee"])[["profit_pv", "premiums_pv"]].sum()
    r["margin"] = r.profit_pv / r.premiums_pv
    print(r["margin"].unstack().round(4))
