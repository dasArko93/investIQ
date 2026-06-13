import pandas as pd
import streamlit as st

from services.holdings_service import HoldingsService
from services.universe_service import UniverseService


def render_sidebar():
    with st.sidebar:
        st.markdown("## InvestIQ `v2.0`")
        st.caption("Portfolio")
        st.page_link("pages/1_Portfolio.py", label="Holdings")
        st.caption("Research")
        st.page_link("pages/2_Stock_Universe.py", label="Stock Universe")
        st.page_link("pages/4_Stock_Analysis.py", label="Fundamental Analysis")
        st.page_link("pages/5_Top_Stocks.py", label="Top Stocks")
        st.page_link("pages/20_Quant_Analytics.py", label="Quant Analytics")
        st.caption("Advisor")
        st.page_link("pages/9_Recommendations.py", label="Recommendations")
        st.page_link("pages/11_Portfolio_Gaps.py", label="Portfolio Gaps")
        st.caption("Actions")
        st.page_link("pages/8_Rebalance.py", label="Rebalance")
        st.page_link("pages/15_Watchlist.py", label="Watchlist")
        st.page_link("pages/16_Alerts.py", label="Alerts")
        st.caption("Reports")
        st.page_link("pages/17_Portfolio_Report.py", label="Portfolio Report")
        st.page_link("pages/18_Investment_Journal.py", label="Investment Journal")


def load_holdings():
    return HoldingsService.dataframe()


def load_universe():
    return UniverseService.dataframe()


def require_data(df, message):
    if df.empty:
        st.info(message)
        return False
    return True


def merged_holdings():
    holdings = load_holdings()
    universe = load_universe()
    if holdings.empty or universe.empty:
        return pd.DataFrame()
    return holdings.merge(universe, left_on="Security", right_on="Ticker", how="left")
