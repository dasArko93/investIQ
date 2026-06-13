# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from services.buy_next_service import BuyNextService
from utils.page_utils import load_holdings, load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Cash Deployment")
cash = st.number_input("Available Cash", min_value=0, value=10000, step=1000)
universe = load_universe()
portfolio = load_holdings()

if require_data(universe, "Upload the stock universe to deploy cash."):
    recommendations = BuyNextService.suggest(universe, portfolio, cash)
    st.dataframe(pd.DataFrame(recommendations), use_container_width=True)
