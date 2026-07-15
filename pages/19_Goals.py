# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from utils.page_utils import render_sidebar

from database.models import Goal
from database.repositories.goal_repository import GoalRepository
from services.goal_service import GoalService


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("Goals")

name = st.selectbox("Goal", ["Retirement", "House", "Emergency Fund", "Child Education", "Custom"])
target = st.number_input("Target Amount", min_value=0, value=1000000, step=50000)
current = st.number_input("Current Amount", min_value=0, value=500000, step=50000)
target_date = st.text_input("Target Date", "2035-12-31")

progress = GoalService.progress(current, target)
st.progress(progress / 100)
st.metric("Progress", f"{progress}%")

if st.button("Save Goal"):
    GoalRepository.add(Goal(goal_name=name, target_amount=target, current_amount=current, target_date=target_date))
    st.success("Goal saved")

rows = GoalRepository.get_all()
data = [
    {
        "Goal": row.goal_name,
        "Target": row.target_amount,
        "Current": row.current_amount,
        "Progress": GoalService.progress(row.current_amount, row.target_amount),
        "Target Date": row.target_date,
    }
    for row in rows
]
st.dataframe(pd.DataFrame(data), width='stretch')