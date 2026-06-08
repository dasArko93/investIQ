import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st

from database.init_db import init_db
from utils.dashboard_ui import render_investiq_dashboard


init_db()

st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.markdown("## InvestIQ `v2.0`")
    st.caption("Portfolio")
    st.page_link("pages/1_Portfolio.py", label="Holdings")
    st.page_link("pages/19_Goals.py", label="Goals")
    st.caption("Research")
    with st.expander("Research Hub", expanded=False):
        st.write("Stock screening, analysis, ranking and quantitative analytics in one place.")
        st.page_link("pages/2_Stock_Universe.py", label="Stock Screener")
        st.page_link("pages/4_Stock_Analysis.py", label="Stock Analysis")
        st.page_link("pages/5_Top_Stocks.py", label="Top Stocks")
        st.page_link("pages/20_Quant_Analytics.py", label="Quant Analytics")
    st.caption("Advisor")
    st.page_link("pages/9_Recommendations.py", label="Recommendations")
    st.page_link("pages/13_Buy_Next.py", label="Buy Next")
    st.page_link("pages/10_Cash_Deployment.py", label="Cash Deployment")
    st.page_link("pages/11_Portfolio_Gaps.py", label="Portfolio Gaps")
    st.caption("Actions")
    st.page_link("pages/8_Rebalance.py", label="Rebalance")
    st.page_link("pages/15_Watchlist.py", label="Watchlist")
    st.page_link("pages/16_Alerts.py", label="Alerts")
    st.caption("Reports")
    st.page_link("pages/17_Portfolio_Report.py", label="Portfolio Report")
    st.page_link("pages/18_Investment_Journal.py", label="Investment Journal")

render_investiq_dashboard()
