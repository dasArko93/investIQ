# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.ranking_service import RankingService
from utils.page_utils import load_holdings, load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Opportunity Dashboard")
universe = load_universe()
portfolio = load_holdings()

if require_data(universe, "Upload the stock universe to view opportunities."):
    owned = set(portfolio["Security"]) if not portfolio.empty else set()
    opportunities = RankingService.rank(universe)
    opportunities = opportunities[~opportunities["Ticker"].isin(owned)]
    st.dataframe(opportunities.head(20), use_container_width=True)
