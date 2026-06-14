# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import pandas as pd
import streamlit as st

from utils.page_utils import render_sidebar

from services.universe_service import UniverseService


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")

from utils.page_utils import require_auth
require_auth()

render_sidebar()

st.title("Stock Universe")
st.write(
    "Upload or review your stock universe here. This page now includes interactive charts to explore quality, sectors, and valuation patterns."
)

file = st.file_uploader("Upload Universe", type=["csv"])
if file:
    count = UniverseService.upload(file)
    st.success(f"{count} stocks loaded")

universe = UniverseService.dataframe()
if universe.empty:
    st.info("Upload the stock universe CSV to enable analysis and recommendations.")
else:
    st.subheader("Universe Sample")
    st.dataframe(universe.head(200), use_container_width=True)

    if "QUALITY_SCORE" in universe.columns:
        score_chart = alt.Chart(universe).mark_bar().encode(
            x=alt.X("QUALITY_SCORE:Q", bin=alt.Bin(maxbins=20), title="Quality Score"),
            y=alt.Y("count():Q", title="Stocks"),
            tooltip=[alt.Tooltip("count():Q", title="Count")],
        ).properties(title="Quality Score Distribution", height=320)
        st.altair_chart(score_chart, use_container_width=True)

    if "Sub-Sector" in universe.columns:
        sector_dist = (
            universe["Sub-Sector"].fillna("Unknown")
            .astype(str)
            .value_counts()
            .reset_index(name="Count")
            .rename(columns={"index": "Sub-Sector"})
        )
        sector_chart = alt.Chart(sector_dist).mark_bar().encode(
            x=alt.X("Count:Q", title="Stock Count"),
            y=alt.Y("Sub-Sector:N", sort="-x", title="Sub-Sector"),
            tooltip=["Sub-Sector", "Count"],
        ).properties(title="Sub-Sector Coverage", height=420)
        st.altair_chart(sector_chart, use_container_width=True)

    if "PE Ratio" in universe.columns and "ROCE" in universe.columns:
        scatter = alt.Chart(universe).mark_circle(size=80, opacity=0.7).encode(
            x=alt.X("PE Ratio:Q", title="PE Ratio"),
            y=alt.Y("ROCE:Q", title="ROCE"),
            color=alt.Color("QUALITY_SCORE:Q", scale=alt.Scale(scheme="tealblues"), title="Quality Score"),
            tooltip=["Name", "Ticker", "PE Ratio", "ROCE", "QUALITY_SCORE"],
        ).properties(title="ROCE vs PE Ratio", height=420)
        st.altair_chart(scatter, use_container_width=True)
