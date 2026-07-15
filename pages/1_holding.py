# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import pandas as pd
import streamlit as st
import plotly.express as px

from services.health_service import HealthService
from services.holdings_service import HoldingsService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from utils.page_utils import load_holdings, load_universe, merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ - holdings", layout="wide", initial_sidebar_state="expanded")

from utils.page_utils import require_auth
require_auth()

render_sidebar()

st.title("holding")
st.write(
    "A unified portfolio view that combines holdings details, allocation insights, health metrics, and executive summary report generation."
)

files = st.file_uploader("Upload Holdings", type=["csv", "xlsx"], accept_multiple_files=True)
if files:
    total_uploaded = 0
    errors = []
    for file in files:
        try:
            rows = HoldingsService.upload(file)
            total_uploaded += rows
        except Exception as e:
            errors.append(f"Failed to process {file.name}: {e}")
    if total_uploaded > 0:
        st.success(f"Successfully uploaded {total_uploaded} holdings from {len(files) - len(errors)} file(s)!")
    for err in errors:
        st.error(err)

holdings = load_holdings()
universe = load_universe()
merged = merged_holdings()

if holdings.empty:
    st.info(
        "Upload your holdings file to populate the portfolio. "
        "For richer allocation and performance analysis, also upload universe data in Stock Screener."
    )
    st.info(
        "💡 **Data Reset Note:** Deployed apps on Streamlit can reset due to inactivity, losing temporary data. "
        "If you previously downloaded a database backup, you can restore it under the 'Backup & Restore' tab in "
        "the [Database Admin](pages/18_Clear_Data.py) page. You can also configure permanent cloud database persistence there."
    )
else:
    holdings = holdings.fillna(0)
    holdings["No. of Smallcases"] = pd.to_numeric(holdings["No. of Smallcases"], errors="coerce").fillna(0)
    holdings["Portfolio Weight %"] = pd.to_numeric(holdings["Portfolio Weight %"], errors="coerce").fillna(0)
    holdings["Current Value Rs"] = pd.to_numeric(holdings["Current Value Rs"], errors="coerce").fillna(0)
    holdings["Invested Value Rs"] = pd.to_numeric(holdings["Invested Value Rs"], errors="coerce").fillna(0)
    holdings["PnL Rs"] = pd.to_numeric(holdings["PnL Rs"], errors="coerce").fillna(0)
    holdings["PnL %"] = pd.to_numeric(holdings["PnL %"], errors="coerce").fillna(0)
    holdings["Day PnL"] = pd.to_numeric(holdings["Day PnL"], errors="coerce").fillna(0)
    holdings["Day PnL %"] = pd.to_numeric(holdings["Day PnL %"], errors="coerce").fillna(0)
    holdings["Broker Sector"] = holdings["Broker Sector"].astype(str)
    holdings["Asset Class"] = holdings["Asset Class"].astype(str)

    total_invested = float(holdings["Invested Value Rs"].sum())
    total_current = float(holdings["Current Value Rs"].sum())
    total_pnl = total_current - total_invested
    pnl_pct = (total_pnl / total_invested * 100.0) if total_invested > 0 else 0.0
    total_day_pnl = holdings["Day PnL"].sum()
    avg_day_pnl_pct = holdings["Day PnL %"].mean()
    
    avg_weight = holdings["Portfolio Weight %"].mean()
    
    avg_quality = merged["QUALITY_SCORE"].fillna(0).mean() if not merged.empty else 0.0
    sector_count = merged["Sub-Sector"].nunique() if not merged.empty else 0
    health = HealthService.evaluate(holdings, avg_quality, sector_count)
    
    if not merged.empty and "Sub-Sector" in merged.columns:
        mode_values = merged["Sub-Sector"].dropna().mode()
        top_sector_exposure = mode_values.iloc[0] if not mode_values.empty else "N/A"
    else:
        top_sector_exposure = "N/A"

    # Calculate concentration warnings
    warnings = []
    if not merged.empty:
        merged["Weight %"] = (merged["Current Value Rs"] / total_current) * 100.0
        
        # Max stock weight
        max_stock_w = merged["Weight %"].max()
        max_stock_rows = merged.loc[merged["Weight %"] == max_stock_w]
        if not max_stock_rows.empty:
            max_stock_row = max_stock_rows.iloc[0]
            if max_stock_w > 20:
                warnings.append(f"Stock Concentration is HIGH. '{max_stock_row['Security']}' represents {max_stock_w:.1f}% of your portfolio.")
            elif max_stock_w >= 10:
                warnings.append(f"Stock Concentration is MODERATE. '{max_stock_row['Security']}' represents {max_stock_w:.1f}% of your portfolio.")
            
        # Max sector weight
        sec_allocs = merged.groupby("Sub-Sector")["Current Value Rs"].sum()
        if not sec_allocs.empty:
            sec_pcts = (sec_allocs / total_current) * 100.0
            max_sec_w = sec_pcts.max()
            max_sec_name = sec_pcts.idxmax()
            if max_sec_w > 40:
                warnings.append(f"Sector Concentration is HIGH. '{max_sec_name}' represents {max_sec_w:.1f}% of your portfolio.")
            elif max_sec_w >= 25:
                warnings.append(f"Sector Concentration is MODERATE. '{max_sec_name}' represents {max_sec_w:.1f}% of your portfolio.")

    # 2. Render KPI Summary Cards
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
    metric_col1.metric("Invested Value", f"₹{total_invested:,.2f}")
    metric_col2.metric("Current Value", f"₹{total_current:,.2f}")
    metric_col3.metric("Total P&L", f"₹{total_pnl:,.2f}", delta=f"{pnl_pct:+.2f}%")
    metric_col4.metric("Day's P&L", f"₹{total_day_pnl:,.2f}", delta=f"{avg_day_pnl_pct:+.2f}%")
    metric_col5.metric("Health Score", f"{health:.1f}/100")
    metric_col6.metric("Avg Stock Quality", f"{avg_quality:.1f}/100")

    st.divider()

    # 3. Interactive Report Tabs
    tab_overview, tab_allocation, tab_health, tab_export = st.tabs([
        "📈 Overview",
        "⚖️ Allocation & Risk",
        "🔍 Fundamentals Audit & Health",
        "📥 Export PDF Report"
    ])

    # --- Tab 1: Overview ---
    with tab_overview:
        st.subheader("Current holding")
        st.dataframe(
            holdings,
            width='stretch',
            hide_index=True,
            column_config={
                "Security": st.column_config.TextColumn("Security"),
                "No. of Smallcases": st.column_config.NumberColumn("No. of Smallcases", format="%d"),
                "Quantity": st.column_config.NumberColumn("Quantity", format="%,.2f"),
                "Average Cost Rs": st.column_config.NumberColumn("Average Cost ₹", format="₹%,.2f"),
                "Portfolio Weight %": st.column_config.NumberColumn("Portfolio Weight %", format="%.2f%%"),
                "LTP Rs": st.column_config.NumberColumn("LTP ₹", format="₹%,.2f"),
                "Invested Value Rs": st.column_config.NumberColumn("Invested Value ₹", format="₹%,.2f"),
                "Current Value Rs": st.column_config.NumberColumn("Current Value ₹", format="₹%,.2f"),
                "PnL Rs": st.column_config.NumberColumn("P & L ₹", format="₹%,.2f"),
                "PnL %": st.column_config.NumberColumn("Net Change %", format="%.2f%%"),
                "Day PnL": st.column_config.NumberColumn("Daily Change ₹", format="₹%,.2f"),
                "Day PnL %": st.column_config.NumberColumn("Daily Change %", format="%.2f%%"),
                "Broker Sector": st.column_config.TextColumn("Broker Sector"),
                "Asset Class": st.column_config.TextColumn("Asset Class"),
            }
        )

        chart_df = merged if not merged.empty else holdings
        col_exec_charts = st.columns(2)
        with col_exec_charts[0]:
            # Donut chart for holdings value exposure
            fig_donut = px.pie(
                chart_df,
                names="Security",
                values="Current Value Rs",
                title="Current Portfolio Value Allocation",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_donut.update_layout(
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000"),
                legend=dict(font=dict(color="#000000"))
            )
            st.plotly_chart(fig_donut, width='stretch')

        with col_exec_charts[1]:
            # Gains/Losses Bar chart
            fig_pnl_bar = px.bar(
                chart_df.sort_values(by="PnL Rs", ascending=True),
                x="PnL Rs",
                y="Security",
                orientation="h",
                title="Absolute Holding-Level Gain/Loss (INR)",
                color="PnL Rs",
                color_continuous_scale="RdYlGn"
            )
            fig_pnl_bar.update_layout(
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000")
            )
            st.plotly_chart(fig_pnl_bar, width='stretch')

        # Day's Performance Bar Chart
        if (holdings["Day PnL"] != 0).any():
            st.write("")
            day_pnl_chart = alt.Chart(holdings).mark_bar().encode(
                x=alt.X("Day PnL:Q", title="Day's P&L (₹)"),
                y=alt.Y("Security:N", sort="-x", title="Security"),
                color=alt.condition(
                    alt.datum["Day PnL"] > 0,
                    alt.value("#48d66d"), # positive green
                    alt.value("#ef4444")  # negative red
                ),
                tooltip=[
                    "Security", 
                    alt.Tooltip("Day PnL", format=",.2f", title="Day PnL (₹)"), 
                    alt.Tooltip("Day PnL %", format="+.2f", title="Day Return (%)")
                ]
            ).properties(
                height=300,
                title="Last Performance Breakdown (Holding-Level Day's P&L)"
            )
            st.altair_chart(day_pnl_chart, width='stretch')

        st.divider()
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        summary_col1.metric("Holdings Count", len(holdings))
        summary_col2.metric("Average Weight", f"{avg_weight:.2f}%")
        summary_col3.metric("Top Exposure", top_sector_exposure)

        # Historical Progress Trend Line
        snapshots = HoldingsService.get_snapshot_summary()
        if len(snapshots) >= 2:
            st.divider()
            
            col_title, col_ctrl = st.columns([3, 1])
            with col_title:
                st.subheader("Historical Progress")
            with col_ctrl:
                view_mode = st.selectbox(
                    "Trend View Mode",
                    options=["All Uploads", "Monthly View", "Yearly View"],
                    index=0,
                    key="portfolio_trend_view_mode",
                    label_visibility="collapsed"
                )
            
            # Group snapshots based on view mode
            grouped_snaps = HoldingsService.group_snapshots_by_mode(snapshots, view_mode)
            
            df_snap = pd.DataFrame(grouped_snaps)
            if view_mode == "Monthly View":
                df_snap["Date"] = df_snap["date"].dt.strftime("%b %Y")
                x_title = "Month"
            elif view_mode == "Yearly View":
                df_snap["Date"] = df_snap["date"].dt.strftime("%Y")
                x_title = "Year"
            else:
                df_snap["Date"] = df_snap["date"].dt.strftime("%d-%b-%y")
                x_title = "Upload Date"
                
            df_melted = df_snap.melt(
                id_vars=["Date"],
                value_vars=["current", "invested", "pnl"],
                var_name="Metric",
                value_name="Value"
            )
            df_melted["Metric"] = df_melted["Metric"].map({
                "current": "Current Value",
                "invested": "Net Investment",
                "pnl": "Net Profit/Loss"
            })
            trend_chart = alt.Chart(df_melted).mark_bar().encode(
                x=alt.X("Date:N", sort=None, title=x_title),
                y=alt.Y("Value:Q", title="Value (₹)", stack=True),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(
                        domain=["Current Value", "Net Investment", "Net Profit/Loss"],
                        range=["#20d3c2", "#48d66d", "#ef4444"]
                    ),
                    legend=alt.Legend(title="Metric", labelColor="#000000", titleColor="#000000")
                ),
                tooltip=["Date:N", "Metric:N", alt.Tooltip("Value:Q", format=",.2f")]
            ).properties(
                height=350,
                title=f"Historical Progress: Stacked Allocation & Performance ({view_mode})"
            )
            st.altair_chart(trend_chart, width='stretch')
            
            st.markdown("### Historical Snapshot Data Summary")
            display_df_snap = df_snap.copy().sort_values(by="date", ascending=False)
            st.dataframe(
                display_df_snap,
                width='stretch',
                hide_index=True,
                column_config={
                    "Date": x_title,
                    "invested": st.column_config.NumberColumn("Net Investment (₹)", format="₹%,.2f"),
                    "current": st.column_config.NumberColumn("Current Value (₹)", format="₹%,.2f"),
                    "pnl": st.column_config.NumberColumn("Net Profit/Loss (₹)", format="₹%,.2f"),
                    "date": None # hide raw datetime column
                }
            )

    # --- Tab 2: Allocation & Risk ---
    with tab_allocation:
        st.subheader("Concentration Check & Diversification Gaps")
        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("✅ Concentration Risk: All stocks represent <20% and all sectors represent <40% of the portfolio. Good diversification!")

        st.subheader("Asset & Sector Group Allocations")
        alloc_mode = st.radio(
            "Group Allocation By:", 
            ["Asset Class", "Broker Sector", "Universe Sector (Requires Stock Screener Data)"], 
            horizontal=True
        )
        
        if alloc_mode == "Asset Class":
            asset_alloc = (
                holdings.groupby("Asset Class")["Current Value Rs"]
                .sum()
                .reset_index()
                .sort_values("Current Value Rs", ascending=False)
            )
            asset_alloc["Allocation %"] = asset_alloc["Current Value Rs"] / total_current * 100
            
            asset_chart = alt.Chart(asset_alloc).mark_bar().encode(
                x=alt.X("Allocation %:Q", title="Allocation (%)"),
                y=alt.Y("Asset Class:N", sort="-x", title="Asset Class"),
                color=alt.Color("Asset Class:N", scale=alt.Scale(scheme="category10"), legend=None),
                tooltip=[
                    "Asset Class", 
                    alt.Tooltip("Allocation %", format=".2f"), 
                    alt.Tooltip("Current Value Rs", format=",.0f", title="Value (₹)")
                ]
            ).properties(height=240, title="Allocation by Asset Class")
            
            st.altair_chart(asset_chart, width='stretch')
            st.markdown("### Allocation Details")
            st.dataframe(
                asset_alloc.rename(columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}),
                width='stretch',
                hide_index=True,
                column_config={
                    "Current Value": st.column_config.NumberColumn("Current Value (₹)", format="₹%,.2f"),
                    "Allocation %": st.column_config.NumberColumn("Allocation (%)", format="%.2f%%")
                }
            )
            
        elif alloc_mode == "Broker Sector":
            broker_alloc = (
                holdings.groupby("Broker Sector")["Current Value Rs"]
                .sum()
                .reset_index()
                .sort_values("Current Value Rs", ascending=False)
            )
            broker_alloc["Allocation %"] = broker_alloc["Current Value Rs"] / total_current * 100
            
            broker_chart = alt.Chart(broker_alloc).mark_bar().encode(
                x=alt.X("Allocation %:Q", title="Allocation (%)"),
                y=alt.Y("Broker Sector:N", sort="-x", title="Sector"),
                color=alt.Color("Broker Sector:N", scale=alt.Scale(scheme="tealblues"), legend=None),
                tooltip=[
                    "Broker Sector", 
                    alt.Tooltip("Allocation %", format=".2f"), 
                    alt.Tooltip("Current Value Rs", format=",.0f", title="Value (₹)")
                ]
            ).properties(height=350, title="Allocation by Broker Sector")
            
            st.altair_chart(broker_chart, width='stretch')
            st.markdown("### Allocation Details")
            st.dataframe(
                broker_alloc.rename(columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}),
                width='stretch',
                hide_index=True,
                column_config={
                    "Current Value": st.column_config.NumberColumn("Current Value (₹)", format="₹%,.2f"),
                    "Allocation %": st.column_config.NumberColumn("Allocation (%)", format="%.2f%%")
                }
            )
            
        else: # Universe Sector
            if require_data(merged, "Upload universe data in Stock Screener to enable allocation analytics."):
                merged["Sector"] = merged["Sub-Sector"].fillna("Unknown")
                merged["Current Value Rs"] = merged["Current Value Rs"].astype(float)

                allocation = (
                    merged.groupby("Sector", dropna=False)["Current Value Rs"]
                    .sum()
                    .reset_index()
                    .sort_values("Current Value Rs", ascending=False)
                )
                allocation["Allocation %"] = allocation["Current Value Rs"] / total_current * 100

                allocation_chart = alt.Chart(allocation).mark_bar().encode(
                    x=alt.X("Allocation %:Q", title="Allocation (%)"),
                    y=alt.Y("Sector:N", sort="-x"),
                    tooltip=[
                        "Sector",
                        alt.Tooltip("Allocation %", format=".2f"),
                        alt.Tooltip("Current Value Rs", format=",.0f"),
                    ],
                ).properties(height=350, title="Sector Allocation (Universe)")

                allocation_table = allocation.rename(
                    columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}
                )

                st.altair_chart(allocation_chart, width='stretch')
                st.markdown("### Allocation Details")
                st.dataframe(
                    allocation_table, 
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Current Value": st.column_config.NumberColumn("Current Value (₹)", format="₹%,.2f"),
                        "Allocation %": st.column_config.NumberColumn("Allocation (%)", format="%.2f%%")
                    }
                )

                st.markdown("### Portfolio Gaps (Sector Coverage)")
                universe = load_universe()
                if not universe.empty:
                    all_sectors = set(universe["Sub-Sector"].dropna().unique())
                    have_sectors = set(merged["Sub-Sector"].dropna().unique())
                    missing_sectors = sorted(list(all_sectors - have_sectors))
                    have_sectors_sorted = sorted(list(have_sectors))

                    have_html = "".join([
                        f'<span style="background: rgba(72, 214, 109, 0.12); color: #48d66d; border: 1px solid rgba(72, 214, 109, 0.3); border-radius: 4px; padding: 6px 12px; margin: 4px; display: inline-block; font-size: 0.85rem; font-weight: 500;">{s}</span>'
                        for s in have_sectors_sorted
                    ])
                    if not have_html:
                        have_html = '<span style="color: #94a3b8; font-size: 0.85rem; font-style: italic;">No sectors currently held.</span>'

                    missing_html = "".join([
                        f'<span style="background: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; padding: 6px 12px; margin: 4px; display: inline-block; font-size: 0.85rem; font-weight: 500;">{s}</span>'
                        for s in missing_sectors
                    ])
                    if not missing_html:
                        missing_html = '<span style="background: rgba(72, 214, 109, 0.12); color: #48d66d; border: 1px solid rgba(72, 214, 109, 0.3); border-radius: 4px; padding: 6px 12px; margin: 4px; display: inline-block; font-size: 0.85rem; font-weight: 500;">✓ Fully Diversified</span>'

                    gaps_layout = f"""
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; margin-bottom: 25px;">
                        <div style="background: rgba(255, 255, 255, 0.45); border: 1px solid rgba(255, 255, 255, 0.5); border-radius: 8px; padding: 18px; min-height: 120px;">
                            <div style="font-weight: 700; color: #16a34a; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center;">
                                <span style="margin-right: 8px;">🟢</span> Sectors in Portfolio ({len(have_sectors_sorted)})
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                                {have_html}
                            </div>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.45); border: 1px solid rgba(255, 255, 255, 0.5); border-radius: 8px; padding: 18px; min-height: 120px;">
                            <div style="font-weight: 700; color: #dc2626; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center;">
                                <span style="margin-right: 8px;">🔴</span> Missing Sectors (Gaps) ({len(missing_sectors)})
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                                {missing_html}
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(gaps_layout, unsafe_allow_html=True)
        
        st.divider()
        contribution = (
            holdings.groupby("Security", dropna=False)["PnL Rs"]
            .sum()
            .reset_index()
            .sort_values("PnL Rs", ascending=False)
        )
        contribution_chart = alt.Chart(contribution.head(10)).mark_bar().encode(
            x=alt.X("PnL Rs:Q", title="PnL Rs"),
            y=alt.Y("Security:N", sort="-x"),
            tooltip=["Security", alt.Tooltip("PnL Rs", format=",.0f")],
        ).properties(height=360, title="Top Contributors to P&L")

        st.markdown("### Top P&L Contributors")
        st.altair_chart(contribution_chart, width='stretch')

    # --- Tab 3: Fundamentals Audit & Health ---
    with tab_health:
        st.subheader("Holdings Financial Health & Quality Audit")

        health_col1, health_col2, health_col3 = st.columns(3)
        health_col1.metric("Health Score", f"{health:.1f}/100")
        health_col2.metric("Avg Stock Quality", f"{avg_quality:.1f}/100")
        health_col3.metric("Sector Diversity", sector_count)
        
        with health_col1:
            with st.popover("❓ How is this calculated?"):
                st.markdown("""
                ### 📊 Portfolio Health Calculation
                The health score is computed out of **100 points** based on the following rules:
                
                1. **Diversification (Max 25 pts):**
                   - `min(number_of_holdings * 2, 25)`
                2. **Concentration Control (Max 25 pts):**
                   - **25 points** if no single stock exceeds `25%` weight.
                   - **10 points** if any stock exceeds `25%` weight (concentration penalty).
                3. **Sector Diversity (Max 20 pts):**
                   - `min(unique_sectors * 2, 20)`
                4. **Average Quality (Max 20 pts):**
                   - `(average_portfolio_quality / 100) * 20`
                5. **Cash Buffer (Fixed 10 pts):**
                   - Fixed 10 points for liquidity buffer.
                """)

        st.write("")
        
        if require_data(merged, "Upload Stock Universe metadata in Stock Screener to review holdings fundamentals."):
            merged["Sector"] = merged["Sub-Sector"].fillna("Unknown")
            merged["QUALITY_SCORE"] = merged["QUALITY_SCORE"].fillna(0).astype(float)
            available_cols = [c for c in ["Security", "QUALITY_SCORE", "ROCE", "Return on Equity", "Debt to Equity", "5Y CAGR", "PE Ratio", "Fundamental Score"] if c in merged.columns]
            audit_df = merged[available_cols].copy()
            st.dataframe(
                audit_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "Security": "Ticker Symbol",
                    "QUALITY_SCORE": st.column_config.NumberColumn("Quality Rating", format="%.0f/100"),
                    "ROCE": st.column_config.NumberColumn("ROCE (%)", format="%.1f%%"),
                    "Return on Equity": st.column_config.NumberColumn("Return on Equity (%)", format="%.1f%%"),
                    "Debt to Equity": st.column_config.NumberColumn("D/E Ratio", format="%.2f"),
                    "5Y CAGR": st.column_config.NumberColumn("5Y CAGR (%)", format="%.1f%%"),
                    "PE Ratio": st.column_config.NumberColumn("PE Ratio", format="%.2f"),
                    "Fundamental Score": st.column_config.NumberColumn("Fundamental Score", format="%.1f")
                }
            )

            # Scatter plot: PE Ratio vs. Quality Score
            fig_scatter = px.scatter(
                merged,
                x="QUALITY_SCORE",
                y="PE Ratio",
                text="Security",
                size="Current Value Rs",
                color="Sub-Sector" if "Sub-Sector" in merged.columns else None,
                title="Holdings Value: Valuation (P/E) vs. Quality Score (Size of bubble represents holding value)",
                hover_data=[c for c in ["Security", "ROCE", "Return on Equity", "Debt to Equity"] if c in merged.columns]
            )
            fig_scatter.update_layout(
                height=400,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000"),
                legend=dict(font=dict(color="#000000"))
            )
            st.plotly_chart(fig_scatter, width='stretch')

            st.subheader("Sector Quality and P&L Breakdown")
            
            col_quality_charts = st.columns(2)
            with col_quality_charts[0]:
                quality_by_sector = (
                    merged.groupby("Sector", dropna=False)["QUALITY_SCORE"]
                    .mean()
                    .reset_index()
                    .sort_values("QUALITY_SCORE", ascending=False)
                )
                fig_qual_sec = px.scatter(
                    quality_by_sector,
                    x="QUALITY_SCORE",
                    y="Sector",
                    color="QUALITY_SCORE",
                    title="Average Quality Score by Sector",
                    color_continuous_scale="Viridis"
                )
                fig_qual_sec.update_layout(
                    height=360,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#000000")
                )
                st.plotly_chart(fig_qual_sec, width='stretch')

            with col_quality_charts[1]:
                performance = merged.copy()
                performance["PnL %"] = (
                    (performance["Current Value Rs"] - performance["Invested Value Rs"]) /
                    performance["Invested Value Rs"].replace({0: pd.NA}) * 100
                ).fillna(0)
                performance_category = performance.groupby("Sector", dropna=False)["PnL %"].mean().reset_index()
                fig_perf_sec = px.bar(
                    performance_category,
                    x="PnL %",
                    y="Sector",
                    orientation="h",
                    title="Average Sector P&L %",
                    color="PnL %",
                    color_continuous_scale="RdYlGn"
                )
                fig_perf_sec.update_layout(
                    height=360,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#000000")
                )
                st.plotly_chart(fig_perf_sec, width='stretch')

            st.markdown(
                "### Health Analysis Notes"
                "\n- Health score uses quality and sector diversification to highlight portfolio resilience."
                "\n- Quality scores are averaged by sector to identify stronger exposures."
                "\n- Sector-level P&L percent offers a view of portfolio performance across exposures."
            )
        else:
            st.info("Portfolio health metrics require universe metadata uploaded in Stock Screener.")

    # --- Tab 4: Export PDF Report ---
    with tab_export:
        st.subheader("📥 Export Executive Report (PDF)")
        st.write("Generate a formal, publication-ready PDF report summary of your portfolio for presentation or archives.")
        
        # Recommendations df is needed by summary dictionary
        recommendations_df = RecommendationService.generate(universe) if not universe.empty else pd.DataFrame()
        summary = ReportService.generate(holdings, health, recommendations_df)
        summary["concentration_warnings"] = warnings
        
        col_preview = st.columns([1, 2])
        with col_preview[0]:
            st.info("📄 **Report Structure Preview:**\n- **Page 1:** Executive Summary, P&L Metrics, and Top Holdings Breakdown Table.\n- **Page 2:** Risk Concentration warnings, Market Cap alignment checklist, and top investment recommendations from the universe.")
            
            if "pdf_ready" not in st.session_state:
                st.session_state.pdf_ready = False
                
            if not st.session_state.pdf_ready:
                if st.button("Generate PDF Report", width='stretch', key="gen_pdf_btn_holdings_page"):
                    st.session_state.pdf_ready = True
                    st.rerun()
            else:
                pdf_data = ReportService.generate_pdf(summary)
                st.download_button(
                    label="📥 Download Executive Portfolio PDF Report",
                    data=pdf_data,
                    file_name="investiq_portfolio_report.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="download_pdf_btn_holdings_page"
                )
                st.write("")
                if st.button("Clear / Regenerate", width='stretch', key="clear_pdf_btn_holdings_page"):
                    st.session_state.pdf_ready = False
                    st.rerun()
