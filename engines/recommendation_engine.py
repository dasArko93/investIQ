import pandas as pd


class RecommendationEngine:
    @staticmethod
    def _series(df, column, default=0):
        if column not in df.columns:
            return pd.Series(default, index=df.index)
        return pd.to_numeric(df[column], errors="coerce").fillna(default)

    @classmethod
    def _normalize(cls, series, inverse=False):
        series = pd.to_numeric(series, errors="coerce").fillna(0)
        if inverse:
            series = series.max() - series
        min_value = series.min()
        max_value = series.max()
        if max_value == min_value:
            return pd.Series(0, index=series.index)
        return ((series - min_value) / (max_value - min_value) * 100).round(2)

    @classmethod
    def score(cls, df):
        work = df.copy()
        revenue_growth = cls._series(work, "5Y Historical Revenue Growth")
        eps_growth = cls._series(work, "5Y CAGR")
        roce = cls._series(work, "ROCE")
        roe = cls._series(work, "ROE")
        debt = cls._series(work, "Debt to Equity", default=999)
        fcf = cls._series(work, "Free Cash Flow")
        pe = cls._series(work, "PE Ratio")
        sector_pe = cls._series(work, "Sector PE")
        peg = cls._series(work, "PEG Ratio")
        dividend_yield = cls._series(work, "Dividend Yield")
        payout_ratio = cls._series(work, "Payout Ratio")

        work["Growth Score"] = (
            cls._normalize(revenue_growth) * 0.35
            + cls._normalize(eps_growth) * 0.35
            + cls._normalize(roce) * 0.20
            + cls._normalize(debt, inverse=True) * 0.10
        ).round(2)
        work["Value Score"] = (
            cls._normalize(sector_pe - pe) * 0.45
            + cls._normalize(fcf) * 0.25
            + cls._normalize(debt, inverse=True) * 0.20
            + cls._normalize(peg, inverse=True) * 0.10
        ).round(2)
        work["Quality Score"] = (
            cls._normalize(roce) * 0.35
            + cls._normalize(roe) * 0.25
            + cls._normalize(fcf) * 0.20
            + cls._normalize(debt, inverse=True) * 0.20
        ).round(2)
        work["Dividend Score"] = (
            cls._normalize(dividend_yield) * 0.35
            + cls._normalize(fcf) * 0.30
            + cls._normalize(debt, inverse=True) * 0.20
            + cls._normalize((payout_ratio >= 30) & (payout_ratio <= 70)) * 0.15
        ).round(2)
        work["Turnaround Score"] = (
            cls._normalize(fcf) * 0.35
            + cls._normalize(revenue_growth) * 0.25
            + cls._normalize(debt, inverse=True) * 0.25
            + cls._normalize(roce) * 0.15
        ).round(2)
        work["Composite Fundamental Score"] = (
            work["Growth Score"] * 0.25
            + work["Value Score"] * 0.20
            + work["Quality Score"] * 0.30
            + work["Dividend Score"] * 0.10
            + work["Turnaround Score"] * 0.15
        ).round(2)
        return work

    @classmethod
    def screen(cls, df):
        if df.empty:
            return df

        work = cls.score(df)
        revenue_growth = cls._series(work, "5Y Historical Revenue Growth")
        eps_growth = cls._series(work, "5Y CAGR")
        roce = cls._series(work, "ROCE")
        roe = cls._series(work, "ROE")
        debt = cls._series(work, "Debt to Equity", default=999)
        fcf = cls._series(work, "Free Cash Flow")
        promoter_holding = cls._series(work, "Promoter Holding")
        peg = cls._series(work, "PEG Ratio")

        screen_mask = (
            (revenue_growth > 15)
            & (eps_growth > 15)
            & (roce > 20)
            & ((roe > 18) if "ROE" in work.columns else True)
            & (debt < 0.5)
            & (fcf > 0)
            & ((promoter_holding > 50) if "Promoter Holding" in work.columns else True)
            & ((peg < 1.5) if "PEG Ratio" in work.columns else True)
        )
        return work[screen_mask].sort_values("Composite Fundamental Score", ascending=False)
