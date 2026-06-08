# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from services.recommendation_service import RecommendationService
from utils.page_utils import load_universe, require_data


st.title("Recommendations")
universe = load_universe()

if require_data(universe, "Upload the stock universe to generate recommendations."):
    recommendations = RecommendationService.generate(universe)
    st.dataframe(recommendations, use_container_width=True)
