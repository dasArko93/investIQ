# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.health_service import HealthService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from utils.page_utils import load_holdings, load_universe, merged_holdings, require_data, render_sidebar


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Portfolio Report")
portfolio = load_holdings()
universe = load_universe()
merged = merged_holdings()

if require_data(portfolio, "Upload holdings to generate a report."):
    avg_quality = merged["QUALITY_SCORE"].fillna(0).mean() if not merged.empty else 0
    sector_count = merged["Sub-Sector"].nunique() if not merged.empty else 0
    health = HealthService.evaluate(portfolio, avg_quality, sector_count)
    recommendations = RecommendationService.generate(universe) if not universe.empty else universe
    summary = ReportService.generate(portfolio, health, recommendations)
    st.json(summary)
    st.download_button(
        "Download PDF",
        ReportService.generate_pdf(summary),
        file_name="investiq_portfolio_report.pdf",
        mime="application/pdf",
    )
