# InvestIQ

InvestIQ is a Streamlit application for long-term Indian equity portfolio research. It works from uploaded holdings and stock-universe files, persists data in SQLite, and avoids external market APIs.

## Run Locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Data Inputs

Upload holdings from `1_Portfolio` and the stock universe from `2_Stock_Universe`.

The application persists data to:

```text
data/investiq.db
```

## Included Features

- Portfolio upload and persisted reload
- Stock universe upload and quality scoring
- Mutual Fund Institutional Holding Pattern: 50+ flagship schemes across 19+ AMCs, rolling disclosure snapshots, consensus metrics, and MoM sentiment delta tracking
- Interactive Portfolio Rebalancing Simulator: Benchmark against Top 10/20/30/50 AUM cohorts, alignment intensity slider, pure buy / self-funding trimming modes, dynamic fresh capital calculations, and actionable order generation with live LTP and market cap tiers
- Dashboard, sector analysis, portfolio health, recommendations, rebalancing, buy-next ideas, watchlist, alerts, goals, journal, reports, and quant analytics
- SQLite models, repositories, services, and engines

## Notes

InvestIQ is intended for personal long-term research. It is not financial advice and is not built for intraday trading.
