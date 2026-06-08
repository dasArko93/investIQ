from engines.recommendation_engine import (
    RecommendationEngine
)


class RecommendationService:

    @staticmethod
    def generate(df):

        return (

            RecommendationEngine
            .screen(df)

        )