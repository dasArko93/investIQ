import pandas as pd


class PortfolioMergeService:

    @staticmethod
    def merge(

        portfolio_df,

        universe_df

    ):

        return pd.merge(

            portfolio_df,

            universe_df,

            left_on="Security",

            right_on="Ticker",

            how="left"

        )