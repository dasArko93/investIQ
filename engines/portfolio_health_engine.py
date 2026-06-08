class PortfolioHealthEngine:
    @staticmethod
    def calculate(portfolio_df, avg_quality, sector_count):
        if portfolio_df.empty:
            return 0

        diversification = min(len(portfolio_df) * 2, 25)
        concentration = 10 if portfolio_df["Portfolio Weight %"].max() > 25 else 25
        sector_score = min(sector_count * 2, 20)
        quality_score = (avg_quality / 100) * 20
        cash_allocation = 10

        total = diversification + concentration + sector_score + quality_score + cash_allocation
        return round(min(total, 100), 2)
