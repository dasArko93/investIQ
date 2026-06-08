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
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, y, "InvestIQ Portfolio Report")
        y -= 35

        pdf.setFont("Helvetica", 11)
        for label, value in [
            ("Portfolio Value", summary.get("portfolio_value", 0)),
            ("Invested Value", summary.get("invested_value", 0)),
            ("Portfolio Health", summary.get("portfolio_health", 0)),
        ]:
            pdf.drawString(50, y, f"{label}: {value}")
            y -= 20

        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Top Holdings")
        y -= 20
        pdf.setFont("Helvetica", 9)
        for row in summary.get("top_holdings", [])[:10]:
            pdf.drawString(50, y, f"{row.get('Security')} - Rs {row.get('Current Value Rs', 0):,.0f}")
            y -= 16

        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Recommendations")
        y -= 20
        pdf.setFont("Helvetica", 9)
        for row in summary.get("recommendations", [])[:10]:
            pdf.drawString(50, y, f"{row.get('Ticker')} - Quality {row.get('QUALITY_SCORE', 0)}")
            y -= 16

        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()
