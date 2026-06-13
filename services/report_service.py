from engines.report_engine import (
    ReportEngine
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO


class ReportService:

    @staticmethod
    def generate(

        portfolio,

        health,

        recommendations

    ):

        return (

            ReportEngine

            .generate_summary(

                portfolio,

                health,

                recommendations

            )

        )

    @staticmethod
    def generate_pdf(summary):
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import datetime

        buffer = BytesIO()
        # Set margins to 0.5 inch (36 points) for maximum printable area
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Color Palette
        primary = colors.HexColor("#0f172a") # dark slate
        secondary = colors.HexColor("#1e293b")
        accent = colors.HexColor("#20d3c2") # teal
        text = colors.HexColor("#334155")
        light_bg = colors.HexColor("#f8fafc")
        border_color = colors.HexColor("#cbd5e1")
        green_text = colors.HexColor("#16a34a")
        red_text = colors.HexColor("#dc2626")
        
        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary,
            spaceAfter=2
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=15
        )
        section_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=primary,
            spaceBefore=10,
            spaceAfter=8,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=text,
            spaceAfter=4
        )
        bold_body_style = ParagraphStyle(
            'BoldBodyTextCustom',
            parent=body_style,
            fontName='Helvetica-Bold'
        )
        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=text
        )
        bold_table_cell_style = ParagraphStyle(
            'BoldTableCell',
            parent=table_cell_style,
            fontName='Helvetica-Bold'
        )
        
        story = []
        
        # 1. Branding Header
        story.append(Paragraph("<b>InvestIQ</b> Portfolio Report", title_style))
        timestamp = datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p")
        story.append(Paragraph(f"CONFIDENTIAL | Generated on: {timestamp}", subtitle_style))
        
        # 2. Executive Summary Metrics Block
        p_val = summary.get("portfolio_value", 0.0)
        inv_val = summary.get("invested_value", 0.0)
        pnl = p_val - inv_val
        pnl_pct = (pnl / inv_val * 100) if inv_val > 0 else 0.0
        health = summary.get("portfolio_health", 0.0)
        
        pnl_color = green_text if pnl >= 0 else red_text
        pnl_symbol = "+" if pnl >= 0 else ""
        
        summary_data = [
            [
                Paragraph("<b>Portfolio Value</b>", body_style),
                Paragraph("<b>Invested Capital</b>", body_style),
                Paragraph("<b>Total Return (P&L)</b>", body_style),
                Paragraph("<b>Health Score</b>", body_style)
            ],
            [
                Paragraph(f"₹{p_val:,.2f}", ParagraphStyle('Val1', parent=bold_body_style, fontSize=12, leading=14)),
                Paragraph(f"₹{inv_val:,.2f}", ParagraphStyle('Val2', parent=bold_body_style, fontSize=12, leading=14)),
                Paragraph(f"<font color='{pnl_color}'><b>{pnl_symbol}₹{pnl:,.2f} ({pnl_symbol}{pnl_pct:.2f}%)</b></font>", ParagraphStyle('Val3', parent=bold_body_style, fontSize=12, leading=14)),
                Paragraph(f"<b>{health:.1f}/100</b>", ParagraphStyle('Val4', parent=bold_body_style, fontSize=12, leading=14, textColor=accent))
            ]
        ]
        summary_table = Table(summary_data, colWidths=[135, 135, 150, 120])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), light_bg),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))
        
        # 3. Top Holdings Section
        story.append(Paragraph("Holdings Breakdown", section_style))
        holdings = summary.get("top_holdings", [])
        
        holdings_headers = ["Security", "Quantity", "Avg Cost", "LTP", "Current Value", "Weight %", "Return"]
        holdings_rows = [[Paragraph(h, header_cell_style) for h in holdings_headers]]
        
        for h in holdings:
            sec = h.get("Security", "N/A")
            qty = h.get("Quantity", 0.0)
            avg_c = h.get("Average Cost Rs", 0.0)
            ltp = h.get("LTP Rs", 0.0)
            c_val = h.get("Current Value Rs", 0.0)
            weight = h.get("Portfolio Weight %", 0.0)
            h_pnl = h.get("PnL Rs", 0.0)
            h_pnl_pct = ((c_val - (qty * avg_c)) / (qty * avg_c) * 100) if (qty * avg_c) > 0 else 0.0
            
            pnl_c = "#16a34a" if h_pnl >= 0 else "#dc2626"
            pnl_s = "+" if h_pnl >= 0 else ""
            
            holdings_rows.append([
                Paragraph(f"<b>{sec}</b>", bold_table_cell_style),
                Paragraph(f"{qty:,.0f}" if qty.is_integer() else f"{qty:,.2f}", table_cell_style),
                Paragraph(f"₹{avg_c:,.2f}", table_cell_style),
                Paragraph(f"₹{ltp:,.2f}", table_cell_style),
                Paragraph(f"₹{c_val:,.2f}", bold_table_cell_style),
                Paragraph(f"{weight:.2f}%", table_cell_style),
                Paragraph(f"<font color='{pnl_c}'><b>{pnl_s}₹{h_pnl:,.0f} ({pnl_s}{h_pnl_pct:.1f}%)</b></font>", table_cell_style)
            ])
            
        holdings_table = Table(holdings_rows, colWidths=[90, 50, 70, 70, 90, 60, 110])
        holdings_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(holdings_table)
        story.append(Spacer(1, 10))
        
        # Page Break to keep it neat
        story.append(PageBreak())
        
        # Page 2: Risk Profile, Concentration Risks and Sector Opportunities
        story.append(Paragraph("Risk, Concentration & Diversification Audit", section_style))
        
        # Risk Warnings Table
        warnings = summary.get("concentration_warnings", [])
        if not warnings:
            warnings = ["No significant stock or sector concentration risks detected. Good diversification!"]
            
        warn_paragraphs = []
        for w in warnings:
            warn_paragraphs.append([Paragraph(f"⚠️ {w}", body_style)])
            
        warn_table = Table(warn_paragraphs, colWidths=[540])
        warn_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fffbeb")), # light yellow warning bg
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#fef3c7")),
            ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor("#f59e0b")),
        ]))
        story.append(warn_table)
        story.append(Spacer(1, 10))
        
        # 4. Strategic Investment Ideas from Stock Universe
        story.append(Paragraph("Recommended Allocations & Stock Screen Ideas", section_style))
        story.append(Paragraph(
            "Below are high-quality compounders selected from the Stock Universe based on the criteria: "
            "ROCE > 20%, Debt-to-Equity < 0.5, Growth > 15%, and strong cash flows:",
            body_style
        ))
        
        recs = summary.get("recommendations", [])
        rec_headers = ["Ticker", "Company Name", "Sector", "ROCE %", "D/E Ratio", "5Y CAGR", "Fund. Score"]
        rec_rows = [[Paragraph(h, header_cell_style) for h in rec_headers]]
        
        for r in recs[:8]: # top 8
            ticker = r.get("Ticker", "N/A")
            name = r.get("Name", "N/A")
            sec = r.get("Sub-Sector", "N/A")
            roce = r.get("ROCE", 0.0)
            de = r.get("Debt to Equity", 0.0)
            cagr = r.get("5Y CAGR", 0.0)
            score = r.get("Composite Fundamental Score", 0.0)
            
            rec_rows.append([
                Paragraph(f"<b>{ticker}</b>", bold_table_cell_style),
                Paragraph(name[:25] + "..." if len(name) > 25 else name, table_cell_style),
                Paragraph(sec, table_cell_style),
                Paragraph(f"{roce:.1f}%", table_cell_style),
                Paragraph(f"{de:.2f}", table_cell_style),
                Paragraph(f"{cagr:.1f}%", table_cell_style),
                Paragraph(f"<b>{score:.1f}/100</b>", bold_table_cell_style)
            ])
            
        rec_table = Table(rec_rows, colWidths=[65, 120, 110, 55, 55, 65, 70])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 15))
        
        # Executive Disclaimer
        disclaimer = (
            "<b>Disclaimer:</b> This report is generated automatically by the InvestIQ analytical system based on "
            "user-provided transaction records and stock master data. It is for informational and educational "
            "purposes only and does not constitute formal financial, tax, or investment advice. Investors should "
            "consult with a certified advisor before making capital allocation decisions."
        )
        story.append(Paragraph(disclaimer, ParagraphStyle('Dis', parent=body_style, fontSize=7, leading=9, textColor=colors.HexColor("#94a3b8"))))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
