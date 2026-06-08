from engines.quality_score_engine import (
    QualityScoreEngine
)


class RankingService:

    @staticmethod
    def rank(df):

        scored = (
            QualityScoreEngine
            .calculate(df)
        )

        return (

            scored

            .sort_values(

                "QUALITY_SCORE",

                ascending=False

            )

        )