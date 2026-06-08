class FilterService:

    @staticmethod
    def quality(df):

        return df[

            df["QUALITY_SCORE"]
            > 70

        ]

    @staticmethod
    def undervalued(df):

        return df[

            df["PE Ratio"]

            <

            df["Sector PE"]

        ]