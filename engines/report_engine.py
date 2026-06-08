class ReportEngine:
    @staticmethod
    def generate_summary(portfolio, health, recommendations):
        return {
            "portfolio_value": float(portfolio["Current Value Rs"].sum()) if not portfolio.empty else 0,
            "invested_value": float(portfolio["Invested Value Rs"].sum()) if not portfolio.empty else 0,
            "portfolio_health": health,
            "top_holdings": portfolio.sort_values("Current Value Rs", ascending=False).head(10).to_dict("records")
            if not portfolio.empty
            else [],
            "recommendations": recommendations.head(10).to_dict("records")
            if hasattr(recommendations, "head")
            else recommendations,
        }
