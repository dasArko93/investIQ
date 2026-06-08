class CapitalAllocationEngine:
    @staticmethod
    def allocate(cash, opportunities, missing_sectors):
        if cash <= 0 or opportunities.empty:
            return []

        candidates = opportunities
        if missing_sectors and "Sub-Sector" in candidates:
            sector_candidates = candidates[candidates["Sub-Sector"].isin(missing_sectors)]
            if not sector_candidates.empty:
                candidates = sector_candidates

        candidates = candidates.sort_values("QUALITY_SCORE", ascending=False).head(5)
        amount = cash / len(candidates)
        return [
            {
                "Ticker": row["Ticker"],
                "Sub-Sector": row.get("Sub-Sector"),
                "Allocation Amount": round(amount),
            }
            for _, row in candidates.iterrows()
        ]
