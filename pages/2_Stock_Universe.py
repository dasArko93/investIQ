# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import io
import requests
import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.universe_service import UniverseService
from services.recommendation_service import RecommendationService
from services.price_history_service import PriceHistoryService
from utils.page_utils import load_holdings, load_universe, require_data, render_sidebar, require_auth


st.set_page_config(page_title="InvestIQ - Stock Universe & Recommendations", layout="wide", initial_sidebar_state="expanded")
require_auth()
render_sidebar()


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions & Session State for Recommendations & Benchmarking
# ─────────────────────────────────────────────────────────────────────────────

def fetch_nifty100_tickers():
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
        "https://niftyindices.com/IndexAutomationData/StockTo%20Attribute/ind_nifty100list.csv"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200 and len(response.text) > 100:
                df = pd.read_csv(io.StringIO(response.text))
                for col in ["Symbol", "symbol", "Ticker", "ticker"]:
                    if col in df.columns:
                        symbols = df[col].dropna().unique().tolist()
                        clean_syms = [str(s).upper().strip() for s in symbols if str(s).strip()]
                        if len(clean_syms) >= 50:
                            return clean_syms
        except Exception:
            continue
    return []


def tune_filters_callback(port_vol, bench_vol, port_pe, bench_pe, port_qual, bench_qual):
    st.session_state.scr_rev_enabled = True
    st.session_state.scr_eps_enabled = True
    st.session_state.scr_roce_enabled = True
    st.session_state.scr_roe_enabled = True
    st.session_state.scr_de_enabled = True
    st.session_state.scr_fcf_enabled = True
    st.session_state.scr_prom_enabled = True
    st.session_state.scr_peg_enabled = True

    if port_vol > bench_vol:
        st.session_state.scr_sharpe_enabled = True
        st.session_state.scr_sharpe_val = 1.2

    if port_pe > bench_pe:
        st.session_state.scr_pe_enabled = True
        st.session_state.scr_pe_val = float(round(bench_pe, 1)) if bench_pe > 0 else 25.0

    if port_qual < bench_qual:
        st.session_state.scr_quality_enabled = True
        st.session_state.scr_quality_val = float(round(bench_qual, 1)) if bench_qual > 0 else 70.0

    st.session_state.balance_tuned = True


def reset_rules_callback():
    st.session_state.scr_rev_enabled = True
    st.session_state.scr_rev_val = 15.0
    st.session_state.scr_eps_enabled = True
    st.session_state.scr_eps_val = 15.0
    st.session_state.scr_roce_enabled = True
    st.session_state.scr_roce_val = 20.0
    st.session_state.scr_roe_enabled = True
    st.session_state.scr_roe_val = 18.0
    st.session_state.scr_de_enabled = True
    st.session_state.scr_de_val = 0.5
    st.session_state.scr_peg_enabled = True
    st.session_state.scr_peg_val = 1.5
    st.session_state.scr_fcf_enabled = True
    st.session_state.scr_fcf_val = True
    st.session_state.scr_prom_enabled = True
    st.session_state.scr_prom_val = 50.0

    st.session_state.scr_pe_enabled = False
    st.session_state.scr_pe_val = 22.0
    st.session_state.scr_quality_enabled = False
    st.session_state.scr_quality_val = 70.0
    st.session_state.scr_sharpe_enabled = False
    st.session_state.scr_sharpe_val = 1.2
    st.session_state.rules_reset_toast = True


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


def get_index_volatility():
    try:
        df = PriceHistoryService.fetch_365_days("^NSEI", auto_map_nse=False)
        if df.empty:
            return 0.0
        df = df.sort_values("date")
        df["daily_return"] = df["close"].pct_change()
        daily_std = df["daily_return"].std()
        return daily_std * (252 ** 0.5) * 100.0 if not pd.isna(daily_std) else 0.0
    except Exception:
        return 0.0


def calculate_portfolio_metrics(ticker_weights, universe_df):
    inverse_pe_sum = 0.0
    weighted_quality_sum = 0.0
    weighted_fundamental_sum = 0.0
    valid_pe_weight = 0.0
    valid_quality_weight = 0.0
    valid_fundamental_weight = 0.0

    for ticker, weight in ticker_weights.items():
        clean_tick = ticker.upper().replace(".NS", "")
        match = universe_df[universe_df["Ticker"].astype(str).str.upper().str.replace(".NS", "") == clean_tick]
        if not match.empty:
            row = match.iloc[0]
            pe = row.get("PE Ratio", 0.0)
            if pe and pe > 0:
                inverse_pe_sum += (weight / pe)
                valid_pe_weight += weight

            qs = row.get("QUALITY_SCORE", 0.0)
            if qs and qs > 0:
                weighted_quality_sum += qs * weight
                valid_quality_weight += weight

            fs = row.get("Fundamental Score", 0.0)
            if fs and fs > 0:
                weighted_fundamental_sum += fs * weight
                valid_fundamental_weight += weight

    pe_avg = valid_pe_weight / inverse_pe_sum if inverse_pe_sum > 0 else 0.0
    quality_avg = weighted_quality_sum / valid_quality_weight if valid_quality_weight > 0 else 0.0
    fundamental_avg = weighted_fundamental_sum / valid_fundamental_weight if valid_fundamental_weight > 0 else 0.0

    weighted_vol_sum = 0.0
    valid_vol_weight = 0.0
    for ticker, weight in ticker_weights.items():
        df = PriceHistoryService.fetch_365_days(ticker, auto_map_nse=True)
        if not df.empty:
            df = df.sort_values("date")
            df["daily_return"] = df["close"].pct_change()
            daily_std = df["daily_return"].std()
            if not pd.isna(daily_std):
                stock_vol = daily_std * (252 ** 0.5) * 100.0
                weighted_vol_sum += stock_vol * weight
                valid_vol_weight += weight

    vol = weighted_vol_sum / valid_vol_weight if valid_vol_weight > 0 else 0.0

    return {
        "pe": pe_avg,
        "quality": quality_avg,
        "fundamental": fundamental_avg,
        "volatility": vol
    }


# Session state defaults
for key, default in [
    ("reset_counter", 0),
    ("scr_rev_enabled", True), ("scr_rev_val", 15.0),
    ("scr_eps_enabled", True), ("scr_eps_val", 15.0),
    ("scr_roce_enabled", True), ("scr_roce_val", 20.0),
    ("scr_roe_enabled", True), ("scr_roe_val", 18.0),
    ("scr_de_enabled", True), ("scr_de_val", 0.5),
    ("scr_fcf_enabled", True), ("scr_fcf_val", True),
    ("scr_prom_enabled", True), ("scr_prom_val", 50.0),
    ("scr_peg_enabled", True), ("scr_peg_val", 1.5),
    ("scr_pe_enabled", False), ("scr_pe_val", 22.0),
    ("scr_quality_enabled", False), ("scr_quality_val", 70.0),
    ("scr_sharpe_enabled", False), ("scr_sharpe_val", 1.2),
    ("balance_tuned", False), ("rules_reset_toast", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────────────────────
# Header & Notifications
# ─────────────────────────────────────────────────────────────────────────────
st.title("🌐 Stock Universe & Recommendations")
st.write(
    "Explore the stock universe, apply quantitative screening cutoffs to discover high-conviction ideas, "
    "and audit your active portfolio against the Nifty 100 benchmark."
)

if st.session_state.get("balance_tuned"):
    st.success("✅ Success! Screening filters have been tuned to balance your portfolio deficits. Review Tab 2 ('Stock Screening & Recommendations').")
    st.session_state.balance_tuned = False

if st.session_state.get("rules_reset_toast"):
    st.success("✅ Screening rules reset to default cut-offs successfully!")
    st.session_state.rules_reset_toast = False

universe = UniverseService.dataframe()

# Load Nifty 100 constituents
fresh_symbols = fetch_nifty100_tickers()
if fresh_symbols:
    clean_fresh = {s.upper().replace(".NS", "").strip() for s in fresh_symbols}
    def is_nifty100_ticker(val):
        if pd.isna(val):
            return False
        return str(val).upper().replace(".NS", "").strip() in clean_fresh
    nifty100_universe = universe[universe["Ticker"].apply(is_nifty100_ticker)].copy() if not universe.empty else pd.DataFrame()
else:
    if not universe.empty:
        nifty100_universe = universe.sort_values(by="Market Cap", ascending=False).head(100).copy() if "Market Cap" in universe.columns else universe.head(100).copy()
    else:
        nifty100_universe = pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# 3 Unified Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_explorer, tab_screening, tab_benchmarking = st.tabs([
    "🌐 Universe Explorer & Upload",
    "🔍 Stock Screening & Recommendations",
    "📊 Portfolio Benchmarking & Volatility Simulator"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Universe Explorer & Upload
# ─────────────────────────────────────────────────────────────────────────────
with tab_explorer:
    st.markdown("### 📥 Data Management")
    upload_col1, upload_col2 = st.tabs(["📁 Upload File", "📋 Paste CSV (Mobile Friendly)"])

    with upload_col1:
        android_mode = st.toggle(
            "📱 Android Compatibility Mode (Show All Files)",
            value=True,
            help="Enable this if CSV files appear grayed out or unselectable in your Android file manager.",
            key="universe_android_mode"
        )
        file_types = None if android_mode else ["csv", "xlsx", "xls", "txt"]
        file = st.file_uploader("Upload Universe (.csv, .xlsx)", type=file_types, key="universe_file_uploader")
        if file:
            fname = getattr(file, "name", "file")
            if android_mode and not fname.lower().endswith((".csv", ".xlsx", ".xls", ".txt")):
                st.error(f"Skipped '{fname}': Please upload a .csv or .xlsx file.")
            else:
                try:
                    count = UniverseService.upload(file)
                    st.success(f"✅ {count} stocks loaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to process universe file: {e}")

    with upload_col2:
        st.caption("📱 **Quick Paste for Mobile Devices:** Copy your stock universe CSV text and paste it below.")
        pasted_universe = st.text_area(
            "Paste Stock Universe CSV Text",
            height=160,
            placeholder="Ticker,Name,Sub-Sector,Market Cap,Close Price,...\nTCS,Tata Consultancy Services,IT - Software,1400000,3500,...",
            key="universe_pasted_text"
        )
        if st.button("⬆️ Process Pasted Universe", type="primary", key="btn_process_pasted_universe"):
            if not pasted_universe.strip():
                st.warning("Please paste your CSV text before submitting.")
            else:
                try:
                    count = UniverseService.upload(pasted_universe.strip())
                    st.success(f"✅ {count} stocks loaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to process pasted universe: {e}")

    st.divider()

    if universe.empty:
        st.info("Upload the stock universe CSV to enable analysis and recommendations.")
    else:
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

        # Quick Filter Options
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
            sub_sectors = sorted(universe["Sub-Sector"].dropna().astype(str).unique().tolist()) if "Sub-Sector" in universe.columns else []
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
            if st.button("Reset Universe Filters", key="reset_filters_btn", width='stretch'):
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
        if selected_sectors and "Sub-Sector" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Sub-Sector"].isin(selected_sectors)]
        if quality_range is not None and "QUALITY_SCORE" in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df["QUALITY_SCORE"] >= quality_range[0]) &
                (filtered_df["QUALITY_SCORE"] <= quality_range[1])
            ]
        if mcap_range is not None and "Market Cap" in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df["Market Cap"] >= mcap_range[0]) &
                (filtered_df["Market Cap"] <= mcap_range[1])
            ]

        st.subheader(f"Universe ({len(filtered_df)} stocks)")
        if filtered_df.empty:
            st.warning("No stocks match the selected filter criteria.")
        else:
            st.dataframe(filtered_df, width='stretch', hide_index=True)

            col_chart_left, col_chart_right = st.columns(2)
            with col_chart_left:
                if "QUALITY_SCORE" in filtered_df.columns:
                    score_chart = alt.Chart(filtered_df).mark_bar(color="#6366f1").encode(
                        x=alt.X("QUALITY_SCORE:Q", bin=alt.Bin(maxbins=20), title="Quality Score"),
                        y=alt.Y("count():Q", title="Stocks"),
                        tooltip=[alt.Tooltip("count():Q", title="Count")],
                    ).properties(title="Quality Score Distribution", height=320)
                    st.altair_chart(score_chart, width='stretch')

            with col_chart_right:
                if "PE Ratio" in filtered_df.columns and "ROCE" in filtered_df.columns:
                    scatter = alt.Chart(filtered_df).mark_circle(size=80, opacity=0.7).encode(
                        x=alt.X("PE Ratio:Q", title="PE Ratio"),
                        y=alt.Y("ROCE:Q", title="ROCE (%)"),
                        color=alt.Color("QUALITY_SCORE:Q", scale=alt.Scale(scheme="tealblues"), legend=alt.Legend(title="Quality Score")),
                        tooltip=["Name", "Ticker", "PE Ratio", "ROCE", "QUALITY_SCORE"],
                    ).properties(title="ROCE vs PE Ratio", height=320)
                    st.altair_chart(scatter, width='stretch')

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Stock Screening & Recommendations
# ─────────────────────────────────────────────────────────────────────────────
with tab_screening:
    st.subheader("🔍 Quantitative Stock Screening & Idea Generation")

    if universe.empty:
        st.info("Upload the stock universe in Tab 1 to run screening filters.")
    else:
        # Interactive Screening Rules Expander
        with st.expander("🛠️ Customize Stock Screening Rules", expanded=True):
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)
            with r_col1:
                st.markdown("**Growth Rules**")
                st.checkbox("Revenue Growth > Min", key="scr_rev_enabled")
                st.number_input("Revenue Growth Min %", min_value=0.0, max_value=100.0, step=1.0, key="scr_rev_val")

                st.checkbox("EPS Growth > Min", key="scr_eps_enabled")
                st.number_input("EPS Growth Min %", min_value=0.0, max_value=100.0, step=1.0, key="scr_eps_val")

            with r_col2:
                st.markdown("**Efficiency Rules**")
                st.checkbox("ROCE > Min", key="scr_roce_enabled")
                st.number_input("ROCE Min %", min_value=0.0, max_value=100.0, step=1.0, key="scr_roce_val")

                st.checkbox("ROE > Min", key="scr_roe_enabled")
                st.number_input("ROE Min %", min_value=0.0, max_value=100.0, step=1.0, key="scr_roe_val")

            with r_col3:
                st.markdown("**Leverage & Valuation**")
                st.checkbox("Debt/Equity < Max", key="scr_de_enabled")
                st.number_input("Debt/Equity Max", min_value=0.0, max_value=10.0, step=0.1, key="scr_de_val")

                st.checkbox("PEG Ratio < Max", key="scr_peg_enabled")
                st.number_input("PEG Max", min_value=0.0, max_value=10.0, step=0.1, key="scr_peg_val")

            with r_col4:
                st.markdown("**Ownership & Cash**")
                st.checkbox("Require Positive FCF", key="scr_fcf_enabled")
                st.checkbox("FCF > 0", key="scr_fcf_val")

                st.checkbox("Promoter Holding > Min", key="scr_prom_enabled")
                st.number_input("Promoter Holding Min %", min_value=0.0, max_value=100.0, step=1.0, key="scr_prom_val")

            st.write("")
            col_reset, _ = st.columns([1.5, 3])
            with col_reset:
                st.button(
                    "🔄 Reset to Default Rules",
                    key="reset_rules_btn",
                    on_click=reset_rules_callback,
                    width='stretch'
                )

        with st.expander("⚖️ Advanced Balancing Filters (PE, Quality, Sharpe)"):
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            with col_adv1:
                st.checkbox("Enable PE Ratio Filter", key="scr_pe_enabled")
                st.number_input("Max PE Ratio", min_value=0.0, max_value=200.0, key="scr_pe_val")
            with col_adv2:
                st.checkbox("Enable Quality Score Filter", key="scr_quality_enabled")
                st.number_input("Min Quality Score", min_value=0.0, max_value=100.0, key="scr_quality_val")
            with col_adv3:
                st.checkbox("Enable Sharpe Ratio Filter", key="scr_sharpe_enabled")
                st.number_input("Min Sharpe Ratio", min_value=-5.0, max_value=10.0, key="scr_sharpe_val")

        recommendations = RecommendationService.generate(universe)
        if recommendations.empty:
            st.info("No recommendations generated based on the stock universe.")
        else:
            recommendations["Market Cap Category"] = recommendations["Market Cap"].apply(classify_mcap)

            filtered_df = recommendations.copy()
            applied_rules = []

            if st.session_state.scr_rev_enabled:
                col = "5Y Historical Revenue Growth"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_rev_val]
                    applied_rules.append(f"Revenue Growth > {st.session_state.scr_rev_val}%")

            if st.session_state.scr_eps_enabled:
                col = "5Y Historical EPS Growth"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_eps_val]
                    applied_rules.append(f"EPS Growth > {st.session_state.scr_eps_val}%")

            if st.session_state.scr_roce_enabled:
                col = "ROCE"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_roce_val]
                    applied_rules.append(f"ROCE > {st.session_state.scr_roce_val}%")

            if st.session_state.scr_roe_enabled:
                col = "Return on Equity"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_roe_val]
                    applied_rules.append(f"ROE > {st.session_state.scr_roe_val}%")

            if st.session_state.scr_de_enabled:
                col = "Debt to Equity"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] < st.session_state.scr_de_val]
                    applied_rules.append(f"Debt/Equity < {st.session_state.scr_de_val}")

            if st.session_state.scr_peg_enabled:
                col = "PEG Ratio (Forward)"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] < st.session_state.scr_peg_val]
                    applied_rules.append(f"PEG < {st.session_state.scr_peg_val}")

            if st.session_state.scr_fcf_enabled and st.session_state.scr_fcf_val:
                col = "Free Cash Flow"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > 0]
                    applied_rules.append("Free Cash Flow > 0")

            if st.session_state.scr_prom_enabled:
                col = "Promoter Holding"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_prom_val]
                    applied_rules.append(f"Promoter Holding > {st.session_state.scr_prom_val}%")

            if st.session_state.scr_pe_enabled:
                col = "PE Ratio"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[(filtered_df[col] > 0) & (filtered_df[col] <= st.session_state.scr_pe_val)]
                    applied_rules.append(f"P/E <= {st.session_state.scr_pe_val}")

            if st.session_state.scr_quality_enabled:
                col = "QUALITY_SCORE"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] >= st.session_state.scr_quality_val]
                    applied_rules.append(f"Quality >= {st.session_state.scr_quality_val}")

            if st.session_state.scr_sharpe_enabled:
                col = "Sharpe Ratio"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] >= st.session_state.scr_sharpe_val]
                    applied_rules.append(f"Sharpe >= {st.session_state.scr_sharpe_val}")

            # Granular Filter Inputs
            st.write("")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                market_cap_categories = ["Large Cap", "Mid Cap", "Small Cap"]
                selected_categories = st.multiselect("Market Cap Segment", options=market_cap_categories, default=[], placeholder="All Segments")
            with f_col2:
                available_sectors = sorted(list(filtered_df["Sub-Sector"].dropna().unique())) if "Sub-Sector" in filtered_df.columns else []
                selected_sectors_rec = st.multiselect("Sectors", options=available_sectors, default=[], placeholder="All Sectors")
            with f_col3:
                sort_order = st.selectbox(
                    "Sort Candidates By",
                    options=[
                        "Highest Quality Score",
                        "Lowest P/E Ratio",
                        "Highest ROCE",
                        "Highest Revenue Growth",
                        "Highest Sharpe Ratio"
                    ],
                    index=0
                )

            final_candidates = filtered_df.copy()
            if selected_categories:
                final_candidates = final_candidates[final_candidates["Market Cap Category"].isin(selected_categories)]
            if selected_sectors_rec and "Sub-Sector" in final_candidates.columns:
                final_candidates = final_candidates[final_candidates["Sub-Sector"].isin(selected_sectors_rec)]

            if sort_order == "Highest Quality Score" and "QUALITY_SCORE" in final_candidates.columns:
                final_candidates = final_candidates.sort_values(by="QUALITY_SCORE", ascending=False)
            elif sort_order == "Lowest P/E Ratio" and "PE Ratio" in final_candidates.columns:
                final_candidates = final_candidates.sort_values(by="PE Ratio", ascending=True)
            elif sort_order == "Highest ROCE" and "ROCE" in final_candidates.columns:
                final_candidates = final_candidates.sort_values(by="ROCE", ascending=False)
            elif sort_order == "Highest Revenue Growth" and "5Y Historical Revenue Growth" in final_candidates.columns:
                final_candidates = final_candidates.sort_values(by="5Y Historical Revenue Growth", ascending=False)
            elif sort_order == "Highest Sharpe Ratio" and "Sharpe Ratio" in final_candidates.columns:
                final_candidates = final_candidates.sort_values(by="Sharpe Ratio", ascending=False)

            st.write("")
            st.markdown(f"#### 🎯 Recommended Candidates ({len(final_candidates)} stocks qualified)")
            if applied_rules:
                st.caption(f"**Applied Rules:** {', '.join(applied_rules)}")

            if final_candidates.empty:
                st.warning("No stocks match the screening rules. Adjust criteria or click 'Reset to Default Rules'.")
            else:
                display_cols = [c for c in [
                    "Ticker", "Name", "Sub-Sector", "Market Cap Category", "Close Price",
                    "PE Ratio", "ROCE", "Return on Equity", "Debt to Equity",
                    "QUALITY_SCORE", "Fundamental Score", "Sharpe Ratio"
                ] if c in final_candidates.columns]
                st.dataframe(final_candidates[display_cols], width='stretch', hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Portfolio Benchmarking & Volatility Simulator
# ─────────────────────────────────────────────────────────────────────────────
with tab_benchmarking:
    st.subheader("📊 Portfolio Benchmarking vs Nifty 100")

    holdings = load_holdings()
    if holdings.empty:
        st.info("⚠️ Please upload your portfolio holdings in the [holding](pages/1_holding.py) page to enable benchmarking.")
    elif universe.empty:
        st.info("⚠️ Please upload the stock universe in Tab 1 to run portfolio benchmarking.")
    else:
        holdings = holdings[holdings["Current Value Rs"] > 0].copy()
        total_val = holdings["Current Value Rs"].sum()

        if total_val == 0:
            st.warning("Your holdings show zero current value. Please upload active holdings to analyze.")
        else:
            current_weights = {}
            for _, row in holdings.iterrows():
                ticker = str(row["Security"])
                val = float(row["Current Value Rs"])
                current_weights[ticker] = val / total_val

            with st.spinner("Calculating benchmark metrics..."):
                bench_vol = get_index_volatility()
                if bench_vol == 0.0:
                    bench_vol = 14.5

                port_metrics = calculate_portfolio_metrics(current_weights, universe)

            bench_pe = float(nifty100_universe["PE Ratio"].dropna().median()) if "PE Ratio" in nifty100_universe.columns and not nifty100_universe.empty else 22.0
            bench_quality = float(nifty100_universe["QUALITY_SCORE"].dropna().mean()) if "QUALITY_SCORE" in nifty100_universe.columns and not nifty100_universe.empty else 60.0

            nifty_df = PriceHistoryService.fetch_365_days("^NSEI", auto_map_nse=False)
            nifty_sharpe = 1.05
            if not nifty_df.empty:
                nifty_df = nifty_df.sort_values("date")
                nifty_df["daily_return"] = nifty_df["close"].pct_change()
                ann_return = nifty_df["daily_return"].mean() * 252 * 100.0
                ann_vol = nifty_df["daily_return"].std() * (252 ** 0.5) * 100.0
                if ann_vol > 0:
                    nifty_sharpe = (ann_return - 6.0) / ann_vol

            weighted_sharpe = 0.0
            valid_sharpe_w = 0.0
            for ticker, w in current_weights.items():
                clean_tick = ticker.upper().replace(".NS", "")
                match = universe[universe["Ticker"].astype(str).str.upper().str.replace(".NS", "") == clean_tick]
                if not match.empty:
                    sh = match.iloc[0].get("Sharpe Ratio", 0.0)
                    if sh:
                        weighted_sharpe += sh * w
                        valid_sharpe_w += w
            port_sharpe = weighted_sharpe / valid_sharpe_w if valid_sharpe_w > 0 else 0.8

            col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
            pe_delta = port_metrics["pe"] - bench_pe
            col_kpi1.metric("Portfolio P/E", f"{port_metrics['pe']:.2f}", delta=f"{pe_delta:+.2f} vs Benchmark", delta_color="inverse")

            vol_delta = port_metrics["volatility"] - bench_vol
            col_kpi2.metric("Annual Volatility", f"{port_metrics['volatility']:.2f}%", delta=f"{vol_delta:+.2f}% vs Index", delta_color="inverse")

            q_delta = port_metrics["quality"] - bench_quality
            col_kpi3.metric("Quality Rating", f"{port_metrics['quality']:.1f}/100", delta=f"{q_delta:+.1f} vs Benchmark")

            s_delta = port_sharpe - nifty_sharpe
            col_kpi4.metric("Sharpe Ratio", f"{port_sharpe:.2f}", delta=f"{s_delta:+.2f} vs Index")

            st.write("")
            st.button(
                "🔧 Tune Screening Filters for Balanced Risk/Reward",
                key="apply_balance_btn",
                on_click=tune_filters_callback,
                args=(port_metrics["volatility"], bench_vol, port_metrics["pe"], bench_pe, port_metrics["quality"], bench_quality),
                width='stretch'
            )

            # Counter Underperformance Recommendations
            st.write("")
            st.subheader("💡 Counter-Underperformance Recommendations")
            advisory_universe = universe[universe["Market Cap"] >= 5000.0] if "Market Cap" in universe.columns else universe
            if len(advisory_universe) < 10:
                advisory_universe = universe

            counter_recs = []
            is_high_vol = port_metrics["volatility"] > bench_vol
            vol_target = "Reduce Volatility" if is_high_vol else "Maintain Low Volatility"
            vol_rationale = "Improve Sharpe ratio and reduce downside variance." if is_high_vol else "Preserve defensive stability."

            defensive = advisory_universe.sort_values(by="Sharpe Ratio", ascending=False) if "Sharpe Ratio" in advisory_universe.columns else pd.DataFrame()
            if not defensive.empty:
                for _, row in defensive.head(5).iterrows():
                    counter_recs.append({
                        "Ticker": row["Ticker"],
                        "Name": row["Name"],
                        "Sector": row.get("Sub-Sector", "N/A"),
                        "Market Cap": classify_mcap(row.get("Market Cap", 0.0)),
                        "Balancing Target": vol_target,
                        "Action / Rationale": vol_rationale,
                        "Key Metric": f"Sharpe: {row.get('Sharpe Ratio', 0.0):.2f}",
                        "pe": float(row.get("PE Ratio", 0.0)) if pd.notna(row.get("PE Ratio")) else 0.0,
                        "quality": float(row.get("QUALITY_SCORE", 0.0)) if pd.notna(row.get("QUALITY_SCORE")) else 0.0,
                        "sharpe": float(row.get("Sharpe Ratio", 0.0)) if pd.notna(row.get("Sharpe Ratio")) else 0.0
                    })

            if counter_recs:
                df_recs = pd.DataFrame(counter_recs)
                st.dataframe(df_recs, width='stretch', hide_index=True)

            # Risk & Reward Simulator Workspace
            st.divider()
            st.subheader("⚡ Risk & Reward Simulator Workspace")
            st.write("Simulate adding a balancing stock to see its instant impact on your portfolio's Volatility, P/E, and Quality rating.")

            sim_col1, sim_col2, sim_col3 = st.columns([2, 1, 1])
            with sim_col1:
                all_tickers = sorted(universe["Ticker"].dropna().unique().tolist()) if "Ticker" in universe.columns else []
                sim_tickers = st.multiselect(
                    "Choose Stocks to Simulate",
                    options=all_tickers,
                    default=[all_tickers[0]] if all_tickers else [],
                    help="Select one or more stocks to run simulation"
                )

            with sim_col2:
                sim_mode = st.selectbox(
                    "Simulation Mode",
                    options=["Allocate from Cash", "Replace Existing Stock"],
                )

            with sim_col3:
                if sim_mode == "Replace Existing Stock":
                    replace_ticker = st.selectbox("Stock to Sell/Replace", options=sorted(list(current_weights.keys())))
                    sim_weight_pct = 0.0
                else:
                    sim_weight_pct = st.slider("Simulated Weight per Stock (%)", min_value=1.0, max_value=30.0, value=5.0, step=1.0)
                    replace_ticker = None

            if sim_tickers:
                sim_weights = {}
                n_sim = len(sim_tickers)
                if sim_mode == "Allocate from Cash":
                    sim_w_per_stock = sim_weight_pct / 100.0
                    total_sim_w = n_sim * sim_w_per_stock
                    if total_sim_w >= 1.0:
                        total_sim_w = 0.9
                        sim_w_per_stock = total_sim_w / n_sim
                    remaining_scale = 1.0 - total_sim_w
                    for t, w in current_weights.items():
                        sim_weights[t] = w * remaining_scale
                    for ticker in sim_tickers:
                        sim_weights[ticker] = sim_weights.get(ticker, 0.0) + sim_w_per_stock
                else:
                    replace_w = current_weights.get(replace_ticker, 0.0)
                    sim_w_per_stock = replace_w / n_sim if n_sim > 0 else 0.0
                    for t, w in current_weights.items():
                        sim_weights[t] = 0.0 if t == replace_ticker else w
                    for ticker in sim_tickers:
                        sim_weights[ticker] = sim_weights.get(ticker, 0.0) + sim_w_per_stock

                sim_metrics = calculate_portfolio_metrics(sim_weights, universe)
                sim_weighted_sharpe = 0.0
                sim_valid_sharpe_w = 0.0
                for ticker, w in sim_weights.items():
                    clean_tick = ticker.upper().replace(".NS", "")
                    match = universe[universe["Ticker"].astype(str).str.upper().str.replace(".NS", "") == clean_tick]
                    if not match.empty:
                        sh = match.iloc[0].get("Sharpe Ratio", 0.0)
                        if sh:
                            sim_weighted_sharpe += sh * w
                            sim_valid_sharpe_w += w
                sim_sharpe = sim_weighted_sharpe / sim_valid_sharpe_w if sim_valid_sharpe_w > 0 else 0.8

                st.markdown("### Simulation Impact Report")
                col_sim1, col_sim2, col_sim3, col_sim4 = st.columns(4)
                pe_change = sim_metrics["pe"] - port_metrics["pe"]
                col_sim1.metric("Simulated P/E", f"{sim_metrics['pe']:.2f}", delta=f"{pe_change:+.2f}", delta_color="inverse")

                vol_change = sim_metrics["volatility"] - port_metrics["volatility"]
                col_sim2.metric("Simulated Volatility", f"{sim_metrics['volatility']:.2f}%", delta=f"{vol_change:+.2f}%", delta_color="inverse")

                q_change = sim_metrics["quality"] - port_metrics["quality"]
                col_sim3.metric("Simulated Quality", f"{sim_metrics['quality']:.1f}/100", delta=f"{q_change:+.1f}")

                s_change = sim_sharpe - port_sharpe
                col_sim4.metric("Simulated Sharpe", f"{sim_sharpe:.2f}", delta=f"{s_change:+.2f}")

                plot_data = pd.DataFrame([
                    {"Category": "Current Portfolio", "P/E Ratio": port_metrics["pe"], "Volatility (%)": port_metrics["volatility"]},
                    {"Category": "Simulated Portfolio", "P/E Ratio": sim_metrics["pe"], "Volatility (%)": sim_metrics["volatility"]},
                    {"Category": "Nifty Benchmark", "P/E Ratio": bench_pe, "Volatility (%)": bench_vol}
                ])
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_pe = px.bar(plot_data, x="Category", y="P/E Ratio", color="Category", title="P/E Ratio Comparison")
                    fig_pe.update_layout(autosize=True, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pe, width='stretch')
                with col_chart2:
                    fig_vol = px.bar(plot_data, x="Category", y="Volatility (%)", color="Category", title="Annualized Volatility (%) Comparison")
                    fig_vol.update_layout(autosize=True, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_vol, width='stretch')
