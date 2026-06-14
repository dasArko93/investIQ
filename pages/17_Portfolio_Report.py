# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st
import plotly.express as px

from services.health_service import HealthService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from utils.page_utils import load_holdings, load_universe, merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ - Executive Portfolio Report", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("📊 Executive Portfolio Report")
st.write("Generate, review, and download a publication-quality executive summary report of your equity portfolio.")

portfolio = load_holdings()
universe = load_universe()
merged = merged_holdings()

if require_data(portfolio, "Upload holdings to generate a report."):
    
    # -------------------------------------------------------------
    # 1. Calculation & Preparation
    # -------------------------------------------------------------
    avg_quality = merged["QUALITY_SCORE"].fillna(0).mean() if not merged.empty else 0.0
    sector_count = merged["Sub-Sector"].nunique() if not merged.empty else 0
    health = HealthService.evaluate(portfolio, avg_quality, sector_count)
    
    recommendations_df = RecommendationService.generate(universe) if not universe.empty else pd.DataFrame()
    
    # Generate the base summary dictionary
    summary = ReportService.generate(portfolio, health, recommendations_df)
    
    # Calculate additional metrics for display and PDF
    total_invested = float(portfolio["Invested Value Rs"].sum())
    total_current = float(portfolio["Current Value Rs"].sum())
    total_pnl = total_current - total_invested
    pnl_pct = (total_pnl / total_invested * 100.0) if total_invested > 0 else 0.0
    
    # Calculate concentration warnings
    warnings = []
    if not merged.empty:
        merged["Weight %"] = (merged["Current Value Rs"] / total_current) * 100.0
        
        # Max stock weight
        max_stock_w = merged["Weight %"].max()
        max_stock_row = merged.loc[merged["Weight %"] == max_stock_w].iloc[0]
        if max_stock_w > 20:
            warnings.append(f"Stock Concentration is HIGH. '{max_stock_row['Security']}' represents {max_stock_w:.1f}% of your portfolio.")
        elif max_stock_w >= 10:
            warnings.append(f"Stock Concentration is MODERATE. '{max_stock_row['Security']}' represents {max_stock_w:.1f}% of your portfolio.")
            
        # Max sector weight
        sec_allocs = merged.groupby("Sub-Sector")["Current Value Rs"].sum()
        sec_pcts = (sec_allocs / total_current) * 100.0
        max_sec_w = sec_pcts.max()
        max_sec_name = sec_pcts.idxmax()
        if max_sec_w > 40:
            warnings.append(f"Sector Concentration is HIGH. '{max_sec_name}' represents {max_sec_w:.1f}% of your portfolio.")
        elif max_sec_w >= 25:
            warnings.append(f"Sector Concentration is MODERATE. '{max_sec_name}' represents {max_sec_w:.1f}% of your portfolio.")
            
    summary["concentration_warnings"] = warnings
    
    # -------------------------------------------------------------
    # 2. Render KPI Summary Cards
    # -------------------------------------------------------------
    metric_cols = st.columns(5)
    metric_cols[0].metric("Net Portfolio Value", f"₹{total_current:,.2f}")
    metric_cols[1].metric("Invested Capital", f"₹{total_invested:,.2f}")
    
    pnl_label = "Total Gain/Loss (Absolute)"
    metric_cols[2].metric(
        pnl_label, 
        f"₹{total_pnl:,.2f}", 
        delta=f"{pnl_pct:+.2f}%", 
        delta_color="normal"
    )
    
    metric_cols[3].metric("Portfolio Health Score", f"{health:.1f}/100")
    metric_cols[4].metric("Average Stock Quality", f"{avg_quality:.1f}/100")
    
    st.divider()
    
    # -------------------------------------------------------------
    # 3. Interactive Report Tabs
    # -------------------------------------------------------------
    tab_overview, tab_risk, tab_quality, tab_download = st.tabs([
        "📈 Executive Summary",
        "⚠️ Risk & Diversification Check",
        "🔍 Holdings Fundamentals Audit",
        "📥 Export PDF Report"
    ])
    
    # --- Tab 1: Executive Summary ---
    with tab_overview:
        st.subheader("Holdings Analysis & Allocation Exposure")
        
        col_charts = st.columns([1, 1])
        with col_charts[0]:
            # Donut chart for holdings value exposure
            fig_donut = px.pie(
                merged,
                names="Security",
                values="Current Value Rs",
                title="Current Portfolio Value Allocation",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_donut.update_layout(
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1")
            )
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with col_charts[1]:
            # Gains/Losses Bar chart
            fig_pnl_bar = px.bar(
                merged.sort_values(by="PnL Rs", ascending=True),
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
                font=dict(color="#cbd5e1")
            )
            st.plotly_chart(fig_pnl_bar, use_container_width=True)
            
        st.markdown("### Portfolio Holdings Details")
        st.dataframe(
            portfolio,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Security": "Security",
                "No. of Smallcases": st.column_config.NumberColumn("No. of Smallcases", format="%d"),
                "Quantity": "Quantity",
                "Average Cost Rs": st.column_config.NumberColumn("Average Cost ₹", format="₹%.2f"),
                "Portfolio Weight %": st.column_config.NumberColumn("Portfolio Weight %", format="%.2f%%"),
                "LTP Rs": st.column_config.NumberColumn("LTP ₹", format="₹%.2f"),
                "Invested Value Rs": st.column_config.NumberColumn("Invested Value ₹", format="₹%.2f"),
                "Current Value Rs": st.column_config.NumberColumn("Current Value ₹", format="₹%.2f"),
                "PnL Rs": st.column_config.NumberColumn("P & L ₹", format="₹%.2f"),
                "PnL %": st.column_config.NumberColumn("Net Change %", format="%.2f%%"),
                "Day PnL": st.column_config.NumberColumn("Daily Change ₹", format="₹%.2f"),
                "Day PnL %": st.column_config.NumberColumn("Daily Change %", format="%.2f%%"),
            }
        )

    # --- Tab 2: Risk & Diversification Check ---
    with tab_risk:
        st.subheader("Concentration Check & Diversification Gaps")
        
        # Display warnings if present
        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("✅ Concentration Risk: All stocks represent <20% and all sectors represent <40% of the portfolio. Good diversification!")
            
        col_risk_breakdown = st.columns(2)
        with col_risk_breakdown[0]:
            st.markdown("##### Sector Exposure Allocation")
            sec_df = merged.groupby("Sub-Sector")["Current Value Rs"].sum().reset_index()
            sec_df["Weight %"] = (sec_df["Current Value Rs"] / total_current) * 100.0
            sec_df = sec_df.sort_values(by="Weight %", ascending=False)
            
            fig_sec_bar = px.bar(
                sec_df,
                x="Weight %",
                y="Sub-Sector",
                orientation="h",
                title="Sector Allocation Weights",
                color="Weight %",
                color_continuous_scale="Viridis"
            )
            fig_sec_bar.update_layout(
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1")
            )
            st.plotly_chart(fig_sec_bar, use_container_width=True)
            
        with col_risk_breakdown[1]:
            st.markdown("##### Market Cap Balance Checklist")
            mc_allocs = merged.groupby("Market Cap")["Current Value Rs"].sum().reset_index() if "Market Cap" in merged.columns else pd.DataFrame()
            if not mc_allocs.empty:
                mc_allocs["Weight %"] = (mc_allocs["Current Value Rs"] / total_current) * 100.0
                st.dataframe(
                    mc_allocs,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Market Cap": "Cap Size",
                        "Current Value Rs": st.column_config.NumberColumn("Current Value (₹)", format="₹%.2f"),
                        "Weight %": st.column_config.NumberColumn("Allocation Weight", format="%.2f%%")
                    }
                )
            else:
                st.info("Market Cap details require Stock Universe metadata uploaded.")

    # --- Tab 3: Holdings Fundamentals Audit ---
    with tab_quality:
        st.subheader("Holdings Financial Health & Quality Metrics")
        
        if require_data(merged, "Upload Stock Universe metadata in Stock Screener to review holdings fundamentals."):
            audit_df = merged[["Security", "QUALITY_SCORE", "ROCE", "Debt to Equity", "5Y Historical Revenue Growth", "PE Ratio", "Sector PE"]].copy()
            st.dataframe(
                audit_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Security": "Ticker Symbol",
                    "QUALITY_SCORE": st.column_config.NumberColumn("Quality Rating", format="%.0f/100"),
                    "ROCE": st.column_config.NumberColumn("ROCE (%)", format="%.1f%%"),
                    "Debt to Equity": st.column_config.NumberColumn("D/E Ratio", format="%.2f"),
                    "5Y Historical Revenue Growth": st.column_config.NumberColumn("5Y Rev Growth (%)", format="%.1f%%"),
                    "PE Ratio": st.column_config.NumberColumn("PE Ratio", format="%.2f"),
                    "Sector PE": st.column_config.NumberColumn("Sector PE", format="%.2f")
                }
            )
            
            # Scatter plot: PE Ratio vs. Quality Score
            fig_scatter = px.scatter(
                merged,
                x="QUALITY_SCORE",
                y="PE Ratio",
                text="Security",
                size="Current Value Rs",
                color="Sub-Sector",
                title="Holdings Value: Valuation (P/E) vs. Quality Score (Size of bubble represents holding value)",
                hover_data=["Security", "ROCE", "Debt to Equity"]
            )
            fig_scatter.update_layout(
                height=400,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1")
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    # --- Tab 4: Export PDF Report ---
    with tab_download:
        st.subheader("📥 Export Executive Report (PDF)")
        st.write("Generate a formal, publication-ready PDF report summary of your portfolio for presentation or archives.")
        
        col_preview = st.columns([1, 2])
        with col_preview[0]:
            st.info("📄 **Report Structure Preview:**\n- **Page 1:** Executive Summary, P&L Metrics, and Top Holdings Breakdown Table.\n- **Page 2:** Risk Concentration warnings, Market Cap alignment checklist, and top investment recommendations from the universe.")
            
            if "pdf_ready" not in st.session_state:
                st.session_state.pdf_ready = False
                
            if not st.session_state.pdf_ready:
                if st.button("Generate PDF Report", use_container_width=True):
                    st.session_state.pdf_ready = True
                    st.rerun()
            else:
                pdf_data = ReportService.generate_pdf(summary)
                st.download_button(
                    label="📥 Download Executive Portfolio PDF Report",
                    data=pdf_data,
                    file_name="investiq_portfolio_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                if st.button("Clear / Regenerate", use_container_width=True):
                    st.session_state.pdf_ready = False
                    st.rerun()