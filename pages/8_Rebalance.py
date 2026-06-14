# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from services.rebalance_service import RebalanceService
from utils.page_utils import merged_holdings, require_data, render_sidebar, load_universe


st.set_page_config(page_title="InvestIQ - Rebalancing Strategy", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("⚖️ Portfolio Rebalancing Engine")
st.write("Assess weight drift, concentration risks, market cap alignment, and simulate capital allocations based on Tickertape management principles.")

portfolio = merged_holdings()

if require_data(portfolio, "Upload both holdings and stock universe to generate rebalancing recommendations."):
    
    unique_sectors = sorted([str(s) for s in portfolio["Sub-Sector"].dropna().unique()])
    
    # -------------------------------------------------------------
    # 1. Configure Target Sector Allocations
    # -------------------------------------------------------------
    st.subheader("1. Configure Target Sector Allocations")
    st.write("Define target weights for each sector. The allocations must sum to 100% for correct drift calculation.")
    
    # Initialize target weights equally if not in session state
    if "target_sector_df" not in st.session_state or not all(sec in st.session_state["target_sector_df"]["Sector"].values for sec in unique_sectors):
        n_sec = len(unique_sectors)
        eq_w = round(100.0 / n_sec, 1) if n_sec > 0 else 0.0
        init_rows = [{"Sector": sec, "Target Weight %": eq_w} for sec in unique_sectors]
        st.session_state["target_sector_df"] = pd.DataFrame(init_rows)
        
    edited_sector_df = st.data_editor(
        st.session_state["target_sector_df"],
        use_container_width=True,
        hide_index=True,
        key="target_sector_editor"
    )
    st.session_state["target_sector_df"] = edited_sector_df
    
    total_target_w = edited_sector_df["Target Weight %"].sum()
    if abs(total_target_w - 100.0) > 0.5:
        st.warning(f"⚠️ Total target weight is **{total_target_w:.1f}%**. Target allocations should sum to exactly **100%**.")
        
    # -------------------------------------------------------------
    # 2. Portfolio Strategy & Risk Settings
    # -------------------------------------------------------------
    st.subheader("2. Rebalancing Strategy Settings")
    
    sett_cols = st.columns(3)
    with sett_cols[0]:
        risk_profile = st.selectbox("Risk Profile (Ideal Market Cap Targets)", ["Conservative", "Moderate", "Aggressive"], index=1)
        rebalance_mode = st.selectbox("Rebalance Mode", ["Hybrid", "Time-Based", "Threshold-Based"], index=0, help="Hybrid triggers rebalance only on review date if threshold is breached. Time-Based reviews periodically. Threshold checks drift constantly.")
        rebalance_level = st.selectbox("Rebalancing Level Focus", ["Stock-Level", "Sector-Level"], index=0, help="Stock-Level focuses on individual stock targets. Sector-Level focuses on sector-wide allocation targets with sector-grouped actions.")
    with sett_cols[1]:
        max_stock = st.slider("Max Permitted Stock Weight (%)", 5.0, 40.0, 15.0, step=1.0)
        max_sector = st.slider("Max Permitted Sector Weight (%)", 10.0, 60.0, 30.0, step=1.0)
    with sett_cols[2]:
        threshold = st.slider("Rebalance Drift Threshold (%)", 1.0, 15.0, 5.0, step=0.5, help="Alert when current weight deviates from target by more than this limit.")
        frequency = st.selectbox("Rebalance Frequency", ["Monthly", "Quarterly", "SemiAnnual", "Annual"], index=1)
        
    adv_cols = st.columns(3)
    with adv_cols[0]:
        smart_rebal = st.checkbox("Smart Rebalancing (Avoid selling high-quality compounders: ROCE >20%, D/E <0.5, Growth >15%)", value=True)
    with adv_cols[1]:
        mom_override = st.checkbox("Momentum Override (Allow winners to run: double threshold for trending holdings)", value=False)
    with adv_cols[2]:
        allow_new_stocks = st.checkbox("Rebalance by Buying New Stocks (Allow unowned high-quality stocks in missing/underweight sectors)", value=True)
        
    # -------------------------------------------------------------
    # 3. New Capital Input & Simulator
    # -------------------------------------------------------------
    st.subheader("3. Rebalancing Simulator")
    new_capital_input = st.number_input("Simulate Additional Cash Deployment (₹)", min_value=0, value=0, step=10000, help="Deploy fresh capital directly into underweight holdings to restore target weights without incurring capital gains tax (STCG) from selling.")

    # -------------------------------------------------------------
    # 4. Process Engine Calculations
    # -------------------------------------------------------------
    target_sector_allocation = dict(zip(edited_sector_df["Sector"], edited_sector_df["Target Weight %"]))
    
    strategy = {
        "targetSectorAllocation": target_sector_allocation,
        "maxStockAllocation": max_stock,
        "maxSectorAllocation": max_sector,
        "rebalanceThresholdPercent": threshold,
        "riskProfile": risk_profile,
        "rebalanceFrequency": frequency,
        "rebalanceMode": rebalance_mode,
        "smartRebalancing": smart_rebal,
        "momentumOverride": mom_override,
        "allowNewStocks": allow_new_stocks,
        "rebalanceLevel": rebalance_level
    }
    
    # Run the Engine
    res = RebalanceService.generate(portfolio, strategy, float(new_capital_input), load_universe())
    
    # Render Prominent Investment Committee Summary
    st.info(f"💡 **Committee Rebalancing Summary:** {res['summary']}")
    
    # -------------------------------------------------------------
    # 5. Core Dashboard KPI Cards
    # -------------------------------------------------------------
    kpi_cols = st.columns(5)
    
    # Portfolio Health
    h_score = res["portfolioHealthScore"]
    kpi_cols[0].metric(
        "Portfolio Health",
        f"{h_score}/100",
        help="Overall score combining diversification, concentration risk, and rebalance drift. Higher is healthier."
    )
    # Diversification Score
    kpi_cols[1].metric(
        "Diversification Score",
        f"{res['diversificationScore']}/100",
        help="Based on Herfindahl-Hirschman index (HHI) of current weights. High score represents healthy asset spreading."
    )
    # Sector Concentration Score
    kpi_cols[2].metric(
        "Sector Concentration",
        f"{res['sectorConcentrationScore']}/100",
        help="Measures concentration risk across sectors. Lower scores flag high concentration in single sectors."
    )
    # Market Cap Balance
    kpi_cols[3].metric(
        "Market Cap Balance",
        f"{res['marketCapBalanceScore']}/100",
        help="Measures alignment of current Large, Mid, and Small Cap allocations against the targets of your chosen risk profile."
    )
    # Urgency Score
    u_score = res["rebalancingUrgencyScore"]
    kpi_cols[4].metric(
        "Rebalancing Urgency",
        f"{u_score}/100",
        help="Indicates severity of target allocation deviations. Higher scores require immediate action."
    )
    
    st.divider()
    
    # -------------------------------------------------------------
    # 6. Dashboard Tabs for Visualizations & Recommendations
    # -------------------------------------------------------------
    t_drift, t_alloc, t_recs, t_sim, t_json = st.tabs([
        "Drift & Heatmaps", 
        "Allocation Treemaps", 
        "Action Plan", 
        "Capital Deployment Simulator", 
        "Structured JSON Output"
    ])
    
    # --- TAB 1: DRIFT ANALYSIS & HEATMAPS ---
    with t_drift:
        st.subheader("Sector Allocation & Drift Analysis")
        
        # Build Sector Drift Dataframe
        drift_df = pd.DataFrame(res["sectorRecommendations"])
        if not drift_df.empty:
            drift_cols = st.columns([2, 1])
            with drift_cols[0]:
                # Plotly Drift Bar Chart
                fig_drift = go.Figure()
                fig_drift.add_trace(go.Bar(
                    name='Current Weight %',
                    x=drift_df['sector'],
                    y=drift_df['currentWeight'],
                    marker_color='#cbd5e1'
                ))
                fig_drift.add_trace(go.Bar(
                    name='Target Weight %',
                    x=drift_df['sector'],
                    y=drift_df['targetWeight'],
                    marker_color='#20d3c2'
                ))
                fig_drift.update_layout(
                    title="Current vs Target Sector Weights",
                    barmode='group',
                    height=360,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_drift, use_container_width=True)
            
            with drift_cols[1]:
                st.markdown("**Sector Drift Heatmap**")
                # Format heatmap table with color codes and true background color heatmap cell styling
                def color_drift(val):
                    # Red for positive drift (overweight), green/teal for negative drift (underweight)
                    # Opacity scales with the absolute drift value to form a visual heatmap
                    opacity = min(0.4, max(0.1, abs(val) / 15.0))
                    if val < 0:
                        bg_color = f"rgba(32, 211, 194, {opacity})"
                        text_color = "#20d3c2"
                    else:
                        bg_color = f"rgba(239, 68, 68, {opacity})"
                        text_color = "#ef4444"
                    return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 4px 8px; border-radius: 4px; font-weight: 700; display: inline-block; min-width: 55px; text-align: right;">{val:+.1f}%</span>'
                
                heatmap_rows = []
                for _, row in drift_df.iterrows():
                    # Construct single-line strings with NO leading indentation/spaces to prevent markdown code block rendering bugs
                    row_html = (
                        f'<tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.15);">'
                        f'<td style="padding: 10px 5px; font-weight: 500;">{row["sector"]}</td>'
                        f'<td style="padding: 10px 5px; text-align: center;">{row["currentWeight"]:.1f}%</td>'
                        f'<td style="padding: 10px 5px; text-align: center;">{row["targetWeight"]:.1f}%</td>'
                        f'<td style="padding: 10px 5px; text-align: right;">{color_drift(row["drift"])}</td>'
                        f'</tr>'
                    )
                    heatmap_rows.append(row_html)
                
                heatmap_html = (
                    f'<table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; color: #cbd5e1;">'
                    f'<thead>'
                    f'<tr style="border-bottom: 2px solid rgba(148, 163, 184, 0.3);">'
                    f'<th style="padding: 8px 5px; text-align: left;">Sector</th>'
                    f'<th style="padding: 8px 5px; text-align: center;">Current</th>'
                    f'<th style="padding: 8px 5px; text-align: center;">Target</th>'
                    f'<th style="padding: 8px 5px; text-align: right;">Drift</th>'
                    f'</tr>'
                    f'</thead>'
                    f'<tbody>'
                    f'{"".join(heatmap_rows)}'
                    f'</tbody>'
                    f'</table>'
                )
                st.markdown(heatmap_html, unsafe_allow_html=True)
        else:
            st.info("No sector drift detected.")
            
        st.subheader("Stock Weights: Before vs After Rebalancing")
        metrics_df = pd.DataFrame({
            "Stock": list(res["beforeMetrics"]["stockAllocations"].keys()),
            "Weight Before %": list(res["beforeMetrics"]["stockAllocations"].values()),
            "Weight After %": list(res["afterMetrics"]["stockAllocations"].values())
        })
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        
    # --- TAB 2: ALLOCATION VISUALS (TREEMAPS) ---
    with t_alloc:
        st.subheader("Current Portfolio Allocation Visualizations")
        
        # Clean dataframe to avoid Plotly's "None entries cannot have not-None children" error
        portfolio_clean = portfolio.copy()
        portfolio_clean["Sub-Sector"] = portfolio_clean["Sub-Sector"].fillna("Unknown Sector").astype(str).str.strip()
        portfolio_clean["Security"] = portfolio_clean["Security"].fillna("Unknown Stock").astype(str).str.strip()
        portfolio_clean["Current Value Rs"] = pd.to_numeric(portfolio_clean["Current Value Rs"], errors="coerce").fillna(0.0)

        # 1. Stock Allocation Treemap
        fig_st_tree = px.treemap(
            portfolio_clean,
            path=["Sub-Sector", "Security"],
            values="Current Value Rs",
            title="Current Stock & Sector Allocation Treemap",
            color="Current Value Rs",
            color_continuous_scale="Viridis"
        )
        fig_st_tree.update_layout(
            height=400,
            margin=dict(t=50, l=10, r=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1")
        )
        st.plotly_chart(fig_st_tree, use_container_width=True)
        
        # 2. Sector Allocation Pie
        fig_sec_pie = px.pie(
            portfolio_clean,
            names="Sub-Sector",
            values="Current Value Rs",
            title="Sector Exposure Mix",
            hole=0.4
        )
        fig_sec_pie.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1")
        )
        st.plotly_chart(fig_sec_pie, use_container_width=True)

    # --- TAB 3: ACTION PLAN RECOMMENDATIONS ---
    with t_recs:
        st.subheader("⚖️ Rebalancing Action Plan")
        
        # Warnings Section
        if res["concentrationWarnings"]:
            st.markdown("##### ⚠️ Concentration Warnings")
            for warn in res["concentrationWarnings"]:
                st.warning(warn)
                
        # Stock recommendations
        st.markdown("##### Stock-Level Recommendations")
        rec_stocks = pd.DataFrame(res["stockRecommendations"])
        if not rec_stocks.empty:
            # Map isNewStock flag to a user-friendly holding type column
            if "isNewStock" in rec_stocks.columns:
                rec_stocks["Type"] = rec_stocks["isNewStock"].apply(lambda x: "New Buy 🚀" if x == True else "Existing 💼")
            else:
                rec_stocks["Type"] = "Existing 💼"
                
            st.dataframe(
                rec_stocks[["ticker", "Type", "currentWeight", "targetWeight", "drift", "action", "priority", "impactScore"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ticker": "Stock Ticker",
                    "Type": "Holding Type",
                    "currentWeight": "Current Weight %",
                    "targetWeight": "Target Weight %",
                    "drift": "Weight Drift %",
                    "action": "Recommended Action",
                    "priority": "Urgency Priority",
                    "impactScore": "Impact Score (0-100)"
                }
            )
        else:
            st.success("All stock allocations are fully aligned with target weights.")
            
        # Sector recommendations
        st.markdown("##### Sector-Level Rebalancing Summary")
        rec_sec = pd.DataFrame(res["sectorRecommendations"])
        if not rec_sec.empty:
            st.dataframe(
                rec_sec[["sector", "currentWeight", "targetWeight", "drift", "action"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "sector": "Sector Name",
                    "currentWeight": "Current Weight %",
                    "targetWeight": "Target Weight %",
                    "drift": "Drift %",
                    "action": "Sector Target Action"
                }
            )
            
        # Market Cap recommendations
        st.markdown("##### Risk Profile Market Cap Rebalancing")
        if res["marketCapRecommendations"]:
            for m_rec in res["marketCapRecommendations"]:
                st.info(m_rec)
        else:
            st.success(f"Market Cap allocation is fully aligned with target {risk_profile} targets.")
            
        # Tax-Aware Rebalancing Details
        st.markdown("##### 🛡️ Tax-Efficient Execution Plan")
        for plan_step in res["taxEfficientPlan"]:
            st.markdown(f"- {plan_step}")

    # --- TAB 4: CAPITAL DEPLOYMENT SIMULATOR ---
    with t_sim:
        st.subheader("Optimal Deployment Simulator")
        st.write("Below is the optimal way to deploy your simulated cash without triggering stock selling transaction fees or capital gains tax:")
        
        if new_capital_input > 0:
            sim_df = pd.DataFrame(res["capitalDeploymentPlan"])
            if not sim_df.empty:
                # Map isNewStock flag to a user-friendly holding type column
                if "isNewStock" in sim_df.columns:
                    sim_df["Type"] = sim_df["isNewStock"].apply(lambda x: "New Buy 🚀" if x == True else "Existing 💼")
                else:
                    sim_df["Type"] = "Existing 💼"
                    
                st.dataframe(
                    sim_df[["ticker", "Type", "allocatedAmount", "reason"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ticker": "Stock Ticker",
                        "Type": "Holding Type",
                        "allocatedAmount": "Allocated Cash (₹)",
                        "reason": "Rationale"
                    }
                )
                
                # Allocation Pie chart
                fig_sim = px.pie(
                    sim_df,
                    names="ticker",
                    values="allocatedAmount",
                    title="Simulated Additional Capital Rebalancing Allocation Map",
                    hole=0.3
                )
                fig_sim.update_layout(
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1")
                )
                st.plotly_chart(fig_sim, use_container_width=True)
            else:
                st.info("No capital deployments required.")
        else:
            st.info("Simulate cash deployment above to view optimal rebalancing allocations.")

    # --- TAB 5: STRUCTURED JSON OUTPUT ---
    with t_json:
        st.subheader("Structured Rebalance Recommendations JSON")
        
        # Display the formatted JSON configuration
        st.json(res)
        
        # Allow user to download the structured JSON config
        import json
        st.download_button(
            label="📥 Download Structured Rebalancing JSON Report",
            data=json.dumps(res, indent=2),
            file_name="investiq_rebalancing_report.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json_rebalance"
        )