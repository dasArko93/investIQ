import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import io
import pandas as pd
from datetime import datetime

from utils.data_utils import parse_holdings_file, read_table
from services.mf_holding_service import MFHoldingService


SAMPLE_HOLDINGS_CSV = """Holdings - 09-Jun-26
Security,Quantity,Average Cost Rs,LTP Rs,Current Value Rs,Invested Value Rs,PnL Rs,Net Change %
TCS,10,3500.00,3800.00,38000.00,35000.00,3000.00,8.57
INFY,20,1400.00,1500.00,30000.00,28000.00,2000.00,7.14
RELIANCE,-,-,-,-,-,-,-
"""

SAMPLE_UNIVERSE_CSV = """Ticker,Name,Sub-Sector,Market Cap,Close Price,PE Ratio,Forward PE Ratio,5Y Historical EPS Growth,1Y Forward EPS Growth,5Y CAGR,Free Cash Flow,Debt to Equity,1M Return vs Nifty,Sharpe Ratio,Alpha,ROCE,Return on Equity,5Y Avg Return on Equity,1Y Forward Revenue Growth,5Y Historical Revenue Growth,5Y Hist Op. Cash Flow Growth,1Y Fwd Op. Cash Flow Growth,5Y Avg Net Profit Margin,Earnings Quality Rank,Price to Intrinsic Value Rank,Fundamental Score,Sector PE
TCS,Tata Consultancy Services,IT - Software,1400000,3800,28.5,25.0,12.5,10.0,15.0,40000,0.05,2.1,1.1,0.5,45.0,38.0,36.0,11.0,13.0,12.0,10.0,22.0,85,75,80,26.0
INFY,Infosys,IT - Software,650000,1500,24.0,22.0,10.0,9.0,12.0,20000,0.08,1.5,0.9,0.3,38.0,30.0,29.0,9.5,11.0,9.0,8.0,19.0,80,70,75,26.0
"""

SAMPLE_TICKERTAPE_TXT = """Holding Pattern History by Tickertape
For: Nippon India Growth Fund
Date Exported: 01-Jan-26

Holding Type,31-Dec-24,31-Mar-25,30-Jun-25,30-Sep-25
Equity,96.5,95.8,97.1,96.2
Debt,1.2,1.5,1.1,1.3
Cash & Cash Equivalents,2.3,2.7,1.8,2.5
"""


def test_parse_holdings_from_string():
    df, snapshot_date = parse_holdings_file(SAMPLE_HOLDINGS_CSV)
    assert not df.empty
    assert len(df) == 2  # RELIANCE with '-' should be skipped
    assert "Security" in df.columns
    assert "Quantity" in df.columns
    assert df.iloc[0]["Security"] == "TCS"
    assert snapshot_date.strftime("%Y-%m-%d") == "2026-06-09"


def test_parse_holdings_from_stringio():
    stream = io.StringIO(SAMPLE_HOLDINGS_CSV)
    df, snapshot_date = parse_holdings_file(stream)
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[1]["Security"] == "INFY"


def test_parse_holdings_from_excel_mock():
    # Build an Excel buffer in memory
    excel_data = [
        ["Holdings - 15-Jul-26"],
        [""],
        ["Security", "Quantity", "Average Cost Rs", "LTP Rs"],
        ["HDFCBANK", 50, 1600.0, 1750.0],
        ["ICICIBANK", 30, 1000.0, 1150.0],
    ]
    df_raw = pd.DataFrame(excel_data)
    excel_buf = io.BytesIO()
    df_raw.to_excel(excel_buf, index=False, header=False)
    excel_buf.seek(0)

    # Class with name attribute mimicking UploadedFile
    class MockUploadedExcel(io.BytesIO):
        name = "holdings.xlsx"

    mock_file = MockUploadedExcel(excel_buf.getvalue())
    df, snapshot_date = parse_holdings_file(mock_file)
    assert not df.empty
    assert len(df) == 2
    assert "Security" in df.columns
    assert df.iloc[0]["Security"] == "HDFCBANK"
    assert snapshot_date.strftime("%Y-%m-%d") == "2026-07-15"


def test_read_table_from_string():
    df = read_table(SAMPLE_UNIVERSE_CSV)
    assert not df.empty
    assert len(df) == 2
    assert "Ticker" in df.columns
    assert "TCS" in df["Ticker"].values


def test_mf_holding_parse_pasted():
    fund_name, df = MFHoldingService.parse_tickertape_file(SAMPLE_TICKERTAPE_TXT)
    assert fund_name == "Nippon India Growth Fund"
    assert not df.empty
    assert "Holding Type" in df.columns
    assert "Equity" in df["Holding Type"].values


if __name__ == "__main__":
    test_parse_holdings_from_string()
    test_parse_holdings_from_stringio()
    test_parse_holdings_from_excel_mock()
    test_read_table_from_string()
    test_mf_holding_parse_pasted()
    print("All mobile upload tests passed successfully!")
