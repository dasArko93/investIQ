import re
import csv
from io import StringIO

import pandas as pd
from pandas.errors import ParserError


HOLDING_COLUMNS = [
    "Security",
    "Quantity",
    "Average Cost Rs",
    "Portfolio Weight %",
    "LTP Rs",
    "Invested Value Rs",
    "Current Value Rs",
    "PnL Rs",
]

UNIVERSE_COLUMNS = [
    "Name",
    "Ticker",
    "Sub-Sector",
    "Market Cap",
    "Close Price",
    "ROCE",
    "PE Ratio",
    "Forward PE Ratio",
    "Sector PE",
    "5Y CAGR",
    "5Y Historical Revenue Growth",
    "Free Cash Flow",
    "Debt to Equity",
    "1M Return vs Nifty",
    "Sharpe Ratio",
    "Alpha",
    "QUALITY_SCORE",
]


def key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def read_table(file):
    name = str(getattr(file, "name", file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    try:
        return pd.read_csv(file)
    except ParserError:
        return read_repaired_csv(file)


def read_repaired_csv(file):
    if hasattr(file, "seek"):
        file.seek(0)
        raw = file.read()
    else:
        with open(file, "rb") as handle:
            raw = handle.read()

    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig")
    else:
        text = raw

    reader = csv.reader(StringIO(text))
    rows = list(reader)
    if not rows:
        return pd.DataFrame()

    header = rows[0]
    width = len(header)
    repaired = []

    for row in rows[1:]:
        if len(row) > width:
            extra = len(row) - width
            row = [",".join(row[: extra + 1])] + row[extra + 1 :]
        elif len(row) < width:
            row = row + [""] * (width - len(row))
        repaired.append(row)

    return pd.DataFrame(repaired, columns=header)


def pick(row, aliases, default=0):
    lookup = {key(column): column for column in row.index}
    for alias in aliases:
        column = lookup.get(key(alias))
        if column is not None:
            return row[column]
    return default


def number(value, default=0.0):
    if pd.isna(value):
        return default
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").replace("Rs", "")
        value = re.sub(r"[^0-9.\-]", "", value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def holdings_to_frame(records):
    rows = [
        {
            "Security": item.security,
            "Quantity": item.quantity,
            "Average Cost Rs": item.average_cost,
            "Portfolio Weight %": item.portfolio_weight,
            "LTP Rs": item.ltp,
            "Invested Value Rs": item.invested_value,
            "Current Value Rs": item.current_value,
            "PnL Rs": item.pnl,
        }
        for item in records
    ]
    return pd.DataFrame(rows, columns=HOLDING_COLUMNS)


def stocks_to_frame(records):
    rows = [
        {
            "Name": item.name,
            "Ticker": item.ticker,
            "Sub-Sector": item.sub_sector,
            "Market Cap": item.market_cap,
            "Close Price": item.close_price,
            "ROCE": item.roce,
            "PE Ratio": item.pe_ratio,
            "Forward PE Ratio": item.forward_pe_ratio,
            "Sector PE": item.sector_pe,
            "5Y CAGR": item.cagr_5y,
            "5Y Historical Revenue Growth": item.revenue_growth_5y,
            "Free Cash Flow": item.free_cash_flow,
            "Debt to Equity": item.debt_to_equity,
            "1M Return vs Nifty": item.return_vs_nifty,
            "Sharpe Ratio": item.sharpe_ratio,
            "Alpha": item.alpha,
            "QUALITY_SCORE": item.quality_score,
        }
        for item in records
    ]
    return pd.DataFrame(rows, columns=UNIVERSE_COLUMNS)
