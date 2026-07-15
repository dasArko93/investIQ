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

# Initialize reset counter if not present
if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0

universe = UniverseService.dataframe()
if universe.empty:
    st.info("Upload the stock universe CSV to enable analysis and recommendations.")
    st.info(
        "💡 **Data Reset Note:** Deployed apps on Streamlit can reset due to inactivity, losing temporary data. "
        "If you previously downloaded a database backup, you can restore it under the 'Backup & Restore' tab in "
        "the [Database Admin](pages/18_Clear_Data.py) page. You can also configure permanent cloud database persistence there."
    )
else:
    # Calculate global range boundaries first
    min_score, max_score = 0.0, 100.0
    if "QUALITY_SCORE" in universe.columns and not universe["QUALITY_SCORE"].isna().all():
        min_score = float(universe["QUALITY_SCORE"].min())
        max_score = float(universe["QUALITY_SCORE"].max())
        if min_score == max_score:
            min_score, max_score = 0.0, 100.0

    min_mcap, max_mcap = 0.0, 1000000.0
    mid_large_boundary = 109140.11
    small_mid_boundary = 35373.40
    if "Market Cap" in universe.columns and not universe["Market Cap"].isna().all():
        sorted_mcap = universe["Market Cap"].dropna().sort_values(ascending=False).tolist()
        num_stocks = len(sorted_mcap)
        min_mcap = float(universe["Market Cap"].min())
        max_mcap = float(universe["Market Cap"].max())
        if min_mcap == max_mcap:
            min_mcap, max_mcap = 0.0, 1000000.0
        if num_stocks >= 100:
            mid_large_boundary = float(sorted_mcap[99])
        if num_stocks >= 250:
            small_mid_boundary = float(sorted_mcap[249])

    # 🔍 Quick Filter Options
    st.markdown("### 🔍 Quick Filter Options")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_query = st.text_input(
            "Search Name / Ticker",
            placeholder="Search by stock name or ticker...",
            value="",
            key=f"universe_search_input_{st.session_state.reset_counter}"
        )
        
    with col2:
        sub_sectors = sorted(universe["Sub-Sector"].dropna().astype(str).unique().tolist())
        selected_sectors = st.multiselect(
            "Filter by Sub-Sector",
            options=sub_sectors,
            default=[],
            key=f"universe_sector_select_{st.session_state.reset_counter}"
        )
        
    with col3:
        if "Market Cap" in universe.columns and not universe["Market Cap"].isna().all():
            prev_cat_key = f"prev_mcap_category_{st.session_state.reset_counter}"
            slider_key = f"universe_mcap_slider_{st.session_state.reset_counter}"
            
            if prev_cat_key not in st.session_state:
                st.session_state[prev_cat_key] = "All"
                
            category = st.radio(
                "Cap Category",
                options=["All", "Smallcap", "Midcap", "Largecap"],
                horizontal=True,
                key=f"mcap_cat_selector_{st.session_state.reset_counter}"
            )
            
            if category != st.session_state[prev_cat_key] or slider_key not in st.session_state:
                st.session_state[prev_cat_key] = category
                if category == "Smallcap":
                    st.session_state[slider_key] = (min_mcap, small_mid_boundary)
                elif category == "Midcap":
                    st.session_state[slider_key] = (small_mid_boundary, mid_large_boundary)
                elif category == "Largecap":
                    st.session_state[slider_key] = (mid_large_boundary, max_mcap)
                else:
                    st.session_state[slider_key] = (min_mcap, max_mcap)

    col4, col5, col6 = st.columns(3)
    with col4:
        if "QUALITY_SCORE" in universe.columns and not universe["QUALITY_SCORE"].isna().all():
            quality_range = st.slider(
                "Filter by Quality Score",
                min_value=min_score,
                max_value=max_score,
                value=(min_score, max_score),
                key=f"universe_quality_slider_{st.session_state.reset_counter}"
            )
        else:
            quality_range = None

    with col5:
        if "Market Cap" in universe.columns and not universe["Market Cap"].isna().all():
            mcap_range = st.slider(
                "Filter by Market Cap (₹ Cr)",
                min_value=min_mcap,
                max_value=max_mcap,
                key=slider_key,
                format="%,.2f"
            )
        else:
            mcap_range = None

    with col6:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Reset Filters", key="reset_filters_btn", width='stretch'):
            st.session_state["reset_counter"] += 1
            st.rerun()

    # Apply Filters
    filtered_df = universe.copy()
    
    if search_query:
        q = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["Name"].str.lower().str.contains(q, na=False) |
            filtered_df["Ticker"].str.lower().str.contains(q, na=False)
        ]
        
    if selected_sectors:
        filtered_df = filtered_df[filtered_df["Sub-Sector"].isin(selected_sectors)]
        
    if quality_range is not None:
        filtered_df = filtered_df[
            (filtered_df["QUALITY_SCORE"] >= quality_range[0]) &
            (filtered_df["QUALITY_SCORE"] <= quality_range[1])
        ]

    if mcap_range is not None:
        filtered_df = filtered_df[
            (filtered_df["Market Cap"] >= mcap_range[0]) &
            (filtered_df["Market Cap"] <= mcap_range[1])
        ]

    st.divider()
    st.subheader(f"Universe ({len(filtered_df)} stocks)")
    
    if filtered_df.empty:
        st.warning("No stocks match the selected filter criteria.")
    else:
        st.dataframe(filtered_df, width='stretch', hide_index=True)
    
        if "QUALITY_SCORE" in filtered_df.columns:
            score_chart = alt.Chart(filtered_df).mark_bar().encode(
                x=alt.X("QUALITY_SCORE:Q", bin=alt.Bin(maxbins=20), title="Quality Score"),
                y=alt.Y("count():Q", title="Stocks"),
                tooltip=[alt.Tooltip("count():Q", title="Count")],
            ).properties(title="Quality Score Distribution (Filtered)", height=320)
            st.altair_chart(score_chart, width='stretch')
    
        if "Sub-Sector" in filtered_df.columns:
            sector_dist = (
                filtered_df["Sub-Sector"].fillna("Unknown")
                .astype(str)
                .value_counts()
                .reset_index(name="Count")
                .rename(columns={"index": "Sub-Sector"})
            )
            sector_chart = alt.Chart(sector_dist).mark_bar().encode(
                x=alt.X("Count:Q", title="Stock Count"),
                y=alt.Y("Sub-Sector:N", sort="-x", title="Sub-Sector"),
                tooltip=["Sub-Sector", "Count"],
            ).properties(title="Sub-Sector Coverage (Filtered)", height=420)
            st.altair_chart(sector_chart, width='stretch')
    
        if "PE Ratio" in filtered_df.columns and "ROCE" in filtered_df.columns:
            scatter = alt.Chart(filtered_df).mark_circle(size=80, opacity=0.7).encode(
                x=alt.X("PE Ratio:Q", title="PE Ratio"),
                y=alt.Y("ROCE:Q", title="ROCE"),
                color=alt.Color("QUALITY_SCORE:Q", scale=alt.Scale(scheme="tealblues"), legend=alt.Legend(title="Quality Score", labelColor="#000000", titleColor="#000000")),
                tooltip=["Name", "Ticker", "PE Ratio", "ROCE", "QUALITY_SCORE"],
            ).properties(title="ROCE vs PE Ratio (Filtered)", height=420)
            st.altair_chart(scatter, width='stretch')

