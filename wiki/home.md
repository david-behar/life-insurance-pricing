# Savings Contract Pricing with lifelib

## Purpose
This demo shows that actuarial cash-flow pricing, of the kind usually done in FIS Prophet, can run end to end in Dataiku:

- assumptions are prepared in the flow;
- surrender behaviour is learned with Visual ML;
- cash flows are projected with the open-source **lifelib** library;
- the price is set with visual recipes.

All data is **synthetic**.

## Product
The product is a French-style savings contract on a euro fund, sold as a new single premium.

| Feature | Value |
|---|---|
| Entry fee | 2% of the premium |
| Guaranteed minimum rate | 0.5% |
| Profit sharing | 90% of the asset yield (3%) is credited to policyholders |
| Management fee | Annual fee on the account value. **This is the price we solve for.** |
| Death and surrender benefit | The account value |
| Projection horizon | 30 years. The account value still in force at the horizon is paid out. |

**Credited rate** = max(guaranteed rate, profit sharing × asset yield).

**Insurer profit** = entry fee + management fee + (asset yield − credited rate) × account value − expenses − commissions.

## Flow
**1. Inputs & assumptions**
- Model points: 500 contracts (uploaded file).
- Mortality table.
- Assumptions: **editable**, one row per parameter.
- Fee grid: **editable**.
- Sensitivities: **editable**.

**2. Lapse study**
- A Visual ML task predicts `surrendered` from age, policy year, account value and the rate spread against competitors. It compares a logistic regression baseline with LightGBM; LightGBM is deployed because it has the better log loss. Class weighting is off so that the probabilities stay calibrated.
- The scored experience is averaged per policy year into `lapse_rates`. The model recovers the surrender spike in policy year 9, after the 8-year tax threshold.

**3. Projection & pricing**
- `project_cashflows_with_lifelib` is the only code recipe. It runs the lifelib `savings/CashValue_ME` model for every fee × sensitivity.
- Visual recipes then:
  - compute present values;
  - compute the profit margin = PV profits / PV premiums;
  - pick the **lowest fee whose base-case margin reaches `target_margin`** (project variable, 10%).

## How this maps to Prophet
| Prophet | Dataiku |
|---|---|
| Model point files | `model_points` dataset |
| Assumption tables | `mortality_table`, `lapse_rates`, `assumptions` datasets |
| Run settings | Project variables (`target_margin`) and `sensitivities` |
| Product library / calculation engine | lifelib model with euro-fund overrides (`euro_fund_projection.py`), versioned on GitHub and imported into the project library as a git reference |
| Multiple runs | One run per row of `fee_grid` × `sensitivities` (`run_id`) |
| Result files | `cashflows`, `pricing_results`, dashboard |

## lifelib overrides
lifelib's savings model credits the full investment return to the account value. For a euro fund the engine overrides these formulas:

| Overridden formula | What it does |
|---|---|
| `inv_return_mth` | The insurer earns the asset yield |
| `credited_rate`, `interest_cr`, `av_pp_at` | The account value is credited at max(guarantee, profit sharing × yield) |
| `mort_rate` | Mortality by attained age and sex, with a shock factor |
| `lapse_rate` | Lapse by policy year from `lapse_rates`, with a shock factor |
| `maint_fee_rate`, `commissions`, `expense_*` | Read from `assumptions` and `fee_grid` |
| `disc_rate_mth`, `disc_factors` | Flat discount rate plus the sensitivity rate shift |

**Validation:** the projection of individual contracts was checked against an independent monthly hand calculation, and matches to the cent.

## Data quality checks
**Checked before every run, on the editable inputs:**
- each parameter, fee and sensitivity name is unique;
- every assumption has a value;
- fees are between 0% and 5%;
- shock factors are not negative.

**Checked after the run:**
- mortality and lapse rates are between 0 and 1;
- account values are never negative;
- the credited rate is never below the guaranteed rate;
- at least one full run (500 contracts × 30 years) was projected;
- each run has exactly one result;
- exactly one recommended fee exists.

## How to re-run
1. Edit one of the **editable datasets** in the grid: `assumptions` (one row per parameter), `fee_grid` or `sensitivities`. Or change the `target_margin` project variable.
2. Run the scenario **Run pricing**. It checks the edited inputs, retrains the lapse model, reruns lifelib, reprices and checks the outputs. If you only changed `target_margin`, **Reprice only** takes seconds.
3. Open the dashboard **Savings Contract Pricing**.

The scenario normally ends in **WARNING**. The scoring recipe warns that the scored data already contains the target `surrendered`. This is intended: the experience is scored so that the predicted lapse rates can be compared with the observed ones.

## Limitations
- Mortality, lapse experience and assumptions are synthetic.
- Economics are deterministic, with one scenario per run. There is no stochastic valuation of the guarantee.
- There is no capital or tax.
