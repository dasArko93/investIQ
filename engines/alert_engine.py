class AlertEngine:
    @staticmethod
    def check(stock):
        return {
            "quality_above_80": stock.get("QUALITY_SCORE", 0) > 80,
            "roce_above_15": stock.get("ROCE", 0) > 15,
            "low_debt": stock.get("Debt to Equity", 0) < 0.5,
            "pe_below_sector": stock.get("PE Ratio", 0) < stock.get("Sector PE", 0),
        }
