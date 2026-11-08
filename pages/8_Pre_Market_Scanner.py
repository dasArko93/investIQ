# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import io
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from utils.page_utils import render_sidebar, require_auth
from engines.pre_market_engine import PreMarketEngine

# ─────────────────────────────────────────────────────────────────────────────
# Page Config & Security
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pre-Market Stock Selection & Breakout Radar | InvestIQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
render_sidebar()

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS Styling (Glassmorphic InvestIQ Theme)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .scanner-hero {
        background: linear-gradient(135deg, rgba(99,102,241,0.16) 0%, rgba(59,130,246,0.12) 50%, rgba(16,185,129,0.10) 100%);
        border: 1px solid rgba(99,102,241,0.30);
        border-radius: 20px;
        padding: 24px 28px 20px 28px;
        margin-bottom: 20px;
        backdrop-filter: blur(14px);
    }
    .scanner-hero h1 { margin: 0 0 6px 0; font-size: 2.0rem; color: #0f172a; font-weight: 800; }
    .scanner-hero p  { margin: 0; color: #475569; font-size: 0.95rem; line-height: 1.5; }

    .kpi-card {
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(226,232,240,0.85);
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.03);
    }
    .kpi-val { font-size: 1.6rem; font-weight: 800; color: #0f172a; }
    .kpi-lbl { font-size: 0.78rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-top: 2px; }

    .regime-box {
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 18px;
        border: 1px solid rgba(0,0,0,0.08);
    }

    .action-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        transition: transform 0.15s ease;
    }
    .action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    }

    .pill-green {
        background: rgba(22,163,74,0.12);
        color: #16a34a;
        border: 1px solid rgba(22,163,74,0.3);
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .pill-red {
        background: rgba(220,38,38,0.12);
        color: #dc2626;
        border: 1px solid rgba(220,38,38,0.3);
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .pill-blue {
        background: rgba(59,130,246,0.12);
        color: #2563eb;
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .pill-purple {
        background: rgba(147,51,234,0.12);
        color: #9333ea;
        border: 1px solid rgba(147,51,234,0.3);
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .pill-gray {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 2px 7px;
        font-size: 0.75rem;
    }

    /* Responsive metric cards & font scaling to prevent ellipsis truncation on any screen width */
    [data-testid="stMetricValue"] {
        font-size: clamp(0.95rem, 1.35vw, 1.35rem) !important;
        font-weight: 800 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: clamp(0.68rem, 0.8vw, 0.78rem) !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
        line-height: 1.2 !important;
    }

    .spotlight-metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .spotlight-metric-lbl {
        color: #64748b;
        font-size: clamp(0.65rem, 0.78vw, 0.74rem);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .spotlight-metric-val {
        font-weight: 800;
        font-size: clamp(0.92rem, 1.25vw, 1.25rem);
        color: #0f172a;
        line-height: 1.2;
        white-space: nowrap;
    }
    .spotlight-metric-sub {
        font-size: clamp(0.65rem, 0.72vw, 0.74rem);
        font-weight: 700;
        margin-top: 2px;
    }

    .section-hdr {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0f172a;
        margin: 16px 0 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Header Hero Banner
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="scanner-hero">
        <h1>⚡ Pre-Market Stock Selection & Breakout Radar</h1>
        <p>
            An End-of-Day (EOD) quantitative screening engine identifying stocks coiled for 
            <strong>2% to 5% intraday expansion moves</strong> across all listed Indian equities 
            (Large, Mid, Small Cap — <em>strictly excluding illiquid penny stocks</em>).
            Implements the multi-stage technical and institutional confirmation funnel.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Strategy Architecture & Funnel Guide
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📘 Strategy Architecture & 3-Stage Filtering Funnel (From Pre-Market Opening Rules)", expanded=False):
    st.markdown(
        """
        ### 🎯 Core Trading Philosophy
        > *"Big stock moves during the day rarely happen out of nowhere; their signals almost always show up the night before on the daily charts."*

        To capture high-probability intraday expansions, the engine executes a **3-stage quantitative funnel**:

        1. **Stage 1: Volatility & Price Compression Scans (EOD 6:30 PM)**
           - **NR7 / NR4**: Identifies stocks where the daily high-to-low range is the tightest within the last 7 or 4 sessions.
           - **Daily Inside Bar**: Range is strictly inside the previous session ($High < High_{-1}$ and $Low > Low_{-1}$).
           - **Narrow Central Pivot Range (CPR)**: Calculated for the next day using $P = (H+L+C)/3$, $BC = (H+L)/2$, $TC = (P-BC)+P$. Flags where $\\frac{|TC-BC|}{Close} < 0.25\\%$.
           - *Outcome: Filters universe down to candidate stocks coiling with potential energy.*

        2. **Stage 2: Institutional Confirmation (EOD 7:30 PM)**
           - **Volume Surge**: Traded volume is $\\ge 1.5\\times$ the 20-day average.
           - **Candle Close Location**: Closes in top 20% (bullish accumulation) or bottom 20% (bearish distribution) of the range.
           - *Outcome: Separates genuine institutional accumulation/distribution from retail noise.*

        3. **Stage 3: Morning Triggers & Risk Rules (Next Morning 9:15–10:15 AM)**
           - **No 9:15 AM Chase**: Wait 15–45 minutes for the market to establish true order flow direction.
           - **Bullish Trigger**: Cross above **Previous Day High (PDH)** on expanding volume.
           - **Bearish Trigger**: Breakdown below **Previous Day Low (PDL)** on expanding volume.
           - **Target**: $1.5\\times$ to $2.0\\times$ Daily ATR (2% to 5% expansion).
           - **Stop Loss**: Invalidation below/above VWAP or day's opening swing.
        """
    )

# ─────────────────────────────────────────────────────────────────────────────
# Macro Context & India VIX Market Regime Strip
# ─────────────────────────────────────────────────────────────────────────────
# Handle Update Now or Manual Override actions
if "manual_vix_override" not in st.session_state:
    st.session_state["manual_vix_override"] = None

reg_banner_col, reg_action_col = st.columns([5.2, 1.4])

with reg_action_col:
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    update_vix = st.button(
        "🔄 Update Now",
        key="btn_update_vix",
        help="Fetch latest live India VIX and refresh market regime.",
        width="stretch",
        type="primary"
    )

    with st.popover("⚙️ Set VIX", help="Simulate or set a specific India VIX value"):
        current_cached_vix = float(PreMarketEngine.get_market_regime()["vix_value"])
        custom_vix_input = st.number_input(
            "Custom VIX Value",
            min_value=5.0,
            max_value=65.0,
            value=current_cached_vix,
            step=0.25,
            help="Simulate regime: <12 (Range-Bound), 12-18.5 (Breakout), >18.5 (High Volatility)"
        )
        if st.button("Apply Value", key="apply_vix_btn", width="stretch"):
            PreMarketEngine.set_manual_vix(float(custom_vix_input))
            st.rerun()

if update_vix:
    with st.spinner("Fetching latest live India VIX..."):
        regime_info = PreMarketEngine.get_market_regime(force_refresh=True)
    st.toast(f"✅ Market Regime updated: India VIX @ {regime_info['vix_value']:.2f}", icon="⚡")
else:
    regime_info = PreMarketEngine.get_market_regime(force_refresh=False)

vix_val = regime_info["vix_value"]
regime_text = regime_info["regime"]
badge_color = regime_info["badge_color"]
sentiment_icon = regime_info["sentiment_icon"]
guidance_text = regime_info["guidance"]
source_note = regime_info.get("source", "Cached")

with reg_action_col:
    st.markdown(f"<div style='text-align:center; font-size:0.75rem; color:#64748b; margin-top:2px;'>Source: {source_note}</div>", unsafe_allow_html=True)

with reg_banner_col:
    st.markdown(
        f"""
        <div class="regime-box" style="background: {badge_color}10; border-left: 6px solid {badge_color}; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <span style="font-size:1.15rem; font-weight:800; color:#0f172a;">
                        {sentiment_icon} India VIX: <strong>{vix_val:.2f}</strong> — {regime_text}
                    </span>
                </div>
                <div>
                    <span class="pill-gray">Updated: {regime_info['as_of']}</span>
                </div>
            </div>
            <div style="margin-top:8px; font-size:0.92rem; color:#334155; line-height:1.5;">
                {guidance_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Interactive Scanner Control Bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">🔍 Screening Universe & Funnel Controls</div>', unsafe_allow_html=True)

ctl1, ctl2, ctl3, ctl4 = st.columns([2.0, 1.2, 1.2, 1.2])

with ctl1:
    tier_options = [
        "All Listed Equities (No Penny Stocks)",
        "Large Cap (Top 100)",
        "Mid Cap (Rank 101–250)",
        "Small Cap (Rank 251+)",
        "Large & Mid Cap (Top 250)",
        "F&O Universe (~180 Stocks)"
    ]
    selected_tier_label = st.selectbox(
        "🎯 Select Equity Universe",
        options=tier_options,
        index=0,
        help="Select market capitalization tier. Strictly covers non-penny equities."
    )
    # Map tier label to internal key
    tier_map = {
        "All Listed Equities (No Penny Stocks)": "All",
        "Large Cap (Top 100)": "Large Cap",
        "Mid Cap (Rank 101–250)": "Mid Cap",
        "Small Cap (Rank 251+)": "Small Cap",
        "Large & Mid Cap (Top 250)": "Large & Mid Cap",
        "F&O Universe (~180 Stocks)": "F&O Universe"
    }
    active_tier = tier_map[selected_tier_label]

with ctl2:
    min_price_input = st.number_input(
        "💵 Min Price (₹)",
        min_value=50.0,
        max_value=1000.0,
        value=100.0,
        step=25.0,
        help="Strictly eliminates penny stocks below ₹100 as prescribed by the strategy rules."
    )

with ctl3:
    max_scan_stocks = st.slider(
        "📊 Stock Batch Limit",
        min_value=30,
        max_value=250,
        value=120,
        step=10,
        help="Number of liquid candidates to scan simultaneously."
    )

with ctl4:
    st.write("")
    st.write("")
    force_scan = st.button("🔄 Run Screener", width="stretch", type="primary")

# ─────────────────────────────────────────────────────────────────────────────
# Execute Screening Engine
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner(f"Scanning {selected_tier_label} for compression & breakout signals..."):
    scan_output = PreMarketEngine.run_screener(
        tier=active_tier,
        min_price=float(min_price_input),
        max_stocks=int(max_scan_stocks),
        force_refresh=force_scan
    )

all_df = scan_output.get("all_results_df", pd.DataFrame())
high_conv_df = scan_output.get("high_conviction_df", pd.DataFrame())
comp_df = scan_output.get("compression_df", pd.DataFrame())
scan_time = scan_output.get("scan_timestamp", datetime.now().strftime("%d %b %Y"))

# ─────────────────────────────────────────────────────────────────────────────
# Executive Funnel KPI Strip
# ─────────────────────────────────────────────────────────────────────────────
total_evaluated = len(all_df)
stage1_count = len(comp_df)
stage2_count = len(high_conv_df)
bullish_count = len(high_conv_df[high_conv_df["Direction"] == "BULLISH"]) if not high_conv_df.empty else 0
bearish_count = len(high_conv_df[high_conv_df["Direction"] == "BEARISH"]) if not high_conv_df.empty else 0

kp1, kp2, kp3, kp4, kp5 = st.columns(5)
kp1.markdown(f'<div class="kpi-card"><div class="kpi-val">{total_evaluated}</div><div class="kpi-lbl">Equities Scanned</div></div>', unsafe_allow_html=True)
kp2.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#2563eb;">{stage1_count}</div><div class="kpi-lbl">Stage 1: Coiling (NR/CPR)</div></div>', unsafe_allow_html=True)
kp3.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#9333ea;">{stage2_count}</div><div class="kpi-lbl">Stage 2: High Conviction</div></div>', unsafe_allow_html=True)
kp4.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#16a34a;">{bullish_count}</div><div class="kpi-lbl">🚀 Bullish Breakouts</div></div>', unsafe_allow_html=True)
kp5.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#dc2626;">{bearish_count}</div><div class="kpi-lbl">🔻 Bearish Breakouts</div></div>', unsafe_allow_html=True)

st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# 5 INTERACTIVE TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_watchlist, tab_compression, tab_playbook, tab_guide, tab_audit = st.tabs([
    "⚡ High-Conviction Actionable Watchlist (Stage 1 + 2 Confirmed)",
    "🔍 Full Market Compression Radar (Stage 1 Candidates)",
    "📋 Next-Morning Execution Playbook (9:15–10:15 AM)",
    "📖 Comprehensive User Guide & Strategy Manual",
    "📊 Session Accuracy & Performance Audit"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: High-Conviction Actionable Watchlist
# ─────────────────────────────────────────────────────────────────────────────
with tab_watchlist:
    st.markdown('<div class="section-hdr">⚡ Priority Breakout Candidates (Stage 1 Compression + Stage 2 Institutional Confirmation)</div>', unsafe_allow_html=True)
    st.caption("These stocks exhibit tight range contraction combined with heavy volume surges or narrow CPR, ready for a 2% to 5% directional intraday expansion.")

    if high_conv_df.empty:
        st.info("No stocks currently meet both strict Stage 1 compression and Stage 2 confirmation criteria in this batch. Review the **Full Market Compression Radar** tab for candidates approaching breakout thresholds.")
    else:
        # Download Watchlist CSV Button
        csv_export = high_conv_df[[
            "Ticker", "Stock Name", "Sector", "Market Cap Tier", "Direction", "Close",
            "PDH", "PDL", "Daily_ATR", "Target_1_5x", "Target_2_0x", "Stop_Loss",
            "Estimated_Expansion_Pct", "Trigger_Rule", "Setup_Tags"
        ]].to_csv(index=False)

        d_col1, d_col2 = st.columns([2.5, 3.5])
        with d_col1:
            st.download_button(
                label=f"📥 Download Priority Watchlist & Triggers (CSV)",
                data=csv_export,
                file_name=f"investiq_premarket_breakouts_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                type="primary",
                width="stretch"
            )
        with d_col2:
            st.caption(f"Generated from latest trading session data ({scan_time}). Zero penny stocks included.")

        st.markdown("---")

        # ─────────────────────────────────────────────────────────────────────
        # CANDIDATE SPOTLIGHT & BREAKOUT INSPECTOR (SINGLE DYNAMIC TILE)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="section-hdr">🎯 Candidate Spotlight & Breakout Inspector</div>',
            unsafe_allow_html=True
        )
        st.caption("Filter and select any priority candidate to inspect its exact morning triggers, expansion targets, and execution rules in a unified spotlight card.")

        # Interactive Filter Bar
        flt_cap_col, flt_sec_col, flt_bias_col, flt_pick_col = st.columns([1.1, 1.4, 1.4, 2.1])

        with flt_cap_col:
            cap_opts = ["All Caps"] + sorted([t for t in high_conv_df["Market Cap Tier"].dropna().unique() if str(t).strip()])
            sel_cap = st.selectbox("🏷️ Market Cap", cap_opts, index=0, key="spotlight_cap_flt")

        with flt_sec_col:
            sec_opts = ["All Sectors"] + sorted([s for s in high_conv_df["Sector"].dropna().unique() if str(s).strip()])
            sel_sec = st.selectbox("🏢 Sector", sec_opts, index=0, key="spotlight_sec_flt")

        with flt_bias_col:
            bias_opts = ["All Biases", "🚀 Bullish Only", "🔻 Bearish Only", "⚖️ Neutral / Bilateral Only"]
            sel_bias = st.selectbox("🧭 Directional Bias", bias_opts, index=0, key="spotlight_bias_flt")

        # Apply filters to narrow down candidates for the inspector
        scoped_df = high_conv_df.copy()
        if sel_cap != "All Caps":
            scoped_df = scoped_df[scoped_df["Market Cap Tier"] == sel_cap]
        if sel_sec != "All Sectors":
            scoped_df = scoped_df[scoped_df["Sector"] == sel_sec]
        if sel_bias == "🚀 Bullish Only":
            scoped_df = scoped_df[scoped_df["Direction"] == "BULLISH"]
        elif sel_bias == "🔻 Bearish Only":
            scoped_df = scoped_df[scoped_df["Direction"] == "BEARISH"]
        elif sel_bias == "⚖️ Neutral / Bilateral Only":
            scoped_df = scoped_df[scoped_df["Direction"] == "NEUTRAL"]

        with flt_pick_col:
            if scoped_df.empty:
                st.selectbox("📌 Select Candidate to Inspect", ["No matching candidates found"], disabled=True, key="spotlight_stock_picker")
                selected_stock_ticker = None
            else:
                stock_label_map = {}
                for _, r in scoped_df.iterrows():
                    d_icon = "🚀" if r["Direction"] == "BULLISH" else ("🔻" if r["Direction"] == "BEARISH" else "⚖️")
                    lbl = f"{r['Ticker']} — {r['Stock Name'][:22]} ({d_icon} {r['Direction']})"
                    stock_label_map[lbl] = r["Ticker"]
                
                chosen_label = st.selectbox("📌 Select Candidate to Inspect", list(stock_label_map.keys()), index=0, key="spotlight_stock_picker")
                selected_stock_ticker = stock_label_map[chosen_label]

        # ─────────────────────────────────────────────────────────────────────
        # Render the Single Spotlight Tile
        # ─────────────────────────────────────────────────────────────────────
        if selected_stock_ticker and not scoped_df.empty:
            match_row = scoped_df[scoped_df["Ticker"] == selected_stock_ticker]
            if not match_row.empty:
                stock = match_row.iloc[0]
                ticker = stock["Ticker"]
                name = stock["Stock Name"]
                sector = stock["Sector"]
                tier = stock["Market Cap Tier"]
                direction = stock["Direction"]
                close_p = stock["Close"]
                pdh = stock["PDH"]
                pdl = stock["PDL"]
                atr = stock["Daily_ATR"]
                atr_pct = stock["Daily_ATR_Pct"]
                tgt1 = stock["Target_1_5x"]
                tgt2 = stock["Target_2_0x"]
                sl = stock["Stop_Loss"]
                exp_pct = stock["Estimated_Expansion_Pct"]
                rule = stock["Trigger_Rule"]
                setups = stock["Setup_Tags"]
                cpr_p = stock["CPR_Pct"]
                vol_r = stock["Vol_Ratio"]

                # Bias-specific badge, colors, and levels
                if direction == "BULLISH":
                    dir_color = "#16a34a"
                    dir_badge = ":green[▲ BULLISH EXPANSION]"
                    trig_lbl = "Trigger (BUY > PDH)"
                    trig_val = pdh
                    trig_sub = "5-min Confirm"
                    tgt1_lbl = "Target 1 (1.5x ATR)"
                    tgt1_val = tgt1
                    tgt1_sub = f"+{exp_pct:.1f}%"
                    tgt2_lbl = "Target 2 (2.0x ATR)"
                    tgt2_val = tgt2
                    tgt2_sub = "Runner Target"
                    sl_lbl = "Stop Loss (VWAP/Low)"
                    sl_val = sl
                    sl_sub = "Risk Invalidation"
                elif direction == "BEARISH":
                    dir_color = "#dc2626"
                    dir_badge = ":red[▼ BEARISH BREAKDOWN]"
                    trig_lbl = "Trigger (SELL < PDL)"
                    trig_val = pdl
                    trig_sub = "5-min Confirm"
                    tgt1_lbl = "Target 1 (1.5x ATR)"
                    tgt1_val = tgt1
                    tgt1_sub = f"-{exp_pct:.1f}%"
                    tgt2_lbl = "Target 2 (2.0x ATR)"
                    tgt2_val = tgt2
                    tgt2_sub = "Runner Target"
                    sl_lbl = "Stop Loss (VWAP/High)"
                    sl_val = sl
                    sl_sub = "Risk Invalidation"
                else:  # NEUTRAL / BILATERAL COIL
                    dir_color = "#6366f1"
                    dir_badge = ":blue[⚖️ BILATERAL BREAKOUT (NEUTRAL COIL)]"
                    trig_lbl = "Buy Trigger (> PDH)"
                    trig_val = pdh
                    trig_sub = "Upside Trigger"
                    tgt1_lbl = "Sell Trigger (< PDL)"
                    tgt1_val = pdl
                    tgt1_sub = "Downside Trigger"
                    tgt2_lbl = "Target Long (+1.5x ATR)"
                    tgt2_val = round(pdh + (1.5 * atr), 2)
                    tgt2_sub = f"+{exp_pct:.1f}%"
                    sl_lbl = "Target Short (-1.5x ATR)"
                    sl_val = round(pdl - (1.5 * atr), 2)
                    sl_sub = f"-{exp_pct:.1f}%"

                with st.container(border=True):
                    # Header row: Direction pill, ticker, name, tier, and sector
                    h1, h2 = st.columns([3.4, 1.2])
                    with h1:
                        st.markdown(f"#### {dir_badge} &nbsp; **{ticker}** · *{name}*")
                    with h2:
                        st.markdown(f"<div style='text-align:right;'><span class='pill-blue'>{tier}</span> <span class='pill-gray'>{sector}</span></div>", unsafe_allow_html=True)

                    # Setups and Compression Signals
                    st.markdown(f"**Setups Detected:** `{setups}` &nbsp;•&nbsp; **CPR Width:** `{cpr_p:.3f}%` &nbsp;•&nbsp; **Volume vs 20D Avg:** `{vol_r:.2f}x`")

                    # 6-Metric Responsive Execution Grid
                    m_cols = st.columns(6)
                    with m_cols[0]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">Closing Price</div>
                                <div class="spotlight-metric-val">₹{close_p:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:#64748b;">EOD Bar</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with m_cols[1]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">{trig_lbl}</div>
                                <div class="spotlight-metric-val" style="color:{dir_color};">₹{trig_val:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:{dir_color};">{trig_sub}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with m_cols[2]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">{tgt1_lbl}</div>
                                <div class="spotlight-metric-val" style="color:#2563eb;">₹{tgt1_val:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:#2563eb;">{tgt1_sub}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with m_cols[3]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">{tgt2_lbl}</div>
                                <div class="spotlight-metric-val" style="color:#7c3aed;">₹{tgt2_val:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:#7c3aed;">{tgt2_sub}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with m_cols[4]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">{sl_lbl}</div>
                                <div class="spotlight-metric-val" style="color:#dc2626;">₹{sl_val:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:#dc2626;">{sl_sub}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with m_cols[5]:
                        st.markdown(
                            f"""
                            <div class="spotlight-metric-card">
                                <div class="spotlight-metric-lbl">Daily ATR (14D)</div>
                                <div class="spotlight-metric-val">₹{atr:,.2f}</div>
                                <div class="spotlight-metric-sub" style="color:#0f172a;">{atr_pct:.2f}% Range</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    st.markdown(f"<div style='margin-top:10px; font-size:0.86rem; color:#475569;'>🎯 <strong>Action Plan:</strong> {rule}. Move stop loss to breakeven once Target 1 is hit.</div>", unsafe_allow_html=True)
        else:
            st.info("No candidates match your selected filters. Try broadening the Market Cap, Sector, or Bias filter above.")

        st.write("")

        # Consolidated High Conviction Table
        st.markdown("**📋 Consolidated High-Conviction Breakout Table:**")
        display_high = high_conv_df[[
            "Ticker", "Stock Name", "Market Cap Tier", "Direction", "Close",
            "PDH", "PDL", "Target_1_5x", "Stop_Loss", "Daily_ATR", "Estimated_Expansion_Pct", "Setup_Tags"
        ]].copy()

        st.dataframe(
            display_high,
            width="stretch",
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Stock Name": st.column_config.TextColumn("Stock Name", width="medium"),
                "Market Cap Tier": st.column_config.TextColumn("Tier", width="small"),
                "Direction": st.column_config.TextColumn("Bias", width="small"),
                "Close": st.column_config.NumberColumn("Close (₹)", format="₹%.2f"),
                "PDH": st.column_config.NumberColumn("PDH (Buy Level)", format="₹%.2f"),
                "PDL": st.column_config.NumberColumn("PDL (Sell Level)", format="₹%.2f"),
                "Target_1_5x": st.column_config.NumberColumn("Target 1 (₹)", format="₹%.2f"),
                "Stop_Loss": st.column_config.NumberColumn("Stop Loss (₹)", format="₹%.2f"),
                "Daily_ATR": st.column_config.NumberColumn("Daily ATR", format="₹%.2f"),
                "Estimated_Expansion_Pct": st.column_config.NumberColumn("Exp %", format="+%.1f%%"),
                "Setup_Tags": st.column_config.TextColumn("Setup Signals", width="large")
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Full Market Compression Radar (Stage 1 Candidates)
# ─────────────────────────────────────────────────────────────────────────────
with tab_compression:
    st.markdown('<div class="section-hdr">🔍 Stage 1 Compression Radar (NR7 / NR4 / Inside Bar / Narrow CPR)</div>', unsafe_allow_html=True)
    st.caption("Displays all non-penny stocks undergoing price and volatility compression. These stocks are building energy for imminent range expansion.")

    if comp_df.empty:
        st.info("No compression candidates detected in this scan batch. Adjust batch limit or universe filters.")
    else:
        rad_c1, rad_c2 = st.columns([1.5, 2.5])
        with rad_c1:
            comp_filter = st.selectbox(
                "Filter Compression Setup",
                ["All Compression Candidates", "NR7 Only (Narrowest in 7 Days)", "NR4 Only (Narrowest in 4 Days)", "Inside Bar Only", "Narrow CPR Only (<0.25%)"],
                index=0
            )
        with rad_c2:
            search_comp = st.text_input("🔍 Search Stock in Compression Radar", placeholder="Type ticker or stock name...", key="comp_search")

        filtered_radar = comp_df.copy()

        if comp_filter == "NR7 Only (Narrowest in 7 Days)":
            filtered_radar = filtered_radar[filtered_radar["NR7"] == True]
        elif comp_filter == "NR4 Only (Narrowest in 4 Days)":
            filtered_radar = filtered_radar[filtered_radar["NR4"] == True]
        elif comp_filter == "Inside Bar Only":
            filtered_radar = filtered_radar[filtered_radar["InsideBar"] == True]
        elif comp_filter == "Narrow CPR Only (<0.25%)":
            filtered_radar = filtered_radar[filtered_radar["Narrow_CPR"] == True]

        if search_comp.strip():
            q = search_comp.strip().upper()
            filtered_radar = filtered_radar[
                filtered_radar["Ticker"].str.contains(q, case=False, na=False) |
                filtered_radar["Stock Name"].str.contains(q, case=False, na=False)
            ]

        # Download Radar CSV Button
        radar_csv = filtered_radar[[
            "Ticker", "Stock Name", "Sector", "Market Cap Tier", "Close", "Range", "Range_Pct",
            "NR7", "NR4", "InsideBar", "CPR_Pct", "Narrow_CPR", "Vol_Ratio", "Setup_Tags"
        ]].to_csv(index=False)

        st.download_button(
            label=f"📥 Download Compression Radar Candidates (CSV)",
            data=radar_csv,
            file_name=f"investiq_compression_radar_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            width="stretch"
        )

        display_radar = filtered_radar[[
            "Ticker", "Stock Name", "Market Cap Tier", "Sector", "Close", "Range_Pct",
            "NR7", "NR4", "InsideBar", "CPR_Pct", "Vol_Ratio", "Setup_Tags"
        ]].copy()

        st.dataframe(
            display_radar,
            width="stretch",
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Stock Name": st.column_config.TextColumn("Stock Name", width="medium"),
                "Market Cap Tier": st.column_config.TextColumn("Tier", width="small"),
                "Sector": st.column_config.TextColumn("Sector", width="medium"),
                "Close": st.column_config.NumberColumn("Close (₹)", format="₹%.2f"),
                "Range_Pct": st.column_config.NumberColumn("Daily Range %", format="%.2f%%"),
                "NR7": st.column_config.CheckboxColumn("NR7"),
                "NR4": st.column_config.CheckboxColumn("NR4"),
                "InsideBar": st.column_config.CheckboxColumn("Inside Bar"),
                "CPR_Pct": st.column_config.NumberColumn("CPR Width %", format="%.3f%%"),
                "Vol_Ratio": st.column_config.NumberColumn("Vol Ratio", format="%.2fx"),
                "Setup_Tags": st.column_config.TextColumn("Compression Setups", width="large")
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Next-Morning Execution Playbook (9:15–10:15 AM)
# ─────────────────────────────────────────────────────────────────────────────
with tab_playbook:
    st.markdown('<div class="section-hdr">📋 Next-Morning Execution Playbook (9:15 – 10:15 AM)</div>', unsafe_allow_html=True)
    st.caption("Step-by-step disciplined morning rules to execute trades safely without getting trapped by opening volatility.")

    pb1, pb2 = st.columns(2)

    with pb1:
        st.markdown(
            """
            #### 🌅 1. The Opening 15–45 Minute Rule
            - **Do NOT place market orders at 9:15 AM.** Opening auction prices often produce fake wicks and erratic fills.
            - Allow the first 15 to 45 minutes (9:15 to 10:00 AM) to establish initial market direction and institutional volume.
            - Verify that the morning opening volume on the 5-minute chart is expanding and trending above its average.

            #### 🚀 2. Bullish Breakout Execution
            - **Setup:** Inside Bar / NR7 / Narrow CPR + Bullish Close / Volume Surge.
            - **Trigger:** Price crosses strictly **ABOVE Previous Day High (PDH)** on expanding volume.
            - **Entry:** Above PDH.
            - **Stop Loss:** Below VWAP or day's opening swing low.
            - **Target:** $1.5\\times$ to $2.0\\times$ Daily ATR (approx 2% to 5% move).
            """
        )

    with pb2:
        st.markdown(
            """
            #### 🔻 3. Bearish Breakdown Execution
            - **Setup:** Inside Bar / NR7 / Narrow CPR + Bearish Close / Heavy Distribution.
            - **Trigger:** Price breaks strictly **BELOW Previous Day Low (PDL)** on expanding volume.
            - **Entry:** Below PDL.
            - **Stop Loss:** Above VWAP or day's opening swing high.
            - **Target:** $1.5\\times$ to $2.0\\times$ Daily ATR.

            #### 🛡️ 4. Trailing Stop Loss & Profit Locking
            - When price reaches **Target 1 ($1.5\\times$ ATR)**, book 50% profits.
            - Move stop loss on remaining 50% position to **Cost / Breakeven**.
            - Trail the remainder using 5-minute swing lows or Supertrend/VWAP until target 2 ($2.0\\times$ ATR) is reached or 3:15 PM intraday square-off.
            """
        )

    st.markdown("---")
    st.markdown("#### 💡 Worked Example (From Strategy Document: Bajaj Finance)")
    st.info(
        """
        - **Evening Before:** Stock coils between ₹990 and ₹1,010 for 4–5 sessions (NR7 / Volatility contraction). Volume drops. Resistance is clearly established at ₹1,010.
        - **Next Morning at 9:15 AM:** Stock opens near ₹1,005 and climbs toward ₹1,010 with surging 15-minute volume.
        - **Breakout Trigger:** Price crosses ₹1,010. Because level was marked the night before, you execute with zero morning guesswork.
        - **The Expansion:** 2% expansion = ₹1,030; 3.5% expansion = ₹1,045. Short covering drives stock to ₹1,035–₹1,045 before the session ends.
        """
    )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Comprehensive User Guide & Strategy Manual
# ─────────────────────────────────────────────────────────────────────────────
with tab_guide:
    st.markdown('<div class="section-hdr">📖 Comprehensive Pre-Market Strategy Manual & User Guide</div>', unsafe_allow_html=True)
    st.caption("Complete reference guide, mathematical formulations, market regime rules, and platform condition breakdown.")

    # Section 1: Core Premise & Flow
    with st.expander("🎯 1. Core Premise & The 3-Stage EOD Filtering Funnel", expanded=True):
        st.markdown(
            """
            #### The Fundamental Law of Intraday Expansions
            > *"Big stock moves during the day rarely happen out of nowhere; their signals almost always show up the night before on the daily charts."*

            Instead of frantically reacting to morning news headlines or scanning random charts at 9:16 AM, this system does all the heavy analytical lifting **the evening before**.
            
            ```
            [ Eligible Listed Indian Equities (~2,500+ Non-Penny Stocks) ]
                                    │
                                    ▼
            ┌──────────────────────────────────────────────────────────────┐
            │ Stage 1: Technical & Price Compression (EOD 6:30–7:00 PM)    │
            │ • Setup 1: NR7 / NR4 (Narrowest Daily Range in 7 or 4 days)  │
            │ • Setup 2: Daily Inside Bar (Coiling within prior day's range│
            │ • Setup 3: Narrow Central Pivot Range (CPR Width < 0.25%)    │
            └──────────────────────────────┬───────────────────────────────┘
                                           │ Filtered to ~10–25 candidates
                                           ▼
            ┌──────────────────────────────────────────────────────────────┐
            │ Stage 2: Institutional Confirmation (EOD 7:30–8:00 PM)       │
            │ • Setup 4: Volume Surge (Traded Volume >= 1.5x 20-day Avg)   │
            │ • Setup 5: Strong Close (Top 20% Bullish or Bottom 20% Bear) │
            │ • Setup 6: Delivery Vol & F&O Open Interest Buildup (> 5%)   │
            └──────────────────────────────┬───────────────────────────────┘
                                           │ Filtered to 3–5 Priority Stocks
                                           ▼
            ┌──────────────────────────────────────────────────────────────┐
            │ Stage 3: Watchlist & Next-Day Trigger Prep (EOD 8:30 PM)     │
            │ • Previous Day High (PDH) = Buy Trigger Level                │
            │ • Previous Day Low (PDL) = Short Trigger Level               │
            │ • Target = 1.5x to 2.0x Daily ATR (2% to 5% expansion move)  │
            │ • Invalidation Stop Loss = Opening Swing Low or VWAP         │
            └──────────────────────────────┬───────────────────────────────┘
                                           │ Morning Open (9:15–10:15 AM)
                                           ▼
            ┌──────────────────────────────────────────────────────────────┐
            │ Execution: Wait 15–45 Min Opening Rules                      │
            │ • Breakout of Day 1 High/Low + Expanding 5-Min Volume        │
            │ • Trailing Stop Loss via ATR & 50% Profit Locking            │
            └──────────────────────────────────────────────────────────────┘
            ```
            """
        )

    # Section 2: Mathematical Formulations
    with st.expander("📐 2. Exact Mathematical Formulations & Screening Logic", expanded=False):
        st.markdown(
            """
            #### A. Narrow Range (NR7 & NR4)
            - $\\text{Range}_t = \\text{High}_t - \\text{Low}_t$
            - **NR4 Condition:** $\\text{Range}_t == \\min(\\text{Range}_{t-3}, \\text{Range}_{t-2}, \\text{Range}_{t-1}, \\text{Range}_t)$
            - **NR7 Condition:** $\\text{Range}_t == \\min(\\text{Range}_{t-6}, \\dots, \\text{Range}_t)$
            - *Rationale:* Volatility behaves like an accordion: extreme contraction leads directly into directional expansion.

            #### B. Daily Inside Bar Formation
            - **Condition:** $\\text{High}_t < \\text{High}_{t-1} \\quad \\text{AND} \\quad \\text{Low}_t > \\text{Low}_{t-1}$
            - *Rationale:* Price is completely contained inside the prior session's high-low extremes, representing temporary balance before explosive breakout.

            #### C. Central Pivot Range (CPR) Calculation
            Calculated for tomorrow using today's High ($H$), Low ($L$), and Close ($C$):
            - **Pivot Point ($P$):**
              $$\\text{Pivot } (P) = \\frac{H + L + C}{3}$$
            - **Bottom Central Pivot ($BC$):**
              $$\\text{Bottom Central } (BC) = \\frac{H + L}{2}$$
            - **Top Central Pivot ($TC$):**
              $$\\text{Top Central } (TC) = (P - BC) + P$$
            - **CPR Width %:**
              $$\\text{CPR Width \\%} = \\frac{|TC - BC|}{\\text{Close}} \\times 100$$
            - **Narrow CPR Trigger:** $\\text{CPR Width \\%} < 0.25\\%$.
            - *Rationale:* A razor-thin CPR band indicates that smart money has compressed prices, signaling a high-probability trending day ahead.

            #### D. Volume Surge & Candle Close Location
            - **Volume Surge:** $\\text{Volume}_t \\ge 1.5 \\times \\text{SMA}_{20}(\\text{Volume})$
            - **Candle Close Location:**
              $$\\text{Position} = \\frac{\\text{Close} - \\text{Low}}{\\text{High} - \\text{Low}}$$
              - Bullish Accumulation: $\\text{Position} \\ge 0.80$ (closes in top 20% of session's range)
              - Bearish Distribution: $\\text{Position} \\le 0.20$ (closes in bottom 20% of session's range)

            #### E. Average True Range (ATR) & Price Targets
            - True Range ($TR$):
              $$TR = \\max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$
            - Daily ATR ($ATR_{14}$): 14-period simple moving average of $TR$.
            - **Bullish Target 1:** $\\text{PDH} + (1.5 \\times ATR_{14})$
            - **Bullish Target 2:** $\\text{PDH} + (2.0 \\times ATR_{14})$
            - **Bearish Target 1:** $\\text{PDL} - (1.5 \\times ATR_{14})$
            - **Bearish Target 2:** $\\text{PDL} - (2.0 \\times ATR_{14})$
            """
        )

    # Section 3: India VIX & Market Regime Guide
    with st.expander("🌡️ 3. India VIX & Macro Regime Interpretation Matrix", expanded=False):
        st.markdown(
            """
            India VIX measures the market's expected 30-day volatility derived from out-of-the-money Nifty option premiums. Use the matrix below to calibrate your intraday playbook:

            | India VIX Range | Expected Market Behavior | Breakout Viability | Strategy Recommendation |
            |---|---|---|---|
            | **Below 12.0** | Quiet, compressed ranges, slow grinds | ⚠️ Low (High False Breakouts) | **Mean Reversion Mode**: Buy near support, sell near resistance. Avoid aggressive breakout chasing. |
            | **12.0 to 18.5** | Clean directional momentum, trending | 🟢 **Optimal (Prime Breakouts)** | **Directional Breakout Mode**: Ideal environment for 2% to 5% intraday expansions on NR7/Inside Bar triggers. |
            | **Above 20.0** | Erratic spikes, wide ranges, sharp reversals | 🔴 Risky (High Whipsaws) | **Defensive Volatility Mode**: Widen stop loss buffers, trade half (0.5x) position size, trail stops aggressively. |
            """
        )

    # Section 4: Platform Comparison (From Strategy Document)
    with st.expander("📊 4. Screener Platform Limitations & Why This Engine is Built", expanded=False):
        st.markdown(
            """
            Standard retail screeners (such as Tickertape) cannot execute this multi-stage quantitative funnel due to technical limitations:

            | # | Setup Condition in Strategy | Feasible in Tickertape? | Technical Limitation / Reason |
            |---|---|:---:|---|
            | **1** | **NR7 / NR4** (Narrowest range in 7 or 4 days) | ❌ **No** | Requires comparative daily high-low math across historical bars ($Range_t < Range_{t-1 \\dots t-6}$). Tickertape lacks custom candle math. |
            | **2** | **Daily Inside Bar** ($High < High_{-1}$ and $Low > Low_{-1}$) | ❌ **No** | Cannot compare current candle extremes against yesterday's candle extremes. |
            | **3** | **Narrow CPR (< 0.25%)** ($P$, $TC$, $BC$ spread) | ❌ **No** | CPR is not a native indicator on basic screeners, nor can users script Central Pivot formulas. |
            | **4** | **Delivery Volume Breakout** (>45% delivery + 1.5x vol) | ⚠️ **Partial** | Basic tools show total volume, but cannot evaluate candle closing position (top/bottom 20%). |
            | **5** | **F&O Open Interest Buildup** (Price vs OI % change) | ❌ **No** | Lacks integration with end-of-day futures open interest contract additions. |

            **💡 Solution:** This InvestIQ engine automates all 5 technical criteria natively in Python, scanning across **Large, Mid, and Small Cap Indian equities**.
            """
        )

    # Section 5: Step-by-Step User Instructions
    with st.expander("🚀 5. How to Use This Dashboard for Daily Trading", expanded=False):
        st.markdown(
            """
            1. **Select Universe & Non-Penny Filter:**
               - Choose between `All Listed Equities (No Penny Stocks)`, `Large Cap (Top 100)`, `Mid Cap (Rank 101–250)`, or `F&O Universe`.
               - Ensure Min Price is at least ₹100 to avoid illiquid micro-caps.
            2. **Inspect the India VIX Regime:**
               - Confirm whether the market is in **Optimal Trend Mode (VIX 12–18.5)** before taking aggressive breakouts.
            3. **Review Tab 1 (Priority Watchlist):**
               - Check the final **3 to 5 candidate cards** that passed both Stage 1 and Stage 2.
               - Note the exact **Trigger Level (PDH for Bullish, PDL for Bearish)**, **ATR Target**, and **Stop Loss**.
            4. **Export Your Pre-Market Plan:**
               - Click **`📥 Download Priority Watchlist & Triggers (CSV)`** to save your trading levels for the morning session.
            5. **Execute in the Morning (9:15–10:15 AM):**
               - Do NOT enter at 9:15 AM. Wait 15–45 minutes for market opening direction.
               - Enter strictly when price breaks the trigger level with expanding 5-minute volume.
               - Take 50% profits at Target 1 ($1.5\\times$ ATR) and move stop loss to breakeven!
            """
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Session Accuracy & Performance Audit
# ─────────────────────────────────────────────────────────────────────────────
with tab_audit:
    st.markdown('<div class="section-hdr">📊 Breakout Performance & Classification Accuracy Audit</div>', unsafe_allow_html=True)
    st.caption("Evaluates whichever candidates are currently in your **Consolidated High-Conviction Breakout Table** against the actual trading session bars, computing the Confusion Matrix, F1 Score, and trade outcomes.")
# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Session Accuracy & Performance Audit
# ─────────────────────────────────────────────────────────────────────────────
with tab_audit:
    st.markdown('<div class="section-hdr">📊 Breakout Performance & Classification Accuracy Audit</div>', unsafe_allow_html=True)
    st.caption("Evaluates whichever candidates are currently in your **Consolidated High-Conviction Breakout Table** against the actual trading session bars, computing the Confusion Matrix, F1 Score, and trade outcomes.")

    audit_ctl1, audit_ctl2 = st.columns([3.8, 1.4])
    with audit_ctl1:
        st.markdown(
            """
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; font-size:0.88rem; color:#334155;">
                📌 <strong>How it works:</strong> Click <strong>Run Accuracy Check</strong> after any market session (or half session). 
                The audit engine pulls the actual OHLCV bars for your current High-Conviction stocks, checks whether the PDH/PDL trigger was breached, whether the 1.5x ATR target was achieved (True Positive), or if the trade was safely filtered out (True Negative).
            </div>
            """,
            unsafe_allow_html=True
        )
    with audit_ctl2:
        st.write("")
        run_audit_btn = st.button("🚀 Run Accuracy Check", type="primary", key="btn_run_accuracy_audit", width="stretch")
    audit_ctl1, audit_ctl2 = st.columns([3.8, 1.4])
    with audit_ctl1:
        st.markdown(
            """
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; font-size:0.88rem; color:#334155;">
                📌 <strong>How it works:</strong> Click <strong>Run Accuracy Check</strong> after any market session (or half session). 
                The audit engine pulls the actual OHLCV bars for your current High-Conviction stocks, checks whether the PDH/PDL trigger was breached, whether the 1.5x ATR target was achieved (True Positive), or if the trade was safely filtered out (True Negative).
            </div>
            """,
            unsafe_allow_html=True
        )
    with audit_ctl2:
        st.write("")
        run_audit_btn = st.button("🚀 Run Accuracy Check", type="primary", key="btn_run_accuracy_audit", width="stretch")

    # Run audit logic on button click or default initial evaluation
    if run_audit_btn or "session_audit_result" not in st.session_state:
        with st.spinner("Analyzing high-conviction breakout candidates against session executions..."):
            audit_res = PreMarketEngine.evaluate_session_accuracy(high_conv_df, force_live=True)
            st.session_state["session_audit_result"] = audit_res
            if run_audit_btn:
                st.toast("✅ Breakout Accuracy Audit Completed!", icon="📊")

    audit_res = st.session_state.get("session_audit_result")

    if audit_res and audit_res.get("success"):
        total_eval = audit_res["total_evaluated"]
        tp = audit_res["tp"]
        fp = audit_res["fp"]
        tn = audit_res["tn"]
        fn = audit_res["fn"]
        prec = audit_res["precision"]
        rec = audit_res["recall"]
        f1 = audit_res["f1_score"]
        spec = audit_res["specificity"]
        cap_pres = audit_res["capital_preservation_rate"]
        avg_vol = audit_res["avg_vol_ratio"]
        avg_rng = audit_res["avg_range_pct"]
        is_trunc = audit_res["is_truncated_session"]
        audit_time = audit_res["audit_timestamp"]
        audit_table_df = audit_res["audit_df"]

        st.write("")

        # Session Context Alert
        if is_trunc:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.10); border-left: 5px solid #d97706; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong style="color:#b45309; font-size: 0.95rem;">⚠️ Truncated / Low-Volume Session Detected (Avg Vol: {avg_vol}x)</strong><br>
                    <span style="color:#334155; font-size: 0.88rem;">
                        Institutional volume was only <strong>{avg_vol}x ({(avg_vol*100):.0f}% of normal)</strong>, compressing average intraday range to just <strong>{avg_rng:.2f}%</strong>.
                        In truncated sessions, directional momentum to 1.5x ATR expansion targets is mathematically blocked by lack of block flow. The tape operated in pure <strong>Mean Reversion / Range-Bound Mode</strong>.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background: rgba(22, 163, 74, 0.10); border-left: 5px solid #16a34a; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong style="color:#15803d; font-size: 0.95rem;">🟢 Standard Trading Session Performance (Avg Vol: {avg_vol}x)</strong><br>
                    <span style="color:#334155; font-size: 0.88rem;">
                        Evaluated {total_eval} high-conviction breakout candidates against session trading bars as of {audit_time}.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Classification KPI Cards
        ak1, ak2, ak3, ak4, ak5 = st.columns(5)
        ak1.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#2563eb;">{total_eval}</div><div class="kpi-lbl">Setups Evaluated</div></div>', unsafe_allow_html=True)
        ak2.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{"#16a34a" if prec > 50 else "#dc2626"};">{prec:.1f}%</div><div class="kpi-lbl">Precision (Win Rate)</div></div>', unsafe_allow_html=True)
        ak3.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{"#16a34a" if f1 > 0.5 else "#dc2626"};">{f1:.3f}</div><div class="kpi-lbl">Session F1 Score</div></div>', unsafe_allow_html=True)
        ak4.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#16a34a;">{cap_pres:.1f}%</div><div class="kpi-lbl">Capital Saved (No-Trade)</div></div>', unsafe_allow_html=True)
        ak5.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#d97706;">{avg_vol}x</div><div class="kpi-lbl">Avg Session Volume</div></div>', unsafe_allow_html=True)

        st.write("")

        # Visual 2x2 Confusion Matrix & Formulas
        st.markdown("#### 🧮 2×2 Confusion Matrix & Classification Metrics")
        cm_col1, cm_col2 = st.columns(2)

        with cm_col1:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:16px;">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; text-align:center;">
                        <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#16a34a; font-family:monospace;">{tp}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#16a34a; text-transform:uppercase;">True Positive (TP)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">1.5x ATR Target Met</div>
                        </div>
                        <div style="background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#dc2626; font-family:monospace;">{fp}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#dc2626; text-transform:uppercase;">False Positive (FP)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Triggered but Faded/SL</div>
                        </div>
                        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#64748b; font-family:monospace;">{fn}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase;">False Negative (FN)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Missed Expansion Move</div>
                        </div>
                        <div style="background:#eff6ff; border:1px solid #93c5fd; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#2563eb; font-family:monospace;">{tn}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#2563eb; text-transform:uppercase;">True Negative (TN)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Rule Shielded Capital ({cap_pres:.0f}%)</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with cm_col2:
            st.markdown(
                f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px;">
                    <h5 style="margin:0 0 10px 0; font-size:1.0rem; color:#0f172a;">📐 Mathematical Formulation & Scores</h5>
                    <div style="font-size:0.88rem; color:#334155; line-height:1.7;">
                        • <strong>Precision:</strong> <code>TP / (TP + FP) = {tp} / ({tp} + {fp}) = {prec:.2f}%</code><br>
                        • <strong>Recall:</strong> <code>TP / (TP + FN) = {tp} / ({tp} + {fn}) = {rec:.2f}%</code><br>
                        • <strong>F1 Score:</strong> <code>2 &times; (Prec &times; Rec) / (Prec + Rec) = {f1:.3f}</code><br>
                        • <strong>Specificity (Noise Shield):</strong> <code>TN / (TN + FP) = {tn} / ({tn} + {fp}) = {spec:.2f}%</code><br>
                        • <strong>Capital Preservation Rate:</strong> <code>{tn} / {total_eval} = {cap_pres:.2f}%</code><br>
                    </div>
                    <div style="margin-top:12px; font-size:0.82rem; color:#64748b; background:#f8fafc; padding:8px 12px; border-radius:6px;">
                        💡 <em>Stage 3 Rule saved capital on {tn} of {total_eval} stocks where price never breached PDH/PDL.</em>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.write("")

        # Candidate-by-Candidate Trade Audit Table
        st.markdown(f"#### 📋 Candidate-by-Candidate Session Audit ({total_eval} Stocks from High-Conviction Table)")
        st.dataframe(
            audit_table_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Stock Name": st.column_config.TextColumn("Stock Name", width="medium"),
                "Tier": st.column_config.TextColumn("Tier", width="small"),
                "Bias": st.column_config.TextColumn("Bias", width="small"),
                "PDH": st.column_config.NumberColumn("PDH (₹)", format="₹%.2f"),
                "PDL": st.column_config.NumberColumn("PDL (₹)", format="₹%.2f"),
                "Session High": st.column_config.NumberColumn("High (₹)", format="₹%.2f"),
                "Session Low": st.column_config.NumberColumn("Low (₹)", format="₹%.2f"),
                "Session Close": st.column_config.NumberColumn("Close (₹)", format="₹%.2f"),
                "Range %": st.column_config.NumberColumn("Range %", format="%.2f%%"),
                "Vol Ratio": st.column_config.TextColumn("Vol vs Prior", width="small"),
                "Trigger Status": st.column_config.TextColumn("Trigger Breach?", width="medium"),
                "Outcome": st.column_config.TextColumn("Trade Outcome", width="large")
            }
        )

        st.write("")

        # Download Report Button
        rep_p = Path(__file__).resolve().parent.parent / "reports" / "breakout_accuracy_audit_20261108.html"
        if rep_p.exists():
            with open(rep_p, "r", encoding="utf-8") as f:
                html_export = f.read()
            st.download_button(
                label="📥 Download Detailed Audit Report (HTML)",
                data=html_export,
                file_name=f"investiq_breakout_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                type="secondary",
                width="stretch"
            )

        st.write("")

        # Deep-Dive Insights & Tactical Rules
        st.markdown("#### 💡 Tactical Playbook Adjustments & Audit Insights")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(
                r"""
                - **1. Volume Starvation Rule:** Directional breakout expansions require institutional volume ($\ge 1.5\times$). If morning volume on the 5-min chart is trending below $0.5\times$, **disable all breakout entry orders**.
                - **2. The Capital Preservation Shield:** The Stage 3 rule ("Never enter without trigger breach") automatically saved capital on all unbreached setups, preventing losing trades in a dead session.
                """
            )
        with t_col2:
            st.markdown(
                r"""
                - **3. Low Range Ceilings:** Intraday ranges in half sessions are capped at $\le 0.5\times$ ATR (under 1.0%), making $1.5\times$ ATR expansion targets mathematically unattainable.
                - **4. Switch to Mean Reversion:** During Muhurat, special weekend, or truncated sessions, favor mean-reversion strategies (fading the edges of Narrow CPR / PDH / PDL) rather than chasing breakouts.
                """
            )
    else:
        st.warning("No High-Conviction candidates available to audit. Run the screener in Tab 1 first.")



    # Run audit logic on button click or default initial evaluation
    if run_audit_btn or "session_audit_result" not in st.session_state:
        with st.spinner("Analyzing high-conviction breakout candidates against session executions..."):
            audit_res = PreMarketEngine.evaluate_session_accuracy(high_conv_df, force_live=True)
            st.session_state["session_audit_result"] = audit_res
            if run_audit_btn:
                st.toast("✅ Breakout Accuracy Audit Completed!", icon="📊")

    audit_res = st.session_state.get("session_audit_result")

    if audit_res and audit_res.get("success"):
        total_eval = audit_res["total_evaluated"]
        tp = audit_res["tp"]
        fp = audit_res["fp"]
        tn = audit_res["tn"]
        fn = audit_res["fn"]
        prec = audit_res["precision"]
        rec = audit_res["recall"]
        f1 = audit_res["f1_score"]
        spec = audit_res["specificity"]
        cap_pres = audit_res["capital_preservation_rate"]
        avg_vol = audit_res["avg_vol_ratio"]
        avg_rng = audit_res["avg_range_pct"]
        is_trunc = audit_res["is_truncated_session"]
        audit_time = audit_res["audit_timestamp"]
        audit_table_df = audit_res["audit_df"]

        st.write("")

        # Session Context Alert
        if is_trunc:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.10); border-left: 5px solid #d97706; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong style="color:#b45309; font-size: 0.95rem;">⚠️ Truncated / Low-Volume Session Detected (Avg Vol: {avg_vol}x)</strong><br>
                    <span style="color:#334155; font-size: 0.88rem;">
                        Institutional volume was only <strong>{avg_vol}x ({(avg_vol*100):.0f}% of normal)</strong>, compressing average intraday range to just <strong>{avg_rng:.2f}%</strong>.
                        In truncated sessions, directional momentum to 1.5x ATR expansion targets is mathematically blocked by lack of block flow. The tape operated in pure <strong>Mean Reversion / Range-Bound Mode</strong>.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background: rgba(22, 163, 74, 0.10); border-left: 5px solid #16a34a; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong style="color:#15803d; font-size: 0.95rem;">🟢 Standard Trading Session Performance (Avg Vol: {avg_vol}x)</strong><br>
                    <span style="color:#334155; font-size: 0.88rem;">
                        Evaluated {total_eval} high-conviction breakout candidates against session trading bars as of {audit_time}.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Classification KPI Cards
        ak1, ak2, ak3, ak4, ak5 = st.columns(5)
        ak1.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#2563eb;">{total_eval}</div><div class="kpi-lbl">Setups Evaluated</div></div>', unsafe_allow_html=True)
        ak2.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{"#16a34a" if prec > 50 else "#dc2626"};">{prec:.1f}%</div><div class="kpi-lbl">Precision (Win Rate)</div></div>', unsafe_allow_html=True)
        ak3.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{"#16a34a" if f1 > 0.5 else "#dc2626"};">{f1:.3f}</div><div class="kpi-lbl">Session F1 Score</div></div>', unsafe_allow_html=True)
        ak4.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#16a34a;">{cap_pres:.1f}%</div><div class="kpi-lbl">Capital Saved (No-Trade)</div></div>', unsafe_allow_html=True)
        ak5.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#d97706;">{avg_vol}x</div><div class="kpi-lbl">Avg Session Volume</div></div>', unsafe_allow_html=True)

        st.write("")

        # Visual 2x2 Confusion Matrix & Formulas
        st.markdown("#### 🧮 2×2 Confusion Matrix & Classification Metrics")
        cm_col1, cm_col2 = st.columns(2)

        with cm_col1:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:16px;">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; text-align:center;">
                        <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#16a34a; font-family:monospace;">{tp}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#16a34a; text-transform:uppercase;">True Positive (TP)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">1.5x ATR Target Met</div>
                        </div>
                        <div style="background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#dc2626; font-family:monospace;">{fp}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#dc2626; text-transform:uppercase;">False Positive (FP)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Triggered but Faded/SL</div>
                        </div>
                        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#64748b; font-family:monospace;">{fn}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase;">False Negative (FN)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Missed Expansion Move</div>
                        </div>
                        <div style="background:#eff6ff; border:1px solid #93c5fd; border-radius:8px; padding:14px;">
                            <div style="font-size:2rem; font-weight:800; color:#2563eb; font-family:monospace;">{tn}</div>
                            <div style="font-size:0.75rem; font-weight:700; color:#2563eb; text-transform:uppercase;">True Negative (TN)</div>
                            <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">Rule Shielded Capital ({cap_pres:.0f}%)</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with cm_col2:
            st.markdown(
                f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px;">
                    <h5 style="margin:0 0 10px 0; font-size:1.0rem; color:#0f172a;">📐 Mathematical Formulation & Scores</h5>
                    <div style="font-size:0.88rem; color:#334155; line-height:1.7;">
                        • <strong>Precision:</strong> <code>TP / (TP + FP) = {tp} / ({tp} + {fp}) = {prec:.2f}%</code><br>
                        • <strong>Recall:</strong> <code>TP / (TP + FN) = {tp} / ({tp} + {fn}) = {rec:.2f}%</code><br>
                        • <strong>F1 Score:</strong> <code>2 &times; (Prec &times; Rec) / (Prec + Rec) = {f1:.3f}</code><br>
                        • <strong>Specificity (Noise Shield):</strong> <code>TN / (TN + FP) = {tn} / ({tn} + {fp}) = {spec:.2f}%</code><br>
                        • <strong>Capital Preservation Rate:</strong> <code>{tn} / {total_eval} = {cap_pres:.2f}%</code><br>
                    </div>
                    <div style="margin-top:12px; font-size:0.82rem; color:#64748b; background:#f8fafc; padding:8px 12px; border-radius:6px;">
                        💡 <em>Stage 3 Rule saved capital on {tn} of {total_eval} stocks where price never breached PDH/PDL.</em>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.write("")

        # Candidate-by-Candidate Trade Audit Table
        st.markdown(f"#### 📋 Candidate-by-Candidate Session Audit ({total_eval} Stocks from High-Conviction Table)")
        st.dataframe(
            audit_table_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Stock Name": st.column_config.TextColumn("Stock Name", width="medium"),
                "Tier": st.column_config.TextColumn("Tier", width="small"),
                "Bias": st.column_config.TextColumn("Bias", width="small"),
                "PDH": st.column_config.NumberColumn("PDH (₹)", format="₹%.2f"),
                "PDL": st.column_config.NumberColumn("PDL (₹)", format="₹%.2f"),
                "Session High": st.column_config.NumberColumn("High (₹)", format="₹%.2f"),
                "Session Low": st.column_config.NumberColumn("Low (₹)", format="₹%.2f"),
                "Session Close": st.column_config.NumberColumn("Close (₹)", format="₹%.2f"),
                "Range %": st.column_config.NumberColumn("Range %", format="%.2f%%"),
                "Vol Ratio": st.column_config.TextColumn("Vol vs Prior", width="small"),
                "Trigger Status": st.column_config.TextColumn("Trigger Breach?", width="medium"),
                "Outcome": st.column_config.TextColumn("Trade Outcome", width="large")
            }
        )

        st.write("")

        # Download Report Button
        rep_p = Path(__file__).resolve().parent.parent / "reports" / "breakout_accuracy_audit_20261108.html"
        if rep_p.exists():
            with open(rep_p, "r", encoding="utf-8") as f:
                html_export = f.read()
            st.download_button(
                label="📥 Download Detailed Audit Report (HTML)",
                data=html_export,
                file_name=f"investiq_breakout_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                type="secondary",
                width="stretch"
            )

        st.write("")

        # Deep-Dive Insights & Tactical Rules
        st.markdown("#### 💡 Tactical Playbook Adjustments & Audit Insights")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(
                r"""
                - **1. Volume Starvation Rule:** Directional breakout expansions require institutional volume ($\ge 1.5\times$). If morning volume on the 5-min chart is trending below $0.5\times$, **disable all breakout entry orders**.
                - **2. The Capital Preservation Shield:** The Stage 3 rule ("Never enter without trigger breach") automatically saved capital on all unbreached setups, preventing losing trades in a dead session.
                """
            )
        with t_col2:
            st.markdown(
                r"""
                - **3. Low Range Ceilings:** Intraday ranges in half sessions are capped at $\le 0.5\times$ ATR (under 1.0%), making $1.5\times$ ATR expansion targets mathematically unattainable.
                - **4. Switch to Mean Reversion:** During Muhurat, special weekend, or truncated sessions, favor mean-reversion strategies (fading the edges of Narrow CPR / PDH / PDL) rather than chasing breakouts.
                """
            )
    else:
        st.warning("No High-Conviction candidates available to audit. Run the screener in Tab 1 first.")


