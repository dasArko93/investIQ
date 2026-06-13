# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from engines.missing_sector_engine import MissingSectorEngine
from utils.page_utils import merged_holdings, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Portfolio Gaps")
merged = merged_holdings()

if merged.empty:
    st.info("Upload both holdings and stock universe to identify missing target sectors.")
else:
    current_sectors = set(merged["Sub-Sector"].dropna())
    missing = MissingSectorEngine.identify(current_sectors)
    st.write(missing or "No target sector gaps found.")
