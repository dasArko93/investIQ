# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import plotly.express as px
import streamlit as st

from engines.sector_engine import SectorEngine
from utils.page_utils import merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("Sector Analysis")
st.info(
    "Sector analysis is now integrated into the consolidated Holdings page. "
    "For a complete view of allocation and quality metrics, use the Holdings dashboard."
)

merged = merged_holdings()

if require_data(merged, "Upload both holdings and stock universe to analyze sectors."):
    sector_data = SectorEngine.sector_allocation(merged).reset_index()
    st.plotly_chart(px.bar(sector_data, x="Sub-Sector", y="Current Value Rs"), width='stretch')
    st.dataframe(sector_data, width='stretch')