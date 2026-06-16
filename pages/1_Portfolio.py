# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import pandas as pd
import streamlit as st

from services.health_service import HealthService
from services.holdings_service import HoldingsService
from utils.page_utils import load_holdings, load_universe, merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")

from utils.page_utils import require_auth
require_auth()

render_sidebar()

st.title("Holdings & Portfolio Analysis")
st.write(
    "A unified portfolio view that combines holdings details, allocation insights, and health metrics. "
    "Use the tabs below to explore overview, allocation, and performance analysis."
)

file = st.file_uploader("Upload Holdings", type=["csv", "xlsx"])
if file:
    rows = HoldingsService.upload(file)
    st.success(f"{rows} holdings uploaded")

holdings = load_holdings()
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

    total_invested = holdings["Invested Value Rs"].sum()
    total_current = holdings["Current Value Rs"].sum()
    total_pnl = holdings["PnL Rs"].sum()
    total_day_pnl = holdings["Day PnL"].sum()
    avg_day_pnl_pct = holdings["Day PnL %"].mean()
    
    return_pct = ((total_current - total_invested) / total_invested * 100) if total_invested else 0
    avg_weight = holdings["Portfolio Weight %"].mean()
    if not merged.empty and "Sub-Sector" in merged.columns:
        mode_values = merged["Sub-Sector"].dropna().mode()
        top_sector_exposure = mode_values.iloc[0] if not mode_values.empty else "N/A"
    else:
        top_sector_exposure = "N/A"

    tab_overview, tab_allocation, tab_health = st.tabs(
        ["Overview", "Allocation", "Health"]
    )

    with tab_overview:
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Invested Value", f"₹{total_invested:,.0f}")
        metric_col2.metric("Current Value", f"₹{total_current:,.0f}")
        metric_col3.metric("Total P&L", f"₹{total_pnl:,.0f}")
        metric_col4.metric("Portfolio Return", f"{return_pct:.2f}%")
        metric_col5.metric("Day's P&L", f"₹{total_day_pnl:,.0f}", delta=f"{avg_day_pnl_pct:+.2f}%")

        st.divider()
        st.subheader("Current holding")
        st.dataframe(
            holdings,
            use_container_width=True,
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
            st.altair_chart(day_pnl_chart, use_container_width=True)

        summary_col1, summary_col2, summary_col3 = st.columns(3)
        summary_col1.metric("Holdings Count", len(holdings))
        summary_col2.metric("Average Weight", f"{avg_weight:.2f}%")
        summary_col3.metric("Top Exposure", top_sector_exposure)

        # Historical Progress Trend Line
        snapshots = HoldingsService.get_snapshot_summary()
        if len(snapshots) >= 2:
            st.divider()
            st.subheader("Historical Progress")
            df_snap = pd.DataFrame(snapshots)
            df_snap["Date"] = df_snap["date"].dt.strftime("%d-%b-%y")
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
                x=alt.X("Date:N", sort=None, title="Upload Date"),
                y=alt.Y("Value:Q", title="Value (₹)", stack=True),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(
                        domain=["Current Value", "Net Investment", "Net Profit/Loss"],
                        range=["#20d3c2", "#48d66d", "#ef4444"]
                    ),
                    legend=alt.Legend(title="Metric")
                ),
                tooltip=["Date:N", "Metric:N", alt.Tooltip("Value:Q", format=",.2f")]
            ).properties(
                height=350,
                title="Historical Progress: Stacked Allocation & Performance (Last 15 Uploads)"
            )
            st.altair_chart(trend_chart, use_container_width=True)
            
            st.markdown("### Historical Snapshot Data Summary")
            display_df_snap = df_snap.copy().sort_values(by="date", ascending=False)
            st.dataframe(
                display_df_snap,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": "Upload Date",
                    "invested": st.column_config.NumberColumn("Net Investment (₹)", format="₹%,.2f"),
                    "current": st.column_config.NumberColumn("Current Value (₹)", format="₹%,.2f"),
                    "pnl": st.column_config.NumberColumn("Net Profit/Loss (₹)", format="₹%,.2f"),
                    "date": None # hide raw datetime column
                }
            )

    with tab_allocation:
        st.subheader("Allocation Insights")
        
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
            
            st.altair_chart(asset_chart, use_container_width=True)
            st.markdown("### Allocation Details")
            st.dataframe(
                asset_alloc.rename(columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}),
                use_container_width=True,
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
            
            st.altair_chart(broker_chart, use_container_width=True)
            st.markdown("### Allocation Details")
            st.dataframe(
                broker_alloc.rename(columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}),
                use_container_width=True,
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
                ).properties(height=420, title="Sector Allocation (Universe)")

                allocation_table = allocation.rename(
                    columns={"Current Value Rs": "Current Value", "Allocation %": "Allocation %"}
                )

                st.altair_chart(allocation_chart, use_container_width=True)
                st.markdown("### Allocation Details")
                st.dataframe(
                    allocation_table, 
                    use_container_width=True,
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
                        <div style="background: #0e1624; border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 8px; padding: 18px; min-height: 120px;">
                            <div style="font-weight: 700; color: #48d66d; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center;">
                                <span style="margin-right: 8px;">🟢</span> Sectors in Portfolio ({len(have_sectors_sorted)})
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                                {have_html}
                            </div>
                        </div>
                        <div style="background: #0e1624; border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 8px; padding: 18px; min-height: 120px;">
                            <div style="font-weight: 700; color: #ef4444; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center;">
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
        st.altair_chart(contribution_chart, use_container_width=True)

    with tab_health:
        st.subheader("Portfolio Health & Quality")

        if require_data(merged, "Upload universe data in Stock Screener to enable health analytics."):
            merged["Sector"] = merged["Sub-Sector"].fillna("Unknown")
            merged["QUALITY_SCORE"] = merged["QUALITY_SCORE"].fillna(0).astype(float)

            avg_quality = merged["QUALITY_SCORE"].mean()
            sector_count = merged["Sector"].nunique()
            health_score = HealthService.evaluate(holdings, avg_quality, sector_count)

            health_col1, health_col2, health_col3 = st.columns(3)
            health_col1.metric("Health Score", f"{health_score:.1f}")
            health_col2.metric("Avg Quality Score", f"{avg_quality:.2f}")
            health_col3.metric("Sector Diversity", sector_count)

            quality_by_sector = (
                merged.groupby("Sector", dropna=False)["QUALITY_SCORE"]
                .mean()
                .reset_index()
                .sort_values("QUALITY_SCORE", ascending=False)
            )
            quality_chart = alt.Chart(quality_by_sector).mark_circle(size=120).encode(
                x=alt.X("QUALITY_SCORE:Q", title="Avg Quality Score"),
                y=alt.Y("Sector:N", sort="-x"),
                color=alt.Color("QUALITY_SCORE:Q", scale=alt.Scale(scheme="tealblues")),
                tooltip=["Sector", alt.Tooltip("QUALITY_SCORE", format=".2f")],
            ).properties(height=420, title="Quality Score by Sector")

            performance = merged.copy()
            performance["PnL %"] = (
                (performance["Current Value Rs"] - performance["Invested Value Rs"]) /
                performance["Invested Value Rs"].replace({0: pd.NA}) * 100
            ).fillna(0)
            performance_category = performance.groupby("Sector", dropna=False)["PnL %"].mean().reset_index()
            performance_chart = alt.Chart(performance_category).mark_bar().encode(
                x=alt.X("PnL %:Q", title="Avg PnL %"),
                y=alt.Y("Sector:N", sort="-x"),
                color=alt.condition(alt.datum["PnL %"] > 0, alt.value("#2ca02c"), alt.value("#d62728")),
                tooltip=["Sector", alt.Tooltip("PnL %", format=".2f")],
            ).properties(height=420, title="Average Sector P&L %")

            st.altair_chart(quality_chart, use_container_width=True)
            st.altair_chart(performance_chart, use_container_width=True)

            st.markdown(
                "### Health Analysis Notes"
                "\n- Health score uses quality and sector diversification to highlight portfolio resilience."
                "\n- Quality scores are averaged by sector to identify stronger exposures."
                "\n- Sector-level P&L percent offers a view of portfolio performance across exposures."
            )
        else:
            st.info("Portfolio health metrics require universe metadata uploaded in Stock Screener.")
