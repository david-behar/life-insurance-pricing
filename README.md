# Savings contract pricing demo (Dataiku + lifelib)

This repository holds the code and docs behind the Dataiku project `SAVINGS_PRICING_DEMO`. The project prices a euro-fund savings contract Prophet-style:
- the open-source [lifelib](https://lifelib.io) savings model projects cash flows;
- a Visual ML lapse study supplies the lapse assumption;
- sensitivity runs and a dashboard show the results.

All data is synthetic.

| Path | What |
|---|---|
| `python/euro_fund_projection.py` | The lifelib euro-fund engine. **The Dataiku project library imports the `python/` folder from this repo** as a git reference. |
| `recipes/project_cashflows_with_lifelib.py` | Code of the Python recipe that calls the engine |
| `tests/test_projection.py` | Checks lifelib against an independent monthly hand calculation (`--quick` checks one run only) |
| `data_gen/generate.py` | Generates the synthetic inputs into `data_gen/out/` (seeded, not committed) |
| `wiki/home.md` | Project wiki article |
| `DEMO.md` | Demo script (about 15 minutes) |

## Assumptions are edited in Dataiku, not here
`assumptions`, `fee_grid` and `sensitivities` are **editable datasets** in the project. To change one:
1. Edit it in the grid.
2. Run the **Run pricing** scenario. It checks the inputs, reruns lifelib, reprices and checks the outputs.

`data_gen/generate.py` only produced their initial values.

## Local development

```bash
uv venv -p 3.11 .venv && uv pip install -p .venv lifelib modelx openpyxl pandas numpy
.venv/bin/python data_gen/generate.py
.venv/bin/python tests/test_projection.py --quick
```

## Releasing engine changes to Dataiku
1. Push to `main`.
2. In Dataiku, open *Project library → Git references → `savings_pricing_engine` → Update from Git*, or run the "Reset from remote" step from the API.
3. Rerun **Run pricing**.
