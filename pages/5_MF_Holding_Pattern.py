# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import io
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from utils.page_utils import merged_holdings, render_sidebar, require_auth
from services.mf_holding_service import MFHoldingService
from services.mf_disclosure_service import MFDisclosureService
from engines.mf_consensus_engine import MFConsensusEngine

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MF Institutional Engine & Holding Pattern | InvestIQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
render_sidebar()

# Ensure database tables exist
MFDisclosureService.ensure_tables()

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS Styling (Consistent with InvestIQ Glassmorphic Theme)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .mf-hero {
        background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(168,85,247,0.12) 50%, rgba(236,72,153,0.10) 100%);
        border: 1px solid rgba(99,102,241,0.30);
        border-radius: 20px;
        padding: 26px 30px 22px 30px;
        margin-bottom: 22px;
        backdrop-filter: blur(14px);
    }
    .mf-hero h1 { margin: 0 0 6px 0; font-size: 2.0rem; color: #1e1b4b; font-weight: 800; }
    .mf-hero p  { margin: 0; color: #475569; font-size: 0.96rem; line-height: 1.5; }

    .kpi-card {
        background: rgba(255,255,255,0.65);
        border: 1px solid rgba(255,255,255,0.8);
        border-radius: 16px;
        padding: 16px 18px;
        backdrop-filter: blur(14px);
        text-align: center;
        box-shadow: 0 6px 20px rgba(99,102,241,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(99,102,241,0.12);
    }
    .kpi-val  { font-size: 1.85rem; font-weight: 800; color: #4f46e5; line-height: 1.1; }
    .kpi-lbl  { font-size: 0.82rem; color: #475569; font-weight: 600; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.04em; }

    .guide-box {
        background: rgba(255, 255, 255, 0.70);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
    }
    .guide-step {
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    .guide-badge {
        background: #6366f1;
        color: #ffffff;
        font-weight: 800;
        border-radius: 50%;
        width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        margin-right: 12px;
        flex-shrink: 0;
    }

    .pill-green  { background:rgba(34,197,94,0.15); color:#16a34a; border:1px solid rgba(34,197,94,0.35); border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:700; }
    .pill-red    { background:rgba(239,68,68,0.15);  color:#dc2626; border:1px solid rgba(239,68,68,0.35);  border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:700; }
    .pill-blue   { background:rgba(99,102,241,0.15); color:#4f46e5; border:1px solid rgba(99,102,241,0.35); border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:700; }
    .pill-amber  { background:rgba(245,158,11,0.15); color:#d97706; border:1px solid rgba(245,158,11,0.35); border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:700; }
    .pill-purple { background:rgba(168,85,247,0.15); color:#9333ea; border:1px solid rgba(168,85,247,0.35); border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:700; }
    .pill-gray   { background:rgba(100,116,139,0.12);color:#475569; border:1px solid rgba(100,116,139,0.25);border-radius:6px; padding:3px 9px; margin:2px; display:inline-block; font-size:0.80rem; font-weight:600; }

    .action-card {
        background: rgba(255,255,255,0.7);
        border: 1px solid rgba(226,232,240,0.9);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    }
    .section-hdr {
        font-size: 1.15rem; font-weight: 700; color: #1e293b;
        border-left: 4px solid #6366f1; padding-left: 12px;
        margin: 20px 0 14px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Hero Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="mf-hero">
        <h1>📊 Mutual Fund Ingestion, Benchmarking & Recommendation Engine</h1>
        <p>
            An institutional analytics engine for ingestion of official AMC monthly portfolio disclosures, 
            consolidated consensus calculations, temporal month-over-month delta tracking, portfolio gap analysis, 
            and an interactive rebalancing simulator.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# USER GUIDE: Interactive Executive Instructions & Methodology
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📖 User Guide: Architecture, Workflow & Metric Interpretation", expanded=False):
    st.markdown(
        """
        <div class="guide-box">
            <h3 style="margin-top:0; color:#4338ca; font-size:1.25rem;">🚀 How to Use the Mutual Fund Ingestion & Benchmarking Engine</h3>
            
            <div class="guide-step">
                <div class="guide-badge">1</div>
                <div>
                    <strong>Data Ingestion & Local Archiving:</strong><br/>
                    Click <em>"Fetch Latest Disclosures"</em> to download official portfolio spreadsheets across top Indian AMCs 
                    (HDFC, SBI, ICICI Prudential, Kotak, Axis, Nippon India, Parag Parikh, Mirae Asset). 
                    Raw files are stored in <code>data/raw_disclosures/YYYY_MM/</code> for historical auditing. You can also upload any custom AMC spreadsheet (<code>.xlsx</code> / <code>.csv</code>).
                </div>
            </div>

            <div class="guide-step">
                <div class="guide-badge">2</div>
                <div>
                    <strong>Institutional Consensus & Hierarchy (Market Cap → Sector → Stock):</strong><br/>
                    Explore institutional conviction across Large Cap, Mid Cap, Small Cap, and Flexi Cap schemes. 
                    Stocks are normalized via <strong>ISIN</strong> with two key weight metrics:
                    <ul>
                        <li><strong>Confidence Score (C<sub>s</sub>):</strong> Percentage of active mutual funds holding the stock in that category.</li>
                        <li><strong>Average Across All Funds:</strong> Mean weight across all schemes (including 0% for non-holders).</li>
                        <li><strong>Conviction Weight:</strong> Mean allocation only among schemes that actively hold the stock.</li>
                    </ul>
                </div>
            </div>

            <div class="guide-step">
                <div class="guide-badge">3</div>
                <div>
                    <strong>Month-over-Month Delta Tracking (Sentiment Engine):</strong><br/>
                    Tracks how professional fund managers shifted allocations between <code>T<sub>0</sub></code> (March 2026) and <code>T<sub>-1</sub></code> (February 2026):
                    <ul>
                        <li><span class="pill-green">🚀 Aggressive Accumulation:</span> Weight change <strong>&Delta;W > +0.5%</strong> AND Confidence change <strong>&Delta;C > +10%</strong>.</li>
                        <li><span class="pill-green">🟢 Modest Buying:</span> Weight change <strong>&Delta;W > 0%</strong> AND Confidence change <strong>&Delta;C &ge; 0%</strong>.</li>
                        <li><span class="pill-amber">🟡 Profit Booking / Trimming:</span> Weight change <strong>&Delta;W < 0%</strong>.</li>
                        <li><span class="pill-red">🔴 Complete Exit:</span> Confidence dropped to 0% from a prior non-zero holding.</li>
                    </ul>
                </div>
            </div>

            <div class="guide-step">
                <div class="guide-badge">4</div>
                <div>
                    <strong>Portfolio Gap & Misalignment Engine:</strong><br/>
                    Compares your personal stock portfolio against mutual fund market consensus:
                    <ul>
                        <li><span class="pill-green">Consensus Aligned:</span> Stocks you hold that also enjoy high mutual fund conviction.</li>
                        <li><span class="pill-amber">Institutional Misses (Gaps):</span> High institutional confidence (&ge; 50-60%) across top funds, but <strong>0% in your portfolio</strong>.</li>
                        <li><span class="pill-red">Unbacked Bets:</span> Stocks where you hold high exposure (> 3-5%), but institutional confidence is under 10-15%.</li>
                        <li><strong>Active Weight Diff:</strong> <code>Your Weight % &minus; MF Consensus Weight %</code> (Overweight > +5%, Underweight < -3%).</li>
                    </ul>
                </div>
            </div>

            <div class="guide-step">
                <div class="guide-badge">5</div>
                <div>
                    <strong>Interactive Rebalancing Simulator:</strong><br/>
                    Use the interactive slider to model rebalancing your portfolio towards institutional consensus. 
                    Real-time formulas calculate the reduction in <strong>Single-Stock Concentration Risk (Herfindahl-Hirschman Index / Top 5 Weight)</strong>, 
                    <strong>Active Variance reduction</strong>, and precise rupee capital shifts (Buy ₹ / Sell ₹).
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Adhoc Trigger & Data Ingestion Bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">📥 Step 1: AMC Disclosure Downloader & Data Ingestion</div>', unsafe_allow_html=True)

ingest_col1, ingest_col2, ingest_col3 = st.columns([2, 1.2, 1.2])

with ingest_col1:
    st.caption(
        "Downloads and ingests institutional portfolio disclosures for all major Indian AMCs — "
        "HDFC, ICICI Pru, SBI, Mirae, Axis, Kotak, Nippon India, DSP, UTI, Aditya Birla SL, Franklin, PPFAS, Quant, Canara Robeco, Tata, and Motilal Oswal. "
        "Covers Large Cap, Mid Cap, Small Cap, Flexi Cap, ELSS, and Thematic/Sectoral funds."
    )
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("⬇️ Download All Disclosures", type="primary", use_container_width=True,
                     help="Ingest portfolio holdings for 45+ schemes across all SEBI categories (Large/Mid/Small/Flexi/ELSS/Sectoral) for T0 + T-1 periods"):
            with st.spinner("📡 Downloading AMFI scheme master & ingesting portfolio disclosures for all Indian AMCs..."):
                res = MFDisclosureService.seed_default_disclosures(overwrite=True)
                cats = ", ".join(res.get('categories_covered', [])[:4])
                amcs = len(res.get('amcs_covered', []))
                st.success(
                    f"✅ Ingested **{res['schemes_count']} schemes** across **{amcs} AMCs** "
                    f"({res['holdings_count']} equity positions) | Categories: {cats}... | "
                    f"Snapshots: {', '.join(res['snapshots'])}"
                )
                st.rerun()

    with btn_col2:
        if st.button("🔄 Sync My Portfolio", use_container_width=True,
                     help="Synchronize user holdings from Holdings page with ISIN mappings for gap analysis"):
            with st.spinner("Mapping user portfolio holdings to standard ISIN codes..."):
                count = MFDisclosureService.sync_user_portfolio()
                st.success(f"✅ Synced {count} user holdings for gap analysis!")
                st.rerun()

    with btn_col3:
        if st.button("📋 Refresh AMFI Scheme List", use_container_width=True,
                     help="Fetch fresh AMFI NAVAll.txt to update the complete scheme master (15,000+ schemes)"):
            with st.spinner("📡 Fetching AMFI scheme master from amfiindia.com..."):
                # Force refresh cache
                cache_path = __import__('pathlib').Path(__file__).resolve().parent.parent / "data" / "amfi_scheme_master.json"
                if cache_path.exists():
                    cache_path.unlink()
                summary = MFDisclosureService.get_amfi_scheme_summary()
                st.success(
                    f"✅ AMFI Scheme Master refreshed: **{summary.get('total', 0):,} total schemes**, "
                    f"**{summary.get('equity_count', 0):,} equity-oriented schemes** across all Indian AMCs"
                )
                st.rerun()

with ingest_col2:
    available_snaps = MFConsensusEngine.get_snapshots()
    snap_options = [s["month_str"] for s in available_snaps] if available_snaps else ["2026-03", "2026-02"]
    selected_snapshot = st.selectbox("📅 Snapshot Period", options=snap_options, index=0, help="Select disclosure month")

with ingest_col3:
    categories = ["All", "Large Cap", "Mid Cap", "Small Cap", "Flexi/Multi Cap", "ELSS", "Thematic/Sectoral"]
    selected_category = st.selectbox("🎯 Fund Category", options=categories, index=0, help="Filter consensus by SEBI fund peer group")

# ─── AMFI Scheme Browser ────────────────────────────────────────────────────
with st.expander("📊 AMFI Scheme Universe Browser (Live — All Indian MF Schemes)", expanded=False):
    st.markdown(
        "Browse the **complete AMFI scheme universe** downloaded live from "
        "`amfiindia.com/spages/NAVAll.txt`. Covers all open-ended & closed-ended schemes "
        "across all Indian AMCs."
    )
    with st.spinner("Loading AMFI scheme master..."):
        amfi_summary = MFDisclosureService.get_amfi_scheme_summary()

    if amfi_summary.get("total", 0) > 0:
        sm_c1, sm_c2, sm_c3, sm_c4 = st.columns(4)
        sm_c1.metric("Total Schemes", f"{amfi_summary['total']:,}")
        sm_c2.metric("Equity-Oriented", f"{amfi_summary['equity_count']:,}")
        sm_c3.metric("AMCs Tracked", f"{len(amfi_summary['by_amc'])}")
        sm_c4.metric("Categories", f"{len(amfi_summary['by_category'])}")

        st.markdown("**Scheme Count by SEBI Category:**")
        cat_df = pd.DataFrame(list(amfi_summary["by_category"].items()), columns=["Category", "Scheme Count"]).sort_values("Scheme Count", ascending=False)
        st.dataframe(cat_df, use_container_width=True, hide_index=True,
                     column_config={"Scheme Count": st.column_config.ProgressColumn("Scheme Count", format="%d", min_value=0, max_value=int(cat_df["Scheme Count"].max()))})

        st.markdown("**Top AMCs by Scheme Count:**")
        amc_df = pd.DataFrame(list(amfi_summary["by_amc"].items()), columns=["AMC", "Scheme Count"]).head(20)
        st.dataframe(amc_df, use_container_width=True, hide_index=True)
    else:
        st.info("Click **'Refresh AMFI Scheme List'** above to fetch the live scheme master from AMFI.")

# ─── Custom File Uploader ────────────────────────────────────────────────────
with st.expander("📤 Upload Custom AMC Monthly Disclosure Spreadsheet (.xlsx, .xls, .csv)", expanded=False):
    st.markdown(
        "Upload any official monthly portfolio disclosure spreadsheet from an AMC (HDFC, SBI, ICICI Prudential, etc.). "
        "The dynamic parser automatically extracts equity holdings, resolves ISINs, "
        "normalizes company names, and strips cash/derivatives/debt instruments."
    )
    up_c1, up_c2, up_c3, up_c4 = st.columns(4)
    with up_c1:
        up_scheme_name = st.text_input("Scheme Name", value="HDFC Flexi Cap Fund")
    with up_c2:
        up_amc_name = st.text_input("AMC Name", value="HDFC Mutual Fund")
    with up_c3:
        up_cat = st.selectbox("SEBI Category", options=["Large Cap", "Mid Cap", "Small Cap", "Flexi/Multi Cap", "ELSS", "Thematic/Sectoral", "Hybrid"], index=3)
    with up_c4:
        up_date = st.date_input("Disclosure Date", value=datetime(2026, 3, 31))

    custom_file = st.file_uploader("Select Spreadsheet", type=["xlsx", "xls", "csv"], key="custom_amc_upload")
    if custom_file and st.button("⬆️ Parse & Store Disclosure", type="primary"):
        with st.spinner("Executing dynamic spreadsheet parser and normalizer..."):
            count, errs = MFDisclosureService.parse_uploaded_disclosure(
                custom_file,
                scheme_name=up_scheme_name,
                amc_name=up_amc_name,
                category=up_cat,
                snapshot_date=datetime(up_date.year, up_date.month, up_date.day)
            )
            if count > 0:
                st.success(f"✅ Successfully extracted and stored {count} equity positions for {up_scheme_name}!")
                st.rerun()
            for err in errs:
                st.error(err)

# Auto-seed if database is currently empty
if not available_snaps:
    st.info("📋 Initializing AMC disclosure data for 45+ Indian equity schemes...")
    MFDisclosureService.seed_default_disclosures(overwrite=False)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Fetch Core Engine Datasets
# ─────────────────────────────────────────────────────────────────────────────
consensus_df = MFConsensusEngine.get_consensus_metrics(
    snapshot_month=selected_snapshot,
    category_filter=selected_category
)
deltas_df = MFConsensusEngine.get_temporal_deltas()
gap_data = MFConsensusEngine.get_portfolio_gap_analysis()
nba_actions = MFConsensusEngine.get_next_best_actions()

# ─────────────────────────────────────────────────────────────────────────────
# Executive KPI Banner Strip
# ─────────────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

total_schemes_count = consensus_df["Total Schemes"].iloc[0] if not consensus_df.empty else len(available_snaps)
stocks_in_consensus = len(consensus_df) if not consensus_df.empty else 0
misses_count = len(gap_data.get("misses", []))
unbacked_count = len(gap_data.get("unbacked", []))
buy_candidates_count = len([a for a in nba_actions if a["type"] == "Buy Candidate"])

kpi_strip = [
    (str(total_schemes_count), "Schemes Tracked"),
    (str(stocks_in_consensus), "Consensus Stocks"),
    (str(misses_count), "Institutional Misses"),
    (str(unbacked_count), "Unbacked Bets"),
    (str(buy_candidates_count), "Buy Candidates"),
]

for col, (val, lbl) in zip([k1, k2, k3, k4, k5], kpi_strip):
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-val">{val}</div><div class="kpi-lbl">{lbl}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# 6 INTERACTIVE TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_consensus, tab_delta, tab_gap, tab_nba, tab_sim, tab_legacy = st.tabs([
    "🏛️ Institutional Consensus & Hierarchy",
    "⏱️ Month-over-Month Delta (Sentiment)",
    "🎯 Portfolio Gap & Alignment",
    "⚡ Next Best Actions (Recommendations)",
    "🎛️ Rebalancing Simulator",
    "📁 Legacy Sector Patterns"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Institutional Consensus & Hierarchy
# ─────────────────────────────────────────────────────────────────────────────
with tab_consensus:
    st.markdown('<div class="section-hdr">Institutional Consensus: Market Cap Tier ➔ Sector ➔ Stock</div>', unsafe_allow_html=True)
    st.caption("Consolidated consensus metrics computed across official AMC disclosures. Filterable by Tier, Sector, and Search query.")

    if consensus_df.empty:
        st.warning("No consensus data available for the selected filter. Click 'Fetch Latest Disclosures' above.")
    else:
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        with c1:
            tier_filter = st.selectbox("Filter Market Cap Tier", ["All Tiers"] + sorted(consensus_df["Market Cap Tier"].unique().tolist()), index=0)
        with c2:
            all_sec = sorted(consensus_df["Sector"].unique().tolist())
            sec_filter = st.selectbox("Filter Sector", ["All Sectors"] + all_sec, index=0)
        with c3:
            search_stock = st.text_input("🔍 Search Stock or ISIN", placeholder="Type Reliance, HDFC, INE...", key="cons_search")

        filtered_cons = consensus_df.copy()
        if tier_filter != "All Tiers":
            filtered_cons = filtered_cons[filtered_cons["Market Cap Tier"] == tier_filter]
        if sec_filter != "All Sectors":
            filtered_cons = filtered_cons[filtered_cons["Sector"] == sec_filter]
        if search_stock.strip():
            q = search_stock.strip().upper()
            filtered_cons = filtered_cons[
                filtered_cons["Ticker"].str.contains(q, case=False, na=False) |
                filtered_cons["Stock Name"].str.contains(q, case=False, na=False) |
                filtered_cons["ISIN"].str.contains(q, case=False, na=False)
            ]

        # Top 15 Holdings Chart
        top15_cons = filtered_cons.head(15).copy()
        if not top15_cons.empty:
            cons_chart = (
                alt.Chart(top15_cons)
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                .encode(
                    y=alt.Y("Ticker:N", sort="-x", title="Stock Ticker"),
                    x=alt.X("Avg Weight All Funds %:Q", title="Average Allocation Across All Funds (%)"),
                    color=alt.Color(
                        "Peer Confidence %:Q",
                        scale=alt.Scale(scheme="purpleblue", domain=[20, 100]),
                        legend=alt.Legend(title="Peer Confidence %", labelColor="#000", titleColor="#000")
                    ),
                    tooltip=[
                        "Stock Name:N",
                        "Ticker:N",
                        "Sector:N",
                        "Market Cap Tier:N",
                        alt.Tooltip("Peer Confidence %:Q", format=".1f"),
                        alt.Tooltip("Avg Weight All Funds %:Q", format=".2f", title="All Funds Avg %"),
                        alt.Tooltip("Conviction Weight %:Q", format=".2f", title="Conviction Weight %"),
                        "Schemes Holding:Q"
                    ]
                )
                .properties(height=380, title=f"Top Institutional Consensus Stocks — {selected_category} ({selected_snapshot})")
            )
            st.altair_chart(cons_chart, use_container_width=True)

        # Consensus Dataframe with Styled Badges
        st.markdown("**Consolidated Institutional Consensus Table:**")
        display_cons = filtered_cons[[
            "Ticker", "Stock Name", "Market Cap Tier", "Sector", "Peer Confidence %",
            "Schemes Holding", "Total Schemes", "Avg Weight All Funds %", "Conviction Weight %", "ISIN"
        ]].copy()

        st.dataframe(
            display_cons,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Peer Confidence %": st.column_config.ProgressColumn("Peer Confidence %", format="%.1f%%", min_value=0, max_value=100),
                "Avg Weight All Funds %": st.column_config.NumberColumn("All Funds Avg %", format="%.2f%%"),
                "Conviction Weight %": st.column_config.NumberColumn("Conviction Weight %", format="%.2f%%"),
                "Schemes Holding": st.column_config.NumberColumn("Holding Funds", format="%d"),
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Month-over-Month Delta (Sentiment Engine)
# ─────────────────────────────────────────────────────────────────────────────
with tab_delta:
    st.markdown('<div class="section-hdr">Temporal Sentiment Engine: Month-over-Month Delta (T₀ vs T₋₁)</div>', unsafe_allow_html=True)
    st.caption("Measures how fund manager sentiment changes month-over-month through Weight Delta (ΔW) and Confidence Delta (ΔC).")

    if deltas_df.empty:
        st.info("At least two monthly disclosure snapshots are required for delta tracking. Click 'Fetch Latest Disclosures' to load T0 and T-1 data.")
    else:
        d_c1, d_c2 = st.columns([1.5, 2])
        with d_c1:
            sentiment_options = ["All Sentiments", "Aggressive Accumulation", "Modest Buying", "Profit Booking / Trimming", "Complete Exit"]
            selected_sentiment = st.selectbox("Filter Sentiment Classification", sentiment_options, index=0)
        with d_c2:
            search_delta = st.text_input("🔍 Search Stock in Delta Engine", placeholder="Type stock name or ticker...", key="delta_search")

        filtered_deltas = deltas_df.copy()
        if selected_sentiment != "All Sentiments":
            filtered_deltas = filtered_deltas[filtered_deltas["Sentiment"] == selected_sentiment]
        if search_delta.strip():
            q = search_delta.strip().upper()
            filtered_deltas = filtered_deltas[
                filtered_deltas["Ticker"].str.contains(q, case=False, na=False) |
                filtered_deltas["Stock Name"].str.contains(q, case=False, na=False)
            ]

        # Delta Bar Chart (Top accumulation & trimming)
        top_deltas = pd.concat([
            filtered_deltas.nlargest(8, "Delta_Weight"),
            filtered_deltas.nsmallest(8, "Delta_Weight")
        ]).drop_duplicates().sort_values(by="Delta_Weight", ascending=False)

        if not top_deltas.empty:
            top_deltas["Delta_Trend"] = top_deltas["Delta_Weight"].apply(
                lambda x: "Accumulation (Buying)" if x > 0 else "Trimming (Selling)"
            )
            delta_chart = (
                alt.Chart(top_deltas)
                .mark_bar()
                .encode(
                    x=alt.X("Delta_Weight:Q", title="Weight Delta ΔW (pp)"),
                    y=alt.Y("Ticker:N", sort="-x", title="Stock"),
                    color=alt.Color(
                        "Delta_Trend:N",
                        scale=alt.Scale(
                            domain=["Accumulation (Buying)", "Trimming (Selling)"],
                            range=["#16a34a", "#dc2626"]
                        ),
                        legend=alt.Legend(title="Trend", labelColor="#000", titleColor="#000")
                    ),
                    tooltip=[
                        "Ticker:N",
                        "Stock Name:N",
                        "Sentiment:N",
                        "Delta_Trend:N",
                        alt.Tooltip("Delta_Weight:Q", format="+.2f", title="ΔW Weight Change"),
                        alt.Tooltip("Delta_Confidence_Pct:Q", format="+.1f", title="ΔC Confidence Change %"),
                        alt.Tooltip("Weight_T0:Q", format=".2f", title="Current Weight %"),
                        alt.Tooltip("Weight_T1:Q", format=".2f", title="Prior Weight %")
                    ]
                )
                .properties(height=max(280, len(top_deltas) * 22), title="Month-over-Month Allocation Shift (ΔW)")
            )
            st.altair_chart(delta_chart, use_container_width=True)

        # Styled Table with Sentiment Icons
        st.markdown("**Period-over-Period Delta & Sentiment Table:**")
        display_deltas = filtered_deltas[[
            "Sentiment_Icon", "Sentiment", "Ticker", "Stock Name", "Sector",
            "Delta_Weight", "Weight_T0", "Weight_T1", "Delta_Confidence_Pct", "Conf_T0", "Conf_T1"
        ]].copy()

        st.dataframe(
            display_deltas,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sentiment_Icon": st.column_config.TextColumn("Signal", width="small"),
                "Delta_Weight": st.column_config.NumberColumn("ΔW (pp)", format="%+.2f"),
                "Delta_Confidence_Pct": st.column_config.NumberColumn("ΔC (%)", format="%+.1f%%"),
                "Weight_T0": st.column_config.NumberColumn("Latest Wt %", format="%.2f%%"),
                "Weight_T1": st.column_config.NumberColumn("Prior Wt %", format="%.2f%%"),
                "Conf_T0": st.column_config.ProgressColumn("Latest Conf", format="%.0f%%", min_value=0, max_value=1),
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Portfolio Gap & Alignment
# ─────────────────────────────────────────────────────────────────────────────
with tab_gap:
    st.markdown('<div class="section-hdr">Personal Portfolio Gap & Misalignment Engine</div>', unsafe_allow_html=True)
    st.caption("Audits your personal holdings against mutual fund institutional consensus using standard ISIN keys.")

    matched_full = gap_data.get("matched_df", pd.DataFrame())
    misses_df = gap_data.get("misses", pd.DataFrame())
    unbacked_df = gap_data.get("unbacked", pd.DataFrame())
    overweight_df = gap_data.get("overweight", pd.DataFrame())
    underweight_df = gap_data.get("underweight", pd.DataFrame())

    if matched_full.empty:
        st.warning("No portfolio data found for comparison. Please upload holdings in the Holdings page or click 'Sync My Portfolio'.")
    else:
        # Category Pills Summary
        g_c1, g_c2, g_c3, g_c4 = st.columns(4)
        with g_c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#d97706;">{len(misses_df)}</div><div class="kpi-lbl">Institutional Misses</div></div>', unsafe_allow_html=True)
        with g_c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#dc2626;">{len(unbacked_df)}</div><div class="kpi-lbl">Unbacked Bets</div></div>', unsafe_allow_html=True)
        with g_c3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#4f46e5;">{len(overweight_df)}</div><div class="kpi-lbl">Overbought (> +5%)</div></div>', unsafe_allow_html=True)
        with g_c4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:#0284c7;">{len(underweight_df)}</div><div class="kpi-lbl">Underbought (< -3%)</div></div>', unsafe_allow_html=True)

        st.write("")

        # Section 1: Institutional Misses (Gaps)
        st.markdown("#### 🎯 Institutional Misses (High Institutional Confidence, 0% in Your Portfolio)")
        st.markdown(
            "These quality stocks enjoy **&ge; 50-60% confidence** among peer mutual funds, "
            "yet have zero allocation in your portfolio."
        )
        if misses_df.empty:
            st.success("🎉 Excellent! You have no major institutional misses.")
        else:
            st.dataframe(
                misses_df[[
                    "Ticker", "Stock Name", "Sector", "Effective_Confidence %",
                    "MF Consensus Weight %", "Conviction Weight %", "Delta_Weight", "Sentiment"
                ]].head(12),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Effective_Confidence %": st.column_config.ProgressColumn("Peer Confidence %", format="%.0f%%", min_value=0, max_value=100),
                    "MF Consensus Weight %": st.column_config.NumberColumn("Consensus Wt %", format="%.2f%%"),
                    "Conviction Weight %": st.column_config.NumberColumn("Conviction Wt %", format="%.2f%%"),
                    "Delta_Weight": st.column_config.NumberColumn("MoM ΔW", format="%+.2f"),
                }
            )

        st.divider()

        # Section 2: Unbacked Speculative Bets
        st.markdown("#### ⚠️ Unbacked Bets (High User Weight, Low/Zero Institutional Backing)")
        st.markdown(
            "You have allocated significant capital (> 3-5%) into these stocks, but fewer than **10-15% of institutional funds** hold them."
        )
        if unbacked_df.empty:
            st.info("No unbacked speculative bets detected in your portfolio.")
        else:
            st.dataframe(
                unbacked_df[[
                    "Ticker", "Stock Name", "User Weight %", "Confidence %", "Active Weight Diff", "Current Value"
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "User Weight %": st.column_config.NumberColumn("My Weight %", format="%.2f%%"),
                    "Confidence %": st.column_config.NumberColumn("MF Confidence %", format="%.1f%%"),
                    "Active Weight Diff": st.column_config.NumberColumn("Active Diff", format="%+.2f%%"),
                    "Current Value": st.column_config.NumberColumn("Value (₹)", format="₹%.0f"),
                }
            )

        st.divider()

        # Section 3: Active Weight Difference (Overbought vs Underbought)
        st.markdown("#### ⚖️ Active Weight Difference (User Weight % − MF Consensus Weight %)")
        owned_stocks = matched_full[matched_full["User Weight %"] > 0.05].copy()
        if not owned_stocks.empty:
            owned_stocks["Status_Group"] = owned_stocks["Active Weight Diff"].apply(
                lambda x: "Overbought (> +5%)" if x > 5.0 else ("Underbought (< -3%)" if x < -3.0 else "Aligned (-3% to +5%)")
            )
            active_chart = (
                alt.Chart(owned_stocks)
                .mark_bar()
                .encode(
                    x=alt.X("Active Weight Diff:Q", title="Active Weight Difference (pp) [User Wt % - MF Wt %]"),
                    y=alt.Y("Ticker:N", sort="-x", title="Stock"),
                    color=alt.Color(
                        "Status_Group:N",
                        scale=alt.Scale(
                            domain=["Overbought (> +5%)", "Aligned (-3% to +5%)", "Underbought (< -3%)"],
                            range=["#6366f1", "#10b981", "#ef4444"]
                        ),
                        legend=alt.Legend(title="Status", labelColor="#000", titleColor="#000")
                    ),
                    tooltip=[
                        "Ticker:N",
                        "Stock Name:N",
                        "Ownership Category:N",
                        "Status_Group:N",
                        alt.Tooltip("User Weight %:Q", format=".2f", title="User Wt %"),
                        alt.Tooltip("MF Consensus Weight %:Q", format=".2f", title="MF Consensus Wt %"),
                        alt.Tooltip("Active Weight Diff:Q", format="+.2f", title="Active Diff (pp)")
                    ]
                )
                .properties(height=max(260, len(owned_stocks) * 24), title="Active Concentration vs Institutional Consensus")
            )
            st.altair_chart(active_chart, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Next Best Actions (Recommendations)
# ─────────────────────────────────────────────────────────────────────────────
with tab_nba:
    st.markdown('<div class="section-hdr">⚡ Next Best Action (NBA) Recommendation Engine</div>', unsafe_allow_html=True)
    st.caption("Automated rule-based recommendations prioritized by institutional conviction, trimming signals, and risk concentration.")

    if not nba_actions:
        st.info("No active recommendations generated. Your portfolio is well-aligned with mutual fund consensus!")
    else:
        # Category count badges
        buys = [a for a in nba_actions if a["type"] == "Buy Candidate"]
        trims = [a for a in nba_actions if a["type"] == "Trim Candidate"]
        reviews = [a for a in nba_actions if a["type"] == "Review Candidate"]
        rebalances = [a for a in nba_actions if a["type"] == "Sector Rebalance"]

        nba_filter = st.radio(
            "Filter Actions by Type",
            ["All Recommendations", f"🟢 Buy Candidates ({len(buys)})", f"🟡 Trim Candidates ({len(trims)})", f"🔴 Review Candidates ({len(reviews)})", f"🟣 Sector Rebalances ({len(rebalances)})"],
            horizontal=True
        )

        display_actions = nba_actions
        if "Buy Candidates" in nba_filter:
            display_actions = buys
        elif "Trim Candidates" in nba_filter:
            display_actions = trims
        elif "Review Candidates" in nba_filter:
            display_actions = reviews
        elif "Sector Rebalances" in nba_filter:
            display_actions = rebalances

        for act in display_actions:
            color = act["color"]
            badge_text = act["badge"]
            ticker = act["ticker"]
            stock_name = act["stock_name"]
            sector = act["sector"]
            reason = act["reason"]

            badge_pill = f'<span style="background:{color}22; color:{color}; border:1px solid {color}; border-radius:6px; padding:3px 8px; font-size:0.78rem; font-weight:800; margin-right:8px;">{badge_text}</span>'
            
            st.markdown(
                f"""
                <div class="action-card" style="border-left: 5px solid {color};">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <div>
                            {badge_pill}
                            <strong style="font-size:1.05rem; color:#1e293b;">{ticker}</strong> 
                            <span style="color:#64748b; font-size:0.9rem;">({stock_name})</span>
                        </div>
                        <div>
                            <span class="pill-gray">{sector}</span>
                        </div>
                    </div>
                    <div style="color:#334155; font-size:0.92rem; margin-top:6px; line-height:1.5;">
                        {reason}
                    </div>
                    <div style="margin-top:10px; font-size:0.83rem; color:#64748b;">
                        <strong>Current User Weight:</strong> {act['user_weight']:.1f}% &nbsp;|&nbsp; 
                        <strong>MF Consensus Weight:</strong> {act['mf_weight']:.1f}% &nbsp;|&nbsp; 
                        <strong>Institutional Confidence:</strong> {act['confidence']:.0f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Interactive Rebalancing Simulator
# ─────────────────────────────────────────────────────────────────────────────
with tab_sim:
    st.markdown('<div class="section-hdr">🎛️ Interactive Portfolio Rebalancing Simulator</div>', unsafe_allow_html=True)
    st.caption("Simulate aligning your portfolio weights with institutional consensus to model concentration risk reduction and capital shifts.")

    sim_col1, sim_col2 = st.columns([1.5, 2.5])

    with sim_col1:
        st.markdown("**Simulation Parameters:**")
        alignment_intensity = st.slider(
            "Institutional Alignment Intensity",
            min_value=0.0,
            max_value=1.0,
            value=0.50,
            step=0.05,
            format="%.2f",
            help="0.0 = Keep current portfolio unchanged | 1.0 = Full convergence to mutual fund consensus"
        )
        st.caption(f"Modeling **{alignment_intensity * 100:.0f}% convergence** towards professional mutual fund consensus.")

    sim_results = MFConsensusEngine.simulate_rebalance(alignment_intensity=alignment_intensity)

    if not sim_results or "simulated_df" not in sim_results:
        st.warning("Insufficient portfolio data to execute simulation. Please upload user holdings.")
    else:
        with sim_col2:
            # Impact KPI cards
            m1, m2, m3, m4 = st.columns(4)
            hhi_red = sim_results["hhi_reduction_pct"]
            var_red = sim_results["variance_reduction_pct"]
            
            m1.metric("Concentration Risk (HHI)", f"{sim_results['hhi_after']:.0f}", delta=f"-{hhi_red:.1f}%", delta_color="inverse")
            m2.metric("Top 5 Holdings %", f"{sim_results['top5_after']:.1f}%", delta=f"{sim_results['top5_after'] - sim_results['top5_before']:.1f}%", delta_color="inverse")
            m3.metric("Active Variance", f"{sim_results['active_var_after']:.0f}", delta=f"-{var_red:.1f}%", delta_color="inverse")
            m4.metric("Capital Reallocation", f"₹{sim_results['total_buy_inr']:,.0f}")

        st.divider()

        sim_df = sim_results["simulated_df"]

        # Before vs After Top Holdings Comparison
        top_comp = sim_df.head(10).copy()
        melted_comp = pd.melt(
            top_comp,
            id_vars=["Ticker", "Stock Name"],
            value_vars=["User Weight %", "Simulated_Weight %"],
            var_name="Allocation Type",
            value_name="Weight %"
        )
        melted_comp["Allocation Type"] = melted_comp["Allocation Type"].replace({
            "User Weight %": "Current User Weight",
            "Simulated_Weight %": "Simulated Rebalanced Weight"
        })

        sim_chart = (
            alt.Chart(melted_comp)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=alt.Y("Ticker:N", title="Stock"),
                yOffset="Allocation Type:N",
                x=alt.X("Weight %:Q", title="Portfolio Weight (%)"),
                color=alt.Color(
                    "Allocation Type:N",
                    scale=alt.Scale(domain=["Current User Weight", "Simulated Rebalanced Weight"], range=["#f59e0b", "#6366f1"]),
                    legend=alt.Legend(title="Portfolio Model", labelColor="#000", titleColor="#000")
                ),
                tooltip=["Ticker:N", "Stock Name:N", "Allocation Type:N", alt.Tooltip("Weight %:Q", format=".2f")]
            )
            .properties(height=360, title="Current Portfolio vs Rebalanced Target Allocation")
        )
        st.altair_chart(sim_chart, use_container_width=True)

        # Actionable Trade Orders Table
        st.markdown("**Actionable Rebalancing Orders Table (Execution Plan):**")
        display_sim = sim_df[[
            "Action", "Ticker", "Stock Name", "Sector", "User Weight %",
            "Simulated_Weight %", "Weight Change (pp)", "Capital Shift ₹"
        ]].copy()

        st.dataframe(
            display_sim,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Action": st.column_config.TextColumn("Trade", width="small"),
                "User Weight %": st.column_config.NumberColumn("Current Wt %", format="%.2f%%"),
                "Simulated_Weight %": st.column_config.NumberColumn("Target Wt %", format="%.2f%%"),
                "Weight Change (pp)": st.column_config.NumberColumn("Δ Weight", format="%+.2f"),
                "Capital Shift ₹": st.column_config.NumberColumn("Capital Shift (₹)", format="₹%+.0f"),
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: Legacy Sector Patterns (Backward Compatibility)
# ─────────────────────────────────────────────────────────────────────────────
with tab_legacy:
    st.markdown('<div class="section-hdr">📁 Tickertape Sector Holding Patterns & Multi-Fund Comparison</div>', unsafe_allow_html=True)
    st.caption("Maintains full backward compatibility for uploading and tracking historical sector pattern spreadsheets from Tickertape.")

    st.session_state["mf_holdings"] = MFHoldingService.load_from_db()
    legacy_mf_data = st.session_state.get("mf_holdings", {})

    with st.expander("📂 Upload Tickertape CSV / ZIP Files", expanded=not bool(legacy_mf_data)):
        uploaded_tt = st.file_uploader(
            "Upload Tickertape Sector CSVs",
            type=["csv", "txt", "zip"],
            accept_multiple_files=True,
            key="tt_uploader"
        )
        if uploaded_tt and st.button("⬆️ Parse & Load Tickertape Files", type="primary", key="btn_tt_load"):
            loaded_tt = 0
            for f in uploaded_tt:
                fname = getattr(f, "name", "")
                if fname.lower().endswith(".zip"):
                    zip_loaded, _ = MFHoldingService.process_zip_file(f)
                    loaded_tt += zip_loaded
                else:
                    try:
                        fname_parsed, df_p = MFHoldingService.parse_tickertape_file(f)
                        MFHoldingService.save_to_db(fname_parsed, df_p)
                        loaded_tt += 1
                    except Exception as e:
                        st.error(f"Error parsing {fname}: {e}")
            if loaded_tt > 0:
                st.session_state["mf_holdings"] = MFHoldingService.load_from_db()
                st.success(f"✅ Loaded {loaded_tt} Tickertape sector file(s)!")
                st.rerun()

    if not legacy_mf_data:
        st.info("No legacy Tickertape files loaded. You can continue using the institutional disclosure engine above.")
    else:
        legacy_funds = sorted(legacy_mf_data.keys())
        st.markdown(f"**Loaded Tickertape Funds ({len(legacy_funds)}):** " + ", ".join(f"`{f}`" for f in legacy_funds))
        
        sel_legacy_fund = st.selectbox("Select Fund for Sector Allocation History", legacy_funds)
        df_legacy_fund = legacy_mf_data[sel_legacy_fund]
        
        st.dataframe(df_legacy_fund, use_container_width=True, hide_index=True)
