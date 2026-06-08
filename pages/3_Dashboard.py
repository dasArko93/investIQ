# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

from utils.dashboard_ui import render_investiq_dashboard


st.set_page_config(page_title="InvestIQ Dashboard", layout="wide", initial_sidebar_state="expanded")
render_investiq_dashboard()
