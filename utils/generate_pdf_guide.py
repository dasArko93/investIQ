import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_pdf(filename="static/fundamental_analysis_guide.pdf"):
    # Ensure assets directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#0f172a") # dark blue
    secondary_color = colors.HexColor("#1e293b") # slate
    accent_color = colors.HexColor("#20d3c2") # teal
    text_color = colors.HexColor("#334155")
    bg_light = colors.HexColor("#f8fafc")
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=primary_color,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        leftIndent=15,
        spaceAfter=5
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    )
    
    story = []
    
    # ---------------------------------------------------------
    # COVER PAGE
    # ---------------------------------------------------------
    story.append(Spacer(1, 100))
    story.append(Paragraph("InvestIQ", ParagraphStyle('CoverBrand', parent=title_style, fontSize=16, textColor=accent_color, spaceAfter=10)))
    story.append(Paragraph("Fundamental Analysis & Quant Forecasting Guide", title_style))
    story.append(Paragraph("A Comprehensive Guide to Stock Selection, Valuation Styles, and Quantitative Forecasting Models", subtitle_style))
    story.append(Spacer(1, 150))
    
    metadata_table = Table(
        [
            [Paragraph("<b>Author:</b> InvestIQ Investment Committee", body_style)],
            [Paragraph("<b>Target Audience:</b> Self-Directed Investors & Portfolio Managers", body_style)],
            [Paragraph("<b>Version:</b> 1.1 (2026 Edition)", body_style)],
        ],
        colWidths=[300]
    )
    metadata_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(metadata_table)
    story.append(PageBreak())
    
    # ---------------------------------------------------------
    # SECTION 1: INTRODUCTION TO FUNDAMENTAL ANALYSIS
    # ---------------------------------------------------------
    story.append(Paragraph("1. Introduction to Fundamental Analysis", h1_style))
    story.append(Paragraph(
        "Fundamental analysis is a method of evaluating a security by measuring its intrinsic value. "
        "It involves studying everything from the overall economy and industry conditions to the financial strength and management quality of individual companies.",
        body_style
    ))
    story.append(Paragraph(
        "While traditional fundamental analysis asks: <i>'Is this a good company with a competitive moat?'</i>, "
        "<b>Quant Analytics</b> builds a bridge to statistics, asking: <i>'What is the probability of this stock outperforming over a specific horizon based on historical distributions, volume confirmations, and momentum parameters?'</i>",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    # Callout Box
    callout_data = [[Paragraph("<b>Key Rule of Investing:</b> Never buy a business you do not understand. A stock is not just a ticker symbol; it represents fractional ownership in a real enterprise with revenues, costs, debts, and cash flows.", callout_style)]]
    callout_table = Table(callout_data, colWidths=[490])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINELEFT', (0,0), (-1,-1), 3, accent_color),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 15))
    
    # ---------------------------------------------------------
    # SECTION 2: INVESTMENT STYLES
    # ---------------------------------------------------------
    story.append(Paragraph("2. Selecting Stocks via Investment Styles", h1_style))
    story.append(Paragraph(
        "InvestIQ classifies companies into distinct investing styles based on academic financial research. "
        "Understanding which style fits your risk profile is critical for building a balanced portfolio.",
        body_style
    ))
    
    styles_list = [
        ("Growth Investing", "Focuses on companies showing rapid earnings and revenue expansion (typically >15% CAGR). Investors look for expanding market share, high return on capital (ROE/ROCE), and strong reinvestment opportunities. Valuation ratios (P/E) are often higher because future growth is discounted into the current price."),
        ("Value Investing", "Pioneered by Benjamin Graham, this style seeks stocks trading below their intrinsic value. Key parameters include low Price-to-Earnings (P/E), low Price-to-Book (P/B), and positive free cash flows. The goal is to find companies suffering from temporary market pessimism that offer a 'margin of safety'."),
        ("Quality Compounders", "Refers to businesses with extremely strong competitive moats, high capital returns (ROCE > 20%), low debt, and predictable cash flows. These companies are held long-term to allow compound interest to maximize returns. Typically consumer staples or niche monopolies."),
        ("GARP (Growth at a Reasonable Price)", "Pioneered by Peter Lynch, GARP blends growth and value styles. It targets companies with robust growth prospects but avoids purchasing them at high valuations. The PEG ratio (P/E divided by Growth Rate) is the primary metric, with a PEG < 1.0 being the gold standard."),
        ("Dividend Investing", "Focuses on cash flow generation. Target metrics include stable dividend yields (>3%) and moderate payout ratios (30-70%) supported by positive free cash flows, ensuring dividends are not paid from debt."),
        ("Turnaround Investing", "High-risk, high-reward style focusing on struggling businesses experiencing structural changes (e.g. debt reduction, management change). Quality scores might be low initially, but margin improvements signal potential outsized recovery.")
    ]
    
    for name, desc in styles_list:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", bullet_style))
    story.append(Spacer(1, 10))
    story.append(PageBreak())
    
    # ---------------------------------------------------------
    # SECTION 3: KEY FINANCIAL METRICS REFERENCE TABLE
    # ---------------------------------------------------------
    story.append(Paragraph("3. Core Financial Metrics Reference", h1_style))
    story.append(Paragraph(
        "When filtering stock universes, look for the following threshold benchmarks to separate high-quality prospects from speculative bets:",
        body_style
    ))
    
    metrics_data = [
        ["Metric Group", "Key Metric", "Ideal Benchmark", "Why it Matters"],
        ["Valuation", "P/E Ratio", "Below Sector Avg", "Compares price to earnings. Low relative P/E implies value."],
        ["Valuation", "PEG Ratio", "< 1.5", "P/E ratio divided by growth rate. Standards growth for price paid."],
        ["Valuation", "P/B Ratio", "< 3.0", "Compares price to book value. Used for financial and asset-rich firms."],
        ["Quality", "ROCE", "> 18% - 20%", "Return on Capital Employed. Measures profit efficiency on total capital."],
        ["Quality", "ROE", "> 15%", "Return on Equity. Measures profitability efficiency on shareholder equity."],
        ["Solvency", "Debt to Equity", "< 0.5", "Measures financial leverage. Low debt protects during recessions."],
        ["Growth", "Revenue Growth", "> 15% CAGR", "Top-line revenue growth rate. Drives earnings expansion."],
        ["Cash Flow", "Free Cash Flow", "Positive", "Operating cash minus capital expenditures. Actual cash available."]
    ]
    
    table = Table(metrics_data, colWidths=[90, 85, 100, 215])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,1), (-1,-1), text_color),
    ]))
    story.append(table)
    story.append(Spacer(1, 15))
    
    # ---------------------------------------------------------
    # SECTION 4: THE QUANT FORECASTING ENGINE
    # ---------------------------------------------------------
    story.append(Paragraph("4. InvestIQ Trend & Forecasting Engine", h1_style))
    story.append(Paragraph(
        "The InvestIQ Trend & Forecasting Engine builds a 12-module qualitative and quantitative ensemble around the stock's 365-day historical OHLCV data. "
        "Here is a breakdown of how the engine derives forecast scores and trading signals:",
        body_style
    ))
    
    modules = [
        ("Module 1: Trend Analysis", "Checks the direction of the trend (Strong Uptrend, Uptrend, Sideways, Downtrend, Strong Downtrend) by analyzing the sequential ordering of 20, 50, 100, and 200 DMAs. If 20 > 50 > 100 > 200, a Strong Uptrend is declared."),
        ("Module 2: Momentum Analysis", "Computes price returns over 7, 30, 90, 180, and 365 trading days and measures Relative Strength against Nifty 50, Nifty 500, and peer sector indices to identify true market outperformance."),
        ("Module 3: Volatility Analysis", "Calcules 30D, 90D, and 365D price volatility alongside the Average True Range (ATR) to measure volatility limits and risk levels."),
        ("Module 4: Support & Resistance", "Detects structural price zones where demand (Support) repeatedly bought the stock, and supply (Resistance) repeatedly capped price expansion. These levels are crucial for setting stop-losses and targets."),
        ("Module 5: Trend Strength (ADX)", "Calculates the Average Directional Index (ADX). An ADX > 25 confirms a strong trending regime, preventing investors from trading sideways noise."),
        ("Module 6: Volume Confirmation", "Checks price-volume correlation. Higher volume on up-days indicates institution-backed 'Accumulation'. Higher volume on down-days indicates 'Distribution'."),
        ("Module 7 & 8: Ensemble Forecast & Confidence", "Runs an ensemble models comprising Prophet (Weekly/Yearly seasonality), XGBoost (Autoregressive lag models), LSTM (recurrent decay return tracker), and Linear Regression. The engine runs a historical backtest (Train 335 Days, Test Last 30 Days) to output metrics like MAE, RMSE, and MAPE, showing the exact model accuracy."),
        ("Module 9 & 10: Risk & Interpretation", "Analyzes forecast bias (Bullish, Bearish, Neutral) and compiles a natural language paragraph translating the quantitative outputs into direct actions."),
        ("Module 11 & 12: Composite Scores & Trading Signals", "Constructs a weighted index: Trend Strength (30%), Momentum (20%), Forecast expected returns (25%), Volume confirmation (15%), and Volatility (10%). Signals span STRONG BUY, BUY, HOLD, REDUCE, and SELL.")
    ]
    
    for title, desc in modules:
        story.append(Paragraph(f"<b>{title}:</b> {desc}", bullet_style))
        
    story.append(PageBreak())
    
    # ---------------------------------------------------------
    # SECTION 5: HOW TO PICK A GOOD STOCK
    # ---------------------------------------------------------
    story.append(Paragraph("5. Step-by-Step Guide: How to Pick a Stock", h1_style))
    story.append(Paragraph(
        "To maximize the utility of the InvestIQ portal, follow this systematic workflow when conducting stock research:",
        body_style
    ))
    
    steps = [
        ("Step 1: Set the Investing Style", "Begin by choosing an investing style (e.g., Quality Compounders if you are looking for long-term safe yields, or GARP if you want growth at a fair price). This populates the default metric filters."),
        ("Step 2: Filter the Universe", "Select a Sector or Sub-Sector. Streamlit displays the list of stocks in the universe. Tweak the User Cutoff rules in the interactive grid editor and click 'Filter Stock'. Only stocks matching all parameters will remain."),
        ("Step 3: Conduct Deep Dives", "Select 1 or more stocks from the filtered table. Analyze the Valuation vs. Return quality scatter plots to compare relative valuations. Check the individual metric tables to spot any red flags."),
        ("Step 4: Run the Quant Forecast Engine", "Scroll down to the '365-Day Quant Analytics & Forecasting' section and click 'Download & Run Quant Analytics Engine'. The cache retrieves the stock's historical OHLCV data. The 12-module JSON outputs, the 7-day future forecast boundary channel, and the moving averages chart will render. Check the Backtest Accuracy (Module 8) to know if the model is reliable for that ticker."),
        ("Step 5: Check Portfolio Gaps", "Navigate back to the Portfolio page. Use the Gaps tab to see which sub-sectors are missing from your holdings based on your uploaded universe file. Diversify by adding strong stocks from the missing sectors.")
    ]
    
    for step_title, step_desc in steps:
        story.append(Paragraph(f"<b>{step_title}</b>", h2_style))
        story.append(Paragraph(step_desc, body_style))
        story.append(Spacer(1, 3))
        
    doc.build(story)

if __name__ == "__main__":
    generate_pdf()
