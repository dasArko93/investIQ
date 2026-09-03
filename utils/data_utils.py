import os
import io
import re
import csv
from io import StringIO
from datetime import datetime

import pandas as pd
from pandas.errors import ParserError


def parse_holdings_excel(file):
    """Parse Excel holdings file (.xlsx or .xls) extracting metadata and rows."""
    if hasattr(file, "seek"):
        file.seek(0)
    df_raw = pd.read_excel(file, header=None)
    if df_raw.empty:
        return pd.DataFrame(), datetime.utcnow()

    # 1. Extract date from the first few rows
    snapshot_date = None
    for r_idx in range(min(15, len(df_raw))):
        row_str = " ".join([str(val) for val in df_raw.iloc[r_idx].dropna()])
        if "Holdings - " in row_str:
            match = re.search(r"Holdings\s*-\s*([A-Za-z0-9\-]+)", row_str)
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
    snapshot_date = datetime(snapshot_date.year, snapshot_date.month, snapshot_date.day)

    # 2. Extract header row
    header_idx = -1
    header_row = None
    for idx in range(len(df_raw)):
        row_vals = [str(x).strip() for x in df_raw.iloc[idx].tolist() if pd.notna(x)]
        if "Security" in row_vals and any(q in row_vals for q in ("Quantity", "Qty", "Qty.")):
            header_idx = idx
            header_row = [str(x).strip() if pd.notna(x) else f"Col_{i}" for i, x in enumerate(df_raw.iloc[idx].tolist())]
            break

    if header_row is None:
        return pd.DataFrame(), snapshot_date

    # 3. Extract valid rows
    data_rows = df_raw.iloc[header_idx + 1:].values.tolist()
    valid_rows = []
    for r in data_rows:
        r_str = [str(x).strip() if pd.notna(x) else "" for x in r]
        if not r_str or len(r_str) == 0:
            continue
        sec = r_str[0]
        if sec in ("", "Stocks/ETFs", "Smallcases", "Security", "nan") or "Visit:" in sec:
            continue

        qty_idx = -1
        for i, col in enumerate(header_row):
            if "Quantity" in col or "Qty" in col:
                qty_idx = i
                break
        if qty_idx != -1 and qty_idx < len(r_str):
            qty_val = r_str[qty_idx]
            if qty_val in ("", "-", "0.00", "0", "nan"):
                if qty_val == "-":
                    continue

        avg_cost_idx = -1
        for i, col in enumerate(header_row):
            if "Average Cost" in col or "Avg Cost" in col:
                avg_cost_idx = i
                break
        if avg_cost_idx != -1 and avg_cost_idx < len(r_str):
            cost_val = r_str[avg_cost_idx]
            if cost_val == "-":
                continue

        valid_rows.append(r_str[:len(header_row)])

    for r in valid_rows:
        if len(r) < len(header_row):
            r.extend([""] * (len(header_row) - len(r)))

    df = pd.DataFrame(valid_rows, columns=header_row)
    return df, snapshot_date


def parse_holdings_file(file):
    name = str(getattr(file, "name", "")).lower()
    if name.endswith((".xlsx", ".xls")):
        return parse_holdings_excel(file)

    if hasattr(file, "read"):
        if hasattr(file, "seek"):
            file.seek(0)
        raw = file.read()
        if isinstance(raw, bytes):
            # Check for Excel PK zip header or OLE header
            if raw.startswith(b"PK\x03\x04") or raw.startswith(b"\xd0\xcf\x11\xe0"):
                return parse_holdings_excel(io.BytesIO(raw))
            text = raw.decode("utf-8-sig", errors="ignore")
        else:
            text = raw
    elif isinstance(file, str):
        if "\n" in file or not os.path.exists(file):
            text = file
        else:
            with open(file, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
    else:
        text = str(file)

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
    "Return on Equity",
    "5Y Avg Return on Equity",
    "1Y Forward Revenue Growth",
    "5Y Historical EPS Growth",
    "1Y Forward EPS Growth",
    "5Y Hist Op. Cash Flow Growth",
    "1Y Fwd Op. Cash Flow Growth",
    "5Y Avg Net Profit Margin",
    "Earnings Quality Rank",
    "Price to Intrinsic Value Rank",
    "Fundamental Score",
    "PEG Ratio (Historical)",
    "PEG Ratio (Forward)",
]


def key(value):
    return re.sub(r"[^a-z0-9%]+", "", str(value).lower())


def read_table(file):
    if isinstance(file, str):
        if "\n" in file or not os.path.exists(file):
            return pd.read_csv(StringIO(file))
        name = file.lower()
    else:
        name = str(getattr(file, "name", "")).lower()

    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    try:
        if hasattr(file, "seek"):
            file.seek(0)
        return pd.read_csv(file)
    except ParserError:
        return read_repaired_csv(file)


def read_repaired_csv(file):
    if hasattr(file, "seek"):
        file.seek(0)
        raw = file.read()
    elif isinstance(file, str):
        if "\n" in file or not os.path.exists(file):
            raw = file
        else:
            with open(file, "rb") as handle:
                raw = handle.read()
    else:
        with open(file, "rb") as handle:
            raw = handle.read()

    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig", errors="ignore")
    else:
        text = str(raw)

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
            "Return on Equity": getattr(item, "return_on_equity", 0.0),
            "5Y Avg Return on Equity": getattr(item, "return_on_equity_5y_avg", 0.0),
            "1Y Forward Revenue Growth": getattr(item, "revenue_growth_1y_fwd", 0.0),
            "5Y Historical EPS Growth": getattr(item, "eps_growth_5y_hist", 0.0),
            "1Y Forward EPS Growth": getattr(item, "eps_growth_1y_fwd", 0.0),
            "5Y Hist Op. Cash Flow Growth": getattr(item, "op_cash_flow_growth_5y_hist", 0.0),
            "1Y Fwd Op. Cash Flow Growth": getattr(item, "op_cash_flow_growth_1y_fwd", 0.0),
            "5Y Avg Net Profit Margin": getattr(item, "net_profit_margin_5y_avg", 0.0),
            "Earnings Quality Rank": getattr(item, "earnings_quality_rank", 0.0),
            "Price to Intrinsic Value Rank": getattr(item, "price_to_intrinsic_value_rank", 0.0),
            "Fundamental Score": getattr(item, "fundamental_score", 0.0),
            "PEG Ratio (Historical)": getattr(item, "peg_historical", 0.0),
            "PEG Ratio (Forward)": getattr(item, "peg_forward", 0.0),
        }
        for item in records
    ]
    return pd.DataFrame(rows, columns=UNIVERSE_COLUMNS)
