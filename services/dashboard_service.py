class DashboardService:
    @staticmethod
    def summary(df):
        invested = df["Invested Value Rs"].sum() if not df.empty else 0
        current = df["Current Value Rs"].sum() if not df.empty else 0
        pnl = current - invested
        return {
            "invested": invested,
            "current": current,
            "pnl": pnl,
            "return_pct": (pnl / invested) * 100 if invested else 0,
        }
