import math
import random
from datetime import datetime
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.dashboard_service import DashboardService
from services.health_service import HealthService
from services.recommendation_service import RecommendationService
from utils.page_utils import load_holdings, load_universe, merged_holdings


def inject_dashboard_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #050912;
            --panel: #0e1624;
            --panel-2: #111b2c;
            --line: rgba(148, 163, 184, 0.15);
            --muted: #94a3b8;
            --text: #eef4ff;
            --blue: #2563eb;
            --cyan: #20d3c2;
            --green: #48d66d;
            --violet: #8b5cf6;
            --amber: #f59e0b;
            --red: #ef4444;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 30% 0%, rgba(37, 99, 235, 0.16), transparent 30%),
                radial-gradient(circle at 80% 20%, rgba(32, 211, 194, 0.09), transparent 24%),
                var(--bg);
            color: var(--text);
            font-family: Inter, sans-serif;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        [data-testid="stSidebar"] {
            background: #060b14;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] * {
            color: #dbeafe;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 1.4rem;
            max-width: 1420px;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(17, 27, 44, 0.96), rgba(12, 18, 30, 0.96));
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 16px 18px;
            min-height: 110px;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.24);
        }

        div[data-testid="stMetric"] label {
            color: var(--muted) !important;
            font-size: 0.75rem !important;
        }

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--text);
            font-size: 1.85rem;
            font-weight: 700;
        }

        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: var(--green);
        }

        .iq-topbar {
            display: grid;
            grid-template-columns: 1fr minmax(320px, 460px) auto;
            gap: 24px;
            align-items: center;
            margin-bottom: 20px;
        }

        .iq-kicker {
            color: var(--muted);
            font-size: 0.86rem;
            margin-top: 5px;
        }

        .iq-title {
            font-size: 1.32rem;
            font-weight: 750;
            letter-spacing: 0;
        }

        .iq-search {
            background: #0c1320;
            border: 1px solid var(--line);
            border-radius: 8px;
            color: #9fb0c8;
            padding: 12px 14px;
            font-size: 0.82rem;
        }

        .iq-avatar {
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: flex-end;
            color: var(--muted);
            font-size: 0.82rem;
        }

        .iq-panel {
            background: linear-gradient(145deg, rgba(17, 27, 44, 0.96), rgba(10, 16, 27, 0.96));
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 18px;
            min-height: 360px !important;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        .iq-panel-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 14px;
        }

        .iq-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--line);
            padding: 10px 0;
            font-size: 0.82rem;
        }

        .iq-row:last-child {
            border-bottom: 0;
        }

        .iq-muted {
            color: var(--muted);
            font-size: 0.72rem;
        }

        .iq-positive {
            color: var(--green);
            font-weight: 650;
        }

        .iq-chip {
            border-radius: 999px;
            padding: 4px 8px;
            background: rgba(37, 99, 235, 0.18);
            color: #9ec5ff;
            font-size: 0.72rem;
            font-weight: 650;
        }

        .iq-alert {
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 9px;
            border: 1px solid var(--line);
            font-size: 0.78rem;
            background: rgba(17, 27, 44, 0.78);
        }

        .iq-alert.red {
            border-color: rgba(239, 68, 68, 0.28);
            background: rgba(239, 68, 68, 0.10);
        }

        .iq-alert.amber {
            border-color: rgba(245, 158, 11, 0.28);
            background: rgba(245, 158, 11, 0.10);
        }

        .iq-alert.green {
            border-color: rgba(72, 214, 109, 0.24);
            background: rgba(72, 214, 109, 0.10);
        }

        .iq-advisor {
            background: linear-gradient(135deg, rgba(91, 33, 182, 0.62), rgba(49, 46, 129, 0.86));
            border: 1px solid rgba(167, 139, 250, 0.28);
            border-radius: 8px;
            padding: 15px;
        }

        .iq-action-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }

        .iq-action {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            min-height: 72px;
        }

        .iq-quick {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            text-align: center;
        }

        .iq-quick-item {
            background: #0d1726;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 18px 8px;
            font-weight: 650;
            font-size: 0.78rem;
        }

        .iq-dot {
            width: 8px;
            height: 8px;
            border-radius: 99px;
            display: inline-block;
            margin-right: 8px;
        }

        [data-testid="stPageLink"] {
            background: transparent;
            border: 0;
            padding: 0;
        }

        [data-testid="stPageLink"] a {
            color: #9ec5ff;
            font-size: 0.76rem;
            padding: 0;
            min-height: 0;
        }

        @media (max-width: 900px) {
            .iq-topbar {
                grid-template-columns: 1fr;
            }
            .iq-action-grid,
            .iq-quick {
                grid-template-columns: 1fr 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def money(value):
    return f"Rs {value:,.0f}"


def percent(value):
    return f"{value:.2f}%"


def demo_portfolio():
    return pd.DataFrame(
        [
            ["HDFC Bank", 10.21, 18.2, 127000, 102000],
            ["Infosys", 9.15, 12.4, 113000, 96000],
            ["ITC", 8.23, 21.7, 102000, 83000],
            ["Tata Motors", 7.48, 32.1, 93000, 68000],
            ["Reliance Ind.", 6.32, 8.7, 78000, 72000],
        ],
        columns=["Security", "Portfolio Weight %", "Gain %", "Current Value Rs", "Invested Value Rs"],
    )


def portfolio_for_display(portfolio):
    if portfolio.empty:
        return portfolio  # Return empty, don't show demo data
    work = portfolio.copy()
    invested = work["Invested Value Rs"].replace(0, pd.NA)
    work["Gain %"] = ((work["Current Value Rs"] - work["Invested Value Rs"]) / invested * 100).fillna(0)
    return work.sort_values("Current Value Rs", ascending=False)


def performance_figure(summary):
    points = 160
    base = max(summary["invested"], 90000)
    end = max(summary["current"], base * 1.18)
    values = []
    benchmark = []
    for i in range(points):
        trend = base + (end - base) * (i / (points - 1))
        wave = math.sin(i / 7) * base * 0.025 + math.sin(i / 17) * base * 0.018
        values.append(trend + wave)
        benchmark.append(base * 0.92 + base * 0.16 * (i / points) + math.sin(i / 9) * base * 0.018)
    # create a date index for the x axis so the chart has meaningful labels
    dates = pd.date_range(end=pd.Timestamp.today(), periods=points)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            name="Your Portfolio",
            line=dict(color="#2f6df6", width=2),
            hovertemplate="Rs %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=benchmark,
            mode="lines",
            name="NIFTY 50",
            line=dict(color="#8b5cf6", width=2),
            hovertemplate="Rs %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        height=360,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=12),
        legend=dict(orientation="h", y=1.02, x=0.02),
        hovermode="x unified",
        xaxis=dict(showgrid=False, tickformat="%b %d", tickangle=-45, nticks=8),
        yaxis=dict(gridcolor="rgba(148,163,184,0.12)", tickprefix="Rs ", separatethousands=True),
    )
    return fig


def allocation_figure(merged):
    if merged.empty or "Sub-Sector" not in merged:
        labels = ["Equity", "Debt", "Cash", "Gold"]
        values = [81.2, 10.3, 6.1, 2.4]
    else:
        sector = merged.groupby("Sub-Sector")["Current Value Rs"].sum().sort_values(ascending=False)
        labels = sector.index[:5].tolist()
        values = sector.iloc[:5].tolist()

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=["#2563eb", "#20d3c2", "#8b5cf6", "#facc15", "#64748b"]),
            textinfo="none",
        )
    )
    fig.update_traces(
        hovertemplate="%{label}: %{percent:.1%}<br>Value: Rs %{value:,.0f}<extra></extra>",
        pull=[0.02 if i == 0 else 0 for i in range(len(labels))],
    )

    fig.update_layout(
        height=320,
        margin=dict(l=8, r=8, t=18, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=12),
        showlegend=True,
        legend=dict(x=0.72, y=0.5),
        annotations=[dict(text="Total", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#94a3b8"))],
    )
    return fig


def health_figure(score):
    values = [85, 88, 75, 90, 80, 72]
    labels = ["Diversification", "Quality", "Momentum", "Liquidity", "Risk", "Valuation"]
    if score:
        values = [min(100, score + 5), min(100, score + 8), max(0, score - 5), min(100, score + 10), score, max(0, score - 8)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            line=dict(color="#20d3c2"),
            fillcolor="rgba(32, 211, 194, 0.22)",
            hovertemplate="%{theta}: %{r}<extra></extra>",
            name="Health",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=12, r=12, t=18, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=12),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(148,163,184,0.16)"),
            angularaxis=dict(gridcolor="rgba(148,163,184,0.16)"),
            domain=dict(x=[0, 1], y=[0, 1]),
        ),
        showlegend=False,
    )
    return fig


def html_panel(title, body):
    html = f'<div class="iq-panel"><div class="iq-panel-title">{escape(str(title))}</div>{body}</div>'
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_rows(items):
    rows = []
    for item in items:
        name = escape(str(item["name"]))
        meta = str(item.get("meta", ""))
        value = escape(str(item["value"]))
        value_class = escape(str(item.get("value_class", "")))
        rows.append(
            '<div class="iq-row">'
            f'<div><div>{name}</div><div class="iq-muted">{meta}</div></div>'
            f'<div class="{value_class}">{value}</div>'
            "</div>"
        )
    return "".join(rows)


def render_investiq_dashboard():
    inject_dashboard_css()

    portfolio = load_holdings()
    universe = load_universe()
    merged = merged_holdings()
    display_portfolio = portfolio_for_display(portfolio)
    summary = DashboardService.summary(display_portfolio)

    avg_quality = merged["QUALITY_SCORE"].fillna(0).mean() if not merged.empty else 78
    sector_count = merged["Sub-Sector"].nunique() if not merged.empty else 6
    health = HealthService.evaluate(portfolio, avg_quality, sector_count) if not portfolio.empty else 87
    total_return = summary["return_pct"]

    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good Morning"
    elif 12 <= hour < 17:
        greeting = "Good Afternoon"
    elif 17 <= hour < 21:
        greeting = "Good Evening"
    else:
        greeting = "Good Night"

    quotes = [
        "Investing is the intersection of economics and psychology.",
        "A diversified portfolio is a free lunch you should always take.",
        "Long-term success is built by small improvements every day.",
        "Markets reward patience and preparation more than timing.",
        "Wealth is created by owning quality assets, not chasing noise.",
    ]
    fan_fact = random.choice(quotes)

    st.markdown(
        f"""
        <div class="iq-topbar">
            <div>
                <div class="iq-title">{greeting}, Arko</div>
                <div class="iq-kicker">{fan_fact}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    c1.metric("Portfolio Value", money(summary["current"]), f"Invested {money(summary['invested'])}")
    c2.metric("Total Returns", money(summary["pnl"]), percent(total_return))
    c3.metric("Portfolio Health", f"{health}/100", "Very Good")

    # Top small charts: show titles only (no surrounding panels)
    top_middle, top_right = st.columns([1, 1])
    with top_middle:
        st.markdown('<div style="margin-bottom:8px;"><div class="iq-panel-title">Asset Allocation</div></div>', unsafe_allow_html=True)
        st.plotly_chart(allocation_figure(merged), use_container_width=True, config={"displayModeBar": True})
        st.page_link("pages/1_Portfolio.py", label="View full allocation ->")
    with top_right:
        st.markdown('<div style="margin-bottom:8px;"><div class="iq-panel-title">Portfolio Health</div></div>', unsafe_allow_html=True)
        st.plotly_chart(health_figure(health), use_container_width=True, config={"displayModeBar": True})
        st.page_link("pages/1_Portfolio.py", label="View detailed analysis ->")

    # Main performance chart below the small panels: show title only, make chart interactive
    st.markdown('<div style="margin-bottom:8px;"><div class="iq-panel-title">Portfolio Performance</div></div>', unsafe_allow_html=True)
    st.plotly_chart(performance_figure(summary), use_container_width=True, config={"displayModeBar": True})

    holdings_col, sector_col, opp_col = st.columns([1.1, 1.25, 1.1])

    top_holdings = display_portfolio.head(5)
    holdings_items = [
        {
            "name": row["Security"],
            "meta": f"{row['Portfolio Weight %']:.2f}%",
            "value": f"+{row.get('Gain %', 0):.1f}%",
            "value_class": "iq-positive",
        }
        for _, row in top_holdings.iterrows()
    ]
    with holdings_col:
        body = '<div class="iq-panel-title">Top Holdings</div>'
        body += '<div style="overflow:auto;flex:1;padding-right:6px;">' + render_rows(holdings_items) + '</div>'
        st.markdown('<div class="iq-panel" style="height:360px;display:flex;flex-direction:column;">' + body + '</div>', unsafe_allow_html=True)

    if not merged.empty and "Sub-Sector" in merged:
        sector_rows = merged.groupby("Sub-Sector")["Current Value Rs"].sum().sort_values(ascending=False).head(5)
        sector_total = sector_rows.sum()
        sector_items = [
            {
                "name": name,
                "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;margin-top:6px;"><div style="height:5px;background:#2563eb;border-radius:999px;width:{:.0f}%"></div></div>'.format(
                    (value / sector_total * 100) if sector_total else 0
                ),
                "value": f"{(value / sector_total * 100) if sector_total else 0:.1f}%",
            }
            for name, value in sector_rows.items()
        ]
    else:
        sector_items = [
            {"name": "Financial Services", "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;"><div style="height:5px;background:#2563eb;border-radius:999px;width:72%"></div></div>', "value": "28.5%"},
            {"name": "Information Technology", "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;"><div style="height:5px;background:#20d3c2;border-radius:999px;width:55%"></div></div>', "value": "19.3%"},
            {"name": "Consumer Goods", "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;"><div style="height:5px;background:#8b5cf6;border-radius:999px;width:44%"></div></div>', "value": "15.6%"},
            {"name": "Automobile", "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;"><div style="height:5px;background:#f59e0b;border-radius:999px;width:34%"></div></div>', "value": "12.2%"},
            {"name": "Energy", "meta": '<div style="height:5px;background:#1f2937;border-radius:999px;"><div style="height:5px;background:#facc15;border-radius:999px;width:28%"></div></div>', "value": "8.7%"},
        ]
    with sector_col:
        body = '<div class="iq-panel-title">Sector Allocation</div>'
        body += '<div style="overflow:auto;flex:1;padding-right:6px;">' + render_rows(sector_items) + '</div>'
        st.markdown('<div class="iq-panel" style="height:360px;display:flex;flex-direction:column;">' + body + '</div>', unsafe_allow_html=True)

    if universe.empty:
        opportunities = pd.DataFrame(
            [
                ["Tata Power", 92, "Strong Buy", 24],
                ["Hindustan Zinc", 88, "Strong Buy", 18],
                ["BPCL", 85, "Buy", 15],
                ["L&T", 82, "Buy", 13],
            ],
            columns=["Name", "QUALITY_SCORE", "Label", "Upside"],
        )
    else:
        opportunities = RecommendationService.generate(universe).sort_values("QUALITY_SCORE", ascending=False).head(4)
        if opportunities.empty:
            opportunities = universe.sort_values("QUALITY_SCORE", ascending=False).head(4)
        opportunities["Label"] = "Buy"
        opportunities["Upside"] = opportunities["QUALITY_SCORE"].clip(0, 100) / 4

    opp_items = [
        {
            "name": row.get("Name", row.get("Ticker")),
            "meta": f"{row.get('Label', 'Buy')} | Score {row.get('QUALITY_SCORE', 0):.0f}",
            "value": f"Upside {row.get('Upside', 0):.0f}%",
            "value_class": "iq-positive",
        }
        for _, row in opportunities.iterrows()
    ]
    with opp_col:
        body = '<div class="iq-panel-title">Top Opportunities</div>'
        body += '<div style="overflow:auto;flex:1;padding-right:6px;">' + render_rows(opp_items) + '</div>'
        st.markdown('<div class="iq-panel" style="height:360px;display:flex;flex-direction:column;">' + body + '</div>', unsafe_allow_html=True)

    # Alerts column removed per user request

    # AI Advisor and quick-action panel removed per user request
