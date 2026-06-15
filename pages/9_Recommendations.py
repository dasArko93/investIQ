# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.recommendation_service import RecommendationService
from utils.page_utils import load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
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

    if recommendations.empty:
        st.info("No recommendations generated based on the stock universe.")
    else:
        import pandas as pd

        def classify_mcap(val):
            if pd.isna(val) or val <= 0:
                return "Small Cap"
            if val > 10000000:
                val = val / 10000000.0  # Scale raw to Crores
            if val > 20000:
                return "Large Cap"
            elif val > 5000:
                return "Mid Cap"
            else:
                return "Small Cap"

        recommendations["Market Cap Category"] = recommendations["Market Cap"].apply(classify_mcap)

        # Filtration Controls
        st.write("---")
        st.subheader("Filter & Sort Recommendations")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_mcaps = st.multiselect(
                "Market Cap Category",
                options=["Large Cap", "Mid Cap", "Small Cap"],
                default=["Large Cap", "Mid Cap", "Small Cap"],
                help="Filter recommendations by market capitalization category"
            )

        with col2:
            all_rec_sectors = sorted(recommendations["Sub-Sector"].dropna().astype(str).unique())
            selected_sectors = st.multiselect(
                "Sub-Sector",
                options=["All"] + all_rec_sectors,
                default=["All"],
                help="Filter recommendations by specific Sub-Sector(s)"
            )

        with col3:
            min_score = st.slider(
                "Min Composite Score",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                help="Minimum Composite Fundamental Score filter"
            )

        with col4:
            sort_by = st.selectbox(
                "Sort By",
                options=[
                    "Composite Fundamental Score",
                    "Quality Score",
                    "Growth Score",
                    "Value Score",
                    "Dividend Score",
                    "Turnaround Score"
                ],
                index=0,
                help="Select score metric to rank the recommended stocks"
            )

        # Apply Filters
        filtered_recs = recommendations.copy()

        if selected_mcaps:
            filtered_recs = filtered_recs[filtered_recs["Market Cap Category"].isin(selected_mcaps)]

        if selected_sectors and "All" not in selected_sectors:
            filtered_recs = filtered_recs[filtered_recs["Sub-Sector"].astype(str).isin(selected_sectors)]

        if "Composite Fundamental Score" in filtered_recs.columns:
            filtered_recs = filtered_recs[filtered_recs["Composite Fundamental Score"] >= min_score]

        # Apply Sorting
        if sort_by in filtered_recs.columns:
            filtered_recs = filtered_recs.sort_values(sort_by, ascending=False)

        st.write(f"Showing {len(filtered_recs)} recommended stocks.")
        if filtered_recs.empty:
            st.warning("No recommendations match the active filter criteria.")
        else:
            display_cols = ["Name", "Ticker", "Sub-Sector", "Market Cap", "Close Price"]
            score_cols = [
                "Composite Fundamental Score",
                "Quality Score",
                "Growth Score",
                "Value Score",
                "Dividend Score",
                "Turnaround Score"
            ]
            columns_to_show = [col for col in display_cols + score_cols if col in filtered_recs.columns]
            st.dataframe(filtered_recs[columns_to_show], use_container_width=True)