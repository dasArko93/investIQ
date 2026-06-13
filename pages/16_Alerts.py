# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from utils.page_utils import render_sidebar

from database.models import Alert
from database.repositories.alert_repository import AlertRepository


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Alerts")

ticker = st.text_input("Ticker").strip().upper()
rule = st.selectbox("Rule", ["QUALITY_SCORE > 80", "ROCE > 15", "Debt to Equity < 0.5", "PE Ratio < Sector PE"])
if st.button("Create Alert") and ticker:
    AlertRepository.add(Alert(ticker=ticker, rule=rule, active=True))
    st.success("Alert created")

rows = AlertRepository.get_all()
data = [{"Ticker": row.ticker, "Rule": row.rule, "Active": row.active} for row in rows]
st.dataframe(pd.DataFrame(data), use_container_width=True)
