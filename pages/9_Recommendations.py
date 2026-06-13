# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.recommendation_service import RecommendationService
from utils.page_utils import load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Recommendations")
universe = load_universe()

if require_data(universe, "Upload the stock universe to generate recommendations."):
    st.subheader("Quick Stock Screening Formula")
    st.write(
        "Revenue Growth > 15%, EPS Growth > 15%, ROCE > 20%, ROE > 18%, "
        "Debt/Equity < 0.5, Positive Free Cash Flow, Promoter Holding > 50%, PEG < 1.5."
    )
    st.caption(
        "This screen narrows the universe to fundamentally strong companies for deeper analysis. "
        "Rules that need unavailable columns are skipped until those fields are uploaded."
    )
    recommendations = RecommendationService.generate(universe)
    st.subheader("Fundamental Score Recommendations")
    st.dataframe(recommendations, use_container_width=True)
