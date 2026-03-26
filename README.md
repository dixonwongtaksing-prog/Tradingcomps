# Services Sector Trading Comps

A Streamlit dashboard for services sector trading comparables, powered by Yahoo Finance.

## Features

### Overview Page
- **KPI Summary** — total market cap, daily gainers/losers count, universe median 1Y return
- **Winners and Losers** — top 10 daily movers by name; sector performance bar chart ranked by 1Y median return; sector daily performance table
- **Index Performance** — market-cap weighted sector indices vs. S&P 500 over the last 12 months, interactive multi-sector selector

### Segment Comps Page
- One tab per sector (10 sectors, 349 companies across US and UK)
- Sector-level KPI cards (company count, total market cap, median EV/EBITDA, median EV/Rev)
- Full sector comps table with median summary row
- Subsector breakdown tabs with individual comps tables and EV/EBITDA vs. revenue growth bubble charts

### Metrics Shown
| Metric | Description |
|--------|-------------|
| Price | Current market price |
| 1D % | Daily price change |
| 1Y % | 52-week price return |
| Mkt Cap | Market capitalisation |
| EV | Enterprise value |
| EV/EBITDA | Enterprise value to EBITDA multiple |
| EV/Rev | Enterprise value to revenue multiple |
| Fwd P/E | Forward price to earnings |
| EBITDA Mg | EBITDA margin |
| Rev Growth | Revenue growth (YoY) |

## Setup

### Local Development

```bash
# Clone or extract the project
cd services_comps

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`

## Deployment to Streamlit Community Cloud

1. Push this folder to a GitHub repository (make it public or connect your account)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Select your repo, branch, and set the main file path to `app.py`
5. Click **Deploy**

> The `expanded_services_universe_us_uk.xlsx` file must be in the same directory as `app.py` in the repo.

## Switching to FactSet

When ready to migrate from Yahoo Finance to FactSet:

1. Replace the `fetch_fundamentals()` function in `app.py` with FactSet API calls
2. Update `fetch_prices()` to use FactSet time-series endpoint
3. The rest of the app (UI, charting, comps tables) requires no changes

The FactSet MCP connector is already available in your Claude environment for future integration.

## File Structure

```
services_comps/
├── app.py                              # Main Streamlit application
├── requirements.txt                    # Python dependencies
├── expanded_services_universe_us_uk.xlsx   # Company universe (349 companies)
└── .streamlit/
    └── config.toml                     # Dark theme configuration
```

## Universe Coverage

| Sector | Companies |
|--------|-----------|
| Consulting and professional services | 48 |
| Insurance services | 47 |
| Information and data services | 52 |
| IT services | 62 |
| Wealth management and advisory | 28 |
| Supply chain services | 47 |
| Field services, engineering services, and TIC | 49 |
| Property services | 26 |
| Education | 14 |
| Alternative asset management | 26 |

US: 264 companies | UK: 85 companies
