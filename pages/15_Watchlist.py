# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st

from database.models import Watchlist
from database.repositories.watchlist_repository import WatchlistRepository


st.title("Watchlist")

ticker = st.text_input("Ticker").strip().upper()
if st.button("Add Stock") and ticker:
    WatchlistRepository.add(Watchlist(ticker=ticker))
    st.success(f"{ticker} added")

rows = WatchlistRepository.get_all()
data = [{"Ticker": row.ticker, "Added": row.added_date} for row in rows]
st.dataframe(pd.DataFrame(data), use_container_width=True)
