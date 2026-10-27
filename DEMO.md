# Demo script: savings contract pricing in Dataiku (≈15 min)

**Project:** `SAVINGS_PRICING_DEMO`, at `{DSS_URL}/projects/SAVINGS_PRICING_DEMO/`. Replace `{DSS_URL}` with your Dataiku instance URL.

**Audience message:** *"Everything you do in Prophet (model points, assumptions, projection, runs, results) can live in one governed, readable Dataiku flow. On top of that, assumptions can be learned from data, and the business can rerun pricing itself."*

---

## Before the demo (5 min)
1. Open these tabs:
   - [Flow]({DSS_URL}/projects/SAVINGS_PRICING_DEMO/flow/)
   - [Dashboard]({DSS_URL}/projects/SAVINGS_PRICING_DEMO/dashboards/SVkholF/view/)
   - [Wiki]({DSS_URL}/projects/SAVINGS_PRICING_DEMO/wiki/)
2. Open the editable `assumptions` dataset, so you can show it in section 2.
3. Check that the `target_margin` project variable is **0.10**: *… menu → Variables*.
4. Check that `recommended_fee` shows **0.8%**. If it doesn't, run the **Run pricing** scenario, which takes about 3 minutes.
5. If you will show the dashboard to people outside the project, grant its sources under *Dashboard → Settings → Authorizations*, or its tiles will be blank for them.

---

## 1. The problem (1 min)
Pricing a savings product means projecting every contract month by month for 30 years. You do this under many fee levels and stress scenarios, then pick the price that meets a profit target.

Today this runs in Prophet: a black box few people can read, with data prep in Excel or SAS around it.

**The product:** a French euro-fund savings contract.

| Feature | Value |
|---|---|
| Entry fee | 2% |
| Guaranteed minimum rate | 0.5% |
| Profit sharing | 90% of a 3% asset yield is credited to policyholders |
| Management fee | **The price we solve for** |

## 2. The flow: Prophet concepts, readable (3 min)
Open the **Flow** and walk through the three zones from left to right.

**Zone 1, Inputs & assumptions.** Open each dataset.

| Dataset | What to say |
|---|---|
| `model_points`, `mortality_table` | "Our model point file (500 new contracts) and mortality table, loaded as files like a policy extract." |
| `assumptions` (editable) | "The assumption table. It's an editable dataset: one row per parameter with unit and description, edited in the grid, with every change tracked." Click a cell to show it's editable. |
| `fee_grid` (editable) | "The prices we test: 0.5% to 1.0%." |
| `sensitivities` (editable) | "Our run structure. Adding a stress test means adding a row, not touching code." |

**Zone 3, Projection & pricing.**
- Open `project_cashflows_with_lifelib`.
  - "This is the only code in the project: about 20 lines that call **lifelib**, an open-source actuarial library, much like Prophet's product library."
  - Show the engine in the project library (*Code → Libraries*). It is a **git reference to a GitHub repo**: "Actuarial code is versioned and reviewed in Git like any software, and Dataiku pulls the released version." Point out the euro-fund crediting override: `max(guarantee, 90% × yield)`.
- Open `cashflows`. "450,000 rows: every contract, every year, every run. It's fully auditable, and you can filter to one contract."
- Then show the visual recipes: `aggregate_present_values_by_run` → `calculate_profit_margin` → `select_recommended_fee`. "The pricing decision itself is visual. An actuary or product manager can read it without Python."

**Trust point:** "We checked the lifelib projection against an independent hand calculation. It matches to the cent." (This is in the wiki.)

## 3. Learned assumptions: the "beyond Prophet" moment (3 min)
Open **Zone 2, Lapse study**, then the ML task (*Lab → Visual analyses*, or double-click `lapse_model`).

- "Instead of an actuary hand-setting surrender rates, we learn them from experience data."
- Two models were trained:

  | Model | Log loss |
  |---|---|
  | Logistic regression (baseline) | 0.270 |
  | LightGBM | **0.262** (wins) |

- Show feature importance or partial dependence on `policy_year` and `rate_spread`.
- On the dashboard, show the chart **"Lapse rate by policy year"**. "The model found the surrender spike in policy year 9 (21%). That is the French 8-year tax threshold, discovered from the data rather than hard-coded."

## 4. Results (3 min)
Open the **Dashboard**.

**KPIs:** recommended fee **0.8%**, profit margin **10.8%** against a 10% target.

**Margin by fee and sensitivity:** every line rises with the fee. Margin at the 0.8% fee:

| Run | Margin |
|---|---|
| Base | 10.8% |
| Lapse −50% | 14.5% |
| Lapse +50% | 8.6% |
| Rates −1% | 9.8% |
| Mortality +15% | 10.6% |

Talking point: *"Lapse risk is the dominant driver for this product, not mortality."*

**Profit signature:**
- Year 1 shows the entry fee net of commission and acquisition costs.
- Profit then runs off with the account value.
- There is a visible drop after year 9, when the surrender spike hits.

## 5. Live what-if: business self-service (2 min)
1. Change the `target_margin` project variable to **0.12** and save.
2. Go to *Scenarios → **Reprice only** → Run*. It takes about 15 seconds and does not rerun lifelib.
3. Refresh the dashboard. The recommended fee becomes **1.0%**, with a margin of 12.5%.
4. "Pricing committee asks for more margin? Answered in seconds, with full lineage."
5. **Reset `target_margin` to 0.10 and run *Reprice only* again**, so the project is ready for the next demo.

**Optional, if you have 3 minutes to fill: edit an assumption.**
1. In the editable `sensitivities` dataset, add a row such as `rates_down_2pct | 1 | 1 | -0.02 | Asset yield and discount rate - 2%`.
   - Alternatively, change `asset_yield` in `assumptions`.
2. Run **Run pricing**. It checks the edited inputs first, then reruns all lifelib projections and checks the outputs. Talk through section 6 while it runs.
3. Show the new line on the margin chart.

At −2% the asset yield is 1%, so 90% × 1% = 0.9% is credited. The guarantee still doesn't bite. To show its cost, set `asset_yield` to 0.005 instead.

**Afterwards, delete the row or reset the value, and rerun.**

## 6. Governance and operations (1 min)
**Scenarios:**
- **Run pricing** gives a full, repeatable run with data-quality checks. Its status is normally WARNING; see the Q&A below.
- **Reprice only** handles quick repricing.

**Data-quality rules:**
- **On the editable inputs, checked before any run:**
  - no duplicate parameters, fees or sensitivity names;
  - every assumption has a value;
  - fees between 0% and 5%;
  - shock factors not negative.

  "A wrong edit stops the run before it produces a wrong price."
- **On the outputs** (open `cashflows → Data Quality`):
  - account values are never negative;
  - the credited rate is never below the guaranteed rate;
  - at least one full run was projected, and each run has exactly one result;
  - mortality and lapse rates are between 0 and 1.

**Wiki:** assumptions, method, how this maps to Prophet, and how to re-run.

---

## Likely questions
| Question | Answer |
|---|---|
| Is this production Prophet replacement? | It's a demonstrator. lifelib is an open-source modelling library (MIT licence), not a certified engine. Dataiku adds governance, data prep, ML and orchestration around any engine, including Prophet itself via its outputs. |
| Speed? | 500 contracts × 30 runs × 360 months takes about 2.5 minutes in one Python process. lifelib is vectorised, and runs can be parallelised or containerised. |
| Real tables? | All data is synthetic. Mortality is a Gompertz curve, not TH/TF 00-02. Plug in real tables by replacing the input datasets. |
| Stochastic / guarantee cost? | Not included: one deterministic scenario per run. Even at "rates −1%", 90% × 2% = 1.8% credited, so the 0.5% guarantee never binds here. A next step is stochastic economic scenarios. |
| Why does Run pricing end in WARNING? | The scoring recipe warns that the scored data contains the target. This is intended, so predicted and observed lapse rates can be compared. |
| Why not all visual? | Recursive monthly projection has no visual equivalent. That's the one place code earns its keep; everything else is visual. |
