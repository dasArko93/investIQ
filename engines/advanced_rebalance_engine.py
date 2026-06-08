class AdvancedRebalanceEngine:
    TARGET_WEIGHT = 10

    @classmethod
    def rebalance(cls, df):
        if df.empty:
            return []

        total = df["Current Value Rs"].sum()
        if total == 0:
            return []

        actions = []
        for _, row in df.iterrows():
            current_weight = (row["Current Value Rs"] / total) * 100
            if current_weight > cls.TARGET_WEIGHT:
                excess = current_weight - cls.TARGET_WEIGHT
                actions.append(
                    {
                        "Ticker": row["Security"],
                        "Action": "SELL",
                        "Amount": round(total * excess / 100),
                        "Reason": "Position exceeds target weight",
                    }
                )
        return actions
