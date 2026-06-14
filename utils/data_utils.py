import re
import csv
from io import StringIO
from datetime import datetime

import pandas as pd
from pandas.errors import ParserError


def parse_holdings_file(file):
    if hasattr(file, "read"):
        if hasattr(file, "seek"):
            file.seek(0)
        raw = file.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig", errors="ignore")
        else:
            text = raw
    else:
        with open(file, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read()

    # 1. Extract date from the first few lines
    snapshot_date = None
    lines = text.splitlines()
    for line in lines[:15]:
        if "Holdings - " in line:
            # Extract date string like '09-Jun-26'
            match = re.search(r"Holdings\s*-\s*([A-Za-z0-9\-]+)", line)
            if match:
                date_str = match.group(1)
                for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d"):
                    try:
                        snapshot_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        pass
            if snapshot_date:
                break

    if not snapshot_date:
        snapshot_date = datetime.utcnow()
    # Normalize to date only (00:00:00) to keep group/distinct clean
    snapshot_date = datetime(snapshot_date.year, snapshot_date.month, snapshot_date.day)

    # 2. Extract headers and rows
    reader = csv.reader(StringIO(text))
    rows = list(reader)

    header_row = None
    header_idx = -1
    for idx, r in enumerate(rows):
        r_clean = [col.strip() for col in r]
        if "Security" in r_clean and ("Quantity" in r_clean or "Qty" in r_clean or "Qty." in r_clean):
            header_row = r_clean
            header_idx = idx
            break

    if header_row is None:
        return pd.DataFrame(), snapshot_date

    valid_rows = []
    for r in rows[header_idx + 1:]:
        if not r or len(r) == 0:
            continue
        sec = r[0].strip()
        # Skip labels/sections
        if sec in ("", "Stocks/ETFs", "Smallcases", "Security") or "Visit:" in sec:
            continue

        # Skip rows where Quantity/Avg Cost are '-' (indicates smallcases or non-stock lines)
        qty_idx = -1
        for i, col in enumerate(header_row):
            if "Quantity" in col or "Qty" in col:
                qty_idx = i
                break
        if qty_idx != -1 and qty_idx < len(r):
            qty_val = r[qty_idx].strip()
            if qty_val in ("", "-", "0.00", "0"):
                if qty_val == "-":
                    continue

        avg_cost_idx = -1
        for i, col in enumerate(header_row):
            if "Average Cost" in col or "Avg Cost" in col:
                avg_cost_idx = i
                break
        if avg_cost_idx != -1 and avg_cost_idx < len(r):
            cost_val = r[avg_cost_idx].strip()
            if cost_val == "-":
                continue

        valid_rows.append(r[:len(header_row)])

    # Pad shorter rows
    for r in valid_rows:
        if len(r) < len(header_row):
            r.extend([""] * (len(header_row) - len(r)))

    df = pd.DataFrame(valid_rows, columns=header_row)
    return df, snapshot_date


HOLDING_COLUMNS = [
    "Security",
    "No. of Smallcases",
    "Quantity",
    "Average Cost Rs",
    "Portfolio Weight %",
    "LTP Rs",
    "Invested Value Rs",
    "Current Value Rs",
    "PnL Rs",
    "PnL %",
    "Day PnL",
    "Day PnL %",
    "Broker Sector",
    "Asset Class",
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
    return re.sub(r"[^a-z0-9%]+", "", str(value).lower())


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
            "No. of Smallcases": item.no_of_smallcases,
            "Quantity": item.quantity,
            "Average Cost Rs": item.average_cost,
            "Portfolio Weight %": item.portfolio_weight,
            "LTP Rs": item.ltp,
            "Invested Value Rs": item.invested_value,
            "Current Value Rs": item.current_value,
            "PnL Rs": item.pnl,
            "PnL %": item.pnl_pct,
            "Day PnL": item.day_pnl,
            "Day PnL %": item.day_pnl_pct,
            "Broker Sector": item.broker_sector,
            "Asset Class": item.asset_class,
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
