# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from database.models import Journal
from database.repositories.journal_repository import JournalRepository


st.title("Investment Journal")

ticker = st.text_input("Ticker").strip().upper()
note = st.text_area("Investment Notes")
if st.button("Save") and note:
    JournalRepository.add(Journal(ticker=ticker, notes=note))
    st.success("Saved")

rows = JournalRepository.get_all()
data = [{"Ticker": row.ticker, "Notes": row.notes, "Created": row.created_date} for row in rows]
st.dataframe(pd.DataFrame(data), use_container_width=True)
