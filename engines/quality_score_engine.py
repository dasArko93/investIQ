import pandas as pd

from utils.data_utils import number


class QualityScoreEngine:
    WEIGHTS = {
        "roce": 25,
        "cagr": 20,
        "revenue": 15,
        "valuation": 15,
        "debt": 10,
        "fcf": 5,
        "sharpe": 5,
        "alpha": 5,
    }

    @staticmethod
    def normalize(series):
        series = pd.to_numeric(series, errors="coerce").fillna(0)
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0, index=series.index)
        return (series - min_val) / (max_val - min_val)

    @classmethod
    def calculate(cls, df):
        work = df.copy()
        for column in [
            "ROCE",
            "5Y CAGR",
            "5Y Historical Revenue Growth",
            "Sector PE",
            "PE Ratio",
            "Debt to Equity",
            "Free Cash Flow",
            "Sharpe Ratio",
            "Alpha",
        ]:
            if column not in work:
                if column == "ROCE" and "Return on Equity" in work:
                    work["ROCE"] = work["Return on Equity"]
                else:
                    work[column] = 0
            work[column] = work[column].apply(number)

        score = pd.Series(0.0, index=work.index)
        score += cls.normalize(work["ROCE"]) * cls.WEIGHTS["roce"]
        score += cls.normalize(work["5Y CAGR"]) * cls.WEIGHTS["cagr"]
        score += cls.normalize(work["5Y Historical Revenue Growth"]) * cls.WEIGHTS["revenue"]
        score += cls.normalize(work["Sector PE"] - work["PE Ratio"]) * cls.WEIGHTS["valuation"]
        score += cls.normalize(work["Debt to Equity"].max() - work["Debt to Equity"]) * cls.WEIGHTS["debt"]
        score += cls.normalize(work["Free Cash Flow"]) * cls.WEIGHTS["fcf"]
        score += cls.normalize(work["Sharpe Ratio"]) * cls.WEIGHTS["sharpe"]
        score += cls.normalize(work["Alpha"]) * cls.WEIGHTS["alpha"]

        work["QUALITY_SCORE"] = score.round(2)
        return work
