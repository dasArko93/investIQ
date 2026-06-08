class BuyNextEngine:
    @staticmethod
    def recommend(universe, portfolio, cash):
        if universe.empty or cash <= 0:
            return []

        owned = set(portfolio["Security"]) if not portfolio.empty else set()
        candidates = universe[~universe["Ticker"].isin(owned)]
        candidates = candidates.sort_values("QUALITY_SCORE", ascending=False).head(5)
        if candidates.empty:
            return []

        allocation = cash / len(candidates)
        return [
            {
                "Ticker": row["Ticker"],
                "Name": row["Name"],
                "Quality Score": row["QUALITY_SCORE"],
                "Allocation Amount": round(allocation),
            }
            for _, row in candidates.iterrows()
        ]
