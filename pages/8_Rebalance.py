# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from services.rebalance_service import RebalanceService
from utils.page_utils import load_holdings, require_data


st.title("Rebalance")
portfolio = load_holdings()

if require_data(portfolio, "Upload holdings to generate a rebalancing plan."):
    actions = RebalanceService.generate(portfolio)
    st.dataframe(pd.DataFrame(actions), use_container_width=True)
