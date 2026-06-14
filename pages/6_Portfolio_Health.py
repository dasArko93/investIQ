# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.health_service import HealthService
from utils.page_utils import load_holdings, merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("Portfolio Health")
st.info(
    "The Portfolio Health dashboard is now part of the consolidated Holdings view. "
    "Use the Holdings page for a richer combined overview of holdings, allocation, and health."
)

portfolio = load_holdings()
merged = merged_holdings()

if require_data(portfolio, "Upload holdings to evaluate portfolio health."):
    avg_quality = merged["QUALITY_SCORE"].fillna(0).mean() if not merged.empty else 0
    sector_count = merged["Sub-Sector"].nunique() if not merged.empty else 0
    health = HealthService.evaluate(portfolio, avg_quality, sector_count)
    st.metric("Portfolio Health", health)
    st.dataframe(portfolio, use_container_width=True)