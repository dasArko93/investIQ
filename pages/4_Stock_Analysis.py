# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from services.price_history_service import PriceHistoryService
from utils.page_utils import load_universe, require_data, render_sidebar


ANALYSIS_STYLES = {
    "Growth Investing": {
        "goal": "Find companies that can grow earnings rapidly for many years.",
        "metrics": [
            ("Revenue Growth", ">15% CAGR", ["Revenue Growth", "5Y Historical Revenue Growth"]),
            ("EPS Growth", ">15-20% CAGR", ["EPS Growth", "5Y CAGR"]),
            ("ROE", ">15%", ["ROE"]),
            ("ROCE", ">18%", ["ROCE"]),
            ("Debt/Equity", "<0.5", ["Debt/Equity", "Debt to Equity"]),
            ("Operating Margin", "Stable or improving", ["Operating Margin"]),
            ("PEG Ratio", "<1.5", ["PEG Ratio", "PEG"]),
        ],
        "look_for": [
            "Large market opportunity",
            "Strong management execution",
            "New products/services",
            "Market share gains",
        ],
        "examples": ["Indian IT during early 2000s", "Specialty chemicals", "Premium consumer brands"],
    },
    "Value Investing": {
        "goal": "Buy businesses below intrinsic value.",
        "metrics": [
            ("P/E", "Below industry average", ["P/E", "PE Ratio"]),
            ("P/B", "<3", ["P/B", "PB Ratio", "Price to Book"]),
            ("EV/EBITDA", "Lower than peers", ["EV/EBITDA"]),
            ("Debt/Equity", "<1", ["Debt/Equity", "Debt to Equity"]),
            ("Free Cash Flow", "Positive", ["Free Cash Flow", "FCF"]),
            ("Current Ratio", ">1.5", ["Current Ratio"]),
        ],
        "look_for": [
            "Temporary market pessimism",
            "Cyclical downturns",
            "Asset-rich companies",
            "Turnaround opportunities",
            "Improving profits",
            "Improving cash flow",
            "Management credibility",
        ],
        "warning": "Cheap stocks often deserve to be cheap.",
    },
    "Quality Compounders": {
        "goal": "Hold for 10-20 years.",
        "metrics": [
            ("ROCE", ">20%", ["ROCE"]),
            ("ROE", ">18%", ["ROE"]),
            ("Debt/Equity", "Near zero", ["Debt/Equity", "Debt to Equity"]),
            ("FCF Conversion", ">80%", ["FCF Conversion"]),
            ("Gross Margin", "Stable", ["Gross Margin"]),
            ("Promoter Holding", "Stable/Increasing", ["Promoter Holding"]),
        ],
        "look_for": ["Strong brands", "Pricing power", "Competitive moat", "Consistent growth"],
        "examples": ["Consumer staples", "Leading financial services", "Niche monopolies"],
    },
    "GARP": {
        "goal": "Mix of Growth + Value",
        "metrics": [
            ("Revenue Growth", ">15%", ["Revenue Growth", "5Y Historical Revenue Growth"]),
            ("EPS Growth", ">15%", ["EPS Growth", "5Y CAGR"]),
            ("PEG Ratio", "<1", ["PEG Ratio", "PEG"]),
            ("ROCE", ">20%", ["ROCE"]),
            ("Debt/Equity", "<0.5", ["Debt/Equity", "Debt to Equity"]),
        ],
        "look_for": [
            "Peter Lynch's favorite style.",
            "Find businesses growing fast but not trading at absurd valuations.",
        ],
    },
    "Dividend Investing": {
        "goal": "Income generation.",
        "metrics": [
            ("Dividend Yield", ">3%", ["Dividend Yield"]),
            ("Payout Ratio", "30-70%", ["Payout Ratio"]),
            ("FCF", "Positive", ["Free Cash Flow", "FCF"]),
            ("Debt/Equity", "Low", ["Debt/Equity", "Debt to Equity"]),
            ("Interest Coverage", ">5", ["Interest Coverage"]),
        ],
        "avoid": ["Very high yields (>8-10%)", "Falling earnings", "Borrowed dividends"],
    },
    "Turnaround Investing": {
        "goal": "Catch recovery before the market does.",
        "metrics": [
            ("Debt", "Falling", ["Debt", "Debt to Equity"]),
            ("EBITDA Margin", "Improving", ["EBITDA Margin"]),
            ("Cash Flow", "Turning Positive", ["Cash Flow", "Free Cash Flow"]),
            ("Promoter Holding", "Increasing", ["Promoter Holding"]),
        ],
        "look_for": ["New management", "Debt reduction", "Margin improvement", "Industry recovery"],
        "warning": "Risky but potentially rewarding.",
    },
}


def first_available_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def metric_table(stock, style):
    rows = []
    for metric, cutoff, candidates in style["metrics"]:
        column = first_available_column(stock, candidates)
        value = stock[column].iloc[0] if column else "Not in universe data"
        rows.append({
            "Metric": metric,
            "Default Cutoff": cutoff,
            "Stock Value": value,
            "Source Column": column or "-",
        })
    return pd.DataFrame(rows)


def numeric_series(df, candidates, default=None):
    column = first_available_column(df, candidates)
    if column is None:
        if default is None:
            return None, None
        return pd.Series(default, index=df.index), None
    return pd.to_numeric(df[column], errors="coerce"), column


def evaluate_cutoff(series, cutoff, fallback):
    text = str(cutoff).strip().lower().replace("%", "").replace("cagr", "")
    if not text:
        return fallback(series)
    if text in {"positive", ">0"}:
        return series > 0
    if text in {"low"}:
        return series < 0.5
    if text in {"near zero", "zero"}:
        return series < 0.25
    if "-" in text and not text.startswith("-"):
        left, right = text.split("-", 1)
        try:
            low = float(left.strip())
            high = float(right.strip())
            return (series >= low) & (series <= high)
        except ValueError:
            return fallback(series)
    for operator in [">=", "<=", ">", "<"]:
        if text.startswith(operator):
            try:
                value = float(text.replace(operator, "").strip())
            except ValueError:
                return fallback(series)
            if operator == ">=":
                return series >= value
            if operator == "<=":
                return series <= value
            if operator == ">":
                return series > value
            return series < value
    try:
        value = float(text)
    except ValueError:
        return fallback(series)
    return series >= value


def apply_style_filter(df, style_name, cutoffs=None):
    cutoffs = cutoffs or {}
    rules = []
    mask = pd.Series(True, index=df.index)

    def add_rule(label, candidates, operator_text, predicate):
        nonlocal mask
        series, column = numeric_series(df, candidates)
        user_cutoff = str(cutoffs.get(label, operator_text)).strip() or operator_text
        if series is None:
            rules.append({
                "Metric": label,
                "Default Cutoff": operator_text,
                "User Cutoff": user_cutoff,
                "Column": "-",
                "Status": "Skipped",
            })
            return
        rule_mask = evaluate_cutoff(series, user_cutoff, predicate).fillna(False)
        mask &= rule_mask
        rules.append({
            "Metric": label,
            "Default Cutoff": operator_text,
            "User Cutoff": user_cutoff,
            "Column": column,
            "Status": f"{int(rule_mask.sum())} pass",
        })

    if style_name == "Growth Investing":
        add_rule("Revenue Growth", ["Revenue Growth", "5Y Historical Revenue Growth"], ">15% CAGR", lambda s: s > 15)
        add_rule("EPS Growth", ["EPS Growth", "5Y CAGR"], ">15%", lambda s: s > 15)
        add_rule("ROE", ["ROE"], ">15%", lambda s: s > 15)
        add_rule("ROCE", ["ROCE"], ">18%", lambda s: s > 18)
        add_rule("Debt/Equity", ["Debt/Equity", "Debt to Equity"], "<0.5", lambda s: s < 0.5)
        add_rule("PEG Ratio", ["PEG Ratio", "PEG"], "<1.5", lambda s: s < 1.5)
    elif style_name == "Value Investing":
        pe, pe_column = numeric_series(df, ["P/E", "PE Ratio"])
        sector_pe, sector_column = numeric_series(df, ["Industry PE", "Sector PE"])
        pe_cutoff = str(cutoffs.get("P/E", "Below industry average")).strip() or "Below industry average"
        if pe is not None and sector_pe is not None:
            rule_mask = evaluate_cutoff(pe, pe_cutoff, lambda s: s < sector_pe).fillna(False)
            mask &= rule_mask
            rules.append({
                "Metric": "P/E",
                "Default Cutoff": "Below industry average",
                "User Cutoff": pe_cutoff,
                "Column": f"{pe_column} vs {sector_column}",
                "Status": f"{int(rule_mask.sum())} pass",
            })
        else:
            rules.append({
                "Metric": "P/E",
                "Default Cutoff": "Below industry average",
                "User Cutoff": pe_cutoff,
                "Column": "-",
                "Status": "Skipped",
            })
        add_rule("P/B", ["P/B", "PB Ratio", "Price to Book"], "<3", lambda s: s < 3)
        add_rule("Debt/Equity", ["Debt/Equity", "Debt to Equity"], "<1", lambda s: s < 1)
        add_rule("Free Cash Flow", ["Free Cash Flow", "FCF"], "Positive", lambda s: s > 0)
        add_rule("Current Ratio", ["Current Ratio"], ">1.5", lambda s: s > 1.5)
    elif style_name == "Quality Compounders":
        add_rule("ROCE", ["ROCE"], ">20%", lambda s: s > 20)
        add_rule("ROE", ["ROE"], ">18%", lambda s: s > 18)
        add_rule("Debt/Equity", ["Debt/Equity", "Debt to Equity"], "Near zero", lambda s: s < 0.25)
        add_rule("FCF Conversion", ["FCF Conversion"], ">80%", lambda s: s > 80)
    elif style_name == "GARP":
        add_rule("Revenue Growth", ["Revenue Growth", "5Y Historical Revenue Growth"], ">15%", lambda s: s > 15)
        add_rule("EPS Growth", ["EPS Growth", "5Y CAGR"], ">15%", lambda s: s > 15)
        add_rule("PEG Ratio", ["PEG Ratio", "PEG"], "<1", lambda s: s < 1)
        add_rule("ROCE", ["ROCE"], ">20%", lambda s: s > 20)
        add_rule("Debt/Equity", ["Debt/Equity", "Debt to Equity"], "<0.5", lambda s: s < 0.5)
    elif style_name == "Dividend Investing":
        add_rule("Dividend Yield", ["Dividend Yield"], ">3%", lambda s: s > 3)
        add_rule("Payout Ratio", ["Payout Ratio"], "30-70%", lambda s: (s >= 30) & (s <= 70))
        add_rule("FCF", ["Free Cash Flow", "FCF"], "Positive", lambda s: s > 0)
        add_rule("Debt/Equity", ["Debt/Equity", "Debt to Equity"], "Low", lambda s: s < 0.5)
        add_rule("Interest Coverage", ["Interest Coverage"], ">5", lambda s: s > 5)
    elif style_name == "Turnaround Investing":
        add_rule("Debt", ["Debt", "Debt to Equity"], "Falling / low", lambda s: s < 1)
        add_rule("EBITDA Margin", ["EBITDA Margin"], "Improving / positive", lambda s: s > 0)
        add_rule("Cash Flow", ["Cash Flow", "Free Cash Flow"], "Turning positive", lambda s: s > 0)
        add_rule("Promoter Holding", ["Promoter Holding"], "Increasing / >50%", lambda s: s > 50)

    return df[mask].copy(), pd.DataFrame(rules)


def display_columns(df):
    requested = ["Name", "Ticker", "Sub-Sector", "Market Cap", "Close Price"]
    return [column for column in requested if column in df.columns]


def sector_options(df):
    if df.empty or "Sub-Sector" not in df.columns:
        return ["All"]
    sectors = sorted(df["Sub-Sector"].dropna().astype(str).unique())
    return ["All"] + sectors


def filter_by_sector(df, sector):
    if sector == "All" or "Sub-Sector" not in df.columns:
        return df
    return df[df["Sub-Sector"].astype(str) == sector].copy()


def true_range(history):
    previous_close = history["close"].shift(1)
    ranges = pd.concat(
        [
            history["high"] - history["low"],
            (history["high"] - previous_close).abs(),
            (history["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def calculate_adx(history, period=14):
    high_diff = history["high"].diff()
    low_diff = -history["low"].diff()
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
    atr = true_range(history).rolling(period).mean()
    plus_di = 100 * pd.Series(plus_dm, index=history.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=history.index).rolling(period).mean() / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.rolling(period).mean()


def support_resistance(history):
    close = history["close"].dropna()
    if close.empty:
        return [], []
    supports = close[close == close.rolling(12, center=True).min()].dropna().round(2).unique().tolist()
    resistances = close[close == close.rolling(12, center=True).max()].dropna().round(2).unique().tolist()
    supports = sorted(supports, reverse=True)[:3]
    resistances = sorted(resistances)[:3]
    return supports, resistances


def linear_forecast(history, periods=7):
    forecast = pd.DataFrame()
    close = history["close"].dropna().reset_index(drop=True)
    if len(close) < 30:
        return forecast, {}

    x = np.arange(len(close))
    slope, intercept = np.polyfit(x, close, 1)
    residual_std = float((close - (slope * x + intercept)).std())
    future_x = np.arange(len(close), len(close) + periods)
    future_dates = pd.bdate_range(history["date"].max() + pd.Timedelta(days=1), periods=periods)
    predicted = slope * future_x + intercept
    forecast = pd.DataFrame({
        "date": future_dates,
        "predicted": predicted,
        "lower": predicted - 1.5 * residual_std,
        "upper": predicted + 1.5 * residual_std,
    })

    test_size = min(30, len(close) // 3)
    train = close.iloc[:-test_size]
    test = close.iloc[-test_size:]
    train_x = np.arange(len(train))
    test_x = np.arange(len(train), len(train) + len(test))
    backtest_slope, backtest_intercept = np.polyfit(train_x, train, 1)
    backtest_pred = backtest_slope * test_x + backtest_intercept
    errors = test.to_numpy() - backtest_pred
    mae = float(np.abs(errors).mean())
    rmse = float(np.sqrt((errors ** 2).mean()))
    mape = float((np.abs(errors) / np.maximum(test.to_numpy(), 1)).mean() * 100)
    accuracy = max(0, min(100, 100 - mape))
    return forecast, {"mae": mae, "rmse": rmse, "mape": mape, "accuracy": accuracy}


def analyze_price_history(history):
    work = history.copy()
    work["date"] = pd.to_datetime(work["date"])
    for column in ["open", "high", "low", "close", "volume"]:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=["date", "close"]).sort_values("date")
    for window in [20, 50, 100, 200]:
        work[f"{window} DMA"] = work["close"].rolling(window).mean()

    latest = work.iloc[-1]
    dma_values = [latest.get(f"{window} DMA") for window in [20, 50, 100, 200]]
    if all(pd.notna(value) for value in dma_values) and dma_values[0] > dma_values[1] > dma_values[2] > dma_values[3]:
        trend = "Strong Uptrend"
    elif pd.notna(dma_values[0]) and pd.notna(dma_values[1]) and dma_values[0] > dma_values[1]:
        trend = "Uptrend"
    elif all(pd.notna(value) for value in dma_values) and dma_values[0] < dma_values[1] < dma_values[2] < dma_values[3]:
        trend = "Strong Downtrend"
    elif pd.notna(dma_values[0]) and pd.notna(dma_values[1]) and dma_values[0] < dma_values[1]:
        trend = "Downtrend"
    else:
        trend = "Sideways"

    returns = {
        f"{days}D Return": ((work["close"].iloc[-1] / work["close"].iloc[-days]) - 1) * 100
        for days in [7, 30, 90, 180, 365]
        if len(work) > days
    }
    daily_returns = work["close"].pct_change()
    volatility = {
        f"{days}D Volatility": daily_returns.tail(days).std() * np.sqrt(252) * 100
        for days in [30, 90, 365]
        if len(work) > days
    }
    atr = true_range(work).rolling(14).mean().iloc[-1]
    adx = calculate_adx(work).iloc[-1]
    supports, resistances = support_resistance(work)

    recent_price_change = work["close"].tail(20).iloc[-1] - work["close"].tail(20).iloc[0]
    recent_volume = work["volume"].tail(20).mean()
    previous_volume = work["volume"].tail(40).head(20).mean()
    if recent_price_change > 0 and recent_volume >= previous_volume:
        volume_trend = "Accumulation"
    elif recent_price_change < 0 and recent_volume >= previous_volume:
        volume_trend = "Distribution"
    elif recent_price_change > 0:
        volume_trend = "Weak Rally"
    else:
        volume_trend = "Weakness"

    forecast, accuracy = linear_forecast(work)
    current_price = work["close"].iloc[-1]
    expected_move = 0
    forecast_bias = "Neutral"
    if not forecast.empty:
        expected_move = ((forecast["predicted"].iloc[-1] / current_price) - 1) * 100
        if expected_move > 2:
            forecast_bias = "Bullish"
        elif expected_move < -2:
            forecast_bias = "Bearish"

    momentum_score = min(100, max(0, 50 + returns.get("30D Return", 0) + returns.get("90D Return", 0) / 2))
    trend_score = min(100, max(0, 50 + (20 if trend.startswith("Strong Up") else 10 if trend == "Uptrend" else -20 if trend.startswith("Strong Down") else -10 if trend == "Downtrend" else 0) + (adx if pd.notna(adx) else 0) / 2))
    forecast_score = min(100, max(0, 50 + expected_move * 5))
    volume_score = 85 if volume_trend == "Accumulation" else 60 if volume_trend == "Weak Rally" else 35 if volume_trend == "Distribution" else 45
    volatility_score = 70 if pd.notna(atr) else 50
    composite = round(trend_score * 0.30 + momentum_score * 0.20 + forecast_score * 0.25 + volume_score * 0.15 + volatility_score * 0.10, 2)
    signal = "Strong Buy" if trend_score > 75 and expected_move > 5 and volume_trend == "Accumulation" else "Buy" if trend_score > 60 and expected_move > 3 else "Hold" if -2 <= expected_move <= 2 else "Sell" if expected_move < -5 else "Reduce" if expected_move < -3 else "Hold"

    return {
        "history": work,
        "forecast": forecast,
        "accuracy": accuracy,
        "summary": {
            "Trend": trend,
            "Trend Confidence": round(trend_score, 2),
            "Momentum Score": round(momentum_score, 2),
            "Volatility": "Moderate" if pd.notna(atr) else "Unavailable",
            "ATR": round(float(atr), 2) if pd.notna(atr) else None,
            "ADX": round(float(adx), 2) if pd.notna(adx) else None,
            "Volume Trend": volume_trend,
            "Forecast Bias": forecast_bias,
            "Expected Move": round(float(expected_move), 2),
            "Forecast Score": composite,
            "Signal": signal,
        },
        "returns": returns,
        "volatility": volatility,
        "supports": supports,
        "resistances": resistances,
    }


def render_price_history_expander(selected):
    with st.expander("365-Day Trend & Forecasting", expanded=False):
        tickers = selected["Ticker"].astype(str).tolist()
        st.caption("Downloads the last 365 calendar days of OHLCV data from Yahoo Finance for the selected stocks.")
        if st.button("Download 365-Day Stock Data", use_container_width=True, key=f"download_365_{'_'.join(tickers)}"):
            st.session_state["price_history_365"] = {}
            for ticker in tickers:
                history = PriceHistoryService.fetch_365_days(ticker, auto_map_nse=True)
                if not history.empty:
                    st.session_state["price_history_365"][ticker] = history

        histories = st.session_state.get("price_history_365", {})
        available_tickers = [ticker for ticker in tickers if ticker in histories and not histories[ticker].empty]
        if not available_tickers:
            st.info("Click the download button to load 365-day OHLCV data for the selected stock(s).")
            return

        tabs = st.tabs(available_tickers)
        for tab, ticker in zip(tabs, available_tickers):
            with tab:
                history = histories[ticker]
                analysis = analyze_price_history(history)
                work = analysis["history"]
                st.download_button(
                    "Download OHLCV CSV",
                    data=work.to_csv(index=False),
                    file_name=f"{ticker}_365_day_ohlcv.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                summary = analysis["summary"]
                cols = st.columns(5)
                for col, key in zip(cols, ["Trend", "Trend Confidence", "Momentum Score", "Forecast Bias", "Signal"]):
                    col.metric(key, summary.get(key))

                st.dataframe(pd.DataFrame([summary]), use_container_width=True)
                st.dataframe(
                    pd.DataFrame({
                        "Metric": list(analysis["returns"].keys()) + list(analysis["volatility"].keys()),
                        "Value": list(analysis["returns"].values()) + list(analysis["volatility"].values()),
                    }),
                    use_container_width=True,
                )

                line_cols = ["date", "close", "20 DMA", "50 DMA", "100 DMA", "200 DMA"]
                line_data = work[[column for column in line_cols if column in work.columns]].melt(
                    "date", var_name="Series", value_name="Price"
                ).dropna()
                price_chart = alt.Chart(line_data).mark_line(point=True).encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("Price:Q", title="Price"),
                    color=alt.Color("Series:N"),
                    tooltip=["date:T", "Series:N", alt.Tooltip("Price:Q", format=",.2f")],
                ).properties(height=360, title="Close Price and Moving Averages")
                st.altair_chart(price_chart, use_container_width=True)

                if not analysis["forecast"].empty:
                    forecast = analysis["forecast"]
                    forecast_band = alt.Chart(forecast).mark_area(opacity=0.18, color="#7ec7ff").encode(
                        x="date:T",
                        y="lower:Q",
                        y2="upper:Q",
                    )
                    forecast_line = alt.Chart(forecast).mark_line(point=True, color="#7ec7ff").encode(
                        x=alt.X("date:T", title="Forecast Date"),
                        y=alt.Y("predicted:Q", title="Predicted Price"),
                        tooltip=["date:T", alt.Tooltip("predicted:Q", format=",.2f"), alt.Tooltip("lower:Q", format=",.2f"), alt.Tooltip("upper:Q", format=",.2f")],
                    )
                    st.altair_chart((forecast_band + forecast_line).properties(height=300, title="7-Day Forecast"), use_container_width=True)
                    st.dataframe(forecast, use_container_width=True)

                support_resistance_rows = pd.DataFrame({
                    "Supports": pd.Series(analysis["supports"]),
                    "Resistances": pd.Series(analysis["resistances"]),
                })
                st.dataframe(support_resistance_rows, use_container_width=True)


def deep_dive(selected, style, sector_base, deep_sector):
    with st.expander("Deep Dive", expanded=True):
        st.subheader("Deep Dive")
        sector_scope = sector_base

        if deep_sector != "All" and not sector_scope.empty:
            st.markdown(f"#### {deep_sector} Sector View")
            metric_columns = [
                column for column in ["Market Cap", "Close Price", "ROCE", "PE Ratio", "5Y CAGR", "Debt to Equity"]
                if column in sector_scope.columns
            ]
            sector_summary = sector_scope[metric_columns].apply(pd.to_numeric, errors="coerce").mean().reset_index()
            sector_summary.columns = ["Metric", "Sector Average"]
            st.dataframe(sector_summary, use_container_width=True)

            sector_chart_data = sector_scope[["Ticker"] + metric_columns].copy()
            for column in metric_columns:
                sector_chart_data[column] = pd.to_numeric(sector_chart_data[column], errors="coerce")
            sector_long = sector_chart_data.melt("Ticker", var_name="Metric", value_name="Value").dropna()
            if not sector_long.empty:
                sector_chart = alt.Chart(sector_long).mark_bar().encode(
                    x=alt.X("Ticker:N", title="Stock"),
                    y=alt.Y("Value:Q", title="Value"),
                    color=alt.Color("Metric:N", title="Metric"),
                    column=alt.Column("Metric:N", title=None),
                    tooltip=["Ticker", "Metric", alt.Tooltip("Value:Q", format=".2f")],
                ).properties(height=220)
                st.altair_chart(sector_chart, use_container_width=True)

        if selected.empty:
            st.info("No selected stocks are available in this sector.")
            if not sector_scope.empty:
                st.caption(f"{len(sector_scope)} stocks are available in {deep_sector} from the filtered universe.")
                st.dataframe(sector_scope, use_container_width=True)
            return

        st.dataframe(selected, use_container_width=True)

        metrics = [
            "ROCE",
            "ROE",
            "5Y CAGR",
            "5Y Historical Revenue Growth",
            "Debt to Equity",
            "PE Ratio",
            "Sector PE",
            "Free Cash Flow",
            "QUALITY_SCORE",
            "Market Cap",
            "Close Price",
        ]
        available_metrics = [column for column in metrics if column in selected.columns]
        numeric = selected[["Ticker"] + available_metrics].copy()
        for column in available_metrics:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")

        if len(selected) == 1:
            stock = selected.iloc[[0]]
            st.markdown(f"#### {stock['Ticker'].iloc[0]} Individual Analysis")
            st.dataframe(metric_table(stock, style), use_container_width=True)

        if available_metrics:
            long_metrics = numeric.melt("Ticker", var_name="Metric", value_name="Value").dropna()
            selected_key = "_".join(selected["Ticker"].astype(str).sort_values().tolist())
            metric_pick = st.multiselect(
                "Deep dive metrics",
                ["All"] + available_metrics,
                default=["All"],
                key=f"deep_dive_metrics_{selected_key}",
            )
            selected_metrics = available_metrics if "All" in metric_pick else metric_pick
            chart_data = long_metrics[long_metrics["Metric"].isin(selected_metrics)]
            if not chart_data.empty:
                for metric in selected_metrics:
                    metric_data = chart_data[chart_data["Metric"] == metric].copy()
                    if metric_data.empty:
                        continue
                    metric_data["Label"] = metric_data["Value"].map(lambda value: f"{value:,.2f}")
                    bars = alt.Chart(metric_data).mark_bar(size=42).encode(
                        x=alt.X("Ticker:N", title="Stock", sort=None),
                        y=alt.Y("Value:Q", title=metric),
                        color=alt.value("#7ec7ff"),
                        tooltip=["Ticker", "Metric", alt.Tooltip("Value:Q", format=",.2f")],
                    )
                    labels = alt.Chart(metric_data).mark_text(
                        align="center",
                        baseline="bottom",
                        dy=-4,
                        color="#eef4ff",
                        fontSize=12,
                    ).encode(
                        x=alt.X("Ticker:N", sort=None),
                        y=alt.Y("Value:Q"),
                        text="Label:N",
                    )
                    st.altair_chart(
                        (bars + labels).properties(height=320, title=metric),
                        use_container_width=True,
                    )

        if {"PE Ratio", "ROCE"}.issubset(selected.columns):
            scatter = selected.copy()
            scatter["PE Ratio"] = pd.to_numeric(scatter["PE Ratio"], errors="coerce")
            scatter["ROCE"] = pd.to_numeric(scatter["ROCE"], errors="coerce")
            if "Market Cap" in scatter.columns:
                scatter["Market Cap"] = pd.to_numeric(scatter["Market Cap"], errors="coerce")
            size_field = "Market Cap" if "Market Cap" in scatter.columns else alt.value(120)
            valuation_chart = alt.Chart(scatter).mark_circle(opacity=0.85, size=180).encode(
                x=alt.X("PE Ratio:Q", title="PE Ratio"),
                y=alt.Y("ROCE:Q", title="ROCE"),
                size=alt.Size(f"{size_field}:Q", title="Market Cap", scale=alt.Scale(range=[180, 900])) if size_field == "Market Cap" else size_field,
                color=alt.Color("Sub-Sector:N", title="Sub-Sector") if "Sub-Sector" in scatter.columns else alt.value("#2563eb"),
                tooltip=[column for column in ["Name", "Ticker", "Sub-Sector", "Market Cap", "Close Price", "PE Ratio", "ROCE"] if column in scatter.columns],
            ).properties(height=380, title="Valuation vs Return Quality")
            st.altair_chart(valuation_chart, use_container_width=True)

        if len(selected) > 1 and "Sub-Sector" in selected.columns:
            sector_data = selected["Sub-Sector"].fillna("Unknown").value_counts().reset_index()
            sector_data.columns = ["Sub-Sector", "Stocks"]
            sector_chart = alt.Chart(sector_data).mark_bar().encode(
                x=alt.X("Stocks:Q", title="Selected Stocks"),
                y=alt.Y("Sub-Sector:N", sort="-x", title="Sub-Sector"),
                tooltip=["Sub-Sector", "Stocks"],
            ).properties(height=260, title="Selected Stock Mix")
            st.altair_chart(sector_chart, use_container_width=True)

    render_price_history_expander(selected)


st.set_page_config(page_title="InvestIQ", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

st.title("Fundamental Analysis")
st.write("Choose an investing style, filter matching stocks, then select companies for individual or comparative deep dives.")
universe = load_universe()

style_name = st.selectbox("Investing Style", list(ANALYSIS_STYLES.keys()))
style = ANALYSIS_STYLES[style_name]

st.subheader(style_name)
st.write(f"Goal: {style['goal']}")

if require_data(universe, "Upload a stock universe to perform fundamental analysis."):
    style_sector = st.selectbox("Investing Style Sector", sector_options(universe), key="style_sector")
    universe_scope = filter_by_sector(universe, style_sector)

    st.subheader("Data Filtration")
    _, default_rules = apply_style_filter(universe_scope, style_name)
    editable_rules = default_rules[["Metric", "Default Cutoff", "User Cutoff", "Column"]].copy()
    edited_rules = st.data_editor(
        editable_rules,
        use_container_width=True,
        hide_index=True,
        disabled=["Metric", "Default Cutoff", "Column"],
        column_config={
            "User Cutoff": st.column_config.TextColumn(
                "User Define Cutoff",
                help="Examples: >20, <0.5, 30-70, positive, low, near zero",
            )
        },
    )

    button_col1, button_col2 = st.columns([1, 1])
    with button_col1:
        filter_clicked = st.button("Filter Stock", type="primary", use_container_width=True)
    with button_col2:
        clear_clicked = st.button("Clear Filter", use_container_width=True)

    state_key = f"fundamental_filter_{style_name}_{style_sector}"
    if clear_clicked:
        st.session_state.pop(state_key, None)
    if filter_clicked:
        cutoff_map = dict(zip(edited_rules["Metric"], edited_rules["User Cutoff"]))
        filtered, applied_rules = apply_style_filter(universe_scope, style_name, cutoff_map)
        st.session_state[state_key] = {
            "tickers": filtered["Ticker"].astype(str).tolist() if "Ticker" in filtered.columns else [],
            "rules": applied_rules.to_dict("records"),
        }

    saved_filter = st.session_state.get(state_key)
    if saved_filter:
        filtered = universe_scope[universe_scope["Ticker"].astype(str).isin(saved_filter["tickers"])].copy()
        applied_rules = pd.DataFrame(saved_filter["rules"])
        st.dataframe(applied_rules, use_container_width=True)

        if filtered.empty:
            st.warning("No stocks match the selected cutoffs for this investing style.")
        else:
            st.caption(f"{len(filtered)} stocks match the selected filters.")
            st.dataframe(filtered[display_columns(filtered)], use_container_width=True)

            deep_sector = st.selectbox("Deep Dive Sector", sector_options(filtered), key="deep_dive_sector")
            deep_scope = filter_by_sector(filtered, deep_sector)
            ticker_labels = [
                f"{row.get('Ticker')} - {row.get('Name', '')}"
                for _, row in deep_scope.sort_values("Ticker").iterrows()
            ]
            label_to_ticker = {label: label.split(" - ", 1)[0] for label in ticker_labels}
            selected_labels = st.multiselect("Select stocks for deep dive", ticker_labels)
            selected_tickers = [label_to_ticker[label] for label in selected_labels]

            if selected_tickers:
                selected = deep_scope[deep_scope["Ticker"].astype(str).isin(selected_tickers)].copy()
                deep_dive(selected, style, deep_scope, deep_sector)

st.subheader("What To Study")
for item in style.get("look_for", []):
    st.markdown(f"- {item}")

if style.get("examples"):
    st.subheader("Examples")
    for item in style["examples"]:
        st.markdown(f"- {item}")

if style.get("avoid"):
    st.subheader("Avoid")
    for item in style["avoid"]:
        st.markdown(f"- {item}")

if style.get("warning"):
    st.warning(style["warning"])
