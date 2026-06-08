class OpportunityEngine:
    @staticmethod
    def find(universe, portfolio):
        if universe.empty:
            return universe

        owned = set(portfolio["Security"]) if not portfolio.empty else set()
        return universe[~universe["Ticker"].isin(owned)].sort_values("QUALITY_SCORE", ascending=False)
