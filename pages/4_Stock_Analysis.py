# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import pandas as pd
import streamlit as st

from utils.page_utils import load_universe, require_data


st.title("Stock Analysis")
st.write("Search a ticker and instantly review its key metrics, valuation, and peer-relative profile.")
universe = load_universe()

if require_data(universe, "Upload a stock universe to search stocks."):
    ticker = st.text_input("Ticker").strip().upper()
    if ticker:
        stock = universe[universe["Ticker"].astype(str).str.upper() == ticker]
        if stock.empty:
            st.warning("No matching stock found. Please check the ticker and try again.")
        else:
            st.subheader(f"{ticker} Profile")
            st.dataframe(stock, use_container_width=True)

            numeric_cols = [
                "ROCE",
                "PE Ratio",
                "Forward PE Ratio",
                "5Y CAGR",
                "Debt to Equity",
                "Sharpe Ratio",
                "Alpha",
                "QUALITY_SCORE",
            ]
            available_cols = [col for col in numeric_cols if col in stock.columns]
            if available_cols:
                metrics = stock[available_cols].iloc[0].to_frame(name="Value").reset_index()
                metrics.columns = ["Metric", "Value"]
                metrics["Value"] = pd.to_numeric(metrics["Value"], errors="coerce")
                metrics = metrics.dropna()
                if not metrics.empty:
                    chart = alt.Chart(metrics).mark_bar().encode(
                        x=alt.X("Value:Q", title="Value"),
                        y=alt.Y("Metric:N", sort="-x"),
                        tooltip=["Metric", alt.Tooltip("Value", format=".2f")],
                    ).properties(height=420, title="Key Stock Metrics")
                    st.altair_chart(chart, use_container_width=True)
