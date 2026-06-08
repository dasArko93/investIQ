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
- Dashboard, sector analysis, portfolio health, recommendations, rebalancing, buy-next ideas, watchlist, alerts, goals, journal, reports, and quant analytics
- SQLite models, repositories, services, and engines

## Notes

InvestIQ is intended for personal long-term research. It is not financial advice and is not built for intraday trading.
