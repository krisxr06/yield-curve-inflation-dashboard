# Yield Curve × Inflation Regime Dashboard

An interactive Streamlit dashboard that explores how yield curve regimes and
inflation regimes have historically interacted, and what the current regime
implies for fixed-income risk.

## Core Question

> *How have yield curve regimes and inflation regimes historically interacted,
> and what does the current regime suggest about fixed-income risk?*

## Dashboard Sections

| Section | Content |
|---------|---------|
| **1 — Current Macro Snapshot** | Metric cards (CPI YoY, Fed Funds, 2Y, 10Y, spread, regimes) + plain-English summary |
| **2 — Yield Curve History** | 10Y–2Y spread time series with color-coded regime shading |
| **3 — Inflation History** | YoY CPI time series with inflation level shading |
| **4 — Regime Interaction** | Heatmap of historical month counts, summary table, interpretation |

## Quick Start

```bash
cd yield-curve-inflation-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Optional: FRED API Key

Data is fetched from the FRED public CSV endpoint by default (no key needed).
For faster/more robust fetching via the `fredapi` library:

```bash
cp .env.example .env
# Edit .env and set FRED_API_KEY=your_key_here
```

Get a free API key at <https://fred.stlouisfed.org/docs/api/api_key.html>.

## Data Series (FRED)

| ID | Description | Frequency |
|----|-------------|-----------|
| `CPIAUCSL` | CPI for All Urban Consumers (SA) | Monthly |
| `FEDFUNDS` | Effective Federal Funds Rate | Monthly |
| `DGS2` | 2-Year Treasury Constant Maturity | Daily → resampled monthly |
| `DGS10` | 10-Year Treasury Constant Maturity | Daily → resampled monthly |

## Derived Metrics

| Metric | Formula |
|--------|---------|
| `cpi_yoy` | 12-month % change in CPIAUCSL |
| `spread_10y2y` | DGS10 − DGS2 |
| `spread_3m_chg` | 3-month difference of spread |
| `cpi_yoy_3m_chg` | 3-month difference of cpi_yoy |

## Regime Definitions

### Yield Curve (priority order)

1. **Re-steepening** — spread was negative in prior 6 months AND spread rose > 0.25 ppts over 3 months AND spread is −0.25 to +0.75
2. **Inverted** — spread < 0
3. **Flat** — spread 0 to 0.50
4. **Normal** — spread > 0.50

### Inflation

**Level:** Low < 2% · Moderate 2–4% · High > 4%
**Direction:** Rising (+0.5 ppt 3m change) · Falling (−0.5 ppt) · Stable
**Combined label:** e.g. `"High / Falling"`

## Project Structure

```
yield-curve-inflation-dashboard/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── data_loader.py      # FRED fetch + parquet cache
│   ├── transforms.py       # Resample + derived metrics
│   ├── regimes.py          # Regime classification
│   ├── charts.py           # Plotly figures
│   └── utils.py            # Latest values + text summaries
└── data/
    └── processed/          # Parquet cache (auto-created)
```

## Caching

On first run the app fetches all four FRED series and writes parquet files
to `data/processed/`. Subsequent runs within 24 hours load from cache.
Delete the parquet files or set `force_refresh=True` in `load_all()` to
force a re-fetch.
