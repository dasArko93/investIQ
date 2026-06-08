from engines.portfolio_health_engine import (
    PortfolioHealthEngine
)


class HealthService:

    @staticmethod
    def evaluate(

        portfolio_df,

        avg_quality,

        sector_count

    ):

        return (

            PortfolioHealthEngine

            .calculate(

                portfolio_df,

                avg_quality,

                sector_count

            )

        )