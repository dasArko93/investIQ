# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import io
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from utils.page_utils import merged_holdings, render_sidebar, require_auth
from services.mf_holding_service import MFHoldingService

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MF Holding Pattern | InvestIQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
render_sidebar()

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .mf-hero {
        background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(168,85,247,0.10) 50%, rgba(236,72,153,0.08) 100%);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 20px;
        padding: 28px 32px 22px 32px;
        margin-bottom: 24px;
    }
    .mf-hero h1 { margin: 0 0 6px 0; font-size: 1.9rem; }
    .mf-hero p  { margin: 0; color: #475569; font-size: 0.95rem; }

    .kpi-card {
        background: rgba(255,255,255,0.5);
        border: 1px solid rgba(255,255,255,0.6);
        border-radius: 16px;
        padding: 18px 20px;
        backdrop-filter: blur(12px);
        text-align: center;
    }
    .kpi-val  { font-size: 1.9rem; font-weight: 800; color: #6366f1; line-height:1.1; }
    .kpi-lbl  { font-size: 0.82rem; color: #64748b; font-weight: 500; margin-top: 4px; }

    .pill-green  { background:rgba(34,197,94,0.15); color:#16a34a; border:1px solid rgba(34,197,94,0.3); border-radius:6px; padding:4px 10px; margin:3px; display:inline-block; font-size:0.82rem; font-weight:600; }
    .pill-red    { background:rgba(239,68,68,0.15);  color:#dc2626; border:1px solid rgba(239,68,68,0.3);  border-radius:6px; padding:4px 10px; margin:3px; display:inline-block; font-size:0.82rem; font-weight:600; }
    .pill-blue   { background:rgba(99,102,241,0.15); color:#4f46e5; border:1px solid rgba(99,102,241,0.3); border-radius:6px; padding:4px 10px; margin:3px; display:inline-block; font-size:0.82rem; font-weight:600; }
    .pill-gray   { background:rgba(100,116,139,0.12);color:#475569; border:1px solid rgba(100,116,139,0.25);border-radius:6px; padding:4px 10px; margin:3px; display:inline-block; font-size:0.82rem; font-weight:600; }

    .section-hdr {
        font-size: 1.05rem; font-weight: 700; color: #1e293b;
        border-left: 4px solid #6366f1; padding-left: 10px;
        margin: 18px 0 12px 0;
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
        <h1>📊 MF Holding Pattern</h1>
        <p>Upload Tickertape mutual fund sector holding CSVs to benchmark your portfolio against professional fund allocations.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Load mf holdings from db to keep memory state in sync with database
st.session_state["mf_holdings"] = MFHoldingService.load_from_db()


# ─────────────────────────────────────────────────────────────────────────────
# Upload Section
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📂 Upload Mutual Fund Files", expanded=not bool(st.session_state["mf_holdings"])):
    st.markdown(
        "Upload one or more **Tickertape Holding Pattern** exports. "
        "Each file should begin with the `Holding Pattern History by Tickertape` header."
    )
    uploaded = st.file_uploader(
        "Select Tickertape CSV files / ZIP Backup",
        type=["csv", "txt", "zip"],
        accept_multiple_files=True,
        key="mf_uploader",
        help="Download from Tickertape → Mutual Fund page → Holdings → Export CSV, or upload a ZIP backup",
    )

    col_upload, col_clear = st.columns([3, 1])
    with col_upload:
        if st.button("⬆️ Parse & Load Selected Files", type="primary", width='stretch'):
            if not uploaded:
                st.warning("Please select at least one file before loading.")
            else:
                errors = []
                loaded = 0
                for f in uploaded:
                    if f.name.endswith(".zip"):
                        zip_loaded, zip_errors = MFHoldingService.process_zip_file(f)
                        loaded += zip_loaded
                        errors.extend(zip_errors)
                    else:
                        try:
                            fname, df = MFHoldingService.parse_tickertape_file(f)
                            st.session_state["mf_holdings"][fname] = df
                            MFHoldingService.save_to_db(fname, df)
                            loaded += 1
                        except Exception as exc:
                            errors.append(f"**{f.name}**: {exc}")
                if loaded:
                    # Sync memory state with newly loaded database items
                    st.session_state["mf_holdings"] = MFHoldingService.load_from_db()
                    st.success(f"✅ Loaded & Saved **{loaded}** fund(s) successfully!")
                for err in errors:
                    st.error(err)
                st.rerun()

    with col_clear:
        if st.button("🗑️ Clear All Funds", width='stretch'):
            st.session_state["mf_holdings"] = {}
            MFHoldingService.clear_all_from_db()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Guard: nothing loaded yet
# ─────────────────────────────────────────────────────────────────────────────
mf_data = st.session_state.get("mf_holdings", {})

if not mf_data:
    st.info(
        "📋 No fund data loaded yet. Upload at least one Tickertape Holding Pattern CSV above "
        "to begin the analysis."
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Utility: build long-form dataframe from all funds
# ─────────────────────────────────────────────────────────────────────────────
def build_long_df(mf_dict: dict) -> pd.DataFrame:
    """Converts dict of {fund: wide_df} into a single long-form DataFrame."""
    records = []
    for fund_name, df in mf_dict.items():
        date_cols = [c for c in df.columns if c != "Holding Type"]
        for _, row in df.iterrows():
            sector = row["Holding Type"]
            for date_col in date_cols:
                records.append(
                    {
                        "Fund": fund_name,
                        "Sector": sector,
                        "Date": date_col,
                        "Allocation": float(row[date_col]),
                    }
                )
    if not records:
        return pd.DataFrame(columns=["Fund", "Sector", "Date", "Allocation"])
    return pd.DataFrame(records)


long_df = build_long_df(mf_data)

all_funds = sorted(mf_data.keys())
all_sectors = sorted(long_df["Sector"].unique().tolist()) if not long_df.empty else []

# Preserve original column order from first fund for dates
all_dates = []
if mf_data:
    _first_fund_df = list(mf_data.values())[0]
    all_dates = [c for c in _first_fund_df.columns if c != "Holding Type"]

# Compute "latest" date (last column in first fund)
latest_date = all_dates[-1] if all_dates else "N/A"

# ─────────────────────────────────────────────────────────────────────────────
# KPI Row
# ─────────────────────────────────────────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi_data = [
    (str(len(all_funds)), "Funds Loaded"),
    (str(len(all_sectors)), "Unique Sectors"),
    (str(len(all_dates)), "Time Periods"),
    (f"{latest_date}", "Latest Period"),
]
for col, (val, lbl) in zip([kpi1, kpi2, kpi3, kpi4], kpi_data):
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-val">{val}</div><div class="kpi-lbl">{lbl}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# Loaded funds pills
# ─────────────────────────────────────────────────────────────────────────────
fund_pills = "".join(f'<span class="pill-blue">📁 {f}</span>' for f in all_funds)
st.markdown(
    f'<div style="margin-bottom:16px;">{fund_pills}</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_overview, tab_trends, tab_benchmark, tab_compare = st.tabs(
    ["🗺️ Overview", "📈 Sector Trends", "🎯 My Portfolio Benchmark", "🔀 Fund Comparison"]
)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab_overview:
    with st.expander("🗺️ Sector Allocation Heatmap (Latest Period)", expanded=True):
        # Per-fund heatmap using latest date
        for fund_name, df in mf_data.items():
            date_cols = [c for c in df.columns if c != "Holding Type"]
            if not date_cols:
                continue
            latest_col = date_cols[-1]
            heatmap_data = df[["Holding Type", latest_col]].copy()
            heatmap_data = heatmap_data.rename(columns={"Holding Type": "Sector", latest_col: "Allocation"})
            heatmap_data = heatmap_data.sort_values("Allocation", ascending=False)

            st.markdown(f"**{fund_name}** — *{latest_col}*")

            heat_chart = (
                alt.Chart(heatmap_data)
                .mark_rect()
                .encode(
                    x=alt.X("Allocation:Q", bin=alt.Bin(maxbins=20), title="Allocation % (binned)"),
                    y=alt.Y("Sector:N", sort="-x", title="Sector"),
                    color=alt.Color(
                        "Allocation:Q",
                        scale=alt.Scale(scheme="purpleblue"),
                        legend=alt.Legend(title="Alloc %", labelColor="#000", titleColor="#000"),
                    ),
                    tooltip=["Sector:N", alt.Tooltip("Allocation:Q", format=".2f", title="Allocation %")],
                )
                .properties(height=max(250, len(heatmap_data) * 22))
            )
            st.altair_chart(heat_chart, width='stretch')

    st.divider()
    st.markdown('<div class="section-hdr">Top 10 Sectors — Allocation Over Time</div>', unsafe_allow_html=True)

    if all_funds:
        fund_sel_ov = st.selectbox("Select Fund", all_funds, key="ov_fund_sel")
        df_sel = mf_data[fund_sel_ov]
        date_cols_sel = [c for c in df_sel.columns if c != "Holding Type"]

        # Top 10 sectors by latest allocation
        latest_col_ov = date_cols_sel[-1] if date_cols_sel else None
        if latest_col_ov:
            top10 = df_sel.nlargest(10, latest_col_ov)["Holding Type"].tolist()
            df_top10 = df_sel[df_sel["Holding Type"].isin(top10)].copy()

            long_top10 = df_top10.melt(id_vars="Holding Type", var_name="Date", value_name="Allocation")
            long_top10 = long_top10.rename(columns={"Holding Type": "Sector"})

            line_chart = (
                alt.Chart(long_top10)
                .mark_line(point=True, strokeWidth=2.5)
                .encode(
                    x=alt.X("Date:N", sort=date_cols_sel, title="Period", axis=alt.Axis(labelAngle=-35)),
                    y=alt.Y("Allocation:Q", title="Allocation %"),
                    color=alt.Color(
                        "Sector:N",
                        legend=alt.Legend(title="Sector", labelColor="#000", titleColor="#000"),
                    ),
                    tooltip=["Sector:N", "Date:N", alt.Tooltip("Allocation:Q", format=".2f", title="Alloc %")],
                )
                .properties(height=420, title=f"Top 10 Sector Allocation History — {fund_sel_ov}")
            )
            st.altair_chart(line_chart, width='stretch')

    # Raw data expander
    with st.expander("📋 View Raw Data Table"):
        for fname, df_raw in mf_data.items():
            st.markdown(f"**{fname}**")
            st.dataframe(df_raw, width='stretch', hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SECTOR TRENDS
# ─────────────────────────────────────────────────────────────────────────────
with tab_trends:
    st.markdown('<div class="section-hdr">Filter & Explore Sector Trends</div>', unsafe_allow_html=True)

    t2_col1, t2_col2 = st.columns([1, 2])
    with t2_col1:
        sel_funds_t2 = st.multiselect(
            "Funds", all_funds, default=all_funds[:2], key="t2_funds"
        )
    with t2_col2:
        sel_sectors_t2 = st.multiselect(
            "Sectors",
            all_sectors,
            default=all_sectors[:6],
            key="t2_sectors",
        )

    if not sel_funds_t2 or not sel_sectors_t2:
        st.info("Select at least one fund and one sector to display the trend chart.")
    else:
        filtered = long_df[
            long_df["Fund"].isin(sel_funds_t2) & long_df["Sector"].isin(sel_sectors_t2)
        ].copy()

        # Preserve column order for dates
        date_order_map = {d: i for i, d in enumerate(all_dates)}
        filtered["DateOrder"] = filtered["Date"].map(date_order_map)
        filtered = filtered.sort_values("DateOrder")

        # Combined label for legend
        filtered["Fund × Sector"] = filtered["Fund"].str.split(" ").str[-3:].apply(" ".join) + " | " + filtered["Sector"]

        trend_line = (
            alt.Chart(filtered)
            .mark_line(point=True, strokeWidth=2.2)
            .encode(
                x=alt.X("Date:N", sort=all_dates, title="Period", axis=alt.Axis(labelAngle=-35)),
                y=alt.Y("Allocation:Q", title="Allocation %"),
                color=alt.Color("Fund × Sector:N", legend=alt.Legend(title="Fund | Sector", labelColor="#000", titleColor="#000")),
                strokeDash=alt.StrokeDash("Fund:N", legend=None),
                tooltip=["Fund:N", "Sector:N", "Date:N", alt.Tooltip("Allocation:Q", format=".2f", title="Alloc %")],
            )
            .properties(height=420, title="Sector Allocation Trend")
        )
        st.altair_chart(trend_line, width='stretch')

        # ── Delta Table (first → last period) ────────────────────────────────
        st.markdown('<div class="section-hdr">Period-over-Period Delta (First → Latest)</div>', unsafe_allow_html=True)

        delta_rows = []
        for fund in sel_funds_t2:
            if fund not in mf_data:
                continue
            df_f = mf_data[fund]
            date_cols_f = [c for c in df_f.columns if c != "Holding Type"]
            if len(date_cols_f) < 2:
                continue
            first_col, last_col = date_cols_f[0], date_cols_f[-1]
            for sector in sel_sectors_t2:
                row = df_f[df_f["Holding Type"] == sector]
                if row.empty:
                    continue
                first_val = float(row[first_col].iloc[0])
                last_val  = float(row[last_col].iloc[0])
                delta     = last_val - first_val
                delta_rows.append(
                    {
                        "Fund": fund,
                        "Sector": sector,
                        f"First ({first_col})": first_val,
                        f"Latest ({last_col})": last_val,
                        "Δ Change (pp)": round(delta, 2),
                        "Direction": "▲ Up" if delta > 0.05 else ("▼ Down" if delta < -0.05 else "→ Flat"),
                    }
                )

        if delta_rows:
            delta_df = pd.DataFrame(delta_rows).sort_values("Δ Change (pp)", ascending=False)
            first_lbl = [c for c in delta_df.columns if c.startswith("First")][0]
            last_lbl  = [c for c in delta_df.columns if c.startswith("Latest")][0]

            def color_delta(val):
                if isinstance(val, (int, float)):
                    if val > 0.05:
                        return "color: #16a34a; font-weight: 700"
                    elif val < -0.05:
                        return "color: #dc2626; font-weight: 700"
                return ""

            styled = delta_df.style.map(color_delta, subset=["Δ Change (pp)"])
            st.dataframe(
                styled,
                width='stretch',
                hide_index=True,
                column_config={
                    first_lbl: st.column_config.NumberColumn(first_lbl, format="%.2f%%"),
                    last_lbl:  st.column_config.NumberColumn(last_lbl,  format="%.2f%%"),
                    "Δ Change (pp)": st.column_config.NumberColumn("Δ Change (pp)", format="%.2f"),
                },
            )

            # Bar chart of deltas
            delta_bar = (
                alt.Chart(delta_df)
                .mark_bar()
                .encode(
                    x=alt.X("Δ Change (pp):Q", title="Change (percentage points)"),
                    y=alt.Y("Sector:N", sort="-x"),
                    color=alt.condition(
                        alt.datum["Δ Change (pp)"] > 0,
                        alt.value("#22c55e"),
                        alt.value("#ef4444"),
                    ),
                    row=alt.Row("Fund:N", header=alt.Header(labelFontSize=13, labelColor="#000")),
                    tooltip=["Fund:N", "Sector:N", alt.Tooltip("Δ Change (pp):Q", format=".2f")],
                )
                .properties(height=max(160, len(sel_sectors_t2) * 24), title="First → Latest Allocation Change")
            )
            st.altair_chart(delta_bar, width='stretch')


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — MY PORTFOLIO BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────
with tab_benchmark:
    st.markdown('<div class="section-hdr">Your Portfolio vs. MF Allocation</div>', unsafe_allow_html=True)

    st.info(
        "This tab maps your portfolio sector exposure (from Holdings + Stock Universe) against "
        "the average allocation of the loaded mutual funds."
    )

    # ── Compute MF average allocation (latest date) ───────────────────────────
    mf_latest_rows = []
    for fund_name, df in mf_data.items():
        date_cols = [c for c in df.columns if c != "Holding Type"]
        if not date_cols:
            continue
        latest = date_cols[-1]
        for _, row in df.iterrows():
            mf_latest_rows.append(
                {"Sector": row["Holding Type"], "Fund": fund_name, "Allocation": float(row[latest])}
            )

    if mf_latest_rows:
        mf_latest_df = pd.DataFrame(mf_latest_rows)
        mf_avg = (
            mf_latest_df.groupby("Sector")["Allocation"].mean().reset_index()
            .rename(columns={"Allocation": "MF Avg %"})
            .sort_values("MF Avg %", ascending=False)
        )
    else:
        mf_avg = pd.DataFrame(columns=["Sector", "MF Avg %"])

    # ── Portfolio Sector Exposure ─────────────────────────────────────────────
    portfolio_sector_df = pd.DataFrame()

    merged = merged_holdings()
    holdings_raw = None
    try:
        from services.holdings_service import HoldingsService
        holdings_raw = HoldingsService.dataframe()
    except Exception:
        pass

    if not merged.empty and "Sub-Sector" in merged.columns and "Current Value Rs" in merged.columns:
        merged["Current Value Rs"] = pd.to_numeric(merged["Current Value Rs"], errors="coerce").fillna(0)
        total_val = merged["Current Value Rs"].sum()
        if total_val > 0:
            sector_alloc = (
                merged.groupby("Sub-Sector")["Current Value Rs"]
                .sum()
                .reset_index()
                .rename(columns={"Sub-Sector": "Sector", "Current Value Rs": "Portfolio %"})
            )
            sector_alloc["Portfolio %"] = (sector_alloc["Portfolio %"] / total_val * 100).round(2)
            portfolio_sector_df = sector_alloc
    elif holdings_raw is not None and not holdings_raw.empty and "Broker Sector" in holdings_raw.columns:
        holdings_raw["Current Value Rs"] = pd.to_numeric(holdings_raw["Current Value Rs"], errors="coerce").fillna(0)
        total_val = holdings_raw["Current Value Rs"].sum()
        if total_val > 0:
            sector_alloc = (
                holdings_raw.groupby("Broker Sector")["Current Value Rs"]
                .sum()
                .reset_index()
                .rename(columns={"Broker Sector": "Sector", "Current Value Rs": "Portfolio %"})
            )
            sector_alloc["Portfolio %"] = (sector_alloc["Portfolio %"] / total_val * 100).round(2)
            portfolio_sector_df = sector_alloc

    if portfolio_sector_df.empty:
        st.warning(
            "⚠️ No portfolio holdings found. Please upload your holdings in the **Holdings** page "
            "and optionally add universe data in **Stock Universe** for sector mapping."
        )
        if not mf_avg.empty:
            mf_bar = (
                alt.Chart(mf_avg)
                .mark_bar(color="#6366f1", opacity=0.85)
                .encode(
                    x=alt.X("MF Avg %:Q", title="Allocation %"),
                    y=alt.Y("Sector:N", sort="-x"),
                    tooltip=["Sector:N", alt.Tooltip("MF Avg %:Q", format=".2f", title="MF Avg %")],
                )
                .properties(height=max(300, len(mf_avg) * 22), title="MF Average Allocation")
            )
            st.altair_chart(mf_bar, width='stretch')
        else:
            st.info("No mutual fund data available to calculate average sector allocation.")
    else:
        # ── Fuzzy merge on sector names ────────────────────────────────────────
        def fuzzy_match(portfolio_sectors, mf_sectors):
            """Returns a dict mapping portfolio_sector -> best mf_sector."""
            mapping = {}
            for ps in portfolio_sectors:
                ps_low = ps.lower().strip()
                best, best_score = None, 0
                for ms in mf_sectors:
                    ms_low = ms.lower().strip()
                    # Exact match
                    if ps_low == ms_low:
                        best, best_score = ms, 100
                        break
                    # Token overlap
                    ps_toks = set(re.split(r"[\s\-&/,]+", ps_low))
                    ms_toks = set(re.split(r"[\s\-&/,]+", ms_low))
                    overlap = len(ps_toks & ms_toks) / max(len(ps_toks | ms_toks), 1)
                    if overlap > best_score:
                        best, best_score = ms, overlap
                if best_score > 0.3:
                    mapping[ps] = best
            return mapping

        sector_map = fuzzy_match(
            portfolio_sector_df["Sector"].tolist(),
            mf_avg["Sector"].tolist(),
        )

        portfolio_sector_df["MF Sector"] = portfolio_sector_df["Sector"].map(sector_map)
        matched  = portfolio_sector_df.dropna(subset=["MF Sector"]).copy()
        unmatched = portfolio_sector_df[portfolio_sector_df["MF Sector"].isna()].copy()

        # Merge matched with MF avg
        if not mf_avg.empty:
            if not matched.empty:
                matched["MF Sector"] = matched["MF Sector"].astype(str)
            mf_avg["Sector"] = mf_avg["Sector"].astype(str)
            bench = matched.merge(mf_avg, left_on="MF Sector", right_on="Sector", how="right", suffixes=("_port", "_mf"))
            
            # Fill NaN values for unheld sectors (right only rows)
            unheld_mask = bench["Sector_port"].isna()
            bench["Sector_port"] = bench["Sector_port"].fillna(bench["Sector_mf"] + " (Not Held)")
            bench["Portfolio %"] = bench["Portfolio %"].fillna(0.0)
            bench["MF Sector"] = bench["MF Sector"].fillna(bench["Sector_mf"])
            
            bench = bench.rename(columns={"Sector_port": "My Sector"})
            bench["Gap (pp)"] = (bench["Portfolio %"] - bench["MF Avg %"]).round(2)
            bench["Status"] = bench["Gap (pp)"].apply(
                lambda x: "🔵 Overweight" if x > 1 else ("🔴 Underweight" if x < -1 else "🟢 Aligned")
            )
            # Override for unheld sectors
            bench.loc[unheld_mask, "Status"] = "🔴 Not Held"
        else:
            bench = pd.DataFrame(columns=["My Sector", "MF Sector", "Portfolio %", "MF Avg %", "Gap (pp)", "Status"])

        bench = bench.sort_values("MF Avg %", ascending=False)

        # ── Gap Table ──────────────────────────────────────────────────────
        if not bench.empty:
            st.markdown('<div class="section-hdr">Overweight / Underweight vs MF Benchmark</div>', unsafe_allow_html=True)

            # ── Filtration Capability ──────────────────────────────────────────
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                search_query = st.text_input("🔍 Search Sectors", "", key="bench_search", placeholder="Type sector name...")
            with col_f2:
                status_options = ["🔵 Overweight", "🔴 Underweight", "🟢 Aligned", "🔴 Not Held"]
                selected_status = st.multiselect(
                    "Filter by Status",
                    options=status_options,
                    default=[],
                    placeholder="Show all",
                    key="bench_status"
                )

            display_bench = bench[["My Sector", "MF Sector", "Portfolio %", "MF Avg %", "Gap (pp)", "Status"]].copy()

            # Apply filters
            if search_query:
                display_bench = display_bench[
                    display_bench["My Sector"].str.contains(search_query, case=False, na=False) |
                    display_bench["MF Sector"].str.contains(search_query, case=False, na=False)
                ]
            if selected_status:
                display_bench = display_bench[display_bench["Status"].isin(selected_status)]

            def style_gap(val):
                if isinstance(val, (int, float)):
                    if val > 1:
                        return "color:#1d4ed8; font-weight:700"
                    elif val < -1:
                        return "color:#dc2626; font-weight:700"
                    return "color:#16a34a; font-weight:600"
                return ""

            styled_bench = display_bench.style.map(style_gap, subset=["Gap (pp)"])
            st.dataframe(
                styled_bench,
                width='stretch',
                hide_index=True,
                column_config={
                    "Portfolio %": st.column_config.NumberColumn("My Portfolio %", format="%.2f%%"),
                    "MF Avg %":    st.column_config.NumberColumn("MF Avg %",      format="%.2f%%"),
                    "Gap (pp)":    st.column_config.NumberColumn("Gap (pp)",       format="%.2f"),
                },
            )

            # ── Status pills ───────────────────────────────────────────────────
            ow = display_bench[display_bench["Status"] == "🔵 Overweight"]["My Sector"].tolist()
            uw = display_bench[display_bench["Status"] == "🔴 Underweight"]["My Sector"].tolist()
            nh = display_bench[display_bench["Status"] == "🔴 Not Held"]["My Sector"].tolist()
            al = display_bench[display_bench["Status"] == "🟢 Aligned"]["My Sector"].tolist()

            st.markdown('<div class="section-hdr">Sector Status Summary</div>', unsafe_allow_html=True)
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.markdown("**🔵 Overweight**")
                if ow:
                    st.markdown("".join(f'<span class="pill-blue">{s}</span>' for s in ow), unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-gray">None</span>', unsafe_allow_html=True)
            with col_b:
                st.markdown("**🔴 Underweight**")
                if uw:
                    st.markdown("".join(f'<span class="pill-red">{s}</span>' for s in uw), unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-gray">None</span>', unsafe_allow_html=True)
            with col_c:
                st.markdown("**🔴 Not Held**")
                if nh:
                    st.markdown("".join(f'<span class="pill-red">{s}</span>' for s in nh), unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-gray">None</span>', unsafe_allow_html=True)
            with col_d:
                st.markdown("**🟢 Aligned**")
                if al:
                    st.markdown("".join(f'<span class="pill-green">{s}</span>' for s in al), unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-gray">None</span>', unsafe_allow_html=True)

        # ── Unmatched Sectors ──────────────────────────────────────────────────
        if not unmatched.empty:
            with st.expander(f"⚠️ {len(unmatched)} portfolio sector(s) could not be mapped to MF sectors"):
                st.markdown(
                    "These sectors exist in your portfolio but do not have a close match in the uploaded MF data. "
                    "Consider uploading more MF files or checking sector naming consistency."
                )
                st.dataframe(
                    unmatched[["Sector", "Portfolio %"]],
                    width='stretch',
                    hide_index=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — FUND COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
with tab_compare:
    st.markdown('<div class="section-hdr">Side-by-Side Fund Comparison</div>', unsafe_allow_html=True)

    if len(all_funds) < 2:
        st.info("Load at least **2 funds** to enable the comparison view.")
    else:
        t4_col1, t4_col2 = st.columns(2)
        with t4_col1:
            fund_a = st.selectbox("Fund A", all_funds, index=0, key="cmp_a")
        with t4_col2:
            fund_b = st.selectbox(
                "Fund B", all_funds, index=min(1, len(all_funds) - 1), key="cmp_b"
            )

        if fund_a == fund_b:
            st.warning("Please select two different funds.")
        else:
            def latest_alloc(fund_name: str) -> pd.Series:
                df = mf_data[fund_name]
                date_cols = [c for c in df.columns if c != "Holding Type"]
                return df.set_index("Holding Type")[date_cols[-1]]

            alloc_a = latest_alloc(fund_a).rename("Fund A")
            alloc_b = latest_alloc(fund_b).rename("Fund B")
            cmp_df = pd.concat([alloc_a, alloc_b], axis=1).fillna(0).reset_index()
            cmp_df.columns = ["Sector", "Fund A", "Fund B"]
            # Only show sectors where at least one fund has meaningful allocation
            cmp_df = cmp_df[(cmp_df["Fund A"] > 0) | (cmp_df["Fund B"] > 0)].copy()
            cmp_df = cmp_df.sort_values("Fund A", ascending=False)

            # ── Grouped Bar ────────────────────────────────────────────────────
            cmp_melt = cmp_df.melt(id_vars="Sector", var_name="Fund", value_name="Allocation %")
            cmp_melt["Fund"] = cmp_melt["Fund"].replace({"Fund A": fund_a, "Fund B": fund_b})

            cmp_bar = (
                alt.Chart(cmp_melt)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    y=alt.Y("Sector:N", sort=list(cmp_df["Sector"]), title="Sector"),
                    yOffset="Fund:N",
                    x=alt.X("Allocation %:Q", title="Allocation %"),
                    color=alt.Color(
                        "Fund:N",
                        scale=alt.Scale(range=["#6366f1", "#f59e0b"]),
                        legend=alt.Legend(title="Fund", labelColor="#000", titleColor="#000"),
                    ),
                    tooltip=["Fund:N", "Sector:N", alt.Tooltip("Allocation %:Q", format=".2f", title="Alloc %")],
                )
                .properties(height=max(300, len(cmp_df) * 28), title=f"{fund_a} vs {fund_b} — Sector Allocation")
            )
            st.altair_chart(cmp_bar, width='stretch')

            st.divider()

            # ── Gap Analysis ───────────────────────────────────────────────────
            st.markdown('<div class="section-hdr">Allocation Gap: Fund A − Fund B</div>', unsafe_allow_html=True)
            cmp_df["Gap (pp)"] = (cmp_df["Fund A"] - cmp_df["Fund B"]).round(2)
            cmp_df = cmp_df.sort_values("Gap (pp)", ascending=False)

            gap_bar = (
                alt.Chart(cmp_df)
                .mark_bar()
                .encode(
                    x=alt.X("Gap (pp):Q", title="Allocation Difference (pp)"),
                    y=alt.Y("Sector:N", sort="-x"),
                    color=alt.condition(
                        alt.datum["Gap (pp)"] > 0,
                        alt.value("#6366f1"),
                        alt.value("#f59e0b"),
                    ),
                    tooltip=[
                        "Sector:N",
                        alt.Tooltip("Fund A:Q", format=".2f", title=f"{fund_a} %"),
                        alt.Tooltip("Fund B:Q", format=".2f", title=f"{fund_b} %"),
                        alt.Tooltip("Gap (pp):Q", format=".2f"),
                    ],
                )
                .properties(height=max(300, len(cmp_df) * 22), title=f"Gap: {fund_a} minus {fund_b}")
            )
            st.altair_chart(gap_bar, width='stretch')

            # ── Correlation (if ≥ 2 funds and multiple dates) ──────────────────
            st.divider()
            st.markdown('<div class="section-hdr">Cross-Fund Correlation Matrix (All Loaded Funds)</div>', unsafe_allow_html=True)

            if len(all_funds) >= 2:
                corr_frames = {}
                for fname, df in mf_data.items():
                    date_cols = [c for c in df.columns if c != "Holding Type"]
                    if not date_cols:
                        continue
                    s = df.set_index("Holding Type")[date_cols].T
                    s.index.name = "Date"
                    corr_frames[fname] = s.mean()  # average allocation per sector

                fund_alloc_df = pd.DataFrame(corr_frames).fillna(0)
                if fund_alloc_df.shape[1] >= 2:
                    corr_matrix = fund_alloc_df.corr().reset_index()
                    corr_long = corr_matrix.melt(id_vars="index", var_name="Fund B", value_name="Correlation")
                    corr_long = corr_long.rename(columns={"index": "Fund A"})

                    corr_heatmap = (
                        alt.Chart(corr_long)
                        .mark_rect()
                        .encode(
                            x=alt.X("Fund A:N", title=None),
                            y=alt.Y("Fund B:N", title=None),
                            color=alt.Color(
                                "Correlation:Q",
                                scale=alt.Scale(scheme="purpleblue", domain=[0, 1]),
                                legend=alt.Legend(title="Corr", labelColor="#000", titleColor="#000"),
                            ),
                            tooltip=["Fund A:N", "Fund B:N", alt.Tooltip("Correlation:Q", format=".3f")],
                        )
                        .properties(height=300, width=300, title="Sector Correlation Between Funds")
                    )

                    corr_text = (
                        alt.Chart(corr_long)
                        .mark_text(fontSize=13, fontWeight="bold")
                        .encode(
                            x="Fund A:N",
                            y="Fund B:N",
                            text=alt.Text("Correlation:Q", format=".2f"),
                            color=alt.condition(
                                alt.datum.Correlation > 0.7,
                                alt.value("white"),
                                alt.value("black"),
                            ),
                        )
                    )
                    st.altair_chart(corr_heatmap + corr_text, width='content')
                else:
                    st.info("Load at least 2 funds to view the correlation matrix.")
