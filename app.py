import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st

from database.init_db import init_db
from utils.dashboard_ui import render_investiq_dashboard
from utils.page_utils import render_sidebar


init_db()

st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")

from utils.page_utils import require_auth
require_auth()

render_sidebar()
render_investiq_dashboard()
