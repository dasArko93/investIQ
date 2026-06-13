# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import streamlit as st

from services.ranking_service import RankingService
from utils.page_utils import load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Top Ranked Stocks")
st.write("View the universe ranked by quality, momentum, or ranking rules as defined in your configuration.")
universe = load_universe()

if require_data(universe, "Upload the stock universe to rank stocks."):
    ranked = RankingService.rank(universe)
    st.subheader("Top 50 Stocks")
    st.dataframe(ranked.head(50), use_container_width=True)

    if "QUALITY_SCORE" in ranked.columns:
        # ensure numeric type and proper tooltip field names
        ranked["QUALITY_SCORE"] = ranked["QUALITY_SCORE"].astype(float)
        ranked["Ticker"] = ranked["Ticker"].astype(str)

        chart = alt.Chart(ranked.head(20)).mark_bar().encode(
            x=alt.X("QUALITY_SCORE:Q", title="Quality Score"),
            y=alt.Y("Ticker:N", sort="-x", title="Ticker"),
            tooltip=[
                alt.Tooltip("Ticker:N", title="Ticker"),
                alt.Tooltip("QUALITY_SCORE:Q", title="Quality Score", format=".2f"),
                alt.Tooltip("Name:N", title="Name"),
            ],
        ).properties(title="Top Stocks by Quality Score", height=420)
        st.altair_chart(chart, use_container_width=True)
