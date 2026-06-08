class RecommendationEngine:
    @staticmethod
    def screen(df):
        if df.empty:
            return df

        return df[
            (df["ROCE"] > 15)
            & (df["5Y CAGR"] > 15)
            & (df["5Y Historical Revenue Growth"] > 10)
            & (df["Debt to Equity"] < 0.5)
            & (df["PE Ratio"] < df["Sector PE"])
            & (df["Free Cash Flow"] > 0)
        ]
