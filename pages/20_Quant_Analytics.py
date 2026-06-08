# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import pandas as pd
import streamlit as st

from engines.cvar_engine import CVaREngine
from engines.var_engine import VaREngine
from services.quant_service import QuantService


st.title("Quant Analytics")
st.write(
    "Analyze portfolio or strategy returns with intuitive quantitative metrics and visualizations. "
    "Upload periodic returns or use sample data for a quick preview."
)

uploaded = st.file_uploader("Upload returns CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    column = st.selectbox("Returns Column", df.columns)
    returns = pd.to_numeric(df[column], errors="coerce").dropna()
else:
    st.info("Upload a CSV with periodic returns. Using sample returns for preview.")
    returns = pd.Series([0.01, -0.004, 0.006, 0.012, -0.008, 0.003])

if returns.empty:
    st.warning("No valid returns values found in the selected column.")
else:
    cumulative_returns = (1 + returns).cumprod()
    peak = cumulative_returns.cummax()
    drawdown = cumulative_returns / peak - 1
    metrics = QuantService.analyze(returns, cumulative_returns)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sharpe", round(metrics.get("sharpe", 0), 2))
    c2.metric("Sortino", round(metrics.get("sortino", 0), 2))
    c3.metric("Max Drawdown", f"{round(drawdown.min() * 100, 2)}%")
    c4.metric("VaR", round(VaREngine.calculate(returns), 4))
    c5.metric("CVaR", round(CVaREngine.calculate(returns), 4))

    st.subheader("Cumulative Return Path")
    st.line_chart(cumulative_returns)

    st.subheader("Drawdown Profile")
    st.area_chart(drawdown)

    st.subheader("Return Distribution")
    hist = pd.DataFrame({"Returns": returns})
    hist_chart = alt.Chart(hist).mark_bar(opacity=0.8).encode(
        alt.X("Returns:Q", bin=alt.Bin(maxbins=25), title="Return"),
        y=alt.Y("count():Q", title="Frequency"),
        tooltip=[alt.Tooltip("count():Q", title="Count")],
    ).properties(title="Distribution of Periodic Returns", height=360)
    st.altair_chart(hist_chart, use_container_width=True)

    st.markdown(
        "### What this means"
        "\n- Sharpe and Sortino show reward per unit of risk."
        "\n- Max drawdown tracks the worst peak-to-trough loss."
        "\n- VaR and CVaR estimate tail risk exposure."
    )
