# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.recommendation_service import RecommendationService
from services.price_history_service import PriceHistoryService
from utils.page_utils import load_universe, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ - Recommendations", layout="wide", initial_sidebar_state="expanded")

from utils.page_utils import require_auth
require_auth()
render_sidebar()


def fetch_nifty100_tickers():
    import requests
    import io
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
    
    # 1. High Volatility Check
    if port_vol > bench_vol:
        st.session_state.scr_sharpe_enabled = True
        st.session_state.scr_sharpe_val = 1.2
        
    # 2. Valuation Check
    if port_pe > bench_pe:
        st.session_state.scr_pe_enabled = True
        st.session_state.scr_pe_val = float(round(bench_pe, 1)) if bench_pe > 0 else 25.0
        
    # 3. Quality Check
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


# Initialize session state for screening rule values and checks
if "scr_rev_enabled" not in st.session_state:
    st.session_state.scr_rev_enabled = True
if "scr_rev_val" not in st.session_state:
    st.session_state.scr_rev_val = 15.0

if "scr_eps_enabled" not in st.session_state:
    st.session_state.scr_eps_enabled = True
if "scr_eps_val" not in st.session_state:
    st.session_state.scr_eps_val = 15.0

if "scr_roce_enabled" not in st.session_state:
    st.session_state.scr_roce_enabled = True
if "scr_roce_val" not in st.session_state:
    st.session_state.scr_roce_val = 20.0

if "scr_roe_enabled" not in st.session_state:
    st.session_state.scr_roe_enabled = True
if "scr_roe_val" not in st.session_state:
    st.session_state.scr_roe_val = 18.0

if "scr_de_enabled" not in st.session_state:
    st.session_state.scr_de_enabled = True
if "scr_de_val" not in st.session_state:
    st.session_state.scr_de_val = 0.5

if "scr_fcf_enabled" not in st.session_state:
    st.session_state.scr_fcf_enabled = True
if "scr_fcf_val" not in st.session_state:
    st.session_state.scr_fcf_val = True

if "scr_prom_enabled" not in st.session_state:
    st.session_state.scr_prom_enabled = True
if "scr_prom_val" not in st.session_state:
    st.session_state.scr_prom_val = 50.0

if "scr_peg_enabled" not in st.session_state:
    st.session_state.scr_peg_enabled = True
if "scr_peg_val" not in st.session_state:
    st.session_state.scr_peg_val = 1.5

# Advanced/Balancing filters
if "scr_pe_enabled" not in st.session_state:
    st.session_state.scr_pe_enabled = False
if "scr_pe_val" not in st.session_state:
    st.session_state.scr_pe_val = 22.0

if "scr_quality_enabled" not in st.session_state:
    st.session_state.scr_quality_enabled = False
if "scr_quality_val" not in st.session_state:
    st.session_state.scr_quality_val = 70.0

if "scr_sharpe_enabled" not in st.session_state:
    st.session_state.scr_sharpe_enabled = False
if "scr_sharpe_val" not in st.session_state:
    st.session_state.scr_sharpe_val = 1.2

if "balance_tuned" not in st.session_state:
    st.session_state.balance_tuned = False

if "rules_reset_toast" not in st.session_state:
    st.session_state.rules_reset_toast = False


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
    # 1. P/E, Quality, and Fundamental
    weighted_pe_sum = 0.0
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
                weighted_pe_sum += pe * weight
                valid_pe_weight += weight
            
            qs = row.get("QUALITY_SCORE", 0.0)
            if qs and qs > 0:
                weighted_quality_sum += qs * weight
                valid_quality_weight += weight
                
            fs = row.get("Fundamental Score", 0.0)
            if fs and fs > 0:
                weighted_fundamental_sum += fs * weight
                valid_fundamental_weight += weight
                
    pe_avg = weighted_pe_sum / valid_pe_weight if valid_pe_weight > 0 else 0.0
    quality_avg = weighted_quality_sum / valid_quality_weight if valid_quality_weight > 0 else 0.0
    fundamental_avg = weighted_fundamental_sum / valid_fundamental_weight if valid_fundamental_weight > 0 else 0.0
    
    # 2. Volatility
    price_dfs = []
    for ticker in ticker_weights.keys():
        df = PriceHistoryService.fetch_365_days(ticker, auto_map_nse=True)
        if not df.empty:
            df = df.sort_values("date").copy()
            df["daily_return"] = df["close"].pct_change()
            df = df[["date", "daily_return"]].rename(columns={"daily_return": ticker})
            price_dfs.append(df)
            
    vol = 0.0
    portfolio_daily_returns = pd.Series()
    if price_dfs:
        merged_returns = price_dfs[0]
        for df in price_dfs[1:]:
            merged_returns = pd.merge(merged_returns, df, on="date", how="outer")
        merged_returns = merged_returns.sort_values("date").fillna(0)
        
        portfolio_daily_returns = pd.Series(0.0, index=merged_returns.index)
        for ticker, weight in ticker_weights.items():
            if ticker in merged_returns.columns:
                portfolio_daily_returns += merged_returns[ticker] * weight
                
        daily_std = portfolio_daily_returns.std()
        vol = daily_std * (252 ** 0.5) * 100.0 if not pd.isna(daily_std) else 0.0
        
    return {
        "pe": pe_avg,
        "quality": quality_avg,
        "fundamental": fundamental_avg,
        "volatility": vol,
        "returns": portfolio_daily_returns
    }


st.title("Recommendations")

if st.session_state.get("balance_tuned"):
    st.success("Success! Screening filters have been tuned to balance your portfolio deficits. Switch to the first tab ('Stock Screening Recommendations') to review.")
    st.session_state.balance_tuned = False

if st.session_state.get("rules_reset_toast"):
    st.success("Screening rules reset to default cut-offs successfully!")
    st.session_state.rules_reset_toast = False

with st.popover("📖 Quick Start User Guide & Help Docs", width='stretch'):
    st.markdown("""
    ### 📖 How to Use the Recommendations Workspace

    Welcome to the quantitative screening and benchmarking suite. This workspace is divided into two operational modules:

    #### 1. 🔍 Stock Screening Recommendations
    * **Custom Screening Rules:** Expand the rules panel to enable/disable or adjust the numeric cutoff criteria (e.g. minimum ROCE, maximum Debt/Equity, require positive FCF).
    * **Fine-Tuning Filters:** Use the multi-select inputs below the rules to narrow your output by Market Cap segments, specific sectors, or rank them by custom score rankings (Growth, Quality, Value, or Turnaround scores).

    #### 2. 📊 Portfolio Benchmarking & Volatility Simulator
    * **Index Benchmarking:** Audits your active portfolio metrics (weighted P/E, quality score, historical annual volatility, and Sharpe Ratio) against the Nifty 100 benchmark.
    * **One-Click Gap Alignment:** Click **"Tune Screening Filters for Balanced Risk/Reward"** to automatically adjust Tab 1 filters. This auto-applies defensive, valuation, or quality target metrics to help correct any portfolio deficits.
    * **Advisory Pool:** Lists all liquid Mid and Large Cap stocks countering your deficits. You can filter this list instantly by sector, cap size, goal focus, or specific metrics (Max PE, Min Quality, Min Sharpe).
    * **Portfolio Simulator:** Select any countering stock and run a simulation. Choose **Allocate from Cash** (enter 1% to 30% weight) or **Replace Stock** (sell an existing stock to fund it). View side-by-side impact metrics and comparisons.
    """)

universe = load_universe()

# Dynamically identify fresh Nifty 100 tickers loaded from NSE (with Market Cap fallback)
fresh_symbols = fetch_nifty100_tickers()
if fresh_symbols:
    clean_fresh = {s.upper().replace(".NS", "").strip() for s in fresh_symbols}
    def is_nifty100_ticker(val):
        if pd.isna(val):
            return False
        return str(val).upper().replace(".NS", "").strip() in clean_fresh
    nifty100_universe = universe[universe["Ticker"].apply(is_nifty100_ticker)].copy()
    st.toast("Loaded fresh Nifty 100 constituent list from NSE!")
else:
    # Fallback: Define Nifty 100 as the top 100 constituent stocks sorted by Market Cap
    if not universe.empty:
        if "Market Cap" in universe.columns:
            nifty100_universe = universe.sort_values(by="Market Cap", ascending=False).head(100).copy()
        else:
            nifty100_universe = universe.head(100).copy()
    else:
        nifty100_universe = pd.DataFrame()

if require_data(universe, "Upload the stock universe to generate recommendations."):
    
    # Preview stocks fetched fresh from NSE
    with st.expander("📋 Live Stock Universe & Core Ratios Preview", expanded=False):
        st.write("Below is the list of constituent stocks currently loaded in your database universe:")
        
        # Interactive Filter Widgets
        p_col1, p_col2, p_col3 = st.columns([1, 1, 1])
        with p_col1:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            only_nifty100 = st.checkbox("Show Only Nifty 100 Constituents", value=False, help="Filter to active Nifty 100 symbols fetched from NSE")
        with p_col2:
            mcap_choices = ["Large Cap", "Mid Cap", "Small Cap"]
            selected_mcaps = st.multiselect("Market Cap Categories", options=mcap_choices, default=[], placeholder="All Market Caps (Default)")
        with p_col3:
            all_sectors = sorted(list(universe["Sub-Sector"].dropna().unique())) if "Sub-Sector" in universe.columns else []
            selected_sectors = st.multiselect("Sectors", options=all_sectors, default=[], placeholder="All Sectors (Default)")
            
        # Apply filters to preview_df
        preview_df = universe.copy()
        preview_df["Market Cap Category"] = preview_df["Market Cap"].apply(classify_mcap)
        
        if only_nifty100 and not nifty100_universe.empty:
            nifty_tickers = {t.upper().replace(".NS", "").strip() for t in nifty100_universe["Ticker"].unique()}
            preview_df = preview_df[preview_df["Ticker"].astype(str).str.upper().str.replace(".NS", "").str.strip().isin(nifty_tickers)]
            
        if selected_mcaps:
            preview_df = preview_df[preview_df["Market Cap Category"].isin(selected_mcaps)]
        if selected_sectors:
            preview_df = preview_df[preview_df["Sub-Sector"].fillna("Unknown").isin(selected_sectors)]
            
        # Prepare clean display dataframe
        cols_to_show = []
        rename_map = {}
        for col, display in [
            ("Ticker", "Ticker"),
            ("Name", "Company Name"),
            ("Sub-Sector", "Sector"),
            ("Market Cap", "Market Cap (Cr)"),
            ("PE Ratio", "P/E Ratio"),
            ("QUALITY_SCORE", "Quality Score"),
            ("Sharpe Ratio", "Sharpe Ratio")
        ]:
            if col in preview_df.columns:
                cols_to_show.append(col)
                rename_map[col] = display
                
        if cols_to_show:
            preview_display = preview_df[cols_to_show].rename(columns=rename_map)
            st.dataframe(preview_display, width='stretch', hide_index=True)
        else:
            st.dataframe(preview_df, width='stretch')
            
    st.write("")
    st.markdown("#### 📊 Live Stock Universe Dashboard")
    
    # Calculate summary statistics for the filtered preview stocks
    pe_vals = pd.to_numeric(preview_df["PE Ratio"], errors="coerce").dropna()
    valid_pe_vals = pe_vals[(pe_vals > 0) & (pe_vals <= 300)]
    pe_avg = valid_pe_vals.mean() if not valid_pe_vals.empty else (pe_vals.median() if not pe_vals.empty else 0.0)
    
    quality_vals = pd.to_numeric(preview_df["QUALITY_SCORE"], errors="coerce").dropna()
    quality_avg = quality_vals.mean() if not quality_vals.empty else 0.0
    
    sharpe_vals = pd.to_numeric(preview_df["Sharpe Ratio"], errors="coerce").dropna()
    sharpe_avg = sharpe_vals.mean() if not sharpe_vals.empty else 0.0
    
    sector_count = preview_df["Sub-Sector"].nunique() if "Sub-Sector" in preview_df.columns else 0
    
    # 1. Summary Metric Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Universe Average P/E", f"{pe_avg:.2f}")
    m_col2.metric("Universe Average Quality", f"{quality_avg:.1f}/100")
    m_col3.metric("Universe Average Sharpe", f"{sharpe_avg:.2f}")
    m_col4.metric("Unique Sectors", f"{sector_count}")
    
    st.write("")
    
    # 2. visual charts layout
    ch_col1, ch_col2 = st.columns(2)
    
    with ch_col1:
        # Sector distribution
        if "Sub-Sector" in preview_df.columns:
            sector_counts = preview_df["Sub-Sector"].value_counts().reset_index()
            sector_counts.columns = ["Sector", "Count"]
            fig_sector = go.Figure(data=[
                go.Bar(
                    x=sector_counts["Sector"],
                    y=sector_counts["Count"],
                    marker=dict(
                        color=sector_counts["Count"],
                        colorscale="Viridis",
                        showscale=False
                    ),
                    hovertemplate="Sector: %{x}<br>Number of Stocks: %{y}<extra></extra>"
                )
            ])
            fig_sector.update_layout(
                title="Sector Distribution",
                autosize=True,
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000"),
                xaxis=dict(showgrid=False, title="Sector / Industry"),
                yaxis=dict(gridcolor="rgba(0,0,0,0.05)", title="Number of Stocks")
            )
            st.plotly_chart(fig_sector, width='stretch', config={"displayModeBar": True, "responsive": True})
            
    with ch_col2:
        # P/E vs Quality Scatter Plot
        if "PE Ratio" in preview_df.columns and "QUALITY_SCORE" in preview_df.columns:
            scatter_data = preview_df[
                (preview_df["PE Ratio"] > 0) & 
                (preview_df["PE Ratio"] < 150) & 
                (preview_df["QUALITY_SCORE"] > 0)
            ].copy()
            if not scatter_data.empty:
                colors = scatter_data["Sharpe Ratio"] if "Sharpe Ratio" in scatter_data.columns else "#20d3c2"
                hover_texts = []
                for _, row in scatter_data.iterrows():
                    t = f"Ticker: {row['Ticker']}<br>Name: {row.get('Name', '')}<br>P/E Ratio: {row['PE Ratio']:.2f}<br>Quality Score: {row['QUALITY_SCORE']:.1f}"
                    if "Sharpe Ratio" in scatter_data.columns:
                        t += f"<br>Sharpe Ratio: {row['Sharpe Ratio']:.2f}"
                    hover_texts.append(t)
                    
                fig_scatter = go.Figure(data=[
                    go.Scatter(
                        x=scatter_data["PE Ratio"],
                        y=scatter_data["QUALITY_SCORE"],
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=colors,
                            colorscale="RdYlGn",
                            showscale=True,
                            colorbar=dict(title="Sharpe" if "Sharpe Ratio" in scatter_data.columns else "")
                        ),
                        text=hover_texts,
                        hovertemplate="%{text}<extra></extra>"
                    )
                ])
                fig_scatter.update_layout(
                    title="Quality Score vs P/E Ratio (Scatter Plot)",
                    autosize=True,
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#000000"),
                    xaxis=dict(gridcolor="rgba(0,0,0,0.05)", title="P/E Ratio"),
                    yaxis=dict(gridcolor="rgba(0,0,0,0.05)", title="Quality Score (0-100)")
                )
                st.plotly_chart(fig_scatter, width='stretch', config={"displayModeBar": True, "responsive": True})

    tab_screening, tab_benchmarking = st.tabs([
        "🔍 Stock Screening Recommendations",
        "📊 Portfolio Benchmarking & Volatility Simulator"
    ])
    
    # -------------------------------------------------------------
    # TAB 1: Stock Screening Recommendations
    # -------------------------------------------------------------
    with tab_screening:
        st.subheader("Quick Stock Screening Filters")
        
        # Interactive filters layout
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
            col_reset, _ = st.columns([1.2, 3])
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
            
            # Apply dynamic rule checks
            filtered_df = recommendations.copy()
            applied_rules = []
            skipped_rules = []
            
            if st.session_state.scr_rev_enabled:
                col = "5Y Historical Revenue Growth"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_rev_val]
                    applied_rules.append(f"Revenue Growth > {st.session_state.scr_rev_val}%")
                else:
                    skipped_rules.append("Revenue Growth")
                    
            if st.session_state.scr_eps_enabled:
                col = "5Y Historical EPS Growth"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_eps_val]
                    applied_rules.append(f"EPS Growth > {st.session_state.scr_eps_val}%")
                else:
                    skipped_rules.append("EPS Growth")
                    
            if st.session_state.scr_roce_enabled:
                col = "ROCE"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_roce_val]
                    applied_rules.append(f"ROCE > {st.session_state.scr_roce_val}%")
                else:
                    skipped_rules.append("ROCE")
                    
            if st.session_state.scr_roe_enabled:
                col = "Return on Equity"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_roe_val]
                    applied_rules.append(f"Return on Equity > {st.session_state.scr_roe_val}%")
                else:
                    skipped_rules.append("Return on Equity")
                    
            if st.session_state.scr_de_enabled:
                col = "Debt to Equity"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] < st.session_state.scr_de_val]
                    applied_rules.append(f"Debt to Equity < {st.session_state.scr_de_val}")
                else:
                    skipped_rules.append("Debt to Equity")
                    
            if st.session_state.scr_fcf_enabled:
                col = "Free Cash Flow"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    if st.session_state.scr_fcf_val:
                        filtered_df = filtered_df[filtered_df[col] > 0]
                        applied_rules.append("Free Cash Flow > 0")
                else:
                    skipped_rules.append("Free Cash Flow")
                    
            if st.session_state.scr_prom_enabled:
                col = "Promoter Holding"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_prom_val]
                    applied_rules.append(f"Promoter Holding > {st.session_state.scr_prom_val}%")
                else:
                    skipped_rules.append("Promoter Holding")
                    
            if st.session_state.scr_peg_enabled:
                col = "PEG Ratio (Forward)"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] < st.session_state.scr_peg_val]
                    applied_rules.append(f"PEG < {st.session_state.scr_peg_val}")
                else:
                    skipped_rules.append("PEG")

            # Advanced Balancing Filters
            if st.session_state.scr_pe_enabled:
                col = "PE Ratio"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] < st.session_state.scr_pe_val]
                    applied_rules.append(f"PE Ratio < {st.session_state.scr_pe_val}")
                    
            if st.session_state.scr_quality_enabled:
                col = "QUALITY_SCORE"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_quality_val]
                    applied_rules.append(f"Quality Score > {st.session_state.scr_quality_val}")
                    
            if st.session_state.scr_sharpe_enabled:
                col = "Sharpe Ratio"
                if col in filtered_df.columns:
                    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
                    filtered_df = filtered_df[filtered_df[col] > st.session_state.scr_sharpe_val]
                    applied_rules.append(f"Sharpe Ratio > {st.session_state.scr_sharpe_val}")
            
            if applied_rules:
                st.success(f"✓ Applied screening filters: {', '.join(applied_rules)}")
            if skipped_rules:
                st.info(f"💡 Skipped rules (Data missing in uploaded universe): {', '.join(skipped_rules)}")
    
            # Filtration Controls
            st.write("---")
            st.subheader("Filter & Sort Results")
    
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
    
            # Apply secondary filters on parsed result
            filtered_recs = filtered_df.copy()
    
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
                st.dataframe(filtered_recs[columns_to_show], width='stretch')

    # -------------------------------------------------------------
    # TAB 2: Portfolio Benchmarking & Volatility Simulator
    # -------------------------------------------------------------
    with tab_benchmarking:
        st.subheader("📊 Portfolio Benchmarking vs Nifty 100")
        
        # Load user holdings
        from utils.page_utils import load_holdings
        holdings = load_holdings()
        
        if holdings.empty:
            st.info("⚠️ Please upload your portfolio holdings in the [holding](pages/1_holding.py) page to enable benchmarking.")
        else:
            # We calculate current weights
            holdings = holdings[holdings["Current Value Rs"] > 0].copy()
            total_val = holdings["Current Value Rs"].sum()
            
            if total_val == 0:
                st.warning("Your holdings show zero current value. Please upload active holdings to analyze.")
            else:
                # Prepare current weights dict
                current_weights = {}
                for _, row in holdings.iterrows():
                    ticker = str(row["Security"])
                    val = float(row["Current Value Rs"])
                    current_weights[ticker] = val / total_val
                
                # Fetch Nifty index volatility
                with st.spinner("Calculating benchmark metrics..."):
                    bench_vol = get_index_volatility()
                    if bench_vol == 0.0:
                        bench_vol = 14.5  # Realistic historical fallback if API is blocked
                        
                    # Calculate current portfolio metrics
                    port_metrics = calculate_portfolio_metrics(current_weights, universe)
                
                # Benchmark values
                bench_pe = float(nifty100_universe["PE Ratio"].dropna().median()) if "PE Ratio" in nifty100_universe.columns and not nifty100_universe.empty else 22.0
                bench_quality = float(nifty100_universe["QUALITY_SCORE"].dropna().mean()) if "QUALITY_SCORE" in nifty100_universe.columns and not nifty100_universe.empty else 60.0
                bench_fundamental = float(nifty100_universe["Fundamental Score"].dropna().mean()) if "Fundamental Score" in nifty100_universe.columns and not nifty100_universe.empty else 50.0
                
                # Nifty Sharpe Ratio proxy: fetch nifty returns and compute it
                nifty_df = PriceHistoryService.fetch_365_days("^NSEI", auto_map_nse=False)
                nifty_sharpe = 1.05 # default
                if not nifty_df.empty:
                    nifty_df = nifty_df.sort_values("date")
                    nifty_df["daily_return"] = nifty_df["close"].pct_change()
                    ann_return = nifty_df["daily_return"].mean() * 252 * 100.0
                    ann_vol = nifty_df["daily_return"].std() * (252 ** 0.5) * 100.0
                    if ann_vol > 0:
                        nifty_sharpe = (ann_return - 6.0) / ann_vol # assume 6% risk free rate
                
                # Portfolio weighted Sharpe Ratio
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
                
                # Render KPIs Side by Side
                col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                
                pe_delta = port_metrics["pe"] - bench_pe
                col_kpi1.metric(
                    "Portfolio P/E Ratio", 
                    f"{port_metrics['pe']:.2f}",
                    delta=f"{pe_delta:+.2f} vs Benchmark",
                    delta_color="inverse"
                )
                
                vol_delta = port_metrics["volatility"] - bench_vol
                col_kpi2.metric(
                    "Annual Volatility %",
                    f"{port_metrics['volatility']:.2f}%",
                    delta=f"{vol_delta:+.2f}% vs Index",
                    delta_color="inverse"
                )
                
                q_delta = port_metrics["quality"] - bench_quality
                col_kpi3.metric(
                    "Avg Quality Rating",
                    f"{port_metrics['quality']:.1f}/100",
                    delta=f"{q_delta:+.1f} vs Benchmark"
                )
                
                s_delta = port_sharpe - nifty_sharpe
                col_kpi4.metric(
                    "Composite Sharpe Ratio",
                    f"{port_sharpe:.2f}",
                    delta=f"{s_delta:+.2f} vs Index"
                )
                
                # Dynamic rules apply button
                st.write("")
                st.subheader("⚖️ Dynamic Risk Balancing")
                st.write("Apply balancing rules directly to the screening filters to isolate stocks that neutralize your deficits:")
                
                st.button(
                    "🔧 Tune Screening Filters for Balanced Risk/Reward", 
                    key="apply_balance_btn", 
                    on_click=tune_filters_callback,
                    args=(port_metrics["volatility"], bench_vol, port_metrics["pe"], bench_pe, port_metrics["quality"], bench_quality),
                    width='stretch'
                )

                # Summary checklist
                st.write("")
                st.subheader("💡 Counter-Underperformance Recommendations")
                st.write("Below are stocks from the universe selected specifically to balance risk and counter your portfolio's relative weaknesses:")
                
                # Focus counter recommendations on liquid Mid and Large Cap stocks (market cap >= 5000 Cr)
                # to match standard benchmarking tiers and avoid highly speculative micro-cap recommendations.
                advisory_universe = universe[universe["Market Cap"] >= 5000.0]
                if len(advisory_universe) < 10:
                    advisory_universe = universe

                # Evaluate counter recommendations
                counter_recs = []
                
                # 1. High Volatility Check
                if port_metrics["volatility"] > bench_vol:
                    defensive = advisory_universe[advisory_universe["Sharpe Ratio"] >= 1.0].sort_values(by="Sharpe Ratio", ascending=False)
                    if defensive.empty:
                        defensive = advisory_universe.sort_values(by="Sharpe Ratio", ascending=False).head(15)
                    for _, row in defensive.iterrows():
                        counter_recs.append({
                            "Ticker": row["Ticker"],
                            "Name": row["Name"],
                            "Sector": row.get("Sub-Sector", "N/A"),
                            "Market Cap": classify_mcap(row.get("Market Cap", 0.0)),
                            "Balancing Target": "Reduce Volatility (Risk)",
                            "Action / Rationale": "Inject defensive stability and improve Sharpe ratio (risk-adjusted return).",
                            "Key Metric": f"Sharpe Ratio: {row.get('Sharpe Ratio', 0.0):.2f}",
                            "pe": float(row.get("PE Ratio", 0.0)) if pd.notna(row.get("PE Ratio")) else 0.0,
                            "quality": float(row.get("QUALITY_SCORE", 0.0)) if pd.notna(row.get("QUALITY_SCORE")) else 0.0,
                            "sharpe": float(row.get("Sharpe Ratio", 0.0)) if pd.notna(row.get("Sharpe Ratio")) else 0.0
                        })
                
                # 2. Valuation Check
                if port_metrics["pe"] > bench_pe:
                    value_picks = advisory_universe[(advisory_universe["PEG Ratio (Forward)"] > 0) & (advisory_universe["PEG Ratio (Forward)"] < 1.5) & (advisory_universe["PE Ratio"] < bench_pe)].sort_values(by="PEG Ratio (Forward)", ascending=True)
                    if value_picks.empty:
                        value_picks = advisory_universe[(advisory_universe["PE Ratio"] > 0) & (advisory_universe["PE Ratio"] < bench_pe)].sort_values(by="PE Ratio", ascending=True)
                    for _, row in value_picks.iterrows():
                        if not any(r["Ticker"] == row["Ticker"] for r in counter_recs):
                            counter_recs.append({
                                "Ticker": row["Ticker"],
                                "Name": row["Name"],
                                "Sector": row.get("Sub-Sector", "N/A"),
                                "Market Cap": classify_mcap(row.get("Market Cap", 0.0)),
                                "Balancing Target": "Reduce Valuation (P/E)",
                                "Action / Rationale": "Lower overall portfolio P/E with high-growth, lower-PEG value stocks.",
                                "Key Metric": f"Forward PEG: {row.get('PEG Ratio (Forward)', 0.0):.2f}",
                                "pe": float(row.get("PE Ratio", 0.0)) if pd.notna(row.get("PE Ratio")) else 0.0,
                                "quality": float(row.get("QUALITY_SCORE", 0.0)) if pd.notna(row.get("QUALITY_SCORE")) else 0.0,
                                "sharpe": float(row.get("Sharpe Ratio", 0.0)) if pd.notna(row.get("Sharpe Ratio")) else 0.0
                            })
                            
                # 3. Quality Check
                if port_metrics["quality"] < bench_quality:
                    quality_picks = advisory_universe[advisory_universe["QUALITY_SCORE"] >= 70.0].sort_values(by="QUALITY_SCORE", ascending=False)
                    if quality_picks.empty:
                        quality_picks = advisory_universe.sort_values(by="QUALITY_SCORE", ascending=False).head(15)
                    for _, row in quality_picks.iterrows():
                        if not any(r["Ticker"] == row["Ticker"] for r in counter_recs):
                            counter_recs.append({
                                "Ticker": row["Ticker"],
                                "Name": row["Name"],
                                "Sector": row.get("Sub-Sector", "N/A"),
                                "Market Cap": classify_mcap(row.get("Market Cap", 0.0)),
                                "Balancing Target": "Boost Quality Score",
                                "Action / Rationale": "Enhance safety margins and ROCE/ROE via Quality Compounders.",
                                "Key Metric": f"Quality: {row.get('QUALITY_SCORE', 0.0):.1f}/100",
                                "pe": float(row.get("PE Ratio", 0.0)) if pd.notna(row.get("PE Ratio")) else 0.0,
                                "quality": float(row.get("QUALITY_SCORE", 0.0)) if pd.notna(row.get("QUALITY_SCORE")) else 0.0,
                                "sharpe": float(row.get("Sharpe Ratio", 0.0)) if pd.notna(row.get("Sharpe Ratio")) else 0.0
                            })
                            
                # Fill general strong recommendations if list is short
                if len(counter_recs) < 15:
                    strong_picks = advisory_universe[advisory_universe["Fundamental Score"] >= 65.0].sort_values(by="Fundamental Score", ascending=False)
                    if strong_picks.empty:
                        strong_picks = advisory_universe.sort_values(by="Fundamental Score", ascending=False).head(15)
                    for _, row in strong_picks.iterrows():
                        if not any(r["Ticker"] == row["Ticker"] for r in counter_recs):
                            counter_recs.append({
                                "Ticker": row["Ticker"],
                                "Name": row["Name"],
                                "Sector": row.get("Sub-Sector", "N/A"),
                                "Market Cap": classify_mcap(row.get("Market Cap", 0.0)),
                                "Balancing Target": "Boost Overall Fundamentals",
                                "Action / Rationale": "Reinforce general portfolio fundamental composition.",
                                "Key Metric": f"Fundamental Score: {row.get('Fundamental Score', 0.0):.1f}",
                                "pe": float(row.get("PE Ratio", 0.0)) if pd.notna(row.get("PE Ratio")) else 0.0,
                                "quality": float(row.get("QUALITY_SCORE", 0.0)) if pd.notna(row.get("QUALITY_SCORE")) else 0.0,
                                "sharpe": float(row.get("Sharpe Ratio", 0.0)) if pd.notna(row.get("Sharpe Ratio")) else 0.0
                            })
                
                # Render counter recommendations as a structured table list
                if counter_recs:
                    df_recs = pd.DataFrame(counter_recs)
                    
                    # Dedicated filters layout for advisory list
                    st.write("")
                    st.caption("🔍 **Filter recommendations below:**")
                    
                    # Row 1 filters
                    rec_col1, rec_col2, rec_col3 = st.columns(3)
                    with rec_col1:
                        search_term = st.text_input("Search Ticker or Name", value="", key="counter_search")
                    with rec_col2:
                        sector_list = ["All"] + sorted(list(df_recs["Sector"].dropna().unique()))
                        selected_rec_sectors = st.multiselect("Filter by Sector / Industry", options=sector_list, default=["All"], key="counter_sector")
                    with rec_col3:
                        mcap_list = ["All"] + sorted(list(df_recs["Market Cap"].dropna().unique()))
                        selected_rec_mcaps = st.multiselect("Filter by Cap size", options=mcap_list, default=["All"], key="counter_mcap")
                        
                    # Row 2 filters
                    rec_col4, rec_col5 = st.columns(2)
                    with rec_col4:
                        target_list = ["All"] + sorted(list(df_recs["Balancing Target"].dropna().unique()))
                        selected_rec_targets = st.multiselect("Filter by Balancing Focus Target", options=target_list, default=["All"], key="counter_target")
                    with rec_col5:
                        rationale_list = ["All"] + sorted(list(df_recs["Action / Rationale"].dropna().unique()))
                        selected_rec_rationales = st.multiselect("Filter by Action / Rationale", options=rationale_list, default=["All"], key="counter_rationale")
                        
                    # Row 3 metrics filters
                    rec_exp = st.expander("📊 Advanced Metrics Filtering (P/E, Quality, Sharpe)", expanded=False)
                    with rec_exp:
                        m_col1, m_col2, m_col3 = st.columns(3)
                        with m_col1:
                            max_pe_filter = st.slider("Max P/E Ratio", min_value=0.0, max_value=150.0, value=150.0, step=1.0, key="counter_max_pe")
                        with m_col2:
                            min_quality_filter = st.slider("Min Quality Score", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="counter_min_quality")
                        with m_col3:
                            min_sharpe_filter = st.slider("Min Sharpe Ratio", min_value=-2.0, max_value=5.0, value=-2.0, step=0.1, key="counter_min_sharpe")
                            
                    # Apply filters
                    filtered_df_recs = df_recs.copy()
                    if search_term:
                        filtered_df_recs = filtered_df_recs[
                            filtered_df_recs["Ticker"].str.contains(search_term, case=False, na=False) |
                            filtered_df_recs["Name"].str.contains(search_term, case=False, na=False)
                        ]
                    if selected_rec_sectors and "All" not in selected_rec_sectors:
                        filtered_df_recs = filtered_df_recs[filtered_df_recs["Sector"].isin(selected_rec_sectors)]
                    if selected_rec_mcaps and "All" not in selected_rec_mcaps:
                        filtered_df_recs = filtered_df_recs[filtered_df_recs["Market Cap"].isin(selected_rec_mcaps)]
                    if selected_rec_targets and "All" not in selected_rec_targets:
                        filtered_df_recs = filtered_df_recs[filtered_df_recs["Balancing Target"].isin(selected_rec_targets)]
                    if selected_rec_rationales and "All" not in selected_rec_rationales:
                        filtered_df_recs = filtered_df_recs[filtered_df_recs["Action / Rationale"].isin(selected_rec_rationales)]
                        
                    # Apply Advanced Metrics filters
                    filtered_df_recs = filtered_df_recs[
                        (filtered_df_recs["pe"] <= max_pe_filter) &
                        (filtered_df_recs["quality"] >= min_quality_filter) &
                        (filtered_df_recs["sharpe"] >= min_sharpe_filter)
                    ]
                        
                    st.dataframe(
                        filtered_df_recs,
                        width='stretch',
                        hide_index=True,
                        column_config={
                            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                            "Name": st.column_config.TextColumn("Company Name", width="medium"),
                            "Sector": st.column_config.TextColumn("Sector / Industry", width="medium"),
                            "Market Cap": st.column_config.TextColumn("Market Cap", width="small"),
                            "Balancing Target": st.column_config.TextColumn("Balancing Target", width="medium"),
                            "Action / Rationale": st.column_config.TextColumn("Action / Rationale", width="large"),
                            "Key Metric": st.column_config.TextColumn("Key Metric", width="small"),
                            "pe": st.column_config.NumberColumn("PE", width="small", format="%.2f"),
                            "quality": st.column_config.NumberColumn("Quality", width="small", format="%.1f"),
                            "sharpe": st.column_config.NumberColumn("Sharpe", width="small", format="%.2f")
                        }
                    )
                else:
                    st.info("No countering recommendations needed. Your portfolio aligns well with Nifty 100 benchmark stats!")
                
                # --- INTERACTIVE SIMULATOR ---
                st.divider()
                st.subheader("⚡ Risk & Reward Simulator Workspace")
                st.write("Simulate adding a balancing stock to see its instant impact on your portfolio's Volatility, P/E, and Quality rating.")
                
                sim_col1, sim_col2, sim_col3 = st.columns([2, 1, 1])
                
                with sim_col1:
                    rec_tickers = [r["Ticker"] for r in counter_recs]
                    other_tickers = [t for t in sorted(universe["Ticker"].tolist()) if t not in rec_tickers]
                    options_list = rec_tickers + other_tickers
                    
                    sim_tickers = st.multiselect(
                        "Choose Stocks to Simulate",
                        options=options_list,
                        default=[options_list[0]] if options_list else [],
                        help="Select one or more stocks to run addition simulation"
                    )
                
                with sim_col2:
                    sim_mode = st.selectbox(
                        "Simulation Mode",
                        options=["Allocate from Cash", "Replace Existing Stock"],
                        help="Choose whether to add these stocks using new cash or replace a current holding"
                    )
                    
                with sim_col3:
                    if sim_mode == "Replace Existing Stock":
                        replace_ticker = st.selectbox(
                            "Stock to Sell/Replace",
                            options=sorted(list(current_weights.keys())),
                            help="Select which holding is sold to buy the simulated stocks"
                        )
                        sim_weight_pct = 0.0
                    else:
                        sim_weight_pct = st.slider(
                            "Simulated Allocation Weight per Stock (%)",
                            min_value=1.0,
                            max_value=30.0,
                            value=5.0,
                            step=1.0,
                            help="Weight allocated to each of the selected simulated stocks"
                        )
                        replace_ticker = None
                        
                if not sim_tickers:
                    st.info("💡 Please select at least one stock to simulate.")
                    st.stop()
                    
                # Perform simulation logic
                sim_weights = {}
                n_sim = len(sim_tickers)
                
                if sim_mode == "Allocate from Cash":
                    sim_w_per_stock = sim_weight_pct / 100.0
                    total_sim_w = n_sim * sim_w_per_stock
                    
                    if total_sim_w >= 1.0:
                        total_sim_w = 0.9
                        sim_w_per_stock = total_sim_w / n_sim
                        st.warning(f"⚠️ Total simulated weight capped at 90% ({sim_w_per_stock*100:.1f}% per stock) to preserve portfolio structure.")
                        
                    remaining_scale = 1.0 - total_sim_w
                    for t, w in current_weights.items():
                        sim_weights[t] = w * remaining_scale
                    for ticker in sim_tickers:
                        sim_weights[ticker] = sim_weights.get(ticker, 0.0) + sim_w_per_stock
                else:
                    replace_w = current_weights.get(replace_ticker, 0.0)
                    sim_w_per_stock = replace_w / n_sim if n_sim > 0 else 0.0
                    
                    for t, w in current_weights.items():
                        if t == replace_ticker:
                            sim_weights[t] = 0.0
                        else:
                            sim_weights[t] = w
                    for ticker in sim_tickers:
                        sim_weights[ticker] = sim_weights.get(ticker, 0.0) + sim_w_per_stock
                    
                # Calculate simulated metrics
                with st.spinner("Simulating portfolio changes..."):
                    sim_metrics = calculate_portfolio_metrics(sim_weights, universe)
                    
                # Simulated Sharpe Ratio
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
                
                # Side-by-Side Simulation Metrics
                st.write("")
                st.markdown("### Simulation Impact Report")
                
                col_sim1, col_sim2, col_sim3, col_sim4 = st.columns(4)
                
                # P/E comparison
                pe_change = sim_metrics["pe"] - port_metrics["pe"]
                col_sim1.metric(
                    "Simulated P/E",
                    f"{sim_metrics['pe']:.2f}",
                    delta=f"{pe_change:+.2f} Change",
                    delta_color="inverse"
                )
                
                # Volatility comparison
                vol_change = sim_metrics["volatility"] - port_metrics["volatility"]
                col_sim2.metric(
                    "Simulated Volatility",
                    f"{sim_metrics['volatility']:.2f}%",
                    delta=f"{vol_change:+.2f}% Change",
                    delta_color="inverse"
                )
                
                # Quality comparison
                q_change = sim_metrics["quality"] - port_metrics["quality"]
                col_sim3.metric(
                    "Simulated Quality Rating",
                    f"{sim_metrics['quality']:.1f}/100",
                    delta=f"{q_change:+.1f} Change"
                )
                
                # Sharpe comparison
                s_change = sim_sharpe - port_sharpe
                col_sim4.metric(
                    "Simulated Sharpe Ratio",
                    f"{sim_sharpe:.2f}",
                    delta=f"{s_change:+.2f} Change"
                )
                
                # Plot Simulation Comparison Chart
                st.write("")
                plot_data = pd.DataFrame([
                    {"Category": "Current Portfolio", "P/E Ratio": port_metrics["pe"], "Volatility (%)": port_metrics["volatility"]},
                    {"Category": "Simulated Portfolio", "P/E Ratio": sim_metrics["pe"], "Volatility (%)": sim_metrics["volatility"]},
                    {"Category": "Nifty Benchmark", "P/E Ratio": bench_pe, "Volatility (%)": bench_vol}
                ])
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_pe = px.bar(
                        plot_data,
                        x="Category",
                        y="P/E Ratio",
                        color="Category",
                        title="P/E Ratio Comparison",
                        color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96"]
                    )
                    fig_pe.update_layout(autosize=True, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pe, width='stretch', config={"displayModeBar": True, "responsive": True})
                
                with col_chart2:
                    fig_vol = px.bar(
                        plot_data,
                        x="Category",
                        y="Volatility (%)",
                        color="Category",
                        title="Annualized Volatility (%) Comparison",
                        color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96"]
                    )
                    fig_vol.update_layout(autosize=True, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_vol, width='stretch', config={"displayModeBar": True, "responsive": True})